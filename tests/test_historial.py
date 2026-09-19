"""Historia sintética: publicación antigua nunca se convierte en observación antigua."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from bio import historial


def fila(id='uno', url='https://example.org/a', observado='2026-09-19T12:00:00Z'):
    return dict(id=id, url=url, fuente='FIXTURE', fecha='2010-01-01',
                claim_literal='Fixture de metadatos públicos', recolectado_en=observado)


class HistorialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def archivo(self, name, rows):
        path = self.root / name
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        return path

    def test_union_conserva_observacion_mas_antigua_no_publicacion(self):
        a = self.archivo('a.jsonl', [dict(fila(), origen_etiqueta='humano')])
        b = self.archivo('b.jsonl', [dict(fila(observado='2026-09-18T12:00:00Z'), revisor='NO PROPAGAR')])
        before = {p:p.read_bytes() for p in (a,b)}
        out = self.root / 'unido'
        result = historial.ejecutar([a,b], out)
        rows = [json.loads(s) for s in (out/'senales.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['recolectado_en'], '2026-09-18T12:00:00Z')
        self.assertNotIn('revisor', rows[0])
        self.assertEqual(result['dias_observados'], 1)
        self.assertIs(result['publicable'], False)
        for name, sha in result['artefactos_sha256'].items():
            self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(), sha)
        self.assertEqual(before, {p:p.read_bytes() for p in (a,b)})

    def test_conflicto_entre_snapshots_no_produce_manifest(self):
        a=self.archivo('a', [fila()]);b=self.archivo('b', [fila(url='https://example.org/b')])
        with self.assertRaises(ValueError): historial.ejecutar([a,b], self.root/'out')
        self.assertFalse((self.root/'out/manifest.json').exists())

    def test_salida_existente_symlink_y_limites(self):
        a=self.archivo('a', [fila()])
        historial.ejecutar([a], self.root/'out')
        with self.assertRaises(FileExistsError):historial.ejecutar([a], self.root/'out')
        (self.root/'link').symlink_to(a)
        with self.assertRaises(ValueError):historial.ejecutar([self.root/'link'], self.root/'out2')
        with mock.patch.object(historial, 'MAX_BYTES', 20):
            with self.assertRaises(ValueError):historial.ejecutar([a], self.root/'out3')
        with self.assertRaises(ValueError):historial.ejecutar([], self.root/'out4')

    def test_cli_y_preparacion_reales_sin_red(self):
        a=self.archivo('a', [fila(str(i), 'https://example.org/'+str(i)) for i in range(50)])
        cwd=Path(historial.__file__).resolve().parent.parent
        run=subprocess.run([sys.executable,'-m','bio.historial','--entrada',str(a),
                            '--salida',str(self.root/'unido')],capture_output=True,text=True,cwd=cwd,timeout=10)
        self.assertEqual(run.returncode,0,run.stderr)
        prep=subprocess.run([sys.executable,'-m','bio.preparacion','--entrada',str(self.root/'unido/senales.jsonl'),
                             '--salida',str(self.root/'prep'),'--corte','2026-09-20',
                             '--dorado',str(self.root/'ausente')],capture_output=True,text=True,cwd=cwd,timeout=10)
        self.assertEqual(prep.returncode,0,prep.stderr)
        result=json.loads(prep.stdout)
        self.assertEqual(result['estado_validacion'],'PENDIENTE_DORADO')
        self.assertIs(result['publicable'],False)


if __name__=='__main__':unittest.main()
