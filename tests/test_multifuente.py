"""Feeds y observaciones SINTÉTICOS; no fuentes ni revisiones humanas reales."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import tempfile
import unittest
from unittest import mock
from urllib.request import Request

from bio.recolector import multifuente as m

OBS = '2026-09-19T12:00:00Z'
RSS = b'''<rss version="2.0"><channel><title>Fixture</title><item>
<title>Public health policy fixture</title><link>https://example.org/a</link>
<pubDate>Fri, 18 Sep 2026 12:00:00 GMT</pubDate>
</item></channel></rss>'''
ATOM = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
<title>Fixture atom</title><link rel="alternate" href="https://example.org/b"/>
<published>2026-09-17T02:00:00Z</published></entry></feed>'''


class MultifuenteTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(m, 'datetime', wraps=datetime)
        clock = patcher.start()
        self.addCleanup(patcher.stop)
        clock.now.return_value = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)

    def test_rss_atom_solo_campos_fuente_observacion_real(self):
        for raw in (RSS, ATOM):
            rows, meta = m.parsear_feed(raw, 'ecdc', OBS)
            self.assertEqual(len(rows), 1)
            self.assertEqual(set(rows[0]), {'id','fuente','fecha','url','claim_literal','recolectado_en'})
            self.assertEqual(rows[0]['recolectado_en'], OBS)
            self.assertEqual(meta['descartadas'], 0)
            self.assertIs(meta['cobertura_exhaustiva'], False)

    def test_xml_inseguro_html_y_limite_rechazados(self):
        for raw in (b'<!DOCTYPE rss [<!ENTITY x "fixture">]><rss/>', b'<html/>', b'bad',
                    b'x' * (m.MAX_BYTES + 1), '<rss/>'.encode('utf-16')):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                m.parsear_feed(raw, 'ecdc', OBS)

    def test_item_sin_fecha_o_futuro_no_se_inventa(self):
        for raw in (RSS.replace(b'<pubDate>', b'<otro>').replace(b'</pubDate>', b'</otro>'),
                    RSS.replace(b'18 Sep 2026', b'18 Sep 2027'),
                    RSS.replace(b'https://example.org/a', b'javascript:fixture')):
            rows, meta = m.parsear_feed(raw, 'ecdc', OBS)
            self.assertEqual(rows, [])
            self.assertEqual(meta['descartadas'], 1)

    def test_publicacion_futura_dentro_del_mismo_dia(self):
        for raw in (RSS.replace(b'18 Sep 2026 12:00:00', b'19 Sep 2026 23:00:00'),
                    ATOM.replace(b'2026-09-17T02:00:00Z', b'2026-09-19T23:00:00Z')):
            with self.subTest(raw=raw[:30]):
                rows, meta = m.parsear_feed(raw, 'ecdc', OBS)
                self.assertEqual(rows, [])
                self.assertEqual(meta['descartadas'], 1)

    def test_limite_items_y_feed_antiguo_visibles(self):
        item = RSS.split(b'<item>')[1].split(b'</item>')[0]
        raw = b'<rss><channel>' + b''.join(b'<item>'+item.replace(b'/a',('/a'+str(i)).encode())+b'</item>' for i in range(4)) + b'</channel></rss>'
        with mock.patch.object(m, 'MAX_ITEMS', 2):
            rows, meta = m.parsear_feed(raw, 'ecdc', OBS)
        self.assertEqual(len(rows), 2)
        self.assertEqual(meta['omitidas_por_limite'], 2)
        rows, meta = m.parsear_feed(RSS, 'ecdc', '2027-09-19T12:00:00Z')
        self.assertIn('SIN_PUBLICACIONES_RECIENTES', meta['advertencias'])
        self.assertEqual(rows[0]['fecha'], '2026-09-18')

    def test_redirecciones_fuera_de_allowlist_rechazadas(self):
        request = Request(m.FUENTES['ecdc']['url'])
        handler = m.Redirecciones({'www.ecdc.europa.eu'})
        for url in ('http://www.ecdc.europa.eu/feed', 'https://127.0.0.1/feed',
                    'https://www.ecdc.europa.eu:444/feed', 'https://u:p@www.ecdc.europa.eu/feed'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, '', {}, url)

    def test_redireccion_no_lee_cuerpo_sin_limite(self):
        request = Request(m.FUENTES['ecdc']['url'])
        request.timeout = 15
        body = mock.Mock()
        body.read.side_effect = AssertionError('no leer cuerpo de redirección')
        handler = m.Redirecciones({'www.ecdc.europa.eu'})
        with self.assertRaises(ValueError):
            handler.http_error_302(request, body, 302, '',
                                   {'location':'https://www.ecdc.europa.eu/nuevo-feed'})
        body.read.assert_not_called()

    def test_descarga_limitada_y_subproceso_timeout(self):
        class Response(io.BytesIO):
            def geturl(self): return m.FUENTES['ecdc']['url']
        opener = mock.Mock()
        opener.open.return_value = Response(b'x' * (m.MAX_BYTES + 1))
        with mock.patch.object(m.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(ValueError): m.descargar('ecdc')
        with mock.patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixture', 15)):
            with self.assertRaises(subprocess.TimeoutExpired): m.descargar_acotado('ecdc')

    def test_descargador_real_se_autolimita_sin_red(self):
        script = '''import time
from bio.recolector import multifuente as m
m.TIMEOUT=0.2
m.descargar=lambda _: time.sleep(10)
m.main(['--descargar','ecdc'])
'''
        result = subprocess.run([sys.executable,'-c',script],capture_output=True,cwd=m.RAIZ,timeout=3)
        self.assertEqual(result.returncode,2)

    def test_descargador_no_queda_huerfano_si_muere_supervisor(self):
        with tempfile.TemporaryDirectory() as tmp:
            ready = Path(tmp).resolve() / 'ready'
            child_script = '''import sys,time
from pathlib import Path
from bio.recolector import multifuente as m
def lento(_):
    Path(sys.argv[2]).write_text('FIXTURE esperando')
    time.sleep(60)
    return b''
m.descargar=lento
m.main(['--descargar','ecdc','--padre',sys.argv[1]])
'''
            parent_script = '''import subprocess,sys,os,time
p=subprocess.Popen([sys.executable,'-c',sys.argv[1],str(os.getpid()),sys.argv[2]])
print(p.pid,flush=True)
time.sleep(60)
'''
            parent = subprocess.Popen([sys.executable,'-c',parent_script,child_script,str(ready)],
                                      stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=m.RAIZ)
            child_pid = None
            try:
                child_pid = int(parent.stdout.readline())
                deadline = time.monotonic()+3
                while not ready.exists() and time.monotonic()<deadline: time.sleep(0.05)
                self.assertTrue(ready.exists())
                parent.kill()
                # El nieto heredó los pipes: communicate solo termina cuando también sale.
                parent.communicate(timeout=3)
                child_pid = None
            finally:
                if parent.poll() is None: parent.kill()
                if child_pid is not None:
                    try: os.kill(child_pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                parent.communicate(timeout=3)

    def test_snapshot_hashes_dedup_y_no_sobrescribir(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp).resolve() / 'run'
            with mock.patch.object(m, 'descargar_acotado', return_value=RSS):
                result = m.ejecutar(out, ['ecdc', 'oms'])
            self.assertEqual(result['estado'], 'RECOLECCION_COMPLETA')
            self.assertEqual(result['senales_unicas'], 1)
            self.assertEqual(len(result['fuentes']), 2)
            self.assertIs(result['publicable'], False)
            for name, digest in result['artefactos_sha256'].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError): m.ejecutar(out, ['ecdc'])

    def test_fallo_de_fuente_no_se_oculta_con_datos_de_otra(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(m, 'descargar_acotado', side_effect=[RSS, OSError('FIXTURE')]):
                r = m.ejecutar(Path(tmp).resolve() / 'run', ['ecdc', 'oms'])
            self.assertEqual(r['estado'], 'RECOLECCION_PARCIAL')
            self.assertEqual(r['errores'], 1)
            self.assertEqual(r['senales_unicas'], 1)

    def test_seleccion_invalida_y_carpeta_enlace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for selection in ([], ['desconocida'], ['ecdc','ecdc']):
                with self.assertRaises(ValueError): m.ejecutar(root / 'run', selection)
            (root / 'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError): m.ejecutar(root / 'link/run', ['ecdc'])


if __name__ == '__main__': unittest.main()
