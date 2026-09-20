"""Flujo local opt-in de metadatos: clasificación y crítica documental, nunca ciencia validada."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
import signal
import sys

from bio import evaluacion, ollama_local, radar
from bio.json_estricto import cargar
from bio.preparacion import escribir_json, jsonl
from bio.vigilar import RAIZ, Reloj, huellas_codigo, leer, ruta_segura

CAMPOS = ('id', 'fuente', 'fecha', 'url', 'claim_literal', 'recolectado_en')


def ejecutar(entrada, salida, *, extractor, analista, refutador, puerto=11434,
             cantidad=3, max_segundos=600, dorado=None, corte=None):
    if type(cantidad) is not int or not 1 <= cantidad <= 50:
        raise ValueError('cantidad entre1 y50')
    if type(max_segundos) not in (int, float) or not math.isfinite(max_segundos) or not 1 <= max_segundos <= 3600:
        raise ValueError('presupuesto entre1 y3600s')
    clock = Reloj();codigo = huellas_codigo()
    salida = ruta_segura(salida)
    if salida.exists() or salida.is_symlink(): raise FileExistsError('salida debe ser nueva')
    if salida.is_relative_to(RAIZ):
        parts = salida.relative_to(RAIZ).parts
        if len(parts) < 3 or parts[:2] != ('salidas','modelos'):
            raise ValueError('dentro del repo usar salidas/modelos/NOMBRE')
    raw = leer(entrada)
    parsed = radar.parsear_jsonl(raw.decode('utf-8'))
    if not parsed or len(parsed) > 5000 or cantidad > len(parsed): raise ValueError('cantidad de señales incompatible')
    signals = [{k: r[k] for k in CAMPOS} for r in parsed]
    if any(len(s['claim_literal']) > 4096 for s in signals): raise ValueError('titular excesivo')
    # Selección determinista explícita, sin fingir que se procesó el corpus completo.
    selected = sorted(signals, key=lambda s: s['id'])[:cantidad]
    reference = None;gold_raw = None
    if dorado is not None:
        gold_raw = leer(dorado)
        reference = [cargar(line) for line in gold_raw.decode('utf-8').splitlines() if line.strip()]
        evaluacion._validar_dorado(reference)
    def detener():
        if (salida/'STOP').exists() or (salida/'STOP').is_symlink(): return True
        if clock.segundos() >= max_segundos or clock.retrocedio: raise TimeoutError('presupuesto global agotado')
        return False
    def guard():
        if detener(): raise InterruptedError('STOP solicitado')
    def coherencia():
        guard()
        if huellas_codigo() != codigo: raise ValueError('código cambió; salida no finalizada')
        guard()
    client = ollama_local.Cliente(puerto, detener)
    identities = {}
    for role, name in [('extractor',extractor),('analista',analista),('refutador',refutador)]:
        guard()
        identities[role] = client.identidad(name, timeout=min(15,max_segundos-clock.segundos()))
    if (identities['analista']['sha256_modelo'] == identities['refutador']['sha256_modelo']
            or identities['analista']['familia'] == identities['refutador']['familia']):
        raise ValueError('analista/refutador requieren digest y familia diferentes')
    coherencia()
    salida.mkdir(parents=True, exist_ok=False)
    manifest_path = salida/'manifest.json'
    try:
        (salida/'entrada.jsonl').write_bytes(raw)
        (salida/'seleccion.jsonl').write_text(jsonl(selected),encoding='utf-8')
        if gold_raw is not None:(salida/'dorado-snapshot.jsonl').write_bytes(gold_raw)
        escribir_json(salida/'config.json',dict(modelos=identities, cantidad=cantidad,
            max_segundos=max_segundos, puerto_local=puerto, codigo_sha256=codigo, publicable=False))
        predictions=[];records=[]
        for index, s in enumerate(selected):
            context={}
            for role in ('extractor','analista','refutador'):
                coherencia()
                remaining=max_segundos-clock.segundos()
                result=client.inferir(role,s,identities[role],contexto=context,
                                     timeout=min(180,remaining),detener=detener)
                guard()
                escribir_json(salida/f'{index:03d}-{role}.json',dict(id=s['id'],
                    sha256_senal=evaluacion.huella_senal(s),**result))
                context[role]=result['datos']
                if role=='extractor':
                    category=result['datos']['categoria'];cita=result['datos']['cita']
                    start=s['claim_literal'].find(cita) if cita else 0
                    predictions.append(dict(version=1,id=s['id'],sha256_senal=evaluacion.huella_senal(s),
                        origen_prediccion='ollama_v1',**identities[role],categoria_predicha=category,
                        abstencion=category is None,verificado=False,publicable=False,
                        motivo='abstencion_modelo' if category is None else 'propuesta_modelo',
                        evidencia=[] if not cita else [dict(texto=cita,inicio=start,fin=start+len(cita))]))
            records.append(dict(id=s['id'],sha256_senal=evaluacion.huella_senal(s),
                estado='PENDIENTE_HUMANO',publicable=False,verificado=False,**context))
        coherencia()
        metrics=(evaluacion.evaluar(reference,predictions,origen_esperado='ollama_v1') if reference is not None
                 else dict(estado='PENDIENTE_DORADO',publicable=False,total_referencia=0,
                           exactitud_global=None,cobertura=None,motivo='sin etiquetas humanas reales'))
        corte=corte or (datetime.now(timezone.utc).date()+timedelta(days=1))
        detection=radar.detectar(signals,corte)
        (salida/'predicciones.jsonl').write_text(jsonl(predictions),encoding='utf-8')
        (salida/'revision-documental.jsonl').write_text(jsonl(records),encoding='utf-8')
        escribir_json(salida/'metricas.json',metrics)
        escribir_json(salida/'deteccion.json',detection)
        # Paquete ciego nuevo, sin copiar sugerencias ni modificar revisiones anteriores.
        radar.preparar(signals,salida/'revision',cantidad=min(50,len(signals)))
        (salida/'informe.md').write_text('\n'.join([
            '# Pipeline local de metadatos','', '**NO PUBLICABLE. No valida ciencia ni genera alertas.**','',
            f'- Corpus: {len(signals)}; registros procesados por modelos: {len(records)}.',
            f'- Solicitudes de inferencia: {client.solicitudes}; secuenciales, keep_alive:0.',
            f'- Evaluación: {metrics["estado"]}; detector: {detection["estado"]}.',
            '- Análisis/refutación solo documentales; no verifican fuentes completas ni hipótesis.',
            '- Familias diferentes reducen una dependencia, no prueban independencia de errores.',
            '- Ningún dictamen automático habilita importación humana o publicación.',
            '- Evidencia literal y esquema válido no garantizan clasificación correcta.',
            '- Sin dorado no se mide calidad; las filas no seleccionadas no fueron procesadas.',
            '- Si el servidor falla/cambia o vence el plazo, no se finaliza el manifiesto.',
            '- Los datos y modelos locales no se suben a Git ni a APIs externas.',
        ]),encoding='utf-8')
        coherencia()
        paths=sorted(p for p in salida.rglob('*') if p.is_file())
        manifest=dict(version=1,estado='PIPELINE_LOCAL_COMPLETO',publicable=False,
            estado_validacion=metrics['estado'],estado_detector=detection['estado'],
            corpus=len(signals),procesadas=len(records),modelos=identities,
            solicitudes_inferencia=client.solicitudes,etiquetas_humanas_generadas=0,gasto_api_usd=0,
            origen_predicciones='ollama_v1',codigo_sha256=codigo,
            entrada_sha256=hashlib.sha256(raw).hexdigest(),
            dorado_sha256=hashlib.sha256(gold_raw).hexdigest() if gold_raw is not None else None,
            artefactos_sha256={str(p.relative_to(salida)):hashlib.sha256(leer(p)).hexdigest() for p in paths},
            creado_en=datetime.now(timezone.utc).isoformat(),duracion_segundos=clock.segundos())
        coherencia();escribir_json(manifest_path,manifest);guard()
        escribir_json(salida/'estado.json',dict(estado='COMPLETO',publicable=False,solicitudes_inferencia=client.solicitudes))
        coherencia()
        return manifest
    except BaseException as exc:
        # Nuestro directorio nuevo conserva evidencia, pero nunca un manifiesto de éxito tardío.
        if manifest_path.exists():manifest_path.rename(salida/'manifest-no-finalizado.json')
        state=salida/'estado.json'
        if state.exists():state.rename(salida/'estado-no-finalizado.json')
        try:escribir_json(state,dict(estado='ERROR',publicable=False,error=type(exc).__name__,
                                   detalle=str(exc)[:300],solicitudes_inferencia=client.solicitudes))
        except OSError:pass
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada',type=Path,required=True)
    parser.add_argument('--salida',type=Path,required=True)
    for role in ('extractor','analista','refutador'):parser.add_argument('--'+role,required=True)
    parser.add_argument('--puerto',type=int,default=11434)
    parser.add_argument('--cantidad',type=int,default=3)
    parser.add_argument('--max-segundos',type=float,default=600)
    parser.add_argument('--dorado',type=Path)
    def interrumpir(*_):raise InterruptedError('señal recibida')
    signal.signal(signal.SIGTERM,interrumpir)
    try:
        result=ejecutar(**vars(parser.parse_args()))
    except (OSError,ValueError,TypeError,KeyboardInterrupt) as exc:
        print('pipeline no finalizado: '+str(exc),file=sys.stderr);return 2
    print(json.dumps({k:result[k] for k in ('estado','estado_validacion','publicable','procesadas','solicitudes_inferencia')}))
    return 0


if __name__=='__main__':sys.exit(main())
