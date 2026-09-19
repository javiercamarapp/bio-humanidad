#!/usr/bin/env python3
"""Recolector de titulares de HN/Algolia — una fuente, sin llaves.

Uso:
    python3 -m bio.recolector.recolector --salida datos/senales/senales.jsonl

No usa IA. Solo recoge, normaliza y guarda. Si esto es frágil, nada más importa.
"""
from __future__ import annotations
import sys, json, time, hashlib, pathlib, argparse, urllib.parse, urllib.request
import fcntl
import os

from bio.radar import normalizar, parsear_jsonl, url_canonica

UA = {"User-Agent": "bio-humanidad/0.1 (+research)"}
TERMINOS = [
    "biosecurity", "pandemic", "outbreak", "DNA synthesis screening",
    "gain of function", "biosurveillance", "wastewater surveillance",
    "protein design", "bioweapon", "pathogen",
]


def get_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def hn(termino: str, desde: int = 1700000000) -> list[dict]:
    q = urllib.parse.urlencode({
        "query": termino, "tags": "story",
        "numericFilters": f"created_at_i>{desde}",
    })
    d = get_json(f"https://hn.algolia.com/api/v1/search?{q}")
    out = []
    for h in d.get("hits", []):
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        out.append({
            "id": hashlib.sha1(url.encode()).hexdigest()[:16],
            "fuente": "HN", "fecha": (h.get("created_at") or "")[:10],
            "entidad": "", "claim_literal": h.get("title") or "",
            "categoria": "otro", "metodo_mencionado": None,
            "salvaguarda_mencionada": None, "url": url, "cita": h.get("title") or "",
            "recolectado_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "verificado": False,
        })
    return out


def recolecta() -> tuple[list[dict], list[str]]:
    señales, vistas, errores = [], set(), []
    for t in TERMINOS:
        try:
            for s in hn(t):
                if s["id"] not in vistas:
                    vistas.add(s["id"])
                    señales.append(s)
        except Exception as e:
            mensaje = f"fallo en '{t}': {e}"
            errores.append(mensaje)
            print(f"aviso: {mensaje}", file=sys.stderr)
    return señales, errores


def guardar(path: pathlib.Path, nuevas: list[dict]) -> int:
    """Añade URLs nuevas bajo bloqueo local; no reescribe el historial.

    No basta con deduplicar dentro de una consulta: una ejecución posterior no
    debe convertir el mismo titular en una observación histórica independiente.
    """
    nuevas = normalizar(nuevas)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        texto = f.read()
        previas = parsear_jsonl(texto)
        normalizar(previas + nuevas)  # Rechaza ids conflictivos antes de escribir.
        conocidas = {url_canonica(s["url"]) for s in previas}
        pendientes = [s for s in nuevas if s["url"] not in conocidas]
        if pendientes:
            f.seek(0, os.SEEK_END)
            prefijo = "\n" if texto and not texto.endswith("\n") else ""
            f.write(prefijo + "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in pendientes))
            f.flush()
            os.fsync(f.fileno())
        return len(pendientes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="datos/senales/senales.jsonl")
    a = ap.parse_args()
    p = pathlib.Path(a.salida)
    p.parent.mkdir(parents=True, exist_ok=True)

    nuevas, errores = recolecta()
    try:
        agregadas = guardar(p, nuevas)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"{agregadas} señales nuevas de HN -> {p}; consultas fallidas: {len(errores)}")
    if not nuevas and not errores:
        print("aviso: las consultas no devolvieron señales; no demuestra ausencia de incidentes", file=sys.stderr)
    return 2 if errores else 0


if __name__ == "__main__":
    sys.exit(main())