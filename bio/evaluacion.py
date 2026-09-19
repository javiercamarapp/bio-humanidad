"""Evaluación offline de concordancia con un registro local de revisión humana.

No autentica personas ni valida científicamente titulares. No realiza E/S.
Los campos adicionales se ignoran; las entradas nunca se modifican.
"""

import hashlib
import json
import re
from collections import Counter
from datetime import date


CATEGORIAS = ('brote', 'vigilancia', 'sintesis', 'dual-use', 'politica',
              'capacidad', 'otro')
_SEVERIDADES = ('baja', 'media', 'alta', 'no_aplica')
_FECHA = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
_HASH = re.compile(r'[0-9a-fA-F]{64}')


def _texto(value):
    return isinstance(value, str) and bool(value.strip())


def huella_senal(s: dict) -> str:
    """SHA-256 de id, URL y literal exactos, sin normalizar ningún texto."""
    if not isinstance(s, dict) or not all(
            _texto(s.get(key)) for key in ('id', 'url', 'claim_literal')):
        raise ValueError('La señal requiere id, url y claim_literal strings no vacíos')
    contenido = json.dumps([s['id'], s['url'], s['claim_literal']],
                           ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()


def _validar_dorado(dorado):
    if not isinstance(dorado, list) or len(dorado) < 50:
        raise ValueError('El dorado requiere al menos 50 IDs distintos')
    referencia = {}
    for s in dorado:
        huella = huella_senal(s)
        if s['id'] in referencia:
            raise ValueError('ID duplicado en dorado')
        if (s.get('categoria_humana') not in CATEGORIAS
                or s.get('severidad_humana') not in _SEVERIDADES
                or not _texto(s.get('revisor'))
                or s.get('origen_etiqueta') != 'humano'):
            raise ValueError('Etiquetado humano inválido')
        fecha = s.get('fecha_revision')
        if not isinstance(fecha, str) or _FECHA.fullmatch(fecha) is None:
            raise ValueError('fecha_revision debe ser YYYY-MM-DD')
        try:
            date.fromisoformat(fecha)
        except ValueError as exc:
            raise ValueError('fecha_revision no es una fecha real') from exc
        referencia[s['id']] = (s['categoria_humana'], huella)
    return referencia


def _prediccion_valida(p):
    if not isinstance(p, dict):
        return False
    requeridos = ('id', 'sha256_senal', 'categoria_predicha', 'abstencion',
                  'origen_prediccion')
    if not all(key in p for key in requeridos):
        return False
    categoria = p['categoria_predicha']
    return (_texto(p['id'])
            and isinstance(p['sha256_senal'], str)
            and _HASH.fullmatch(p['sha256_senal']) is not None
            and (categoria is None or categoria in CATEGORIAS)
            and type(p['abstencion']) is bool
            and p['abstencion'] == (categoria is None)
            and p['origen_prediccion'] == 'reglas_v1')


def evaluar(dorado: list[dict], predicciones: list[dict]) -> dict:
    """Mide clasificación frente al dorado, manteniendo todos los denominadores.

    Un ID string no vacío cuenta como presente incluso en un registro inválido,
    y su repetición siempre falla, también para IDs desconocidos. Primero se
    valida el esquema: solo registros bien formados pueden ser desconocidos.
    En IDs conocidos se exige además la huella vigente (hex admite mayúsculas).
    Invalidas y desconocidas son conteos disjuntos. Toda referencia sin respuesta
    válida, incluidas abstenciones, aporta un falso negativo a su categoría.
    por_categoria contiene todas las categorías; la matriz solo celdas no cero,
    en el orden de CATEGORIAS. El registro humano no autentica al revisor.
    """
    referencia = _validar_dorado(dorado)
    if not isinstance(predicciones, list):
        raise ValueError('predicciones debe ser una lista')

    vistos = set()
    for p in predicciones:
        if isinstance(p, dict) and _texto(p.get('id')):
            if p['id'] in vistos:
                raise ValueError('ID duplicado en predicciones')
            vistos.add(p['id'])

    invalidas = desconocidas = abstenciones = respondidas = correctas = 0
    matriz = Counter()
    soporte = Counter(real for real, _ in referencia.values())
    predichas = Counter()
    verdaderos = Counter()
    for p in predicciones:
        if not _prediccion_valida(p):
            invalidas += 1
            continue
        if p['id'] not in referencia:
            desconocidas += 1
            continue
        real, huella = referencia[p['id']]
        if p['sha256_senal'].lower() != huella:
            invalidas += 1
            continue
        if p['abstencion']:
            abstenciones += 1
            continue
        predicha = p['categoria_predicha']
        respondidas += 1
        predichas[predicha] += 1
        matriz[real, predicha] += 1
        if real == predicha:
            correctas += 1
            verdaderos[real] += 1

    por_categoria = {}
    for categoria in CATEGORIAS:
        tp = verdaderos[categoria]
        n = soporte[categoria]
        np = predichas[categoria]
        por_categoria[categoria] = {
            'soporte': n, 'precision': tp / np if np else None,
            'recall': tp / n if n else None, 'tp': tp, 'fp': np - tp,
            'fn': n - tp,
        }
    total = len(referencia)
    total_predicciones = len(predicciones)
    return {
        'version': 1,
        'estado': 'EVALUADO_TECNICAMENTE',
        'publicable': False,
        'total_referencia': total,
        'total_predicciones': total_predicciones,
        'respondidas': respondidas,
        'correctas': correctas,
        'abstenciones': abstenciones,
        'ausentes': len(referencia.keys() - vistos),
        'invalidas': invalidas,
        'desconocidas': desconocidas,
        'cobertura': respondidas / total,
        'exactitud_global': correctas / total,
        'exactitud_selectiva': correctas / respondidas if respondidas else None,
        'tasa_esquema_invalido': (
            invalidas / total_predicciones if total_predicciones else None),
        'matriz_confusion': [
            {'real': real, 'predicha': predicha, 'conteo': matriz[real, predicha]}
            for real in CATEGORIAS for predicha in CATEGORIAS
            if matriz[real, predicha]
        ],
        'por_categoria': por_categoria,
        'limitaciones': [
            'Mide concordancia de clasificación con las etiquetas del dorado.',
            'No constituye validación científica ni verifica la verdad de los titulares.',
            'La revisión humana es un registro local; no autentica personas.',
            'Costo y latencia no medidos.',
            'El dorado puede tener sesgo y no representar otros titulares.',
        ],
    }
