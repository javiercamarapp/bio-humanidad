"""Vigilancia operativa acotada: recolección pública y preparación offline.

No investiga, usa modelos ni publica. No hay reanudación ni daemon interno;
un supervisor externo puede lanzar una corrida nueva. estado.json es metadata,
no prueba de vida: su PID puede ser obsoleto o reutilizado. Nunca usarlo para
matar procesos. STOP es una parada operativa, nunca un descubrimiento.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import threading
import time

from bio.bucle import json_atomico, sin_enlaces
from bio.radar import parsear_jsonl
from bio.json_estricto import cargar

RAIZ = Path(__file__).resolve().parent.parent
MAX_BYTES = 10_000_000


def ruta_segura(path):
    # No resolve(): ocultaría enlaces aportados por el usuario.
    if '..' in Path(path).parts:
        raise ValueError('no se permiten componentes ..')
    path = Path(os.path.abspath(path))
    sin_enlaces(path, Path(path.anchor))
    return path


def leer(path):
    path = ruta_segura(path)
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('la entrada debe ser un archivo regular')
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('entrada superior a 10 MB')
    return raw


def huellas_codigo():
    return {str(p.relative_to(RAIZ)): hashlib.sha256(leer(p)).hexdigest()
            for p in sorted((RAIZ / 'bio').rglob('*.py'))}


def corte_utc():
    # Incluye el día actual incompleto; no afirma cobertura diaria exhaustiva.
    return (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()


def limites(max_vueltas, intervalo_segundos, max_segundos, sin_red):
    if type(max_vueltas) is not int or not 1 <= max_vueltas <= 24:
        raise ValueError('max_vueltas debe ser entero entre 1 y 24')
    for name, value, cap in [('intervalo_segundos', intervalo_segundos, 86400),
                             ('max_segundos', max_segundos, 86400)]:
        if type(value) not in (int, float) or not math.isfinite(value) or not 1 <= value <= cap:
            raise ValueError(name + ' debe ser finito entre 1 y 86400')
    if type(sin_red) is not bool:
        raise ValueError('sin_red debe ser booleano')


class Reloj:
    """Presupuesto conservador: incluye suspensión y nunca devuelve tiempo gastado.

    monotonic() puede excluir la suspensión en macOS. El civil puede saltar:
    un avance consume presupuesto; un retroceso observado exige parar.
    """
    def __init__(self):
        self.inicio_mono = time.monotonic()
        self.inicio_civil = self.ultimo_civil = time.time()
        self.transcurrido = 0.0
        self.retrocedio = False

    def segundos(self):
        civil = time.time()
        self.retrocedio |= civil < self.ultimo_civil
        self.ultimo_civil = civil
        self.transcurrido = max(self.transcurrido,
                               time.monotonic() - self.inicio_mono,
                               civil - self.inicio_civil)
        return self.transcurrido


def subproceso(modulo, argumentos, timeout, detener):
    """Solo termina el hijo creado aquí; observa STOP y señales cada <=1s."""
    reloj = Reloj()
    command = [sys.executable, '-m', modulo] + argumentos
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    with subprocess.Popen(command, cwd=str(RAIZ), env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, errors='replace') as child:
        motivo = None
        try:
            while True:
                motivo = detener()
                remaining = timeout - reloj.segundos()
                if reloj.retrocedio:
                    motivo = motivo or 'RELOJ_RETROCEDIO'
                if motivo or remaining <= 0:
                    motivo = motivo or 'TIMEOUT'
                    child.kill()
                    stdout, stderr = child.communicate()
                    break
                try:
                    stdout, stderr = child.communicate(timeout=min(1, remaining))
                    motivo = detener()
                    transcurrido = reloj.segundos()
                    if reloj.retrocedio:
                        motivo = motivo or 'RELOJ_RETROCEDIO'
                    if transcurrido >= timeout:
                        motivo = motivo or 'TIMEOUT'
                    break
                except subprocess.TimeoutExpired:
                    continue
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()
        return dict(modulo=modulo, codigo=child.returncode, stdout=stdout,
                    stderr=stderr, interrupcion=motivo,
                    timeout_segundos=timeout, publicable=False)


def ejecutar(salida, *, entrada=None, sin_red=False, max_vueltas=24,
             intervalo_segundos=3600, max_segundos=86400):
    limites(max_vueltas, intervalo_segundos, max_segundos, sin_red)
    if sin_red and entrada is None:
        raise ValueError('--sin-red requiere --entrada')
    if not sin_red and entrada is not None:
        raise ValueError('--entrada solo se permite con --sin-red')
    reloj = Reloj()
    run = ruta_segura(salida)
    if run.is_relative_to(RAIZ) and not run.is_relative_to(RAIZ / 'salidas/vigilancia'):
        raise ValueError('dentro del proyecto use salidas/vigilancia/NOMBRE')
    if run == RAIZ / 'salidas/vigilancia':
        raise ValueError('se requiere nombre de corrida')
    if run.exists():
        raise FileExistsError('salida debe ser nueva')
    origen = ruta_segura(entrada) if entrada is not None else None
    run.mkdir(parents=True, exist_ok=False)
    datos = run / 'titulares.jsonl'
    evento = threading.Event()
    senales = []
    anteriores = {}
    state = dict(pid=os.getpid(), estado='EN_CURSO', motivo_final=None, vueltas=0,
                 informes=[], errores=0, errores_consecutivos=0,
                 red_habilitada=not sin_red, publicable=False, gasto_api_usd=0,
                 reanudacion_soportada=False, proceso_activo=True)
    motivo = 'ERROR'
    record = None
    entrega_pendiente = False
    previous_key = None
    codigo_inicial = huellas_codigo()
    state['codigo_sha256'] = codigo_inicial

    def guardar(estado):
        state.update(estado=estado, heartbeat=datetime.now(timezone.utc).isoformat(),
                     segundos_transcurridos=reloj.segundos())
        ruta_segura(run / 'estado.json')
        json_atomico(run / 'estado.json', state)

    def descartar_entrega_por_error(reason):
        if entrega_pendiente and record and 'informe' in record:
            informe_pendiente = record.pop('informe')
            if informe_pendiente in state['informes']:
                state['informes'].remove(informe_pendiente)
            record.update(estado=reason, error=True,
                          detalle='falló la persistencia de la entrega; no está confirmada')
            json_atomico(ciclo / 'registro.json', record)

    def detener():
        if evento.is_set():
            return senales[-1] if senales else 'INTERRUPCION'
        if os.path.lexists(str(run / 'STOP')):
            return 'STOP'
        transcurrido = reloj.segundos()
        if reloj.retrocedio:
            return 'RELOJ_RETROCEDIO'
        if transcurrido >= max_segundos:
            return 'PRESUPUESTO'
        return None

    def marcar(signum, frame):
        senales.append(signal.Signals(signum).name)
        evento.set()

    def comprobar_codigo():
        if huellas_codigo() != codigo_inicial:
            senales.append('CODIGO_CAMBIO')
            evento.set()
            return False
        return True

    def lanzar(modulo, args, record):
        if not comprobar_codigo():
            record.update(estado='CODIGO_CAMBIO', error=True)
            return False
        reason = detener()
        if reason:
            record['estado'] = reason
            return False
        restante = min(300, max_segundos - reloj.segundos())
        reason = detener()
        if reason or restante <= 0:
            record['estado'] = reason or 'PRESUPUESTO'
            return False
        result = subproceso(modulo, args, restante, detener)
        record['procesos'].append(result)
        comprobar_codigo()
        reason = detener() or result['interrupcion']
        if reason or result['codigo'] != 0:
            record['estado'] = reason or ('RECOLECCION_PARCIAL' if result['codigo'] == 2
                                         and modulo.endswith('recolector') else 'ERROR_SUBPROCESO')
            record['error'] = reason not in {'STOP', 'SIGTERM', 'SIGINT', 'INTERRUPCION'}
            return False
        return True

    try:
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM, signal.SIGINT):
                anteriores[sig] = signal.signal(sig, marcar)
        guardar('EN_CURSO')
        if origen is not None:
            raw = leer(origen)
            with datos.open('xb') as stream:
                stream.write(raw)
        while state['vueltas'] < max_vueltas:
            motivo = detener()
            if motivo:
                break
            state.pop('siguiente_lectura', None)
            guardar('EN_CURSO')
            numero = state['vueltas'] + 1
            ciclo = run / ('ciclo-%03d' % numero)
            ciclo.mkdir()
            record = dict(numero=numero, estado='ERROR', procesos=[], error=False,
                          publicable=False, gasto_api_usd=0)
            try:
                ruta_segura(datos)
                recolectado = sin_red or lanzar('bio.recolector.recolector',
                                                ['--salida', str(datos)], record)
                if recolectado:
                    raw = leer(datos)
                    digest = hashlib.sha256(raw).hexdigest()
                    corte = corte_utc()
                    key = (digest, corte)
                    record.update(sha256=digest, corte_exclusivo_utc=corte)
                    if not comprobar_codigo():
                        record.update(estado='CODIGO_CAMBIO', error=True)
                    elif key == previous_key:
                        record['estado'] = 'SIN_CAMBIOS'
                    else:
                        rows = parsear_jsonl(raw.decode('utf-8'))
                        record['unicos'] = len(rows)
                        if len(rows) < 50:
                            record['estado'] = 'MUESTRA_INSUFICIENTE'
                            previous_key = key
                        else:
                            snapshot = ciclo / 'entrada.jsonl'
                            with snapshot.open('xb') as stream:
                                stream.write(raw)
                            ausente = run / 'dorado-ausente.jsonl'
                            if os.path.lexists(str(ausente)):
                                raise ValueError('dorado de corrida debe permanecer ausente')
                            informe = ciclo / 'preparacion'
                            if lanzar('bio.preparacion', ['--entrada', str(snapshot), '--salida',
                                    str(informe), '--corte', corte,
                                    '--cantidad', '50', '--dorado', str(ausente)], record):
                                manifest = cargar(leer(informe / 'manifest.json'))
                                if (not isinstance(manifest, dict) or manifest.get('publicable') is not False or
                                        manifest.get('entrada_sha256') != digest or
                                        manifest.get('estado') != 'PREPARACION_COMPLETA'):
                                    raise ValueError('manifiesto inválido')
                                record['estado'] = 'PREPARACION_COMPLETA'
                                record['informe'] = str(informe.relative_to(run))
                                entrega_pendiente = True
                                previous_key = key
                reason = detener()
                if reason:
                    record['estado'] = reason
                    record.pop('informe', None)  # Nunca aceptar una entrega tardía.
            except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
                record.update(estado='ERROR', error=True, detalle=str(exc))
            except KeyboardInterrupt:
                evento.set()
                record['estado'] = 'INTERRUPCION'
            except Exception as exc:
                # Un defecto inesperado del padre no es éxito ni se reintenta.
                record.update(estado='ERROR_INESPERADO', error=True,
                              detalle=type(exc).__name__ + ': ' + str(exc))
                record.pop('informe', None)
                senales.append('ERROR_INESPERADO')
                evento.set()
            finally:
                json_atomico(ciclo / 'registro.json', record)
                # Persistir también consume presupuesto (incluye suspensión en I/O).
                reason = detener()
                if reason:
                    record['estado'] = reason
                    record.pop('informe', None)
                    json_atomico(ciclo / 'registro.json', record)
                state['vueltas'] += 1
                state['errores'] += int(record['error'])
                state['errores_consecutivos'] = state['errores_consecutivos'] + 1 if record['error'] else 0
                if 'informe' in record:
                    state['informes'].append(record['informe'])
                guardar('EN_CURSO')
            motivo = detener()
            if motivo:
                # Un checkpoint EN_CURSO es provisional, no una entrega final.
                if 'informe' in record:
                    state['informes'].remove(record.pop('informe'))
                    record['estado'] = motivo
                    json_atomico(ciclo / 'registro.json', record)
                break
            if state['errores_consecutivos'] >= 3:
                motivo = 'TRES_ERRORES_CONSECUTIVOS'
                break
            if state['vueltas'] >= max_vueltas:
                motivo = 'MAX_VUELTAS'
                break
            entrega_pendiente = False  # Vuelta cerrada antes de empezar la espera.
            siguiente = min(max_segundos, reloj.segundos() + intervalo_segundos)
            state['siguiente_lectura'] = time.time() + siguiente - reloj.segundos()
            guardar('ESPERANDO')
            ultimo_heartbeat = reloj.segundos()
            while reloj.segundos() < siguiente and not detener():
                time.sleep(min(1, max(0, siguiente - reloj.segundos())))
                if reloj.segundos() - ultimo_heartbeat >= 30:
                    guardar('ESPERANDO')
                    ultimo_heartbeat = reloj.segundos()
    except KeyboardInterrupt:
        motivo = 'INTERRUPCION'
    except Exception as exc:
        state['errores'] += 1
        state['detalle'] = type(exc).__name__ + ': ' + str(exc)
        motivo = 'ERROR' if isinstance(exc, (OSError, ValueError, TypeError)) else 'ERROR_INESPERADO'
        descartar_entrega_por_error(motivo)
    finally:
        if motivo == 'RELOJ_RETROCEDIO' and not state['errores']:
            state['errores'] += 1
        state.update(motivo_final=motivo, proceso_activo=False,
                     codigo_salida=2 if state['errores'] else 0)
        state.pop('siguiente_lectura', None)
        try:
            try:
                guardar('DETENIDO')
            except Exception as exc:
                state['errores'] += 1
                state['detalle'] = type(exc).__name__ + ': ' + str(exc)
                motivo = 'ERROR'
                state.update(motivo_final=motivo, codigo_salida=2)
                descartar_entrega_por_error(motivo)
                # Un único intento de persistir el error, no una aceptación.
                guardar('DETENIDO')
            reason = detener()
            if reason and reason != motivo:
                # El último checkpoint también es I/O: no cerrar con entrega tardía.
                # Las vueltas ya cerradas antes de una espera conservan sus informes.
                if motivo == 'MAX_VUELTAS' and record and 'informe' in record:
                    state['informes'].remove(record.pop('informe'))
                    record['estado'] = reason
                    json_atomico(ciclo / 'registro.json', record)
                if reason == 'RELOJ_RETROCEDIO' and not state['errores']:
                    state['errores'] += 1
                state.update(motivo_final=reason, codigo_salida=2 if state['errores'] else 0)
                # Solo se persiste una invalidación; no hay reintento ni aceptación nueva.
                guardar('DETENIDO')
        finally:
            for sig, handler in anteriores.items():
                signal.signal(sig, handler)
    state['codigo_salida'] = 2 if state['errores'] else 0
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, required=True)
    parser.add_argument('--entrada', type=Path)
    parser.add_argument('--sin-red', action='store_true')
    parser.add_argument('--max-vueltas', type=int, default=24)
    parser.add_argument('--intervalo-segundos', type=float, default=3600)
    parser.add_argument('--max-segundos', type=float, default=86400)
    args = parser.parse_args(argv)
    try:
        limites(args.max_vueltas, args.intervalo_segundos, args.max_segundos, args.sin_red)
        if not args.sin_red and args.intervalo_segundos < 60:
            raise ValueError('CLI con red requiere intervalo >=60 segundos')
        result = ejecutar(**vars(args))
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps(dict(estado='DETENIDO', detalle=str(exc), publicable=False,
                              gasto_api_usd=0)))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return result['codigo_salida']


if __name__ == '__main__':
    sys.exit(main())
