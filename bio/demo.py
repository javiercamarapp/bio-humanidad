"""Demo reproducible sin red, modelos ni etiquetas humanas reales."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

from bio.preparacion import ejecutar


def demo(salida: Path) -> dict:
    if salida.exists() or salida.is_symlink():
        raise FileExistsError('usa una carpeta nueva para la demo')
    titles = ('Public health policy meeting', 'Wastewater surveillance dashboard', 'Municipal data update')
    rows = [dict(id=f'DEMO-{i:04d}', fuente='DEMO_SINTETICA', fecha='2026-01-01',
                 claim_literal=f'[DEMO SINTÉTICA] {titles[i % len(titles)]} {i}',
                 url=f'https://example.org/demo/{i}', recolectado_en='2026-01-01T12:00:00Z')
            for i in range(60)]
    salida.mkdir(parents=True, exist_ok=False)
    source = salida / 'senales-sinteticas.jsonl'
    with source.open('x', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    prepared = ejecutar(source, salida / 'preparacion', date(2026, 1, 2), dorado=None)
    report = dict(estado='DEMO_COMPLETA', datos_sinteticos=True, publicable=False,
                  senales=60, etiquetas_humanas_generadas=0, llamadas_red=0,
                  estado_validacion=prepared['estado_validacion'],
                  informe=str(salida / 'preparacion/informe.md'),
                  advertencia='No utilizar estos datos como evidencia real ni dorado científico.')
    with (salida / 'demo.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(demo(args.salida), ensure_ascii=False))
    except (OSError, ValueError) as exc:
        print('error de demo: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
