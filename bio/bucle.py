"""Bucle acotado de validación. No genera hipótesis ni llama modelos.

python3 -m bio.bucle --max-vueltas 200 --max-segundos 900
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from bio.validador.validar import leer_texto

CATEGORIAS = {'brote', 'vigilancia', 'sintesis', 'dual-use', 'politica', 'capacidad', 'otro'}
SEVERIDADES = {'baja', 'media', 'alta', 'no_aplica'}
ESTADOS = {'ACEPTADA', 'RECHAZADA', 'DUPLICADA', 'PENDIENTE_HUMANO',
           'PENDIENTE_RED', 'ESCALAR_HUMANO', 'FUENTE_NO_VERIFICABLE', 'ERROR'}
CODIGO = Path(__file__).resolve().parent


def sin_enlaces(path: Path, root: Path):
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError('no se permiten enlaces simbólicos: ' + str(current))


def json_atomico(path: Path, data):
    if path.exists() and (path.is_symlink() or path.stat().st_size == 0):
        raise ValueError('no sobrescribir enlace ni posible placeholder: ' + str(path))
    tmp = path.with_name('.' + path.name + '-' + uuid.uuid4().hex)
    with tmp.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def huellas_protegidas(root: Path) -> dict:
    paths = set()
    for name in ('bio', 'tests', 'datos/dorado', 'datos/revisiones'):
        base = root / name
        sin_enlaces(base, root)
        for path in base.rglob('*'):
            if '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            sin_enlaces(path, root)
            if path.is_file():
                paths.add(path)
    for name in ('01-ALCANCE-Y-LIMITES.md', '02-PROGRAMA-BUCLE.md', 'PROGRAMA.md'):
        path = root / name
        sin_enlaces(path, root)
        if path.exists():
            paths.add(path)
    # Incluye el código efectivamente ejecutado también en pruebas con un root temporal.
    for path in (CODIGO / 'bucle.py', CODIGO / 'validador/validar.py'):
        paths.add(path)
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def validar_dorado(root: Path) -> list[str]:
    path = root / 'datos/dorado/senales.jsonl'
    try:
        sin_enlaces(path, root)
        if not path.is_file():
            return ['falta datos/dorado/senales.jsonl con al menos 50 etiquetas humanas']
        if not 0 < path.stat().st_size <= 10_000_000:
            return ['conjunto dorado vacío o demasiado grande']
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        ids = set()
        for row in rows:
            if not isinstance(row, dict):
                return ['registro dorado no es objeto']
            required = ('id', 'claim_literal', 'url', 'revisor', 'fecha_revision')
            if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
                return ['registro dorado incompleto']
            if (row.get('origen_etiqueta') != 'humano'
                    or row.get('categoria_humana') not in CATEGORIAS
                    or row.get('severidad_humana') not in SEVERIDADES):
                return ['etiquetas humanas pendientes o inválidas']
            dt.date.fromisoformat(row['fecha_revision'])
            if row['id'] in ids:
                return ['ID duplicado en conjunto dorado']
            ids.add(row['id'])
        return [] if len(ids) >= 50 else ['se requieren al menos 50 IDs humanos distintos']
    except (OSError, ValueError, TypeError) as exc:
        return ['conjunto dorado inválido: ' + type(exc).__name__]


def evaluar_subproceso(path: Path, revisiones: Path, accepted: list[Path],
                       sin_red: bool, timeout: float) -> dict:
    command = [sys.executable, str(CODIGO / 'validador/validar.py'), str(path),
               '--json', '--revisiones', str(revisiones)]
    if sin_red:
        command.append('--sin-red')
    for previous in accepted:
        command.extend(['--comparar', str(previous)])
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode not in (0, 2):
        raise ValueError('validador terminó con código ' + str(result.returncode))
    output = json.loads(result.stdout)
    records = output['resultados']
    if len(records) != 1 or records[0]['estado'] not in ESTADOS:
        raise ValueError('respuesta inválida del validador')
    record = records[0]
    if record.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('validador no confirma hash del snapshot')
    return record


def cargar_intentos(run: Path) -> list[dict]:
    attempts = []
    for path in sorted((run / 'intentos').iterdir()):
        if path.name.startswith('.'):
            continue  # Snapshot incompleto tras crash: no está comprometido.
        sin_enlaces(path / 'registro.json', run)
        sin_enlaces(path / 'candidato.md', run)
        if not re.fullmatch(r'\d{6}-[a-f0-9]{64}', path.name):
            raise ValueError('intento con nombre inválido')
        record = json.loads((path / 'registro.json').read_text())
        if (record['numero'] != len(attempts) + 1 or record['estado'] not in ESTADOS
                or record['sha256'] != hashlib.sha256((path / 'candidato.md').read_bytes()).hexdigest()
                or path.name != f"{record['numero']:06d}-{record['sha256']}"):
            raise ValueError('historial inconsistente; se requiere revisión manual')
        attempts.append(record)
    return attempts


def limites_validos(config: dict):
    for key, cap in [('max_vueltas', 200), ('max_segundos', 14 * 86400),
                     ('sin_mejora', 25), ('timeout_vuelta', 300)]:
        value = config[key]
        if type(value) is not int or not 1 <= value <= cap:
            raise ValueError(f'{key} debe estar entre 1 y {cap}')


def ejecutar(root: Path, *, max_vueltas=200, max_segundos=900, sin_mejora=25,
             timeout_vuelta=30, sin_red=False, reanudar: Path | None = None) -> dict:
    root = root.resolve()
    base = root / 'salidas/bucle'
    sin_enlaces(base, root)
    base.mkdir(parents=True, exist_ok=True)
    if reanudar is None:
        config = dict(max_vueltas=max_vueltas, max_segundos=max_segundos,
                      sin_mejora=sin_mejora, timeout_vuelta=timeout_vuelta, sin_red=sin_red)
        limites_validos(config)
        run = base / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
        run.mkdir()
    else:
        run = reanudar if reanudar.is_absolute() else root / reanudar
        sin_enlaces(run, root)
        if run.parent != base or not run.is_dir():
            raise ValueError('reanudación debe apuntar a una corrida en salidas/bucle/')
    lock_path = run / '.lock'
    sin_enlaces(lock_path, root)
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('otra ejecución posee el bloqueo de esta corrida')
        if reanudar is None:
            config.update(inicio=time.time(), protegidos=huellas_protegidas(root), root=str(root))
            json_atomico(run / 'config.json', config)
            (run / 'intentos').mkdir()
        else:
            for name in ('config.json', 'intentos'):
                sin_enlaces(run / name, root)
            config = json.loads((run / 'config.json').read_text())
            limites_validos(config)
            if config['root'] != str(root):
                raise ValueError('la corrida pertenece a otro proyecto')
        attempts = cargar_intentos(run)

        def finish(reason, details=()):
            accepted = sum(a['estado'] == 'ACEPTADA' for a in attempts)
            report = dict(corrida=str(run), motivo_parada=reason, detalles=list(details),
                          vueltas=len(attempts), aceptadas=accepted,
                          no_aceptadas=len(attempts) - accepted,
                          estados={s: sum(a['estado'] == s for a in attempts) for s in sorted(ESTADOS)},
                          segundos_transcurridos=round(time.time() - config['inicio'], 3),
                          gasto_api_usd=0, proceso_activo=None if reason == 'EN_CURSO' else False,
                          limites={k: config[k] for k in ('max_vueltas', 'max_segundos', 'sin_mejora', 'timeout_vuelta')})
            json_atomico(run / 'estado.json', report)
            return report

        def guardias():
            if huellas_protegidas(root) != config['protegidos']:
                return 'PROTEGIDOS_CAMBIARON', ['iniciar otra corrida tras revisar los cambios; no se reinicia este presupuesto']
            errors = validar_dorado(root)
            if errors:
                return 'DORADO_PENDIENTE', errors
            return None

        blocked = guardias()
        if blocked:
            return finish(*blocked)
        if attempts and attempts[-1]['estado'] in {'ESCALAR_HUMANO', 'PENDIENTE_HUMANO', 'PENDIENTE_RED'}:
            return finish(attempts[-1]['estado'], attempts[-1]['motivos'])
        candidates = root / 'salidas/hipotesis'
        sin_enlaces(candidates, root)
        files = sorted(candidates.glob('*.md'))
        seen = {a['sha256'] for a in attempts}
        no_improvement = 0
        for attempt in reversed(attempts):
            if attempt['estado'] == 'ACEPTADA':
                break
            no_improvement += 1
        for candidate in files:
            blocked = guardias()
            if blocked:
                return finish(*blocked)
            elapsed = time.time() - config['inicio']
            if elapsed < 0:
                return finish('RELOJ_RETROCEDIO')
            remaining = config['max_segundos'] - elapsed
            if len(attempts) >= config['max_vueltas'] or remaining <= 0:
                return finish('PRESUPUESTO')
            if no_improvement >= config['sin_mejora']:
                return finish('AGOTAMIENTO')
            try:
                sin_enlaces(candidate, root)
                content = leer_texto(candidate)
            except (OSError, ValueError) as exc:
                return finish('CANDIDATO_INVALIDO', [candidate.name, type(exc).__name__])
            digest = hashlib.sha256(content.encode()).hexdigest()
            if digest in seen:
                continue
            number = len(attempts) + 1
            pending = run / 'intentos' / ('.incompleto-' + uuid.uuid4().hex)
            pending.mkdir()
            snapshot = pending / 'candidato.md'
            with snapshot.open('x', encoding='utf-8', newline='') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            accepted_paths = [run / 'intentos' / f"{a['numero']:06d}-{a['sha256']}" / 'candidato.md'
                              for a in attempts if a['estado'] == 'ACEPTADA']
            try:
                result = evaluar_subproceso(snapshot, root / 'datos/revisiones', accepted_paths,
                                           config['sin_red'], min(config['timeout_vuelta'], remaining))
            except (subprocess.TimeoutExpired, OSError, ValueError, KeyError, TypeError) as exc:
                result = dict(estado='ERROR', motivos=[type(exc).__name__])
            blocked = guardias()
            if blocked:
                return finish(*blocked)  # El snapshot incompleto no cuenta como aceptado.
            if time.time() - config['inicio'] >= config['max_segundos']:
                result = dict(estado='ERROR', motivos=['presupuesto de tiempo agotado durante intento'])
            result.update(numero=number, sha256=digest, candidato=candidate.name)
            json_atomico(pending / 'registro.json', result)
            pending.rename(run / 'intentos' / f'{number:06d}-{digest}')
            attempts.append(result)
            seen.add(digest)
            no_improvement = 0 if result['estado'] == 'ACEPTADA' else no_improvement + 1
            finish('EN_CURSO')  # Checkpoint; proceso_activo no es un detector de PID.
            if result['estado'] in {'ESCALAR_HUMANO', 'PENDIENTE_HUMANO', 'PENDIENTE_RED'}:
                return finish(result['estado'], result['motivos'])
        if len(attempts) >= config['max_vueltas'] or time.time() - config['inicio'] >= config['max_segundos']:
            return finish('PRESUPUESTO')
        if no_improvement >= config['sin_mejora']:
            return finish('AGOTAMIENTO')
        return finish('COLA_AGOTADA')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-vueltas', type=int, default=200)
    parser.add_argument('--max-segundos', type=int, default=900)
    parser.add_argument('--sin-mejora', type=int, default=25)
    parser.add_argument('--timeout-vuelta', type=int, default=30)
    parser.add_argument('--sin-red', action='store_true')
    parser.add_argument('--reanudar', type=Path, help='usa configuración y presupuesto originales')
    args = parser.parse_args()
    try:
        result = ejecutar(Path.cwd(), **vars(args))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'motivo_parada': 'ERROR_ESTADO', 'detalle': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['motivo_parada'] == 'COLA_AGOTADA' else 2


if __name__ == '__main__':
    sys.exit(main())
