"""Pipeline offline con fixtures sintéticos; ninguna etiqueta real generada."""
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from bio.preparacion import ejecutar


def senal(i):
    return {'id': str(i), 'fuente': 'HN', 'fecha': '2026-09-19',
            'claim_literal': 'Wastewater surveillance dashboard updated',
            'url': f'https://example.org/{i}', 'recolectado_en': '2026-09-19T12:00:00Z'}


class PreparacionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / 'senales.jsonl'
        self.output = self.root / 'salida'
        self.data = [senal(i) for i in range(50)]
        self.input.write_text(''.join(json.dumps(s) + '\n' for s in self.data))
        self.cutoff = date(2026, 9, 20)

    def run_pipeline(self, **kwargs):
        return ejecutar(self.input, self.output, self.cutoff, **kwargs)

    def test_sin_dorado_prepara_pero_no_certifica(self):
        before = self.input.read_bytes()
        result = self.run_pipeline()
        self.assertEqual(result['estado'], 'PREPARACION_COMPLETA')
        self.assertEqual(result['estado_validacion'], 'PENDIENTE_DORADO')
        self.assertFalse(result['publicable'])
        self.assertEqual(result['senales'], 50)
        self.assertEqual(self.input.read_bytes(), before)
        self.assertFalse((self.root / 'datos/dorado').exists())
        metrics = json.loads((self.output / 'metricas.json').read_text())
        self.assertIsNone(metrics['exactitud_global'])
        self.assertIsNone(metrics['exactitud_selectiva'])
        detection = json.loads((self.output / 'deteccion.json').read_text())
        self.assertEqual(detection['estado'], 'DATOS_INSUFICIENTES')
        self.assertEqual(detection['novedades'], [])

    def test_sin_red_en_todo_el_pipeline(self):
        with mock.patch('urllib.request.urlopen', side_effect=AssertionError('NO RED')), \
                mock.patch('socket.socket', side_effect=AssertionError('NO RED')):
            self.run_pipeline()

    def test_muestra_nunca_se_autorrevisa(self):
        self.data[0].update(categoria_humana='vigilancia', revisor='inyectado', origen_etiqueta='humano')
        self.input.write_text(''.join(json.dumps(s) + '\n' for s in self.data))
        self.run_pipeline()
        with (self.output / 'revision/revision.csv').open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 50)
        for row in rows:
            for key in ['categoria_humana', 'severidad_humana', 'revisor', 'fecha_revision', 'origen_etiqueta']:
                self.assertEqual(row[key], '')

    def test_hashes_de_todos_los_artefactos_cuadran(self):
        result = self.run_pipeline()
        for name, digest in result['artefactos_sha256'].items():
            self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(result['entrada_sha256'], hashlib.sha256(self.input.read_bytes()).hexdigest())

    def test_repeticion_no_sobrescribe_y_no_modifica_original(self):
        self.run_pipeline()
        before = (self.output / 'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_pipeline()
        self.assertEqual((self.output / 'manifest.json').read_bytes(), before)

    def test_resultados_reproducibles_en_otra_carpeta(self):
        self.run_pipeline()
        another = self.root / 'otra'
        ejecutar(self.input, another, self.cutoff)
        for name in ['predicciones.jsonl', 'deteccion.json', 'metricas.json', 'revision/revision.csv']:
            self.assertEqual((self.output / name).read_bytes(), (another / name).read_bytes())

    def test_casos_sinteticos_evaluados_no_se_vuelven_publicables(self):
        gold = self.root / 'gold.jsonl'
        rows = [{**s, 'categoria_humana': 'vigilancia', 'severidad_humana': 'no_aplica',
                 'revisor': 'FIXTURE SINTETICO', 'fecha_revision': '2026-09-19',
                 'origen_etiqueta': 'humano'} for s in self.data]
        gold.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        before = gold.read_bytes()
        result = self.run_pipeline(dorado=gold)
        metrics = json.loads((self.output / 'metricas.json').read_text())
        self.assertEqual(metrics['exactitud_global'], 1.0)
        self.assertEqual(result['estado_validacion'], 'EVALUADO_TECNICAMENTE')
        self.assertFalse(result['publicable'])
        self.assertEqual(gold.read_bytes(), before)

    def test_dorado_corrupto_no_entrega_un_exito(self):
        gold = self.root / 'gold.jsonl'
        gold.write_text('{mal JSON}\n')
        with self.assertRaises(ValueError):
            self.run_pipeline(dorado=gold)
        self.assertFalse(self.output.exists())

    def test_dorado_con_categoria_duplicada_no_se_evaluara(self):
        gold = self.root / 'gold.jsonl'
        rows = [{**s, 'categoria_humana': 'brote', 'severidad_humana': 'no_aplica',
                 'revisor': 'FIXTURE', 'fecha_revision': '2026-09-19', 'origen_etiqueta': 'humano'}
                for s in self.data]
        gold.write_text(''.join(json.dumps(r)[:-1] + ', "categoria_humana": "vigilancia"}\n' for r in rows))
        with self.assertRaisesRegex(ValueError, 'duplicada'):
            self.run_pipeline(dorado=gold)
        self.assertFalse(self.output.exists())

    def test_dorado_ausente_explicito_es_pendiente(self):
        result = self.run_pipeline(dorado=self.root / 'ausente.jsonl')
        self.assertEqual(result['estado_validacion'], 'PENDIENTE_DORADO')

    def test_muestra_insuficiente_no_hace_entrega_falsa(self):
        self.input.write_text(json.dumps(self.data[0]) + '\n')
        with self.assertRaises(ValueError):
            self.run_pipeline()
        self.assertFalse(self.output.exists())

    def test_json_invalido_no_crea_salida(self):
        self.input.write_text('no json')
        with self.assertRaises(ValueError):
            self.run_pipeline()
        self.assertFalse(self.output.exists())

    def test_rechaza_enlace_simbolico_a_entrada(self):
        link = self.root / 'link.jsonl'
        link.symlink_to(self.input)
        with self.assertRaises(ValueError):
            ejecutar(link, self.output, self.cutoff)

    def test_codigo_cambia_durante_corrida_no_emite_manifiesto_final(self):
        with mock.patch('bio.preparacion.huellas_codigo',
                        side_effect=[{'codigo': 'antes'}, {'codigo': 'despues'}], create=True):
            with self.assertRaisesRegex(ValueError, 'código'):
                self.run_pipeline()
        self.assertFalse((self.output / 'manifest.json').exists())

    def test_fallo_de_escritura_no_deja_manifiesto_de_exito(self):
        with mock.patch('bio.preparacion.radar.preparar', side_effect=OSError('fixture de disco lleno')):
            with self.assertRaises(OSError):
                self.run_pipeline()
        self.assertFalse((self.output / 'manifest.json').exists())

    def test_cli_salida_completa_sin_afirmar_validacion(self):
        result = subprocess.run([sys.executable, '-m', 'bio.preparacion',
                                 '--entrada', str(self.input), '--salida', str(self.output),
                                 '--corte', '2026-09-20', '--dorado', str(self.root / 'no-gold')],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary['estado_validacion'], 'PENDIENTE_DORADO')
        self.assertFalse(summary['publicable'])


if __name__ == '__main__':
    unittest.main()
