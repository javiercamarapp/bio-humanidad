"""Relojes del bucle: origen monotónico común entre procesos del mismo arranque.

En macOS Python 3.9, time.monotonic() usa una referencia por proceso.
CLOCK_MONOTONIC evita persistir ese origen privado y mezclar intérpretes.
La identidad de arranque se comprueba por separado; no es tiempo real duro.
"""
import time as _time


def time() -> float:
    return _time.time()


def monotonic() -> float:
    return _time.clock_gettime(_time.CLOCK_MONOTONIC)
