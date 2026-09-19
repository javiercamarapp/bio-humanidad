"""Lectura JSON sin claves repetidas ni números no finitos."""
import json
import math

MAX_PROFUNDIDAD = 64


def _objeto(pares):
    resultado = {}
    for clave, valor in pares:
        if clave in resultado:
            raise ValueError(f'clave JSON duplicada: {clave!r}')
        resultado[clave] = valor
    return resultado


def _no_finito(valor):
    raise ValueError(f'JSON no admite número no finito: {valor}')


def _real(valor):
    numero = float(valor)
    if not math.isfinite(numero):
        _no_finito(valor)
    return numero


def _entero(valor):
    if len(valor) > 1000:
        raise ValueError('entero JSON demasiado largo')
    return int(valor)


def cargar(texto):
    try:
        resultado = json.loads(texto, object_pairs_hook=_objeto, parse_constant=_no_finito,
                               parse_float=_real, parse_int=_entero)
        # La profundidad de json.loads cambia entre versiones de Python. Impone
        # nuestro límite sin depender de RecursionError ni recurrir otra vez.
        pendientes = [(resultado, 0)]
        while pendientes:
            valor, nivel = pendientes.pop()
            if isinstance(valor, (dict, list)):
                nivel += 1
                if nivel > MAX_PROFUNDIDAD:
                    raise ValueError('JSON supera la profundidad permitida')
                hijos = valor.values() if isinstance(valor, dict) else valor
                pendientes.extend((hijo, nivel) for hijo in hijos if isinstance(hijo, (dict, list)))
        return resultado
    except RecursionError as exc:
        raise ValueError('JSON supera la profundidad permitida') from exc
