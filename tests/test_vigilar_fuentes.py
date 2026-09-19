"""Vigilancia de feeds con XML sintético; red sustituida, preparación CLI real."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from bio import vigilar
from bio.recolector import multifuente
from test_multifuente import RSS


class VigilanciaFuentesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_feed_prepara_revision_sin_inventar_etiquetas(self):
        item = RSS.split(b'<item>')[1].split(b'</item>')[0].replace(b'2026', b'2020')
        raw = b'<rss><channel>' + b''.join(b'<item>'+item.replace(b'/a', ('/'+str(i)).encode())+b'</item>' for i in range(60)) + b'</channel></rss>'
        real = vigilar.subproceso
        def worker(modulo, args, timeout, detener):
            if modulo == 'bio.recolector.multifuente':
                with mock.patch.object(multifuente, 'descargar_acotado', return_value=raw):
                    result = multifuente.ejecutar(Path(args[args.index('--salida')+1]), ['ecdc'])
                return dict(modulo=modulo, codigo=0, stdout=json.dumps(result), stderr='', interrupcion=None)
            return real(modulo, args, timeout, detener)
        with mock.patch.object(vigilar, 'subproceso', side_effect=worker):
            state = vigilar.ejecutar(self.root/'run', fuentes=['ecdc'], max_vueltas=1, max_segundos=30)
        self.assertEqual(state['errores'], 0)
        self.assertEqual(len(state['informes']), 1)
        self.assertEqual(state['fuentes'], ['ecdc'])
        manifest=json.loads((self.root/'run'/state['informes'][0]/'manifest.json').read_text())
        self.assertEqual(manifest['etiquetas_humanas_generadas'], 0)
        self.assertEqual(manifest['estado_validacion'], 'PENDIENTE_DORADO')
        self.assertIs(manifest['publicable'], False)

    def test_snapshot_alterado_no_se_incorpora(self):
        def worker(modulo, args, timeout, detener):
            directory=Path(args[args.index('--salida')+1])
            with mock.patch.object(multifuente, 'descargar_acotado', return_value=RSS.replace(b'2026',b'2020')):
                multifuente.ejecutar(directory,['ecdc'])
            with (directory/'senales.jsonl').open('a') as f: f.write('\n')
            return dict(modulo=modulo,codigo=0,stdout='',stderr='',interrupcion=None)
        with mock.patch.object(vigilar,'subproceso',side_effect=worker):
            state=vigilar.ejecutar(self.root/'run',fuentes=['ecdc'],max_vueltas=1,max_segundos=30)
        self.assertEqual(state['errores'],1)
        self.assertEqual(state['informes'],[])
        self.assertFalse((self.root/'run/titulares.jsonl').exists())

    def test_parcial_no_autoriza_informe(self):
        result=dict(modulo='bio.recolector.multifuente', codigo=2, stdout='', stderr='FIXTURE', interrupcion=None)
        with mock.patch.object(vigilar, 'subproceso', return_value=result):
            state=vigilar.ejecutar(self.root/'run', fuentes=['ecdc'], max_vueltas=1, max_segundos=30)
        self.assertEqual(state['informes'], [])
        self.assertEqual(state['errores'], 1)
        record=json.loads((self.root/'run/ciclo-001/registro.json').read_text())
        self.assertEqual(record['estado'], 'RECOLECCION_PARCIAL')

    def test_seleccion_incompatible_no_inicia_corrida(self):
        for selection in ([], ['otra'], ['cdc','cdc']):
            with self.assertRaises(ValueError): vigilar.ejecutar(self.root/'run', fuentes=selection)
        with self.assertRaises(ValueError):
            vigilar.ejecutar(self.root/'run', fuentes=['ecdc'], sin_red=True, entrada=self.root/'archivo')
        self.assertFalse((self.root/'run').exists())


if __name__=='__main__':unittest.main()
