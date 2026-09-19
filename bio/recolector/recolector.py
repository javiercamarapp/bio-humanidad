#!/usr/bin/env python3
"""Recolector de señales — cinco fuentes públicas, sin llaves.

Uso:
    python3 -m bio.recolector.recolector --salida datos/senales/senales.jsonl

No usa IA. Solo recoge, normaliza y guarda. Si esto es frágil, nada más importa.
"""
from __future__ import annotations
import sys, json, time, hashlib, pathlib, argparse, urllib.parse, urllib.request

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


def recolecta() -> list[dict]:
    señales, vistas = [], set()
    for t in TERMINOS:
        try:
            for s in hn(t):
                if s["id"] not in vistas:
                    vistas.add(s["id"])
                    señales.append(s)
        except Exception as e:
            print(f"aviso: fallo en '{t}': {e}", file=sys.stderr)
    return señales


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="datos/senales/senales.jsonl")
    a = ap.parse_args()
    p = pathlib.Path(a.salida)
    p.parent.mkdir(parents=True, exist_ok=True)

    nuevas = recolecta()
    with p.open("a", encoding="utf-8") as f:
        for s in nuevas:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"{len(nuevas)} señales -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())