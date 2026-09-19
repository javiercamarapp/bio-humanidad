import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from bio import bucle
from test_validador import CANDIDATO


def dorado_sintetico(root):
    """Solo fixtures temporales. Nunca se escribe en el dorado del proyecto."""
    path = root / 'datos/dorado/senales.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [dict(id=str(i), claim_literal='Fixture de calidad de datos, no evidencia real',
                 url='https://www.who.int/example', revisor='FIXTURE SINTÉTICO',
                 fecha_revision='2026-09-19', origen_etiqueta='humano',
                 categoria_humana='otro', severidad_humana='no_aplica') for i in range(50)]
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    return path


class BucleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.candidates = self.root / 'salidas/hipotesis'
        self.candidates.mkdir(parents=True)

    def candidate(self, i=1):
        path = self.candidates / f'{i:03d}.md'
        path.write_text(CANDIDATO + f'\nRegistro de prueba {i}.')
        return path

    def run_loop(self, **kwargs):
        return bucle.ejecutar(self.root, **kwargs)

    def test_sin_dorado_cero_intentos_y_sin_worker(self):
        self.candidate()
        with mock.patch.object(bucle, 'evaluar_subproceso') as worker:
            result = self.run_loop()
        self.assertEqual(result['motivo_parada'], 'DORADO_PENDIENTE')
        self.assertEqual(result['vueltas'], 0)
        worker.assert_not_called()
        self.assertTrue((Path(result['corrida']) / 'estado.json').is_file())

    def test_rechaza_dorado_con_etiquetas_automaticas(self):
        path = dorado_sintetico(self.root)
        path.write_text(path.read_text().replace('"humano"', '"modelo"'))
        self.assertTrue(bucle.validar_dorado(self.root))

    def test_dorado_con_claves_duplicadas_se_bloquea(self):
        path = dorado_sintetico(self.root)
        lines = path.read_text().splitlines()
        lines[0] = lines[0][:-1] + ', "categoria_humana": "brote"}'
        path.write_text('\n'.join(lines) + '\n')
        self.assertTrue(bucle.validar_dorado(self.root))

    def test_dorado_50_ids_duplicados_no_cuenta(self):
        path = dorado_sintetico(self.root)
        path.write_text(path.read_text().splitlines()[0] + '\n')
        path.write_text(path.read_text() * 50)
        self.assertTrue(bucle.validar_dorado(self.root))

    def test_worker_real_se_detiene_en_revision_humana(self):
        dorado_sintetico(self.root)
        original = self.candidate()
        before = original.read_bytes()
        result = self.run_loop(sin_red=True)
        self.assertEqual(result['motivo_parada'], 'PENDIENTE_HUMANO')
        self.assertEqual(result['vueltas'], 1)
        self.assertEqual(result['aceptadas'], 0)
        self.assertEqual(original.read_bytes(), before)
        self.assertEqual(result['gasto_api_usd'], 0)

    def test_cola_vacia_no_inventa_candidatos(self):
        dorado_sintetico(self.root)
        result = self.run_loop()
        self.assertEqual(result['motivo_parada'], 'COLA_AGOTADA')
        self.assertEqual(result['vueltas'], 0)

    def test_limite_vueltas_no_se_reinicia_al_reanudar(self):
        dorado_sintetico(self.root)
        self.candidate(1)
        self.candidate(2)
        rejected = {'estado': 'RECHAZADA', 'motivos': ['fixture']}
        with mock.patch.object(bucle, 'evaluar_subproceso', side_effect=lambda *a: dict(rejected)) as worker:
            first = self.run_loop(max_vueltas=1)
            resumed = self.run_loop(reanudar=Path(first['corrida']), max_vueltas=200)
        self.assertEqual(first['motivo_parada'], 'PRESUPUESTO')
        self.assertEqual(resumed['vueltas'], 1)
        self.assertEqual(worker.call_count, 1)

    def test_crash_registrado_y_se_sigue(self):
        dorado_sintetico(self.root)
        self.candidate(1)
        self.candidate(2)
        with mock.patch.object(bucle, 'evaluar_subproceso', side_effect=[
                subprocess.TimeoutExpired('fixture', 1), {'estado': 'RECHAZADA', 'motivos': ['fixture']} ]):
            result = self.run_loop()
        self.assertEqual(result['vueltas'], 2)
        self.assertEqual(result['estados']['ERROR'], 1)
        self.assertEqual(result['estados']['RECHAZADA'], 1)
        self.assertEqual(result['motivo_parada'], 'COLA_AGOTADA_CON_ERRORES')

    def test_agotamiento(self):
        dorado_sintetico(self.root)
        for i in range(4):
            self.candidate(i)
        with mock.patch.object(bucle, 'evaluar_subproceso', side_effect=lambda *a: {'estado': 'RECHAZADA', 'motivos': ['fixture']}):
            result = self.run_loop(sin_mejora=2)
        self.assertEqual(result['motivo_parada'], 'AGOTAMIENTO')
        self.assertEqual(result['vueltas'], 2)

    def test_aceptacion_reinicia_estancamiento_y_se_conserva(self):
        dorado_sintetico(self.root)
        for i in range(3):
            self.candidate(i)
        with mock.patch.object(bucle, 'evaluar_subproceso', side_effect=[
                {'estado': 'RECHAZADA', 'motivos': []},
                {'estado': 'ACEPTADA', 'motivos': []},
                {'estado': 'RECHAZADA', 'motivos': []}]):
            result = self.run_loop(sin_mejora=2)
        self.assertEqual(result['motivo_parada'], 'COLA_AGOTADA')
        self.assertEqual(result['vueltas'], 3)
        self.assertEqual(result['aceptadas'], 1)
        self.assertEqual(len(list((Path(result['corrida']) / 'intentos').glob('*/registro.json'))), 3)

    def test_hash_visto_no_se_procesa_dos_veces(self):
        dorado_sintetico(self.root)
        path = self.candidate()
        (self.candidates / 'duplicado.md').write_bytes(path.read_bytes())
        with mock.patch.object(bucle, 'evaluar_subproceso', side_effect=lambda *a: {'estado': 'RECHAZADA', 'motivos': []}) as worker:
            first = self.run_loop()
            result = self.run_loop(reanudar=Path(first['corrida']))
        self.assertEqual(worker.call_count, 1)
        self.assertEqual(result['vueltas'], 1)

    def test_guardia_cambio_codigo_descarta_intento_incompleto(self):
        dorado_sintetico(self.root)
        self.candidate()
        protected = self.root / 'bio/example.py'
        protected.parent.mkdir()
        protected.write_text('# antes')

        def mutate(*args):
            protected.write_text('# después')
            return {'estado': 'ACEPTADA', 'motivos': []}

        with mock.patch.object(bucle, 'evaluar_subproceso', side_effect=mutate):
            result = self.run_loop()
        self.assertEqual(result['motivo_parada'], 'PROTEGIDOS_CAMBIARON')
        self.assertEqual(result['aceptadas'], 0)
        self.assertEqual(result['vueltas'], 0)

    def test_etiquetar_dorado_requiere_nueva_corrida(self):
        first = self.run_loop()
        dorado_sintetico(self.root)
        second = self.run_loop(reanudar=Path(first['corrida']))
        self.assertEqual(second['motivo_parada'], 'PROTEGIDOS_CAMBIARON')

    def test_cerrojo_excluye_otro_proceso(self):
        first = self.run_loop()
        run = Path(first['corrida'])
        with (run / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'bloqueo'):
                self.run_loop(reanudar=run)

    def test_estado_corrupto_no_reinicia_presupuesto(self):
        first = self.run_loop()
        run = Path(first['corrida'])
        (run / 'config.json').write_text('{corrupto')
        with self.assertRaises(ValueError):
            self.run_loop(reanudar=run)

    def test_snapshot_adulterado_impide_reanudar(self):
        dorado_sintetico(self.root)
        self.candidate()
        result = self.run_loop(sin_red=True)
        run = Path(result['corrida'])
        next((run / 'intentos').glob('*/candidato.md')).write_text('modificado')
        with self.assertRaisesRegex(ValueError, 'historial inconsistente'):
            self.run_loop(reanudar=run)

    def test_protege_ruta_de_salida_symlink(self):
        outside = self.root / 'fuera'
        outside.mkdir()
        (self.root / 'salidas/bucle').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'enlaces'):
            self.run_loop()
        self.assertEqual(list(outside.iterdir()), [])

    def test_presupuesto_invalido(self):
        for kwargs in [{'max_vueltas': 0}, {'max_vueltas': 201}, {'max_segundos': -1},
                       {'max_segundos': 14 * 86400 + 1}, {'sin_mejora': 0}, {'timeout_vuelta': 301}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_loop(**kwargs)

    def test_no_acepta_resultado_tardio(self):
        dorado_sintetico(self.root)
        self.candidate()
        now = [1000.0]

        def slow(*args):
            now[0] += 5
            return {'estado': 'ACEPTADA', 'motivos': []}

        with mock.patch.object(bucle.time, 'time', side_effect=lambda: now[0]), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=slow):
            result = self.run_loop(max_segundos=1)
        self.assertEqual(result['motivo_parada'], 'PRESUPUESTO')
        self.assertEqual(result['aceptadas'], 0)

    def test_retroceso_reloj_en_ultimo_intento_no_acepta(self):
        dorado_sintetico(self.root)
        self.candidate()
        now = [1000.0]

        def rollback(*args):
            now[0] = 999.0
            return {'estado': 'ACEPTADA', 'motivos': []}

        with mock.patch.object(bucle.time, 'time', side_effect=lambda: now[0]), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=rollback):
            result = self.run_loop(max_segundos=1)
        self.assertEqual(result['motivo_parada'], 'RELOJ_RETROCEDIO')
        self.assertEqual(result['aceptadas'], 0)

    def test_reloj_civil_congelado_no_extiende_presupuesto(self):
        dorado_sintetico(self.root)
        self.candidate()
        monotonic = [100.0]

        def slow(*args):
            monotonic[0] += 5
            return {'estado': 'ACEPTADA', 'motivos': []}

        with mock.patch.object(bucle.time, 'time', return_value=1000.0), \
                mock.patch.object(bucle.time, 'monotonic', side_effect=lambda: monotonic[0]), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=slow):
            result = self.run_loop(max_segundos=1)
        self.assertEqual(result['motivo_parada'], 'PRESUPUESTO')
        self.assertEqual(result['aceptadas'], 0)

    def test_reanudar_detecta_reloj_anterior_al_ultimo_checkpoint(self):
        dorado_sintetico(self.root)
        self.candidate()
        now = [1000.0]

        def advance(*args):
            now[0] = 1020.0
            return {'estado': 'RECHAZADA', 'motivos': []}

        with mock.patch.object(bucle.time, 'time', side_effect=lambda: now[0]), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=advance):
            first = self.run_loop(max_segundos=100)
            now[0] = 1010.0
            result = self.run_loop(reanudar=Path(first['corrida']))
        self.assertEqual(result['motivo_parada'], 'RELOJ_RETROCEDIO')
        self.assertGreaterEqual(result['tiempo_consumido'], first['tiempo_consumido'])

    def test_snapshot_incompleto_no_cuenta_como_aceptado(self):
        dorado_sintetico(self.root)
        first = self.run_loop()
        run = Path(first['corrida'])
        pending = run / 'intentos/.incompleto-fixture'
        pending.mkdir()
        (pending / 'candidato.md').write_text(CANDIDATO)
        result = self.run_loop(reanudar=run)
        self.assertEqual(result['aceptadas'], 0)
        self.assertEqual(result['vueltas'], 0)

    def test_candidato_vacio_produce_estado_no_crash(self):
        dorado_sintetico(self.root)
        (self.candidates / 'vacio.md').write_bytes(b'')
        result = self.run_loop()
        self.assertEqual(result['motivo_parada'], 'CANDIDATO_INVALIDO')
        self.assertEqual(result['vueltas'], 0)

    def test_candidato_symlink_no_se_lee(self):
        dorado_sintetico(self.root)
        original = self.root / 'original.md'
        original.write_text(CANDIDATO)
        (self.candidates / 'enlace.md').symlink_to(original)
        result = self.run_loop()
        self.assertEqual(result['motivo_parada'], 'CANDIDATO_INVALIDO')

    def test_worker_salida_malformada_falla(self):
        path = self.candidate()
        with mock.patch.object(bucle.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{}', '')):
            with self.assertRaises(KeyError):
                bucle.evaluar_subproceso(path, self.root / 'datos/revisiones', [], True, 1)

    def test_worker_hash_incorrecto_falla(self):
        path = self.candidate()
        output = json.dumps({'resultados': [{'estado': 'ACEPTADA', 'sha256': '0' * 64}]})
        with mock.patch.object(bucle.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output, '')):
            with self.assertRaisesRegex(ValueError, 'hash'):
                bucle.evaluar_subproceso(path, self.root / 'datos/revisiones', [], True, 1)

    def test_placeholder_estado_no_se_sobrescribe(self):
        first = self.run_loop()
        run = Path(first['corrida'])
        (run / 'estado.json').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            self.run_loop(reanudar=run)


if __name__ == '__main__':
    unittest.main()
