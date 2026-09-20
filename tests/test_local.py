"""Contratos locales con servidor HTTP sintético; no son evaluaciones de modelos."""
import copy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

from bio import ollama_local as o, pipeline_local as p, evaluacion

S = dict(id='fixture-1', fuente='FIXTURE', fecha='2026-01-01',
         recolectado_en='2026-01-01T12:00:00Z', url='https://example.org/fixture',
         claim_literal='Weekly public health surveillance report')
MODELS = {'mini:1': ('a'*64, 'gemma4'), 'grande:1': ('b'*64, 'qwen35')}


class Servidor:
    def __init__(self):
        self.chat_count = 0
        self.cambio = False
        self.mal = False
        self.delay = 0
        self.mode = None
        self.get_count = 0
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def send(self, value):
                raw = json.dumps(value).encode()
                self.send_response(200); self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                try: self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError): pass
            def do_GET(self):
                outer.get_count += 1
                if outer.mode == 'redirect':
                    self.send_response(302);self.send_header('Location','http://127.0.0.1:1/evil')
                    self.send_header('Content-Length','0');self.end_headers();return
                if outer.mode == 'big': self.send({'data':'x'*o.MAX_BYTES});return
                if outer.mode == 'duplicate':
                    raw=b'{"models":[],"models":[]}'
                    self.send_response(200);self.send_header('Content-Length',str(len(raw)))
                    self.end_headers();self.wfile.write(raw);return
                rows = []
                for name, (digest, family) in MODELS.items():
                    if outer.cambio and outer.chat_count: digest = 'c'*64
                    rows.append(dict(name=name, digest=digest, size=100, details={'family':family}))
                self.send({'models': rows})
            def do_POST(self):
                req = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/api/show':
                    self.send({'details': {'family': MODELS[req['model']][1]}}); return
                outer.chat_count += 1
                time.sleep(outer.delay)
                datum = json.loads(req['messages'][1]['content'])
                text = datum['senal']['claim_literal']
                role = req['messages'][0]['content'].split('\n')[0]
                if role == 'ROLE=extractor': data = {'categoria':'vigilancia','cita':text}
                elif role == 'ROLE=analista': data = {'limitacion':'solo_titular','cita':text}
                else: data = {'dictamen':'objecion','motivo':'falta_fuente_completa','cita':text}
                if role != 'ROLE=extractor':data['observacion']='Solo se recibió un titular; no se revisó la fuente completa.'
                if outer.mal: data['publicable'] = True
                self.send(dict(model=req['model'], done=True, done_reason='stop',
                    message={'role':'assistant','content':json.dumps(data)}, eval_count=8, eval_duration=1000))
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.port = self.http.server_address[1]
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
    def __enter__(self): self.thread.start(); return self
    def __exit__(self, *args): self.http.shutdown(); self.http.server_close(); self.thread.join()


class LocalTests(unittest.TestCase):
    def test_validacion_citas_categorias_y_aprobaciones(self):
        self.assertEqual(o.validar('extractor', {'categoria':None,'cita':''}, S)['categoria'], None)
        bad = [dict(categoria='vigilancia',cita='inventada'),
               dict(categoria='vigilancia',cita=S['claim_literal'],publicable=True),
               dict(categoria='invalida',cita=S['claim_literal']),
               dict(categoria=None,cita=S['claim_literal'])]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError): o.validar('extractor',value,S)
        with self.assertRaises(ValueError):
            o.validar('refutador',dict(dictamen='sin_objecion_documental',motivo='falta_fuente_completa',cita='Weekly',observacion='Fixture de contradicción documental.'),S)

    def test_observacion_documental_acotada_sin_fuentes_inventadas(self):
        value=dict(limitacion='solo_titular',cita='Weekly',observacion='El título no aporta cifras ni texto completo.')
        self.assertEqual(o.validar('analista',value,S),value)
        for text in ('','x'*401,'Fuente inventada https://example.org/otra'):
            with self.assertRaises(ValueError):o.validar('analista',dict(value,observacion=text),S)

    def test_transporte_real_local_y_modelo_cambiado(self):
        with Servidor() as server:
            client=o.Cliente(server.port)
            identity=client.identidad('mini:1')
            result=client.inferir('extractor',S,identity,timeout=5)
            self.assertEqual(result['datos']['categoria'],'vigilancia')
            self.assertEqual(client.solicitudes,1)
            server.cambio=True
            with self.assertRaises(ValueError): client.inferir('extractor',S,identity,timeout=5)
            self.assertEqual(server.chat_count,1)

    def test_cambio_durante_generacion_y_campos_extra(self):
        with Servidor() as server:
            client=o.Cliente(server.port);identity=client.identidad('mini:1');server.cambio=True
            with self.assertRaises(ValueError): client.inferir('extractor',S,identity,timeout=5)
        with Servidor() as server:
            client=o.Cliente(server.port);identity=client.identidad('mini:1');server.mal=True
            with self.assertRaises(ValueError): client.inferir('extractor',S,identity,timeout=5)

    def test_timeout_y_stop_durante_http(self):
        with Servidor() as server:
            server.delay=3
            client=o.Cliente(server.port);identity=client.identidad('mini:1')
            start=time.monotonic()
            with self.assertRaises(TimeoutError): client.inferir('extractor',S,identity,timeout=.6)
            self.assertLess(time.monotonic()-start,2)
            stop=threading.Event();timer=threading.Timer(.4,stop.set);timer.start()
            try:
                with self.assertRaises(InterruptedError): client.inferir('extractor',S,identity,timeout=5,detener=stop.is_set)
            finally:timer.join()

    def test_http_hostil_no_redirige_ni_acepta_exceso_o_json_ambiguo(self):
        for mode in ('redirect','big','duplicate'):
            with self.subTest(mode=mode),Servidor() as server:
                server.mode=mode
                with self.assertRaises(ValueError):o.Cliente(server.port).identidad('mini:1')
                self.assertEqual(server.get_count,1)
        for port in (True,0,65536):
            with self.assertRaises(ValueError):o.Cliente(port)

    def test_hijo_se_detiene_si_muere_el_padre(self):
        import subprocess,sys,select
        with Servidor() as server:
            server.delay=10
            payload={'model':'mini:1','messages':[{'content':'ROLE=extractor'},
                       {'content':json.dumps({'senal':S})}]}
            code=('import bio.ollama_local as o; old=o.subprocess.Popen\n'
                  'def create(*a,**k):\n p=old(*a,**k);print(p.pid,flush=True);return p\n'
                  'o.subprocess.Popen=create\n'
                  f'o.solicitar({server.port},"/api/chat",{payload!r},timeout=15)')
            parent=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                self.assertTrue(select.select([parent.stdout],[],[],5)[0])
                child=int(parent.stdout.readline())
                parent.kill();parent.communicate(timeout=3)
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    state=subprocess.run(['ps','-p',str(child),'-o','stat='],capture_output=True,text=True)
                    if state.returncode:
                        self.assertFalse(state.stderr.strip(), state.stderr)
                        break
                    if state.stdout.strip().startswith('Z'):break
                    time.sleep(.05)
                else:self.fail('worker huérfano sigue vivo')
            finally:
                if parent.poll() is None:parent.kill()
                parent.communicate(timeout=3)

    def test_prompt_excesivo_no_inicia_generacion(self):
        with Servidor() as server:
            client=o.Cliente(server.port);identity=client.identidad('mini:1')
            with self.assertRaises(ValueError):client.inferir('extractor',dict(S,claim_literal='x'*4096),identity,timeout=5)
            self.assertEqual(server.chat_count,0);self.assertEqual(client.solicitudes,0)

    def test_no_modelos_cloud_o_inexistentes(self):
        with Servidor() as server:
            client=o.Cliente(server.port)
            for name in ('mini:cloud','inexistente:1','mini','http://remoto'):
                with self.subTest(name=name),self.assertRaises(ValueError):client.identidad(name)
            self.assertEqual(server.chat_count,0)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.input=self.root/'entrada.jsonl';self.input.write_text(json.dumps(S)+'\n')
    def tearDown(self):self.tmp.cleanup()
    def run_pipeline(self,server,**kwargs):
        return p.ejecutar(self.input,self.root/'salida',extractor='mini:1',analista='grande:1',
                          refutador=kwargs.pop('refutador','mini:1'),puerto=server.port,cantidad=1,
                          max_segundos=kwargs.pop('max_segundos',30),**kwargs)
    def test_e2e_local_sintetico_sin_etiquetas_humanas(self):
        import hashlib
        original=self.input.read_bytes()
        with Servidor() as server:result=self.run_pipeline(server)
        self.assertEqual(result['estado'],'PIPELINE_LOCAL_COMPLETO')
        self.assertEqual(result['solicitudes_inferencia'],3)
        self.assertFalse(result['publicable'])
        self.assertEqual(result['estado_validacion'],'PENDIENTE_DORADO')
        for name,sha in result['artefactos_sha256'].items():
            self.assertEqual(hashlib.sha256((self.root/'salida'/name).read_bytes()).hexdigest(),sha)
        pred=json.loads((self.root/'salida/predicciones.jsonl').read_text())
        self.assertEqual(pred['origen_prediccion'],'ollama_v1');self.assertFalse(pred['verificado'])
        self.assertEqual(self.input.read_bytes(),original)
        with Servidor() as server, self.assertRaises(FileExistsError):self.run_pipeline(server)
    def test_no_misma_familia_refutador(self):
        with Servidor() as server,self.assertRaises(ValueError):self.run_pipeline(server,refutador='grande:1')
        self.assertFalse((self.root/'salida/manifest.json').exists())
    def test_fallo_no_finaliza(self):
        with Servidor() as server:
            server.mal=True
            with self.assertRaises(ValueError):self.run_pipeline(server)
        self.assertFalse((self.root/'salida/manifest.json').exists())
        state=json.loads((self.root/'salida/estado.json').read_text())
        self.assertEqual(state['estado'],'ERROR');self.assertFalse(state['publicable'])
    def test_alias_no_simula_independencia(self):
        for digest,family in [('b'*64,'gemma4'),('c'*64,'qwen35')]:
            with mock.patch.dict(MODELS,{'alias:1':(digest,family)}),Servidor() as server:
                with self.assertRaises(ValueError):self.run_pipeline(server,refutador='alias:1')
                self.assertEqual(server.chat_count,0)

    def test_stop_durante_generacion_no_finaliza(self):
        with Servidor() as server:
            server.delay=2
            def stop():
                end=time.monotonic()+10
                while time.monotonic()<end:
                    if server.chat_count:
                        (self.root/'salida/STOP').touch();return
                    time.sleep(.03)
            t=threading.Thread(target=stop,daemon=True);t.start()
            try:
                with self.assertRaises(InterruptedError):self.run_pipeline(server)
            finally:t.join(timeout=11)
        self.assertFalse((self.root/'salida/manifest.json').exists())
        self.assertEqual(json.loads((self.root/'salida/estado.json').read_text())['estado'],'ERROR')

    def test_escritura_final_fuera_de_tiempo_retira_manifiesto(self):
        class Clock:
            elapsed=0
            retrocedio=False
            def segundos(self):return self.elapsed
        clock=Clock();write=p.escribir_json
        def delayed(path,data):
            write(path,data)
            if path.name=='manifest.json':clock.elapsed=31
        with Servidor() as server,mock.patch.object(p,'Reloj',return_value=clock),mock.patch.object(p,'escribir_json',side_effect=delayed):
            with self.assertRaises(TimeoutError):self.run_pipeline(server)
        self.assertFalse((self.root/'salida/manifest.json').exists())
        self.assertTrue((self.root/'salida/manifest-no-finalizado.json').exists())
        self.assertEqual(json.loads((self.root/'salida/estado.json').read_text())['estado'],'ERROR')

    def test_cli_real_sobre_servidor_fixture(self):
        import subprocess,sys
        with Servidor() as server:
            run=subprocess.run([sys.executable,'-m','bio.pipeline_local','--entrada',str(self.input),
                '--salida',str(self.root/'cli'),'--extractor','mini:1','--analista','grande:1',
                '--refutador','mini:1','--puerto',str(server.port),'--cantidad','1','--max-segundos','30'],
                capture_output=True,text=True,timeout=40)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout)['estado'],'PIPELINE_LOCAL_COMPLETO')

    def test_dorado_fixture_mide_cobertura_sin_rellenar_ausencias(self):
        rows=[dict(S,id=str(i),url=f'https://example.org/{i}') for i in range(50)]
        self.input.write_text(''.join(json.dumps(s)+'\n' for s in rows))
        gold=[dict(s,categoria_humana='vigilancia',severidad_humana='no_aplica',
                   revisor='FIXTURE_NO_HUMANO_REAL',origen_etiqueta='humano',fecha_revision='2026-01-02') for s in rows]
        path=self.root/'dorado-fixture.jsonl';path.write_text(''.join(json.dumps(s)+'\n' for s in gold))
        with Servidor() as server:result=self.run_pipeline(server,dorado=path)
        metrics=json.loads((self.root/'salida/metricas.json').read_text())
        self.assertEqual(result['estado_validacion'],'EVALUADO_TECNICAMENTE')
        self.assertEqual(metrics['correctas'],1);self.assertEqual(metrics['ausentes'],49)
        self.assertEqual(metrics['cobertura'],.02)
        self.assertFalse(result['publicable'])

    def test_evaluacion_explicita_y_default_intacto(self):
        gold=[dict(S,id=str(i),categoria_humana='vigilancia',severidad_humana='no_aplica',
                   revisor='FIXTURE_NO_HUMANO_REAL',origen_etiqueta='humano',fecha_revision='2026-01-02') for i in range(50)]
        predictions=[dict(id=s['id'],sha256_senal=evaluacion.huella_senal(s),categoria_predicha='vigilancia',
                         abstencion=False,origen_prediccion='ollama_v1') for s in gold]
        self.assertEqual(evaluacion.evaluar(gold,predictions)['invalidas'],50)
        self.assertEqual(evaluacion.evaluar(gold,predictions,origen_esperado='ollama_v1')['correctas'],50)
        with self.assertRaises(ValueError):evaluacion.evaluar(gold,predictions,origen_esperado='arbitrario')

if __name__=='__main__':unittest.main()
