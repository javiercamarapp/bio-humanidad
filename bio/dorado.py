"""Comprobar/importar un CSV ya revisado por una persona; nunca generar etiquetas."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from bio.evaluacion import CATEGORIAS, _SEVERIDADES
from bio.json_estricto import cargar
from bio.radar import celda, digest, normalizar

FUENTE = ('id', 'fuente', 'fecha', 'url', 'claim_literal', 'recolectado_en')
FUENTE_CSV = FUENTE[:-1]
HUMANOS = ('categoria_humana', 'severidad_humana', 'origen_etiqueta', 'fecha_revision', 'revisor')
OPCIONALES = ('clase', 'nota', 'revisado_en')
MAX_BYTES = 10_000_000


def _leer(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError('archivo ausente o enlace simbólico: ' + str(path))
    with path.open('rb') as f:
        raw = f.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('archivo vacío o superior a 10 MB: ' + str(path))
    return raw


def _errores_revision(row: dict) -> list[str]:
    errors = [key for key in HUMANOS if not row[key].strip()]
    if row['origen_etiqueta'] != 'humano':
        errors.append('origen_etiqueta debe ser humano')
    if row['categoria_humana'] not in (*CATEGORIAS, 'informacion_insuficiente'):
        errors.append('categoria_humana inválida')
    if row['severidad_humana'] not in _SEVERIDADES:
        errors.append('severidad_humana inválida')
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['fecha_revision']):
            raise ValueError('formato de fecha')
        date.fromisoformat(row['fecha_revision'])
    except ValueError:
        errors.append('fecha_revision inválida')
    if row['categoria_humana'] == 'informacion_insuficiente' and not row.get('nota', '').strip():
        errors.append('exclusión ambigua requiere nota')
    return errors


def comprobar(carpeta: Path) -> tuple[list[dict], dict]:
    if carpeta.is_symlink():
        raise ValueError('carpeta de revisión no puede ser enlace simbólico')
    raw_sample = _leer(carpeta / 'muestra.jsonl')
    raw_state = _leer(carpeta / 'estado.json')
    raw_csv = _leer(carpeta / 'revision.csv')
    sample = [cargar(line) for line in raw_sample.decode('utf-8').splitlines() if line.strip()]
    state = cargar(raw_state.decode('utf-8'))
    if (not sample or len(sample) > 5000
            or any(not isinstance(row, dict) or set(row) != set(FUENTE) for row in sample)):
        raise ValueError('snapshot de muestra inválido')
    if len(normalizar(sample)) != len(sample) or len({s['id'] for s in sample}) != len(sample):
        raise ValueError('snapshot contiene IDs o URLs duplicados')
    if (not isinstance(state, dict) or state.get('version') != 1
            or state.get('estado') != 'PENDIENTE_REVISION_HUMANA'
            or type(state.get('muestra')) is not int or state['muestra'] != len(sample)
            or state.get('sha256_muestra') != digest(sample)):
        raise ValueError('manifiesto o hash de muestra incompatible')
    originals = {celda(s['id']): s for s in sample}
    if len(originals) != len(sample):
        raise ValueError('IDs ambiguos después de escapar el CSV')
    reader = csv.DictReader(io.StringIO(raw_csv.decode('utf-8-sig'), newline=''), strict=True)
    required = set(FUENTE_CSV + HUMANOS)
    try:
        headers = reader.fieldnames
        if (not headers or len(headers) != len(set(headers)) or not required.issubset(headers)
                or set(headers) - required - set(OPCIONALES)):
            raise ValueError('cabecera CSV inválida, desconocida o duplicada')
        rows = list(reader)
    except csv.Error as exc:
        raise ValueError('CSV inválido') from exc
    if len(rows) != len(sample):
        raise ValueError('el CSV debe incluir todos los casos de la muestra, sin omisiones ni extras')
    provenance = dict(csv_sha256=hashlib.sha256(raw_csv).hexdigest(),
                      muestra_sha256=hashlib.sha256(raw_sample).hexdigest(),
                      manifiesto_sha256=hashlib.sha256(raw_state).hexdigest())
    seen, records, pending, excluded = set(), [], [], []
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError('número de columnas CSV inconsistente')
        key = row['id']
        if key not in originals or key in seen:
            raise ValueError('ID desconocido o duplicado en CSV')
        seen.add(key)
        source = originals[key]
        if any(row[field] != celda(source[field]) for field in FUENTE_CSV):
            raise ValueError('campo fuente modificado para ID ' + repr(source['id']))
        errors = _errores_revision(row)
        if errors:
            pending.append(dict(id=source['id'], campos=errors))
        elif row['categoria_humana'] == 'informacion_insuficiente':
            excluded.append(dict(id=source['id'], nota=row['nota']))
        else:
            records.append({**source, **{k: row[k] for k in HUMANOS},
                            'nota': row.get('nota', ''), 'procedencia_revision': dict(provenance)})
    status = ('PENDIENTE_REVISION_HUMANA' if pending else
              'LISTO_PARA_IMPORTAR' if len(records) >= 50 else 'MUESTRA_INSUFICIENTE')
    report = dict(estado=status, muestra=len(sample), validas=len(records), pendientes=len(pending),
                  excluidas=len(excluded), minimo_requerido=50, publicable=False,
                  detalles_pendientes=sorted(pending, key=lambda r: r['id']),
                  detalles_excluidas=sorted(excluded, key=lambda r: r['id']),
                  hashes=provenance,
                  advertencia='Registro local de revisión: no autentica personas ni valida ciencia.')
    return sorted(records, key=lambda r: r['id']), report


def importar(carpeta: Path, salida: Path, *, confirmar: bool = False) -> dict:
    if confirmar is not True:
        raise ValueError('se requiere confirmación humana explícita; no se generan etiquetas')
    if salida.exists() or salida.is_symlink():
        raise FileExistsError('no se sobrescribe el dorado existente, ni un placeholder')
    records, report = comprobar(carpeta)
    if report['estado'] != 'LISTO_PARA_IMPORTAR':
        raise ValueError('revisión no importable: ' + report['estado'])
    payload = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n'
                      for row in records).encode('utf-8')
    salida.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.dorado-incompleto-', dir=salida.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        # Publicar bytes completos sin reemplazar ningún archivo, incluso si otro
        # importador ganó la carrera. Si el FS no admite enlaces duros, falla cerrado.
        os.link(temporary, salida)
    finally:
        if temporary.exists() and temporary.stat().st_size > 0:
            temporary.unlink()  # Solo nuestro temporal recién creado/materializado.
    return dict(report, estado='IMPORTADO', importadas=len(records), salida=str(salida),
                salida_sha256=hashlib.sha256(payload).hexdigest())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='comando', required=True)
    check = commands.add_parser('comprobar', help='solo lectura; nunca rellena campos')
    check.add_argument('carpeta', type=Path)
    apply = commands.add_parser('importar', help='requiere revisión completa y confirmación explícita')
    apply.add_argument('carpeta', type=Path)
    apply.add_argument('--salida', type=Path, default=Path('datos/dorado/senales.jsonl'))
    apply.add_argument('--confirmar-revision-humana', action='store_true')
    args = parser.parse_args()
    try:
        if args.comando == 'comprobar':
            _, report = comprobar(args.carpeta)
        else:
            report = importar(args.carpeta, args.salida, confirmar=args.confirmar_revision_humana)
    except (OSError, ValueError, TypeError) as exc:
        print('error de revisión: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report['estado'] in {'LISTO_PARA_IMPORTAR', 'IMPORTADO'} else 2


if __name__ == '__main__':
    sys.exit(main())
