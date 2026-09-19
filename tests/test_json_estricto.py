import unittest

from bio.json_estricto import cargar


class JsonEstrictoTests(unittest.TestCase):
    def test_json_valido_conserva_valores(self):
        self.assertEqual(cargar('{"texto":"ñ","n":1.25,"lista":[true,null,2]}'),
                         {'texto': 'ñ', 'n': 1.25, 'lista': [True, None, 2]})

    def test_rechaza_claves_duplicadas_incluso_anidadas_y_escapadas(self):
        for text in ['{"a":1,"a":2}', '{"x":{"a":1,"a":2}}',
                     '{"a":1,"\\u0061":2}', '{"a":1,"a":1}']:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'duplicada'):
                cargar(text)

    def test_rechaza_no_finitos_y_overflow(self):
        for text in ['NaN', 'Infinity', '-Infinity', '1e999', '-1e999', '{"n":NaN}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                cargar(text)

    def test_enteros_y_profundidad_acotados(self):
        with self.assertRaises(ValueError):
            cargar('1' * 1001)
        with self.assertRaises(ValueError):
            cargar('[' * 1500 + '0' + ']' * 1500)

    def test_misma_clave_en_objetos_distintos_es_valida(self):
        self.assertEqual(cargar('[{"a":1},{"a":2}]'), [{'a': 1}, {'a': 2}])


if __name__ == '__main__':
    unittest.main()
