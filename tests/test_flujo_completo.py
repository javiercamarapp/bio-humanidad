"""E2E por CLI, sin red: datos y revisión SIMULADOS en un temporal.

Los campos origen_etiqueta='humano' son fixtures para probar el importador,
NO etiquetas humanas reales ni evidencia científica. Nunca se escribe en datos/
o salidas/ del repositorio. No se rellenan revisiones de candidatos.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_validador import CANDIDATO

RAIZ = Path(__file__).resolve().parent.parent


class FlujoCompletoTests(unittest.TestCase):
    def test_flujo_cli_sintetico_y_gates_independientes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            env = dict(os.environ, PYTHONPATH=str(RAIZ), PYTHONDONTWRITEBYTECODE='1')

            def cli(modulo, *args, exit_code=0):
                result = subprocess.run([sys.executable, '-m', modulo, *map(str, args)],
                                        cwd=root, env=env, capture_output=True,
                                        text=True, timeout=20)
                self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
                return result

            def json_cli(modulo, *args, **kwargs):
                return json.loads(cli(modulo, *args, **kwargs).stdout)

            def comprobar_hashes(carpeta):
                manifest = json.loads((carpeta / 'manifest.json').read_text())
                self.assertIs(manifest['publicable'], False)
                for relative, digest in manifest['artefactos_sha256'].items():
                    self.assertEqual(hashlib.sha256((carpeta / relative).read_bytes()).hexdigest(), digest)
                return manifest

            demo = root / 'demo'
            result = json_cli('bio.demo', '--salida', demo)
            self.assertTrue(result['datos_sinteticos'])
            self.assertEqual(result['etiquetas_humanas_generadas'], 0)
            self.assertEqual(result['llamadas_red'], 0)
            self.assertEqual(result['estado_validacion'], 'PENDIENTE_DORADO')
            comprobar_hashes(demo / 'preparacion')
            source = demo / 'senales-sinteticas.jsonl'
            original = source.read_bytes()
            review = demo / 'preparacion/revision'
            reference = root / 'datos/dorado/senales.jsonl'
            before = {p.name: p.read_bytes() for p in review.iterdir()}
            pending = json_cli('bio.dorado', 'comprobar', review, exit_code=2)
            self.assertEqual((pending['pendientes'], pending['validas']), (50, 0))
            cli('bio.dorado', 'importar', review, '--salida', reference,
                '--confirmar-revision-humana', exit_code=1)
            self.assertFalse(reference.exists())
            self.assertEqual(before, {p.name: p.read_bytes() for p in review.iterdir()})

            # Un candidato sintético sigue bloqueado antes de disponer del dorado.
            candidates = root / 'salidas/hipotesis'
            candidates.mkdir(parents=True)
            (candidates / 'fixture.md').write_text(CANDIDATO, encoding='utf-8')
            blocked = json_cli('bio.bucle', '--sin-red', '--max-vueltas', 1,
                               '--max-segundos', 10, exit_code=2)
            self.assertEqual(blocked['motivo_parada'], 'DORADO_PENDIENTE')
            self.assertEqual(blocked['vueltas'], 0)

            # Simulación SOLO en este temporal, sin mirar predicciones para etiquetar.
            csv_path = review / 'revision.csv'
            with csv_path.open(encoding='utf-8', newline='') as stream:
                reader = csv.DictReader(stream)
                fields, rows = reader.fieldnames, list(reader)
            for row in rows:
                row.update(categoria_humana='otro', severidad_humana='no_aplica',
                           origen_etiqueta='humano', fecha_revision='2026-01-02',
                           revisor='FIXTURE SINTETICO E2E; NO PERSONA REAL')
            with csv_path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            ready = json_cli('bio.dorado', 'comprobar', review)
            self.assertEqual(ready['estado'], 'LISTO_PARA_IMPORTAR')
            cli('bio.dorado', 'importar', review, '--salida', reference, exit_code=1)
            self.assertFalse(reference.exists())
            imported = json_cli('bio.dorado', 'importar', review, '--salida', reference,
                                '--confirmar-revision-humana')
            self.assertEqual(imported['importadas'], 50)
            self.assertIs(imported['publicable'], False)
            gold_bytes = reference.read_bytes()
            self.assertEqual(hashlib.sha256(gold_bytes).hexdigest(), imported['salida_sha256'])
            cli('bio.dorado', 'importar', review, '--salida', reference,
                '--confirmar-revision-humana', exit_code=1)
            self.assertEqual(reference.read_bytes(), gold_bytes)

            evaluated = root / 'evaluada'
            result = json_cli('bio.preparacion', '--entrada', source, '--salida', evaluated,
                              '--corte', '2026-01-02', '--dorado', reference)
            self.assertEqual(result['estado_validacion'], 'EVALUADO_TECNICAMENTE')
            manifest = comprobar_hashes(evaluated)
            self.assertEqual(manifest['dorado_sha256'], imported['salida_sha256'])
            metrics = json.loads((evaluated / 'metricas.json').read_text())
            self.assertEqual(metrics['total_referencia'], 50)
            self.assertIsNotNone(metrics['exactitud_global'])
            self.assertIsNotNone(metrics['cobertura'])
            self.assertIs(metrics['publicable'], False)
            self.assertEqual(source.read_bytes(), original)

            # Importar dorado no autoriza reanudar configuración previa ni un candidato.
            resumed = json_cli('bio.bucle', '--reanudar', blocked['corrida'], exit_code=2)
            self.assertEqual(resumed['motivo_parada'], 'PROTEGIDOS_CAMBIARON')
            candidate_gate = json_cli('bio.bucle', '--sin-red', '--max-vueltas', 1,
                                     '--max-segundos', 10, exit_code=2)
            self.assertEqual(candidate_gate['motivo_parada'], 'PENDIENTE_HUMANO')
            self.assertEqual(candidate_gate['aceptadas'], 0)
            self.assertFalse((root / 'datos/revisiones').exists())


if __name__ == '__main__':
    unittest.main()
