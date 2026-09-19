"""Referencia léxica offline: propone categorías de titulares, no hechos ni riesgos.

No es el extractor de IA previsto en la arquitectura. Es una línea base versionada
con abstención; requiere evaluación humana antes de atribuirle calidad.
"""
from __future__ import annotations

import re

ORIGEN = 'reglas_v1'
MAX_TITULAR = 4096
REGLAS = {
    'brote': ('outbreak', 'pandemic', 'brote', 'pandemia'),
    'vigilancia': ('surveillance', 'biosurveillance', 'aguas residuales',
                   'vigilancia epidemiológica', 'vigilancia sanitaria'),
    'sintesis': ('DNA synthesis', 'synthesis screening', 'síntesis de ADN', 'cribado de ADN'),
    'dual-use': ('dual-use', 'dual use', 'doble uso', 'biosecurity', 'bioseguridad'),
    'politica': ('public health policy', 'health funding', 'financiación de salud pública',
                 'health regulation', 'regulación sanitaria'),
    'capacidad': ('machine learning', 'inteligencia artificial', 'artificial intelligence'),
}


def clasificar_titular(texto: str) -> dict:
    if not isinstance(texto, str) or not texto.strip() or len(texto) > MAX_TITULAR:
        raise ValueError('titular debe tener entre 1 y 4096 caracteres')
    evidence = []
    for category, phrases in REGLAS.items():
        for phrase in phrases:
            pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
            for match in re.finditer(pattern, texto, flags=re.IGNORECASE):
                evidence.append(dict(categoria=category, texto=match.group(),
                                     inicio=match.start(), fin=match.end()))
    evidence.sort(key=lambda e: (e['inicio'], e['fin'], e['categoria']))
    categories = {item['categoria'] for item in evidence}
    category = next(iter(categories)) if len(categories) == 1 else None
    reason = 'coincidencia_unica' if category else ('categorias_ambiguas' if categories else 'sin_coincidencias')
    return dict(categoria_predicha=category, abstencion=category is None,
                motivo=reason, evidencia=evidence)


def extraer(senal: dict) -> dict:
    from bio.evaluacion import huella_senal
    digest = huella_senal(senal)
    return dict(version=1, id=senal['id'], sha256_senal=digest,
                origen_prediccion=ORIGEN, verificado=False, publicable=False,
                **clasificar_titular(senal['claim_literal']))


def extraer_lote(senales: list[dict]) -> list[dict]:
    predictions, ids = [], set()
    for signal in senales:
        result = extraer(signal)
        if result['id'] in ids:
            raise ValueError('ID duplicado en lote')
        ids.add(result['id'])
        predictions.append(result)
    return sorted(predictions, key=lambda p: p['id'])
