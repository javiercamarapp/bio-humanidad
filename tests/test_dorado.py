"""Revisiones SINTÉTICAS en temporales, nunca el dorado del proyecto."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import os

from bio.dorado import comprobar, importar
from bio.radar import preparar
from bio.bucle import validar_dorado


class DoradoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.review = self.root / 'revision'
        self.output = self.root / 'datos/dorado/senales.jsonl'
        self.signals = [dict(id=str(i), fuente='HN', fecha='2026-09-19',
                             url=f'https://example.org/{i}', claim_literal=f'Public surveillance {i}',
                             recolectado_en='2026-09-19T12:00:00Z') for i in range(50)]
        preparar(self.signals, self.review)

    def rows(self):
        with (self.review / 'revision.csv').open(newline='') as f:
            reader = csv.DictReader(f)
            return reader.fieldnames, list(reader)

    def save(self, fields, rows):
        with (self.review / 'revision.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def reviewed(self):
        fields, rows = self.rows()
        for row in rows:
            row.update(categoria_humana='vigilancia', severidad_humana='no_aplica',
                       origen_etiqueta='humano', fecha_revision='2026-09-19', revisor='FIXTURE SINTETICO')
        self.save(fields, rows)

    def test_csv_vacio_es_pendiente_y_no_escribe(self):
        records, report = comprobar(self.review)
        self.assertEqual(records, [])
        self.assertEqual(report['estado'], 'PENDIENTE_REVISION_HUMANA')
        self.assertEqual(report['pendientes'], 50)
        self.assertFalse(self.output.exists())

    def test_importar_pendiente_falla_aun_con_confirmacion(self):
        with self.assertRaises(ValueError):
            importar(self.review, self.output, confirmar=True)
        self.assertFalse(self.output.parent.exists())

    def test_importar_requiere_confirmacion_explicita(self):
        self.reviewed()
        for confirm in [False, 'true', 1]:
            with self.subTest(confirm=confirm), self.assertRaises(ValueError):
                importar(self.review, self.output, confirmar=confirm)
        self.assertFalse(self.output.exists())

    def test_importacion_compatible_con_guardia_sin_modificar_entradas(self):
        self.reviewed()
        before = {p.name: p.read_bytes() for p in self.review.iterdir()}
        report = importar(self.review, self.output, confirmar=True)
        self.assertEqual(report['estado'], 'IMPORTADO')
        self.assertEqual(report['importadas'], 50)
        self.assertEqual(validar_dorado(self.root), [])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.review.iterdir()})
        parsed = [json.loads(s) for s in self.output.read_text().splitlines()]
        self.assertTrue(all(p['procedencia_revision']['csv_sha256'] for p in parsed))
        self.assertFalse(report['publicable'])

    def test_no_sobrescribe_nada_incluso_placeholder(self):
        self.reviewed()
        self.output.parent.mkdir(parents=True)
        for raw in [b'', b'archivo previo']:
            self.output.write_bytes(raw)
            with self.assertRaises(FileExistsError):
                importar(self.review, self.output, confirmar=True)
            self.assertEqual(self.output.read_bytes(), raw)

    def test_carrera_de_publicacion_no_reemplaza_al_ganador(self):
        self.reviewed()
        real_link = os.link

        def race(source, destination):
            Path(destination).write_bytes(b'otro importador gano')
            return real_link(source, destination)

        with mock.patch('bio.dorado.os.link', side_effect=race):
            with self.assertRaises(FileExistsError):
                importar(self.review, self.output, confirmar=True)
        self.assertEqual(self.output.read_bytes(), b'otro importador gano')
        self.assertEqual(list(self.output.parent.glob('.dorado-incompleto-*')), [])

    def test_filesystem_sin_enlaces_falla_sin_publicar(self):
        self.reviewed()
        with mock.patch('bio.dorado.os.link', side_effect=OSError('FS sin enlaces duros')):
            with self.assertRaises(OSError):
                importar(self.review, self.output, confirmar=True)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.glob('.dorado-incompleto-*')), [])

    def test_fuente_editada_en_csv_se_rechaza(self):
        self.reviewed()
        fields, rows = self.rows()
        rows[0]['claim_literal'] = 'Otro titular'
        self.save(fields, rows)
        with self.assertRaisesRegex(ValueError, 'fuente'):
            comprobar(self.review)

    def test_snapshot_adulterado_se_rechaza(self):
        path = self.review / 'muestra.jsonl'
        path.write_text(path.read_text().replace('Public', 'Changed'))
        with self.assertRaisesRegex(ValueError, 'hash'):
            comprobar(self.review)

    def test_no_permite_ids_duplicados_ni_casos_omitidos(self):
        fields, rows = self.rows()
        for broken in [rows[:-1], rows + [rows[0]]]:
            self.save(fields, broken)
            with self.assertRaises(ValueError):
                comprobar(self.review)

    def test_cabeceras_duplicadas_rechazadas(self):
        path = self.review / 'revision.csv'
        text = path.read_text()
        path.write_text(text.replace('"nota"', '"categoria_humana"', 1))
        with self.assertRaisesRegex(ValueError, 'cabecera'):
            comprobar(self.review)

    def test_etiqueta_de_modelo_o_fecha_invalida_no_se_convierte(self):
        self.reviewed()
        fields, rows = self.rows()
        for field, value in [('origen_etiqueta', 'modelo'), ('fecha_revision', '2026-02-30'),
                             ('revisor', ' '), ('categoria_humana', 'inventada')]:
            changed = [dict(r) for r in rows]
            changed[0][field] = value
            self.save(fields, changed)
            _, report = comprobar(self.review)
            self.assertEqual(report['pendientes'], 1)
            self.assertEqual(report['estado'], 'PENDIENTE_REVISION_HUMANA')

    def test_excluir_ambiguo_exige_nota_y_no_rebaja_minimo(self):
        self.reviewed()
        fields, rows = self.rows()
        rows[0]['categoria_humana'] = 'informacion_insuficiente'
        self.save(fields, rows)
        self.assertEqual(comprobar(self.review)[1]['pendientes'], 1)
        rows[0]['nota'] = 'Fixture: falta contexto para decidir'
        self.save(fields, rows)
        records, report = comprobar(self.review)
        self.assertEqual(len(records), 49)
        self.assertEqual(report['excluidas'], 1)
        self.assertEqual(report['estado'], 'MUESTRA_INSUFICIENTE')

    def test_bom_y_reordenar_csv_no_cambia_asociacion(self):
        self.reviewed()
        fields, rows = self.rows()
        self.save(fields, list(reversed(rows)))
        path = self.review / 'revision.csv'
        path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes())
        records, report = comprobar(self.review)
        self.assertEqual(len(records), 50)
        self.assertEqual(report['estado'], 'LISTO_PARA_IMPORTAR')

    def test_formula_escapada_recupera_literal_del_snapshot(self):
        other = self.root / 'formulas'
        signals = [dict(s) for s in self.signals]
        signals[0]['claim_literal'] = '=FIXTURE()'
        preparar(signals, other)
        old_review = self.review
        self.review = other
        self.reviewed()
        records, _ = comprobar(other)
        self.review = old_review
        self.assertEqual(next(r for r in records if r['id'] == '0')['claim_literal'], '=FIXTURE()')

    def test_symlink_de_csv_se_rechaza(self):
        path = self.review / 'revision.csv'
        moved = self.root / 'otro.csv'
        path.rename(moved)
        path.symlink_to(moved)
        with self.assertRaises(ValueError):
            comprobar(self.review)

    def test_cli_comprobar_es_solo_lectura_y_exit_2_si_pendiente(self):
        before = {p.name: p.read_bytes() for p in self.review.iterdir()}
        result = subprocess.run([sys.executable, '-m', 'bio.dorado', 'comprobar', str(self.review)],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)['pendientes'], 50)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.review.iterdir()})


if __name__ == '__main__':
    unittest.main()
