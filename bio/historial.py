"""Une snapshots offline sin inventar días de observación ni propagar aprobaciones.

python3 -m bio.historial --entrada ARCHIVO1.jsonl ARCHIVO2.jsonl --salida CARPETA_NUEVA
Los originales permanecen intactos. No supone independencia entre fuentes repetidas.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import sys
import json

from bio import radar
from bio.json_estricto import cargar
from bio.preparacion import escribir_json, jsonl
from bio.vigilar import leer, ruta_segura

MAX_BYTES = 10_000_000
MAX_ENTRADAS = 32
MAX_REGISTROS = 5000
CAMPOS = ('id', 'fuente', 'fecha', 'claim_literal', 'url', 'recolectado_en')


def ejecutar(entradas, salida):
    if not 1 <= len(entradas) <= MAX_ENTRADAS:
        raise ValueError('se requieren entre1 y32 snapshots')
    salida = ruta_segura(salida)
    if salida.exists():
        raise FileExistsError('salida debe ser nueva')
    sources, rows, size = [], [], 0
    for entrada in entradas:
        path = ruta_segura(entrada)
        raw = leer(path)
        size += len(raw)
        if not raw.strip() or size > MAX_BYTES:
            raise ValueError('entrada vacía o suma superior a10MB')
        parsed = [cargar(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
        unique_in_source = len(radar.normalizar(parsed))  # Valida, pero NO descarta originales.
        rows.extend({key: row[key] for key in CAMPOS} for row in parsed)
        sources.append((path, raw, unique_in_source))
    normalized = radar.normalizar(rows)
    if not normalized or len(normalized) > MAX_REGISTROS:
        raise ValueError('se requieren de1 a5000 señales únicas')
    # Toda validación anterior a reservar una salida, sin reemplazar otro historial.
    salida.mkdir(parents=True, exist_ok=False)
    inputs = []
    for index, (path, raw, count) in enumerate(sources, 1):
        name = f'entrada-{index:03d}.jsonl'
        with (salida / name).open('xb') as stream:
            stream.write(raw)
        inputs.append(dict(origen=str(path), snapshot=name, sha256=hashlib.sha256(raw).hexdigest(),
                           senales_unicas_en_entrada=count))
    with (salida / 'senales.jsonl').open('x', encoding='utf-8') as stream:
        stream.write(jsonl(normalized))
    result = dict(version=1, estado='HISTORIAL_UNIDO', publicable=False, llamadas_red=0,
                  etiquetas_humanas_generadas=0, entradas=inputs, senales_unicas=len(normalized),
                  fuentes=dict(sorted(Counter(row['fuente'] for row in normalized).items())),
                  dias_observados=len({radar.fecha_utc(r['recolectado_en']).date() for r in normalized}),
                  advertencias=['Primera observación por URL, no fecha de publicación.',
                                'Unir archivos no crea días de cobertura ni fuentes independientes.',
                                'Los hashes acreditan bytes, no veracidad de datos aportados.'],
                  artefactos_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in salida.iterdir() if p.is_file()})
    escribir_json(salida / 'manifest.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', dest='entradas', type=Path, nargs='+', required=True)
    parser.add_argument('--salida', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(ejecutar(**vars(args)), ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print('error de historial: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
