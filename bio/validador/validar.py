#!/usr/bin/env python3
"""Validador de hipótesis — la métrica del bucle.

Uso:
    python3 -m bio.validador.validar salidas/hipotesis/ --rubrica

Imprime `cobertura = N/M` y las fallas. No decide: mide.
"""
from __future__ import annotations
import sys, re, json, pathlib, argparse, urllib.request, urllib.error

CAMPOS = ["falsable", "prueba", "costo", "alcance", "fuentes", "estado"]
ALCANCE_OK = {"defensa", "preparacion", "vigilancia", "evals", "pendiente"}


def frontmatter(texto: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", texto, re.S)
    if not m:
        return {}
    fm = {}
    for linea in m.group(1).splitlines():
        if ":" in linea:
            k, v = linea.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def url_viva(url: str, timeout: int = 8) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


def parse_fuentes(v: str) -> list[str]:
    try:
        return json.loads(v) if v.strip().startswith("[") else re.findall(r"https?://[^\s,\"']+", v)
    except Exception:
        return re.findall(r"https?://[^\s,\"']+", v)


def valida(path: pathlib.Path, verificar_red: bool) -> tuple[bool, list[str]]:
    fallas = []
    fm = frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    if not fm:
        return False, ["sin frontmatter"]
    for c in CAMPOS:
        if not fm.get(c):
            fallas.append(f"falta {c}")
    if fm.get("falsable") and len(fm["falsable"]) < 20:
        fallas.append("falsable demasiado vaga")
    if fm.get("alcance") and fm["alcance"] not in ALCANCE_OK:
        fallas.append(f"alcance fuera: {fm['alcance']}")
    urls = parse_fuentes(fm.get("fuentes", ""))
    if not urls:
        fallas.append("sin fuentes")
    if verificar_red:
        muertas = [u for u in urls if not url_viva(u)]
        if muertas:
            fallas.append(f"fuente(s) no verificable(s): {len(muertas)}")
    return (not fallas), fallas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--rubrica", action="store_true")
    ap.add_argument("--sin-red", action="store_true", help="omite re-verificación de URLs")
    a = ap.parse_args()

    archivos = sorted(pathlib.Path(a.carpeta).glob("*.md"))
    if not archivos:
        print("cobertura = 0/0  (sin hipótesis)")
        return 0

    ok = 0
    for f in archivos:
        paso, fallas = valida(f, verificar_red=not a.sin_red)
        ok += paso
        if not paso:
            print(f"FALLA: {f.name} -> {'; '.join(fallas)}")
    print(f"cobertura = {ok}/{len(archivos)}")
    # Umbral de referencia; el bucle decide con esto
    print(f"tasa = {ok/len(archivos):.2f}")
    return 0 if ok == len(archivos) else 1


if __name__ == "__main__":
    sys.exit(main())