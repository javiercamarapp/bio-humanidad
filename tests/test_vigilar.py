"""Fixtures temporales y subprocesos offline; nunca se consulta la red."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from bio import vigilar


class VigilarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.entrada = self.root / 'fixture.jsonl'
        self.salida = self.root / 'run'
        self.raw = ''.join(json.dumps(dict(id=str(i), fuente='HN', fecha='2026-09-18',
                    claim_literal='Public dashboard updated', url='https://example.org/' + str(i),
                    recolectado_en='2026-09-19T12:00:00Z')) + '\n' for i in range(50)).encode()
        self.entrada.write_bytes(self.raw)

    def ejecutar(self, **kwargs):
        config = dict(entrada=self.entrada, sin_red=True, max_vueltas=1,
                      intervalo_segundos=1, max_segundos=30)
        config.update(kwargs)
        return vigilar.ejecutar(self.salida, **config)

    def registros(self):
        return [json.loads(p.read_text()) for p in sorted(self.salida.glob('ciclo-*/registro.json'))]

    def test_preparacion_real_y_duplicados_no_modifica_entrada(self):
        result = self.ejecutar(max_vueltas=2)
        self.assertEqual(result['motivo_final'], 'MAX_VUELTAS')
        self.assertEqual(result['vueltas'], 2)
        self.assertEqual(len(result['informes']), 1)
        self.assertEqual([r['estado'] for r in self.registros()],
                         ['PREPARACION_COMPLETA', 'SIN_CAMBIOS'])
        manifest = json.loads((self.salida / result['informes'][0] / 'manifest.json').read_text())
        self.assertEqual(manifest['estado_validacion'], 'PENDIENTE_DORADO')
        self.assertIsNone(manifest['dorado_sha256'])
        self.assertTrue((self.salida / result['informes'][0] / 'informe.md').is_file())
        self.assertEqual(self.entrada.read_bytes(), self.raw)
        self.assertEqual((self.salida / 'titulares.jsonl').read_bytes(), self.raw)
        self.assertFalse(result['publicable'])
        self.assertFalse(result['proceso_activo'])
        self.assertFalse((self.salida / 'dorado-ausente.jsonl').exists())
        for path in self.salida.rglob('*.json'):
            data = json.loads(path.read_text())
            if 'publicable' in data:
                self.assertIs(data['publicable'], False)
        self.assertEqual(json.loads((self.salida / 'estado.json').read_text())['estado'], 'DETENIDO')

    def test_cambio_de_dia_recalcula_ventana_aunque_datos_sean_iguales(self):
        with mock.patch.object(vigilar, 'corte_utc', side_effect=['2026-09-20', '2026-09-21']):
            result = self.ejecutar(max_vueltas=2)
        self.assertEqual(len(result['informes']), 2)
        self.assertEqual([r['corte_exclusivo_utc'] for r in self.registros()],
                         ['2026-09-20', '2026-09-21'])

    def test_cambio_codigo_detiene_sin_ejecutar_nueva_version(self):
        with mock.patch.object(vigilar, 'huellas_codigo', side_effect=[{'v': 'a'}, {'v': 'b'}]), \
                mock.patch.object(vigilar, 'subproceso') as worker:
            result = self.ejecutar(sin_red=False, entrada=None)
        self.assertEqual(result['motivo_final'], 'CODIGO_CAMBIO')
        self.assertEqual(result['codigo_salida'], 2)
        worker.assert_not_called()
        self.assertFalse(result['proceso_activo'])

    def test_stop_durante_espera(self):
        dormir = time.sleep
        def stop(seconds):
            state = json.loads((self.salida / 'estado.json').read_text())
            if state['estado'] == 'ESPERANDO':
                (self.salida / 'STOP').touch()
            else:
                dormir(seconds)
        with mock.patch.object(vigilar.time, 'sleep', side_effect=stop):
            result = self.ejecutar(max_vueltas=24)
        self.assertEqual(result['motivo_final'], 'STOP')
        self.assertEqual(result['vueltas'], 1)
        self.assertEqual(result['codigo_salida'], 0)
        self.assertNotIn('siguiente_lectura', result)

    def test_muestra_insuficiente_cuenta_unicos(self):
        self.entrada.write_bytes(self.raw.splitlines()[0] + b'\n' + self.raw.splitlines()[0] + b'\n')
        result = self.ejecutar()
        self.assertEqual(self.registros()[0]['estado'], 'MUESTRA_INSUFICIENTE')
        self.assertEqual(self.registros()[0]['unicos'], 1)
        self.assertEqual(result['informes'], [])

    def test_salida_existente_y_enlaces_rechazados(self):
        self.salida.mkdir()
        with self.assertRaises(FileExistsError):
            self.ejecutar()
        self.salida.rmdir()
        self.salida.symlink_to(self.root / 'inexistente')
        with self.assertRaises(ValueError):
            self.ejecutar()
        self.salida.unlink()
        link = self.root / 'enlace.jsonl'
        link.symlink_to(self.entrada)
        with self.assertRaises(ValueError):
            self.ejecutar(entrada=link)
        parent = self.root / 'parent'
        parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            vigilar.ejecutar(parent / 'hijo', entrada=self.entrada, sin_red=True)

    def test_limites_y_tipos_rechazados(self):
        for field in ('max_vueltas', 'max_segundos', 'intervalo_segundos'):
            for value in (0, -1, float('inf'), float('nan'), '2', True, None):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.ejecutar(**{field: value})
        for config in ({'max_vueltas': 25}, {'max_vueltas': 1.5}, {'max_segundos': 86401},
                       {'entrada': None}):
            with self.assertRaises(ValueError):
                self.ejecutar(**config)
        self.assertFalse(self.salida.exists())
        self.assertEqual(vigilar.main(['--salida', str(self.salida), '--intervalo-segundos', '59']), 2)

    def test_parciales_y_errores_consecutivos(self):
        def fallo(modulo, args, timeout, detener):
            self.assertEqual(modulo, 'bio.recolector.recolector')
            self.assertLessEqual(timeout, 300)
            return dict(codigo=2, stdout='parcial', stderr='fallo de fuente', interrupcion=None)
        with mock.patch.object(vigilar, 'subproceso', side_effect=fallo), \
                mock.patch.object(vigilar.time, 'sleep'):
            result = self.ejecutar(sin_red=False, entrada=None, max_vueltas=24)
        self.assertEqual(result['motivo_final'], 'TRES_ERRORES_CONSECUTIVOS')
        self.assertEqual(result['errores'], 3)
        self.assertEqual(result['vueltas'], 3)
        self.assertEqual(result['codigo_salida'], 2)
        self.assertEqual(result['informes'], [])
        self.assertEqual(self.registros()[0]['procesos'][0]['stdout'], 'parcial')
        self.assertEqual(self.registros()[0]['estado'], 'RECOLECCION_PARCIAL')

    def test_presupuesto_incluye_subproceso_y_rechaza_tardio(self):
        reloj = [100.0]
        def tardio(modulo, args, timeout, detener):
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 2)
            (self.salida / 'titulares.jsonl').write_bytes(self.raw)
            reloj[0] += 3
            return dict(codigo=0, stdout='terminado', stderr='', interrupcion=None)
        with mock.patch.object(vigilar.time, 'monotonic', side_effect=lambda: reloj[0]), \
                mock.patch.object(vigilar, 'subproceso', side_effect=tardio):
            result = self.ejecutar(sin_red=False, entrada=None, max_segundos=2)
        self.assertEqual(result['motivo_final'], 'PRESUPUESTO')
        self.assertEqual(result['segundos_transcurridos'], 3)
        self.assertEqual(result['informes'], [])
        self.assertEqual(self.registros()[0]['estado'], 'PRESUPUESTO')

    def test_reloj_civil_incluye_suspension_del_equipo(self):
        wall = [1000.0]
        def late(modulo, args, timeout, detener):
            (self.salida / 'titulares.jsonl').write_bytes(self.raw)
            wall[0] += 60
            return dict(codigo=0, stdout='', stderr='', interrupcion=None)
        with mock.patch.object(vigilar.time, 'time', side_effect=lambda: wall[0]), \
                mock.patch.object(vigilar.time, 'monotonic', return_value=100.0), \
                mock.patch.object(vigilar, 'subproceso', side_effect=late):
            result = self.ejecutar(sin_red=False, entrada=None, max_segundos=2)
        self.assertEqual(result['motivo_final'], 'PRESUPUESTO')
        self.assertEqual(result['informes'], [])

    def test_reloj_civil_retrocede_detiene_sin_entrega(self):
        wall = [1000.0]
        def retroceder(modulo, args, timeout, detener):
            wall[0] -= 1
            return dict(codigo=0, stdout='', stderr='', interrupcion=None)
        with mock.patch.object(vigilar.time, 'time', side_effect=lambda: wall[0]), \
                mock.patch.object(vigilar, 'subproceso', side_effect=retroceder):
            result = self.ejecutar(sin_red=False, entrada=None)
        self.assertEqual(result['motivo_final'], 'RELOJ_RETROCEDIO')
        self.assertEqual(result['codigo_salida'], 2)
        self.assertEqual(result['informes'], [])

    def test_suspension_durante_espera_agota_presupuesto(self):
        self.entrada.write_bytes(b'')
        wall = [1000.0]
        def suspender(seconds):
            wall[0] += 60
        with mock.patch.object(vigilar.time, 'time', side_effect=lambda: wall[0]), \
                mock.patch.object(vigilar.time, 'monotonic', return_value=100.0), \
                mock.patch.object(vigilar.time, 'sleep', side_effect=suspender):
            result = self.ejecutar(max_vueltas=24, max_segundos=2)
        self.assertEqual(result['motivo_final'], 'PRESUPUESTO')
        self.assertEqual(result['vueltas'], 1)
        self.assertEqual(result['segundos_transcurridos'], 60)

    def test_subproceso_suspension_agota_timeout_propio(self):
        wall = [1000.0]
        child = mock.MagicMock()
        child.__enter__.return_value = child
        def comunicar(**kwargs):
            wall[0] += 60
            return ('entrega tardia', '')
        child.communicate.side_effect = comunicar
        child.returncode = 0
        child.poll.return_value = 0
        with mock.patch.object(vigilar.time, 'time', side_effect=lambda: wall[0]), \
                mock.patch.object(vigilar.time, 'monotonic', return_value=100.0), \
                mock.patch.object(vigilar.subprocess, 'Popen', return_value=child):
            result = vigilar.subproceso('bio.preparacion', [], 2, lambda: None)
        self.assertEqual(result['interrupcion'], 'TIMEOUT')

    def test_suspension_en_checkpoint_no_conserva_entrega_tardia(self):
        persistir = vigilar.json_atomico
        for checkpoint in ('registro.json', 'estado.json'):
            with self.subTest(checkpoint=checkpoint):
                self.salida = self.root / checkpoint.replace('.', '-')
                wall = [1000.0]
                retrasado = [False]
                def lento(path, data):
                    persistir(path, data)
                    if (path.name == checkpoint and not retrasado[0]
                            and (data.get('informe') or data.get('informes'))):
                        retrasado[0] = True
                        wall[0] += 60
                with mock.patch.object(vigilar.time, 'time', side_effect=lambda: wall[0]), \
                        mock.patch.object(vigilar, 'json_atomico', side_effect=lento):
                    result = self.ejecutar(max_segundos=2)
                self.assertTrue(retrasado[0])
                self.assertEqual(result['motivo_final'], 'PRESUPUESTO')
                self.assertEqual(result['informes'], [])
                self.assertEqual(self.registros()[0]['estado'], 'PRESUPUESTO')
                self.assertNotIn('informe', self.registros()[0])
                self.assertEqual(json.loads((self.salida / 'estado.json').read_text())['informes'], [])

    def test_crash_inesperado_del_padre_persiste_error_no_exito(self):
        with mock.patch.object(vigilar, 'subproceso', side_effect=RuntimeError('crash fixture')):
            result = self.ejecutar(sin_red=False, entrada=None, max_vueltas=24)
        self.assertEqual(result['motivo_final'], 'ERROR_INESPERADO')
        self.assertEqual(result['codigo_salida'], 2)
        self.assertEqual(result['vueltas'], 1)
        self.assertEqual(result['errores'], 1)
        self.assertEqual(result['informes'], [])
        self.assertEqual(self.registros()[0]['estado'], 'ERROR_INESPERADO')
        self.assertTrue(self.registros()[0]['error'])
        state = json.loads((self.salida / 'estado.json').read_text())
        self.assertEqual(state['codigo_salida'], 2)
        self.assertEqual(state['motivo_final'], 'ERROR_INESPERADO')
        self.assertFalse(state['proceso_activo'])

    def test_timeout_y_codigo_error_registrados(self):
        for interruption, code in [('TIMEOUT', -9), (None, 1)]:
            self.salida = self.root / ('run-' + str(code))
            with mock.patch.object(vigilar, 'subproceso', return_value=dict(
                    codigo=code, stdout='salida', stderr='error', interrupcion=interruption)):
                result = self.ejecutar(sin_red=False, entrada=None)
            record = self.registros()[0]
            self.assertEqual(record['procesos'][0]['codigo'], code)
            self.assertEqual(record['procesos'][0]['stdout'], 'salida')
            self.assertEqual(result['errores'], 1)
            self.assertEqual(result['codigo_salida'], 2)

    def test_subproceso_timeout_mata_solo_hijo(self):
        child = mock.MagicMock()
        child.__enter__.return_value = child
        child.communicate.return_value = ('salida parcial', 'diagnostico')
        child.returncode = -9
        child.poll.return_value = -9
        with mock.patch.object(vigilar.subprocess, 'Popen', return_value=child) as popen:
            result = vigilar.subproceso('bio.preparacion', [], 0, lambda: None)
        child.kill.assert_called_once_with()
        self.assertEqual(result['interrupcion'], 'TIMEOUT')
        self.assertEqual(result['stdout'], 'salida parcial')
        self.assertEqual(popen.call_args.args[0][:3], [sys.executable, '-m', 'bio.preparacion'])
        self.assertEqual(popen.call_args.kwargs['cwd'], str(vigilar.RAIZ))

    def test_hijo_real_timeout_stop_y_crash(self):
        popen_real = subprocess.Popen
        for scenario in ('timeout', 'stop', 'crash'):
            with self.subTest(scenario=scenario):
                children = []
                code = ('import sys; print("diagnostico", flush=True); sys.exit(7)'
                        if scenario == 'crash' else
                        'import time; print("iniciado", flush=True); time.sleep(20)')
                def iniciar(command, **kwargs):
                    child = popen_real([sys.executable, '-c', code], **kwargs)
                    children.append(child)
                    return child
                inicio = time.monotonic()
                def detener():
                    return 'STOP' if scenario == 'stop' and time.monotonic() - inicio > .1 else None
                with mock.patch.object(vigilar.subprocess, 'Popen', side_effect=iniciar):
                    result = vigilar.subproceso('bio.preparacion', [], 1, detener)
                self.assertIsNotNone(children[0].poll())
                self.assertLess(time.monotonic() - inicio, 5)
                if scenario == 'crash':
                    self.assertEqual(result['codigo'], 7)
                    self.assertEqual(result['stdout'].strip(), 'diagnostico')
                    self.assertIsNone(result['interrupcion'])
                else:
                    self.assertEqual(result['interrupcion'], 'STOP' if scenario == 'stop' else 'TIMEOUT')
                    self.assertLess(result['codigo'], 0)

    def test_sigkill_no_autoriza_reanudar_ni_sobrescribir(self):
        child = subprocess.Popen([sys.executable, '-m', 'bio.vigilar', '--salida', str(self.salida),
                    '--sin-red', '--entrada', str(self.entrada), '--intervalo-segundos', '10',
                    '--max-segundos', '30'], cwd=str(vigilar.RAIZ),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            path = self.salida / 'estado.json'
            while time.monotonic() < deadline:
                if path.exists() and json.loads(path.read_text())['estado'] == 'ESPERANDO':
                    break
                time.sleep(.05)
            else:
                self.fail('no llegó a ESPERANDO')
            child.kill()
            child.communicate(timeout=5)
            self.assertEqual(child.returncode, -signal.SIGKILL)
            before = {p.relative_to(self.salida): p.read_bytes()
                      for p in self.salida.rglob('*') if p.is_file()}
            self.assertEqual(json.loads(path.read_text())['estado'], 'ESPERANDO')
            with self.assertRaises(FileExistsError):
                self.ejecutar()
            self.assertEqual(before, {p.relative_to(self.salida): p.read_bytes()
                                     for p in self.salida.rglob('*') if p.is_file()})
            self.assertEqual(self.entrada.read_bytes(), self.raw)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()

    def test_sigterm_finaliza_cli(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        child = subprocess.Popen([sys.executable, '-m', 'bio.vigilar', '--salida', str(self.salida),
                    '--sin-red', '--entrada', str(self.entrada), '--intervalo-segundos', '10',
                    '--max-segundos', '30'], cwd=str(vigilar.RAIZ), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                path = self.salida / 'estado.json'
                if path.exists() and json.loads(path.read_text())['estado'] == 'ESPERANDO':
                    break
                time.sleep(.05)
            else:
                self.fail('no llegó a ESPERANDO')
            child.send_signal(signal.SIGTERM)
            stdout, stderr = child.communicate(timeout=5)
            self.assertEqual(child.returncode, 0, stderr)
            data = json.loads(stdout)
            self.assertEqual(data['motivo_final'], 'SIGTERM')
            self.assertFalse(data['proceso_activo'])
            self.assertEqual(json.loads(path.read_text())['estado'], 'DETENIDO')
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()

    def test_presupuesto_durante_espera_es_parada_normal(self):
        self.entrada.write_bytes(b'')
        reloj = [100.0]
        def avanzar(seconds):
            reloj[0] += seconds
        with mock.patch.object(vigilar.time, 'monotonic', side_effect=lambda: reloj[0]), \
                mock.patch.object(vigilar.time, 'sleep', side_effect=avanzar):
            result = self.ejecutar(max_vueltas=24, max_segundos=2)
        self.assertEqual(result['motivo_final'], 'PRESUPUESTO')
        self.assertEqual(result['vueltas'], 2)
        self.assertEqual(result['codigo_salida'], 0)

    def test_keyboard_interrupt_persiste_parada(self):
        with mock.patch.object(vigilar, 'subproceso', side_effect=KeyboardInterrupt):
            result = self.ejecutar(sin_red=False, entrada=None)
        self.assertEqual(result['estado'], 'DETENIDO')
        self.assertEqual(result['motivo_final'], 'INTERRUPCION')
        self.assertEqual(result['vueltas'], 1)
        self.assertFalse(result['proceso_activo'])
        self.assertEqual(self.registros()[0]['estado'], 'INTERRUPCION')

    def test_entrada_demasiado_grande_guardia(self):
        with self.entrada.open('wb') as stream:
            stream.truncate(vigilar.MAX_BYTES + 1)
        result = self.ejecutar()
        self.assertEqual(result['codigo_salida'], 2)
        self.assertEqual(result['estado'], 'DETENIDO')
        self.assertEqual(result['vueltas'], 0)


if __name__ == '__main__':
    unittest.main()
