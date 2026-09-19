import copy
import hashlib
import json
import unittest

from bio.evaluacion import CATEGORIAS, evaluar, huella_senal


def referencia():
    return [dict(id=str(i), url='https://example.invalid/' + str(i),
                 claim_literal='Titular ficticio ' + str(i),
                 categoria_humana=CATEGORIAS[i % len(CATEGORIAS)],
                 severidad_humana='no_aplica', revisor='revision-local',
                 fecha_revision='2024-02-29', origen_etiqueta='humano')
            for i in range(50)]


def predecir(dorado):
    return [dict(id=s['id'], sha256_senal=huella_senal(s),
                 categoria_predicha=s['categoria_humana'], abstencion=False,
                 origen_prediccion='reglas_v1') for s in dorado]


class EvaluacionTests(unittest.TestCase):
    def setUp(self):
        self.d = referencia()
        self.p = predecir(self.d)

    def test_ideal_50_y_sin_mutacion(self):
        antes = copy.deepcopy((self.d, self.p))
        r = evaluar(self.d, self.p)
        for key in ('total_referencia', 'total_predicciones', 'respondidas', 'correctas'):
            self.assertEqual(r[key], 50)
        for key in ('abstenciones', 'ausentes', 'invalidas', 'desconocidas'):
            self.assertEqual(r[key], 0)
        self.assertEqual(r['cobertura'], 1)
        self.assertEqual(r['exactitud_global'], 1)
        self.assertEqual(r['exactitud_selectiva'], 1)
        self.assertEqual(r['tasa_esquema_invalido'], 0)
        self.assertEqual(r['version'], 1)
        self.assertEqual(r['estado'], 'EVALUADO_TECNICAMENTE')
        self.assertIs(r['publicable'], False)
        self.assertTrue(r['limitaciones'])
        self.assertEqual((self.d, self.p), antes)

    def test_huella_exacta_sin_normalizacion(self):
        s = dict(id=' á ', url='HTTPS://example.invalid/%61 ', claim_literal='ñ\n')
        esperado = hashlib.sha256(json.dumps(
            [s['id'], s['url'], s['claim_literal']], ensure_ascii=False,
            separators=(',', ':')).encode('utf-8')).hexdigest()
        self.assertEqual(huella_senal(s), esperado)
        self.assertNotEqual(huella_senal(s), huella_senal(dict(s, id='á')))
        for value in ('', None, 1, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                huella_senal(dict(s, url=value))
        with self.assertRaises(ValueError):
            huella_senal({})

    def test_abstenciones(self):
        for p in self.p:
            p.update(categoria_predicha=None, abstencion=True)
        r = evaluar(self.d, self.p)
        self.assertEqual(r['abstenciones'], 50)
        self.assertEqual(r['correctas'], 0)
        self.assertEqual(r['cobertura'], 0)
        self.assertIsNone(r['exactitud_selectiva'])
        self.assertEqual(r['matriz_confusion'], [])
        self.assertEqual(sum(v['fn'] for v in r['por_categoria'].values()), 50)

    def test_vacias_y_faltantes(self):
        r = evaluar(self.d, [])
        self.assertEqual(r['ausentes'], 50)
        self.assertIsNone(r['tasa_esquema_invalido'])
        self.assertIsNone(r['exactitud_selectiva'])
        self.assertEqual(r['exactitud_global'], 0)
        r = evaluar(self.d, self.p[:1])
        self.assertEqual(r['ausentes'], 49)
        self.assertEqual(r['exactitud_global'], 1 / 50)
        with self.assertRaises(ValueError):
            evaluar([], [])

    def test_invalidas_desconocidas_hash_y_ausencia(self):
        self.p[0]['abstencion'] = 'false'
        self.p[1]['sha256_senal'] = '0' * 64
        self.d[2]['claim_literal'] += ' cambiado'
        self.p[3]['id'] = 'desconocido'
        self.p.extend([None, {}, dict(id='otro', sha256_senal='mal')])
        r = evaluar(self.d, self.p)
        self.assertEqual(r['invalidas'], 6)
        self.assertEqual(r['desconocidas'], 1)
        self.assertEqual(r['ausentes'], 1)
        self.assertEqual(r['respondidas'], 46)
        self.assertEqual(r['correctas'], 46)
        self.assertEqual(r['tasa_esquema_invalido'], 6 / 53)
        self.assertEqual(r['cobertura'], 46 / 50)

    def test_duplicados_incluso_malformados_y_desconocidos(self):
        for extra in (self.p[0], {'id': '0'}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                evaluar(self.d, self.p + [extra])
        with self.assertRaises(ValueError):
            evaluar(self.d, [{'id': 'fuera'}, {'id': 'fuera'}])
        with self.assertRaises(ValueError):
            evaluar(self.d + [self.d[0]], [])

    def test_dorado_invalido(self):
        cambios = [('origen_etiqueta', 'modelo'), ('revisor', ''), ('revisor', '  '),
                   ('fecha_revision', '2023-02-29'), ('fecha_revision', '2024-2-29'),
                   ('fecha_revision', '2024-02-29T00:00:00'),
                   ('categoria_humana', 'falsa'), ('categoria_humana', []),
                   ('severidad_humana', 'extrema'), ('id', ''), ('url', None),
                   ('claim_literal', ''), ('claim_literal', '\t'), ('id', '  '), ('url', '  ')]
        for key, value in cambios:
            d = copy.deepcopy(self.d)
            d[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                evaluar(d, [])
        with self.assertRaises(ValueError):
            evaluar(self.d[:49], [])
        with self.assertRaises(ValueError):
            evaluar(self.d, None)
        with self.assertRaises(ValueError):
            evaluar(None, [])

    def test_esquema_prediccion(self):
        cambios = [('id', ''), ('sha256_senal', 'g' * 64),
                   ('sha256_senal', 'a' * 63), ('sha256_senal', None),
                   ('categoria_predicha', []), ('categoria_predicha', 'falsa'),
                   ('categoria_predicha', None), ('abstencion', True),
                   ('abstencion', 0), ('abstencion', 'false'),
                   ('origen_prediccion', 'humano')]
        for key, value in cambios:
            p = dict(self.p[0], **{key: value})
            with self.subTest(key=key, value=value):
                r = evaluar(self.d, [p])
                self.assertEqual(r['invalidas'], 1)
                self.assertEqual(r['respondidas'], 0)
        for key in self.p[0]:
            p = dict(self.p[0])
            del p[key]
            self.assertEqual(evaluar(self.d, [p])['invalidas'], 1)
        p = dict(self.p[0], evidencia=[], motivo='ficticio')
        self.assertEqual(evaluar(self.d, [p])['correctas'], 1)

    def test_precision_recall_denominadores(self):
        for s in self.d:
            s['categoria_humana'] = 'brote'
        self.d[1]['categoria_humana'] = 'vigilancia'
        p = predecir(self.d[:4])
        p[1]['categoria_predicha'] = 'brote'
        p[2]['categoria_predicha'] = 'vigilancia'
        p[3].update(categoria_predicha=None, abstencion=True)
        r = evaluar(self.d, p)
        self.assertEqual(r['exactitud_selectiva'], 1 / 3)
        self.assertEqual(r['por_categoria']['brote'],
                         dict(soporte=49, precision=0.5, recall=1 / 49, tp=1, fp=1, fn=48))
        self.assertEqual(r['por_categoria']['vigilancia'],
                         dict(soporte=1, precision=0, recall=0, tp=0, fp=1, fn=1))
        self.assertIsNone(r['por_categoria']['otro']['precision'])
        self.assertIsNone(r['por_categoria']['otro']['recall'])
        self.assertEqual(r['matriz_confusion'], [
            dict(real='brote', predicha='brote', conteo=1),
            dict(real='brote', predicha='vigilancia', conteo=1),
            dict(real='vigilancia', predicha='brote', conteo=1)])

    def test_reproducibilidad_por_orden(self):
        self.p[0]['categoria_predicha'] = 'otro'
        self.p[1].update(categoria_predicha=None, abstencion=True)
        self.p[2]['sha256_senal'] = '0' * 64
        self.p[3]['id'] = 'fuera'
        p = self.p[:-1] + [None]
        a = evaluar(self.d, p)
        b = evaluar(list(reversed(self.d)), list(reversed(p)))
        self.assertEqual(json.dumps(a, ensure_ascii=False), json.dumps(b, ensure_ascii=False))
