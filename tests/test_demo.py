import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from bio.demo import demo


class DemoTests(unittest.TestCase):
    def test_demo_offline_sin_dorado_y_claramente_sintetica(self):
        with tempfile.TemporaryDirectory() as t, mock.patch('socket.socket', side_effect=AssertionError('NO RED')):
            out = Path(t) / 'demo'
            report = demo(out)
            self.assertTrue(report['datos_sinteticos'])
            self.assertFalse(report['publicable'])
            self.assertEqual(report['estado_validacion'], 'PENDIENTE_DORADO')
            rows = [json.loads(line) for line in (out / 'senales-sinteticas.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 60)
            self.assertTrue(all(r['fuente'] == 'DEMO_SINTETICA' and r['id'].startswith('DEMO-') for r in rows))
            self.assertTrue(all('[DEMO SINTÉTICA]' in r['claim_literal'] for r in rows))
            self.assertFalse((Path(t) / 'datos/dorado').exists())
            self.assertEqual(len((out / 'preparacion/predicciones.jsonl').read_text().splitlines()), 60)

    def test_demo_no_sobrescribe(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'demo'
            demo(out)
            before = (out / 'demo.json').read_bytes()
            with self.assertRaises(FileExistsError):
                demo(out)
            self.assertEqual((out / 'demo.json').read_bytes(), before)

    def test_cli_desde_clone_sin_datos_reales(self):
        with tempfile.TemporaryDirectory() as t:
            result = subprocess.run([sys.executable, '-m', 'bio.demo', '--salida', str(Path(t) / 'demo')],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['estado'], 'DEMO_COMPLETA')


if __name__ == '__main__':
    unittest.main()
