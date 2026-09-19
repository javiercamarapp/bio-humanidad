"""Pipeline offline de preparación. No descubre, valida ciencia ni publica alertas."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

from bio import evaluacion, extractor, radar

MAX_BYTES = 10_000_000
MAX_REGISTROS = 5000


def leer_acotado(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError('entrada ausente o enlace simbólico: ' + str(path))
    with path.open('rb') as f:
        raw = f.read(MAX_BYTES + 1)
    if not raw.strip() or len(raw) > MAX_BYTES:
        raise ValueError('entrada vacía o superior a 10 MB')
    return raw


def escribir_json(path: Path, data):
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def jsonl(data: list[dict]) -> str:
    return ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n' for row in data)


def ejecutar(entrada: Path, salida: Path, corte: date, *, dorado: Path | None = None,
             cantidad: int = 50) -> dict:
    inicio = time.monotonic()
    if salida.exists() or salida.is_symlink():
        raise FileExistsError('la carpeta de salida debe ser nueva: ' + str(salida))
    raw = leer_acotado(entrada)
    parsed = radar.parsear_jsonl(raw.decode('utf-8'))
    if not parsed or len(parsed) > MAX_REGISTROS:
        raise ValueError('se requieren de 1 a 5000 señales únicas')
    # No propagar campos de aprobación ni anotaciones aportadas por una fuente.
    fields = ('id', 'fuente', 'fecha', 'claim_literal', 'url', 'recolectado_en')
    signals = [{key: row[key] for key in fields} for row in parsed]
    if type(cantidad) is not int or not 1 <= cantidad <= len(signals):
        raise ValueError(f'muestra solicitada: {cantidad}; disponibles: {len(signals)}')
    predictions = extractor.extraer_lote(signals)
    detection = radar.detectar(signals, corte)
    gold_hash = None
    if dorado is not None and (dorado.exists() or dorado.is_symlink()):
        gold_raw = leer_acotado(dorado)
        reference = [json.loads(line) for line in gold_raw.decode('utf-8').splitlines() if line.strip()]
        metrics = evaluacion.evaluar(reference, predictions)
        gold_hash = hashlib.sha256(gold_raw).hexdigest()
    else:
        metrics = dict(version=1, estado='PENDIENTE_DORADO', publicable=False,
                       total_referencia=0, exactitud_global=None, exactitud_selectiva=None,
                       cobertura=None, motivo='sin etiquetas humanas no se mide exactitud',
                       limitaciones=['Las predicciones automáticas no son un conjunto dorado.'])
    # Preparación completa != validación científica. El manifiesto se escribe al final.
    # mkdir exclusivo reserva el nombre; un crash deja una carpeta sin manifiesto final.
    salida.mkdir(parents=True, exist_ok=False)
    (salida / 'entrada.jsonl').write_bytes(raw)
    (salida / 'normalizadas.jsonl').write_text(jsonl(signals), encoding='utf-8')
    (salida / 'predicciones.jsonl').write_text(jsonl(predictions), encoding='utf-8')
    escribir_json(salida / 'deteccion.json', detection)
    escribir_json(salida / 'metricas.json', metrics)
    sample = radar.preparar(signals, salida / 'revision', cantidad=cantidad)
    summary = Counter(p['categoria_predicha'] or 'abstencion' for p in predictions)
    report = '\n'.join([
        '# Reporte local de preparación', '',
        '**No publicable: no es un hallazgo ni una alerta sanitaria.**', '',
        f'- Señales únicas: {len(signals)}.',
        f'- Categorías sugeridas automáticamente: {sum(not p["abstencion"] for p in predictions)}.',
        f'- Abstenciones del extractor de referencia: {summary["abstencion"]}.',
        f'- Estado del detector léxico: `{detection["estado"]}`.',
        f'- Estado de evaluación: `{metrics["estado"]}`.',
        f'- Muestra para revisión humana: {sample["muestra"]}; etiquetas humanas generadas: 0.',
        '', '## Límites',
        '- Clasificación por reglas de palabras, no IA ni interpretación del contenido de fuentes.',
        '- Una coincidencia no demuestra un brote, peligrosidad o veracidad de un titular.',
        '- Abstención por ambigüedad o falta de coincidencias; no se inventa confianza.',
        '- Sin 90 días observados por fuente, el radar no presenta novedades como anomalías.',
        '- Las fuentes no se consultaron; no hay refutación ni aprobación de publicación.',
        '- El costo monetario y la latencia de modelos no se midieron: no se usaron modelos.',
        '', '## Siguiente intervención humana',
        'Revisar `revision/revision.csv` contra `revision/muestra.jsonl`. Los campos de',
        'categoría, severidad, revisor, fecha y origen humano están vacíos deliberadamente.',
        'No copiar las sugerencias automáticas como si fueran etiquetas revisadas.', '',
    ])
    (salida / 'informe.md').write_text(report, encoding='utf-8')
    paths = sorted(path for path in salida.rglob('*') if path.is_file())
    code_paths = [Path(__file__), Path(radar.__file__), Path(extractor.__file__), Path(evaluacion.__file__)]
    manifest = dict(version=1, estado='PREPARACION_COMPLETA', estado_validacion=metrics['estado'],
                    publicable=False, senales=len(signals), predicciones=len(predictions),
                    categorias=dict(sorted(summary.items())), muestra=cantidad,
                    etiquetas_humanas_generadas=0, estado_detector=detection['estado'],
                    entrada_sha256=hashlib.sha256(raw).hexdigest(), dorado_sha256=gold_hash,
                    entrada_normalizada_sha256=radar.digest(signals),
                    corte_exclusivo_utc=corte.isoformat(), reglas=extractor.ORIGEN,
                    codigo_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in code_paths},
                    artefactos_sha256={str(p.relative_to(salida)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                    llamadas_red=0, llamadas_modelo=0, gasto_api_usd=0,
                    creado_en=datetime.now(timezone.utc).isoformat(),
                    duracion_segundos=round(time.monotonic() - inicio, 6))
    escribir_json(salida / 'manifest.json', manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', type=Path, default=Path('datos/senales/senales.jsonl'))
    parser.add_argument('--salida', type=Path, required=True, help='carpeta nueva; no se sobrescribe')
    parser.add_argument('--corte', type=date.fromisoformat, required=True, help='fecha UTC exclusiva YYYY-MM-DD')
    parser.add_argument('--dorado', type=Path, default=Path('datos/dorado/senales.jsonl'))
    parser.add_argument('--cantidad', type=int, default=50)
    args = parser.parse_args()
    try:
        result = ejecutar(**vars(args))
    except (OSError, ValueError, TypeError) as exc:
        print('error de preparación: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps({key: result[key] for key in ('estado', 'estado_validacion', 'estado_detector',
                                                   'publicable', 'senales', 'predicciones')}, ensure_ascii=False))
    # 0 certifica entrega de preparación, NUNCA calidad científica ni publicación.
    return 0


if __name__ == '__main__':
    sys.exit(main())
