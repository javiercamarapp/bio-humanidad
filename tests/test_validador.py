import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from bio.validador import validar


CANDIDATO = '''---
id: calidad-datos
falsable: "La tasa de registros repetidos no cambia al normalizar URLs."
prueba: "Comparar dos lotes de metadatos públicos sin datos biológicos."
costo: "USD 0; 30 minutos de cómputo local."
alcance: vigilancia
fuentes: ["https://www.who.int/example"]
estado: propuesta
---
# Calidad de metadatos
[V] Se evalúa la trazabilidad de registros públicos, no actividad biológica.
'''


def revision(text):
    return {
        'sha256': hashlib.sha256(text.encode()).hexdigest(),
        'origen': 'humano', 'revisor': 'Fixture sintético; NO persona real',
        'fecha_revision': '2026-09-19', 'decision': 'aprobar',
        'alcance_seguro': True, 'falsable': True, 'prueba_viable': True,
        'novedad_revisada': True, 'fuentes_respaldan': True,
        'citas': [{'url': 'https://www.who.int/example',
                   'texto': 'Public health surveillance requires reliable information.'}],
    }


class RegresionesOriginales(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.path = self.root / 'candidato.md'
        self.path.write_text(CANDIDATO)

    def test_formato_sin_revision_no_es_evidencia(self):
        ok, reasons = validar.valida(self.path, verificar_red=False)
        self.assertFalse(ok, 'Campos completos no equivalen a hipótesis validada')
        self.assertTrue(reasons)

    def test_alcance_pendiente_no_es_aprobacion(self):
        self.path.write_text(CANDIDATO.replace('alcance: vigilancia', 'alcance: pendiente'))
        ok, _ = validar.valida(self.path, verificar_red=False)
        self.assertFalse(ok)

    def test_frontmatter_duplicado_no_sobrescribe_alcance(self):
        self.path.write_text(CANDIDATO.replace('alcance: vigilancia',
                                             'alcance: fuera\nalcance: vigilancia'))
        ok, _ = validar.valida(self.path, verificar_red=False)
        self.assertFalse(ok)

    def test_carpeta_vacia_no_es_exito(self):
        empty = self.root / 'vacio'
        empty.mkdir()
        result = subprocess.run([sys.executable, '-m', 'bio.validador.validar',
                                 str(empty), '--rubrica', '--sin-red'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_fuentes_no_lista_no_provoca_crash(self):
        self.path.write_text(CANDIDATO.replace('["https://www.who.int/example"]', '42'))
        ok, reasons = validar.valida(self.path, verificar_red=False)
        self.assertFalse(ok)
        self.assertTrue(reasons)


class EvidenciaTests(RegresionesOriginales):
    def setUp(self):
        super().setUp()
        self.reviews = self.root / 'revisiones'
        self.reviews.mkdir()
        self.record = revision(CANDIDATO)

    def save_review(self):
        path = self.reviews / (hashlib.sha256(self.path.read_bytes()).hexdigest() + '.json')
        path.write_text(json.dumps(self.record))

    def evaluate(self, **kwargs):
        return validar.evaluar(self.path, revisiones=self.reviews, **kwargs)

    def test_sin_revision_no_consulta_red(self):
        with mock.patch.object(validar, 'texto_fuente') as fetch:
            self.assertEqual(self.evaluate()['estado'], 'PENDIENTE_HUMANO')
            fetch.assert_not_called()

    def test_revision_y_cita_sinteticas_superan_controles(self):
        self.save_review()
        with mock.patch.object(validar, 'texto_fuente', return_value=self.record['citas'][0]['texto']):
            self.assertEqual(self.evaluate()['estado'], 'ACEPTADA')

    def test_http_200_sin_cita_no_es_evidencia(self):
        self.save_review()
        with mock.patch.object(validar, 'texto_fuente', return_value='Una página distinta'):
            self.assertEqual(self.evaluate()['estado'], 'FUENTE_NO_VERIFICABLE')

    def test_revision_con_decisiones_duplicadas_no_autoriza(self):
        self.save_review()
        path = next(self.reviews.glob('*.json'))
        path.write_text('{"decision":"rechazar",' + path.read_text()[1:])
        with mock.patch.object(validar, 'texto_fuente', return_value=self.record['citas'][0]['texto']):
            self.assertEqual(self.evaluate()['estado'], 'RECHAZADA')

    def test_revision_obsoleta_no_se_usa(self):
        self.save_review()
        self.path.write_text(CANDIDATO + '\nCambio posterior a la revisión.')
        self.assertEqual(self.evaluate()['estado'], 'PENDIENTE_HUMANO')

    def test_hash_falso_no_se_usa(self):
        self.record['sha256'] = '0' * 64
        self.save_review()
        self.assertEqual(self.evaluate()['estado'], 'PENDIENTE_HUMANO')

    def test_sin_red_nunca_acepta(self):
        self.save_review()
        self.assertEqual(self.evaluate(verificar_red=False)['estado'], 'PENDIENTE_RED')

    def test_revision_de_modelo_no_es_humana(self):
        self.record['origen'] = 'modelo'
        self.save_review()
        self.assertEqual(self.evaluate()['estado'], 'PENDIENTE_HUMANO')

    def test_rechazo_humano_no_consulta_red(self):
        self.record['decision'] = 'rechazar'
        self.save_review()
        with mock.patch.object(validar, 'texto_fuente') as fetch:
            self.assertEqual(self.evaluate()['estado'], 'RECHAZADA')
            fetch.assert_not_called()

    def test_guardia_humana_no_acepta_string_true(self):
        self.record['alcance_seguro'] = 'true'
        self.save_review()
        self.assertEqual(self.evaluate()['estado'], 'PENDIENTE_HUMANO')

    def test_duplicado_lexico_no_mejora_metrica(self):
        other = self.root / 'anterior.md'
        other.write_text(CANDIDATO.replace('id: calidad-datos', 'id: otra-id'))
        self.assertEqual(self.evaluate(comparar=[other])['estado'], 'DUPLICADA')

    def test_fuente_arbitraria_no_consulta_red(self):
        self.path.write_text(CANDIDATO.replace('www.who.int', '127.0.0.1'))
        with mock.patch.object(validar, 'texto_fuente') as fetch:
            self.assertEqual(self.evaluate()['estado'], 'ESCALAR_HUMANO')
            fetch.assert_not_called()

    def test_enlace_simbolico_no_se_lee(self):
        link = self.root / 'link.md'
        link.symlink_to(self.path)
        self.assertEqual(validar.evaluar(link)['estado'], 'RECHAZADA')

    def test_documento_demasiado_grande(self):
        self.path.write_text('x' * (validar.MAX_DOCUMENTO + 1))
        self.assertEqual(self.evaluate()['estado'], 'RECHAZADA')

    def test_host_puerto_y_credenciales(self):
        for url in ['http://www.who.int/a', 'https://www.who.int.evil.test/a',
                    'https://www.who.int:444/a', 'https://user@www.who.int/a',
                    'file:///etc/passwd', 'https://localhost/a']:
            with self.subTest(url=url):
                self.assertFalse(validar.url_permitida(url))

    def test_redireccion_fuera_de_lista_falla(self):
        with self.assertRaises(ValueError):
            validar.RedireccionSegura().redirect_request(None, None, 302, '', {},
                                                         'http://127.0.0.1/private')

    def test_html_descarta_scripts(self):
        parser = validar.TextoHTML()
        parser.feed('<p>Visible</p><script>no es evidencia</script><style>oculto</style>')
        self.assertEqual(parser.parts, ['Visible'])


if __name__ == '__main__':
    unittest.main()
