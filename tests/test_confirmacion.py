"""Confirmación bajo fallos: SOLO fixtures sintéticos temporales, sin red."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from bio import bucle
from test_bucle import dorado_sintetico
from test_validador import CANDIDATO


class ConfirmacionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def caso(self, name, cantidad=1):
        root = self.root / name
        dorado_sintetico(root)
        candidates = root / 'salidas/hipotesis'
        candidates.mkdir(parents=True)
        for i in range(cantidad):
            (candidates / f'{i}.md').write_text(CANDIDATO + f'\nFixture sintético {i}.')
        return root

    @staticmethod
    def resultado(*args):
        return dict(estado='ACEPTADA', motivos=['FIXTURE SINTETICO, NO PERSONA REAL'])

    def test_eliminar_marcador_tarde_invalida_y_no_reaparece_al_reanudar(self):
        unlink = Path.unlink
        for cantidad, objetivo in ((1, 1), (2, 1), (2, 2)):
            for salto in (60, -60):
                with self.subTest(cantidad=cantidad, objetivo=objetivo, salto=salto):
                    root = self.caso(f'{cantidad}-{objetivo}-{salto}', cantidad)
                    wall, calls = [1000.0], [0]
                    def lento(path, *args, **kwargs):
                        if path.name == '.confirmacion-pendiente':
                            calls[0] += 1
                            if calls[0] == objetivo:
                                wall[0] += salto
                        return unlink(path, *args, **kwargs)
                    with mock.patch.object(bucle.time, 'time', side_effect=lambda: wall[0]), \
                            mock.patch.object(Path, 'unlink', lento), \
                            mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado) as worker:
                        result = bucle.ejecutar(root, sin_red=True, max_segundos=2)
                        resumed = bucle.ejecutar(root, reanudar=Path(result['corrida']))
                    self.assertEqual(result['motivo_parada'], 'PRESUPUESTO' if salto > 0 else 'RELOJ_RETROCEDIO')
                    self.assertEqual(result['aceptadas'], objetivo - 1)
                    self.assertEqual(resumed['aceptadas'], objetivo - 1)
                    self.assertEqual(worker.call_count, objetivo)
                    self.assertEqual(bucle.cargar_intentos(Path(result['corrida']))[-1]['estado'], 'ERROR')

    def test_error_antes_o_despues_de_unlink_bloquea_recuperacion(self):
        unlink = Path.unlink
        for despues in (False, True):
            root = self.caso('error-' + str(despues))
            fired = [False]
            def fallar(path, *args, **kwargs):
                if path.name == '.confirmacion-pendiente' and not fired[0]:
                    fired[0] = True
                    if despues:
                        unlink(path, *args, **kwargs)
                    raise OSError('FIXTURE fallo en confirmación')
                return unlink(path, *args, **kwargs)
            with mock.patch.object(Path, 'unlink', fallar), \
                    mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado):
                with self.assertRaises(OSError):
                    bucle.ejecutar(root, sin_red=True)
            run = next((root / 'salidas/bucle').iterdir())
            with self.assertRaisesRegex(ValueError, 'confirmación pendiente'):
                bucle.ejecutar(root, reanudar=run)
            markers = list(run.glob('intentos/*/.confirmacion-pendiente'))
            self.assertEqual(len(markers), 1)
            self.assertGreater(markers[0].stat().st_size, 0)

    def test_invalidation_fallida_despues_de_unlink_conserva_bloqueo(self):
        root = self.caso('invalidacion')
        unlink, persistir = Path.unlink, bucle.json_atomico
        wall, fired = [1000.0], [False]
        def lento(path, *args, **kwargs):
            if path.name == '.confirmacion-pendiente' and not fired[0]:
                fired[0] = True
                wall[0] += 60
            return unlink(path, *args, **kwargs)
        def fallar(path, data):
            if path.name == 'registro.json' and data.get('estado') == 'ERROR':
                raise OSError('FIXTURE fallo al persistir invalidación')
            persistir(path, data)
        with mock.patch.object(bucle.time, 'time', side_effect=lambda: wall[0]), \
                mock.patch.object(Path, 'unlink', lento), \
                mock.patch.object(bucle, 'json_atomico', side_effect=fallar), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado):
            with self.assertRaises(OSError):
                bucle.ejecutar(root, sin_red=True, max_segundos=2)
        run = next((root / 'salidas/bucle').iterdir())
        with self.assertRaisesRegex(ValueError, 'confirmación pendiente'):
            bucle.ejecutar(root, reanudar=run)

    def test_fallo_al_restaurar_marcador_intenta_error_durable(self):
        root = self.caso('restauracion')
        unlink, abrir = Path.unlink, Path.open
        wall, fired, creaciones = [1000.0], [False], [0]
        def lento(path, *args, **kwargs):
            if path.name == '.confirmacion-pendiente' and not fired[0]:
                fired[0] = True
                wall[0] += 60
            return unlink(path, *args, **kwargs)
        def fallar(path, mode='r', *args, **kwargs):
            if path.name == '.confirmacion-pendiente' and mode == 'xb':
                creaciones[0] += 1
                if creaciones[0] == 2:
                    raise OSError('FIXTURE fallo único al restaurar marcador')
            return abrir(path, mode, *args, **kwargs)
        with mock.patch.object(bucle.time, 'time', side_effect=lambda: wall[0]), \
                mock.patch.object(Path, 'unlink', lento), mock.patch.object(Path, 'open', fallar), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado):
            with self.assertRaises(OSError):
                bucle.ejecutar(root, sin_red=True, max_segundos=2)
            run = next((root / 'salidas/bucle').iterdir())
            resumed = bucle.ejecutar(root, reanudar=run)
        self.assertEqual(creaciones[0], 2)
        self.assertEqual(resumed['aceptadas'], 0)
        self.assertEqual(bucle.cargar_intentos(run)[0]['estado'], 'ERROR')

    def test_cola_aceptada_requiere_inspeccion_al_recuperar(self):
        root = self.caso('cola-aceptada')
        with mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado):
            result = bucle.ejecutar(root, sin_red=True)
        self.assertEqual(result['aceptadas'], 1)
        run = Path(result['corrida'])
        before = {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError, 'aceptación final.*inspección'):
            bucle.ejecutar(root, reanudar=run)
        self.assertEqual(before, {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()})

    def test_fallos_combinados_y_presupuesto_monotonico_no_abren_recuperacion(self):
        for combinado in (True, False):
            with self.subTest(combinado=combinado):
                root = self.caso('combinado-' + str(combinado))
                wall, mono, fired, opens, failed = [1000.0], [100.0], [False], [0], [False]
                unlink, abrir, guardar = Path.unlink, Path.open, bucle.json_atomico
                def eliminar(path, *args, **kwargs):
                    value = unlink(path, *args, **kwargs)
                    if path.name == '.confirmacion-pendiente' and not fired[0]:
                        fired[0] = True
                        if combinado:
                            raise OSError('FIXTURE fallo tras unlink')
                        mono[0] += 60
                    return value
                def abrir_marcador(path, mode='r', *args, **kwargs):
                    if path.name == '.confirmacion-pendiente' and mode == 'xb':
                        opens[0] += 1
                        if combinado and opens[0] == 2:
                            raise OSError('FIXTURE fallo único restaurando marcador')
                    return abrir(path, mode, *args, **kwargs)
                def persistir(path, data):
                    target = (path.name == 'registro.json' and data.get('estado') == 'ERROR') if combinado else (
                        path.name == 'estado.json' and data.get('estados', {}).get('ERROR'))
                    if target and not failed[0]:
                        failed[0] = True
                        raise OSError('FIXTURE fallo único de persistencia')
                    guardar(path, data)
                with mock.patch.object(bucle.time, 'time', side_effect=lambda: wall[0]), \
                        mock.patch.object(bucle.time, 'monotonic', side_effect=lambda: mono[0]), \
                        mock.patch.object(Path, 'unlink', eliminar), mock.patch.object(Path, 'open', abrir_marcador), \
                        mock.patch.object(bucle, 'json_atomico', side_effect=persistir), \
                        mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado) as worker:
                    with self.assertRaises(OSError):
                        bucle.ejecutar(root, sin_red=True, max_segundos=2)
                    run = next((root / 'salidas/bucle').iterdir())
                    if combinado:
                        with self.assertRaisesRegex(ValueError, 'aceptación final.*inspección'):
                            bucle.ejecutar(root, reanudar=run)
                    else:
                        (root / 'salidas/hipotesis/otro.md').write_text(CANDIDATO + '\nSegundo fixture')
                        resumed = bucle.ejecutar(root, reanudar=run)
                        self.assertEqual(resumed['motivo_parada'], 'PRESUPUESTO')
                        self.assertEqual(resumed['aceptadas'], 0)
                        self.assertGreaterEqual(resumed['tiempo_consumido'], 60)
                    self.assertEqual(worker.call_count, 1)
                self.assertTrue(fired[0] and failed[0])

    def test_reinicio_del_equipo_bloquea_reanudacion(self):
        root = self.caso('arranque', 0)
        with mock.patch.object(bucle, 'id_arranque', side_effect=['arranque-A', 'arranque-B'], create=True):
            result = bucle.ejecutar(root, sin_red=True)
            with self.assertRaisesRegex(ValueError, 'arranque'):
                bucle.ejecutar(root, reanudar=Path(result['corrida']))

    def test_cancelacion_tras_unlink_no_recupera_aceptacion(self):
        root = self.caso('cancelacion')
        unlink, fired = Path.unlink, [False]
        def cancelar(path, *args, **kwargs):
            value = unlink(path, *args, **kwargs)
            if path.name == '.confirmacion-pendiente' and not fired[0]:
                fired[0] = True
                raise KeyboardInterrupt('FIXTURE cancelación')
            return value
        with mock.patch.object(Path, 'unlink', cancelar), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado):
            with self.assertRaises(KeyboardInterrupt):
                bucle.ejecutar(root, sin_red=True)
        run = next((root / 'salidas/bucle').iterdir())
        with self.assertRaisesRegex(ValueError, 'pendiente|aceptación final'):
            bucle.ejecutar(root, reanudar=run)

    def test_fallo_estado_tras_invalidar_no_resucita_aceptacion(self):
        root = self.caso('estado')
        unlink, persistir = Path.unlink, bucle.json_atomico
        wall, fired, failed = [1000.0], [False], [False]
        def lento(path, *args, **kwargs):
            if path.name == '.confirmacion-pendiente' and not fired[0]:
                fired[0] = True
                wall[0] += 60
            return unlink(path, *args, **kwargs)
        def fallar(path, data):
            if path.name == 'estado.json' and data.get('estados', {}).get('ERROR') and not failed[0]:
                failed[0] = True
                raise OSError('FIXTURE fallo del estado tras invalidación durable')
            persistir(path, data)
        with mock.patch.object(bucle.time, 'time', side_effect=lambda: wall[0]), \
                mock.patch.object(Path, 'unlink', lento), \
                mock.patch.object(bucle, 'json_atomico', side_effect=fallar), \
                mock.patch.object(bucle, 'evaluar_subproceso', side_effect=self.resultado):
            with self.assertRaises(OSError):
                bucle.ejecutar(root, sin_red=True, max_segundos=2)
            run = next((root / 'salidas/bucle').iterdir())
            resumed = bucle.ejecutar(root, reanudar=run)
        self.assertEqual(resumed['aceptadas'], 0)
        self.assertEqual(bucle.cargar_intentos(run)[0]['estado'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
