"""Radar local de titulares públicos, sin modelos ni llamadas de red.

La novedad léxica NO mide anomalías epidemiológicas ni peligro biológico.
Las observaciones históricas no equivalen a cobertura completa de una fuente.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit

DIAS_BASE = 90
DIAS_ACTUALES = 7
CATEGORIAS = ("brote", "vigilancia", "sintesis", "dual-use", "politica", "capacidad", "otro",
              "informacion_insuficiente")
STOPWORDS = set("the and for with from this that are was has have not una uno los las del con por para como que en de el la".split())
LIMITES = [
    "Mide diferencias léxicas de titulares recolectados, no brotes ni riesgos biológicos.",
    "90 días con observaciones NO prueban 90 días de cobertura completa: faltan registros de ingesta exhaustiva.",
    "HN usa búsquedas limitadas y sesgadas; no representa vigilancia sanitaria multifuente.",
    "Umbral sin calibrar contra etiquetas humanas; no es probabilidad ni confianza.",
    "Sin verificación del contenido de las fuentes, refutación ni aprobación humana: no publicable.",
]


def fecha_utc(valor: str) -> datetime:
    dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("recolectado_en requiere zona horaria")
    return dt.astimezone(timezone.utc)


def url_canonica(valor: str) -> str:
    p = urlsplit(valor)
    if p.scheme.lower() not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("url debe ser HTTP(S), con host y sin credenciales")
    if any(c.isspace() for c in valor):
        raise ValueError("url contiene espacios")
    _ = p.port  # También rechaza puertos malformados.
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ""))


def normalizar(registros: list[dict]) -> list[dict]:
    """Valida sin inferir etiquetas y conserva la primera observación por URL.

    Un id que identifica URLs diferentes es corrupción, no una nueva señal.
    No se infiere independencia entre fuentes que repiten la misma URL.
    """
    ids, unicas = {}, {}
    for numero, s in enumerate(registros, 1):
        try:
            if not isinstance(s, dict):
                raise ValueError("se esperaba un objeto")
            for campo in ("id", "fuente", "fecha", "claim_literal", "url", "recolectado_en"):
                if not isinstance(s.get(campo), str) or not s[campo].strip():
                    raise ValueError(f"falta {campo} válido")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["fecha"]):
                raise ValueError("fecha debe ser YYYY-MM-DD")
            publicacion = date.fromisoformat(s["fecha"])
            observada = fecha_utc(s["recolectado_en"])
            if publicacion > observada.date():
                raise ValueError("fecha de publicación posterior a recolección")
            url = url_canonica(s["url"])
            if s["id"] in ids and ids[s["id"]] != url:
                raise ValueError(f"id {s['id']} conflictivo")
            ids[s["id"]] = url
            copia = {**s, "url": url, "recolectado_en": observada.isoformat().replace("+00:00", "Z")}
            previo = unicas.get(url)
            clave = (observada, json.dumps(copia, sort_keys=True, ensure_ascii=False))
            if previo is None or clave < previo[0]:
                unicas[url] = (clave, copia)
        except (TypeError, ValueError) as e:
            raise ValueError(f"registro {numero}: {e}") from e
    return sorted((x[1] for x in unicas.values()), key=lambda s: (s["recolectado_en"], s["url"]))


def parsear_jsonl(texto: str) -> list[dict]:
    registros = []
    for numero, linea in enumerate(texto.splitlines(), 1):
        if not linea.strip():
            continue
        try:
            s = json.loads(linea)
            normalizar([s])
        except (ValueError, TypeError) as e:
            raise ValueError(f"línea {numero}: {e}") from e
        registros.append(s)
    return normalizar(registros)


def leer(path: Path) -> list[dict]:
    return parsear_jsonl(path.read_text(encoding="utf-8"))


def digest(datos: list[dict]) -> str:
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def celda(valor: str) -> str:
    # CSV es para revisión humana, no para ejecutar fórmulas de una fuente externa.
    return "'" + valor if valor.lstrip().startswith(("=", "+", "-", "@")) or valor.startswith(("\t", "\r", "\n")) else valor


def preparar(registros: list[dict], salida: Path, cantidad: int = 50, semilla: str = "radar-v1") -> dict:
    datos = normalizar(registros)
    if cantidad < 1 or cantidad > len(datos):
        raise ValueError(f"se requieren {cantidad} señales únicas; disponibles: {len(datos)}")
    seleccionadas = sorted(datos, key=lambda s: (hashlib.sha256(f"{semilla}:{s['url']}".encode()).hexdigest(), s["url"]))[:cantidad]
    campos_fuente = ("id", "fuente", "fecha", "url", "claim_literal", "recolectado_en")
    # Las fuentes son datos no confiables, nunca autoras de aprobaciones humanas.
    muestra = [{campo: s[campo] for campo in campos_fuente} for s in seleccionadas]
    estado = {
        "estado": "PENDIENTE_REVISION_HUMANA", "version": 1,
        "senales_unicas": len(datos), "muestra": cantidad, "etiquetas_humanas": 0,
        "sha256_entrada_normalizada": digest(datos), "sha256_muestra": digest(muestra),
        "semilla": semilla, "muestreo": "orden por sha256(semilla:url), no estratificado",
        "fuentes_muestra": dict(sorted(Counter(s["fuente"] for s in muestra).items())),
        "categorias_permitidas": CATEGORIAS,
        "advertencias": ["No es un conjunto dorado: requiere etiquetas humanas y revisión de representatividad.",
                         "No se escribe en datos/dorado ni se declara aprobación humana.",
                         "Categoría insuficiente o ambigua se excluye del futuro conjunto evaluable.",
                         "No se proponen etiquetas ni severidad a partir de un titular."],
    }
    salida.mkdir(parents=True, exist_ok=False)
    campos = ["id", "fuente", "fecha", "url", "claim_literal", "categoria_humana", "clase", "nota", "revisor", "revisado_en"]
    with (salida / "revision.csv").open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for s in muestra:
            writer.writerow({c: celda(s[c]) if c in campos_fuente else "" for c in campos})
    # Snapshot de campos fuente, sin escapes de CSV ni supuestas aprobaciones.
    (salida / "muestra.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in muestra), encoding="utf-8")
    (salida / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return estado


def vector(texto: str) -> Counter:
    return Counter(t for t in re.findall(r"[^\W\d_]{3,}", texto.casefold()) if t not in STOPWORDS)


def similitud(a: Counter, b: Counter) -> float:
    producto = sum(n * b[t] for t, n in a.items())
    norma = math.sqrt(sum(n*n for n in a.values()) * sum(n*n for n in b.values()))
    return min(1.0, producto / norma) if norma else 0.0


def detectar(registros: list[dict], corte: date, umbral: float = 0.85) -> dict:
    """Ventanas por primera recolección UTC: base [corte-97,corte-7), actual [corte-7,corte).

    Solo compara léxico dentro de cada fuente. No consulta las URLs de entrada.
    Se abstiene si alguna fuente candidata carece de observaciones en 90 días distintos.
    """
    if not math.isfinite(umbral) or not 0 <= umbral <= 1:
        raise ValueError("umbral debe estar entre 0 y 1")
    datos = normalizar(registros)
    inicio_actual = corte - timedelta(days=DIAS_ACTUALES)
    inicio_base = inicio_actual - timedelta(days=DIAS_BASE)
    base, actuales = [], []
    for s in datos:
        dia = fecha_utc(s["recolectado_en"]).date()
        if inicio_base <= dia < inicio_actual:
            base.append(s)
        elif inicio_actual <= dia < corte:
            actuales.append(s)
    fuentes = {}
    for nombre in sorted({s["fuente"] for s in base + actuales}):
        historia = [s for s in base if s["fuente"] == nombre]
        dias = len({fecha_utc(s["recolectado_en"]).date() for s in historia})
        fuentes[nombre] = {"senales_base": len(historia), "dias_observados_base": dias,
                           "dias_requeridos": DIAS_BASE, "base_minima": dias == DIAS_BASE}
    reporte = {
        "version": 1, "metodo": "coseno_frecuencia_lexica_titulares_v1",
        "estado": "SIN_CANDIDATAS", "publicable": False, "umbral": umbral,
        "corte_exclusivo_utc": corte.isoformat(), "inicio_base": inicio_base.isoformat(),
        "inicio_actual": inicio_actual.isoformat(), "senales_unicas": len(datos),
        "sha256_entrada_normalizada": digest(datos), "candidatas": len(actuales),
        "excluidas_fuera_ventana": len(datos) - len(base) - len(actuales),
        "fuentes": fuentes, "novedades": [], "candidatas_sin_lexico": 0,
        "limitaciones": list(LIMITES),
    }
    if not actuales:
        return reporte
    if any(not fuentes[s["fuente"]]["base_minima"] for s in actuales):
        reporte["estado"] = "DATOS_INSUFICIENTES"
        return reporte
    reporte["estado"] = "EXPLORATORIO_NO_CALIBRADO"
    vectores = {nombre: [(s, vector(s["claim_literal"])) for s in base if s["fuente"] == nombre] for nombre in fuentes}
    for s in actuales:
        v = vector(s["claim_literal"])
        if not v:
            reporte["candidatas_sin_lexico"] += 1
            continue
        vecinos = [(similitud(v, bv), bs) for bs, bv in vectores[s["fuente"]] if bv]
        if not vecinos:
            reporte["estado"] = "DATOS_INSUFICIENTES"
            reporte["novedades"] = []
            return reporte
        parecido, cercano = max(vecinos, key=lambda x: (x[0], x[1]["url"]))
        novedad = 1 - parecido
        if novedad >= umbral:
            reporte["novedades"].append({
                "id": s["id"], "fuente": s["fuente"], "url": s["url"],
                "fecha_publicacion": s["fecha"], "recolectado_en": s["recolectado_en"],
                "claim_literal": s["claim_literal"], "novedad_lexica": round(novedad, 6),
                "referencia_mas_cercana": cercano["url"], "requiere_revision": True,
            })
    reporte["novedades"].sort(key=lambda x: (-x["novedad_lexica"], x["url"]))
    return reporte


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="comando", required=True)
    revision = sub.add_parser("preparar", help="prepara casos sin etiquetar; nunca escribe el conjunto dorado")
    revision.add_argument("--entrada", type=Path, required=True)
    revision.add_argument("--salida", type=Path, required=True, help="carpeta nueva; no sobrescribe")
    revision.add_argument("--cantidad", type=int, default=50)
    revision.add_argument("--semilla", default="radar-v1")
    detector = sub.add_parser("detectar", help="reporte exploratorio offline; no publica alertas")
    detector.add_argument("--entrada", type=Path, required=True)
    detector.add_argument("--salida", type=Path, required=True, help="JSON nuevo; no sobrescribe")
    detector.add_argument("--corte", type=date.fromisoformat, required=True, help="fecha UTC exclusiva YYYY-MM-DD")
    detector.add_argument("--umbral", type=float, default=0.85)
    args = ap.parse_args()
    try:
        datos = leer(args.entrada)
        if args.comando == "preparar":
            resultado = preparar(datos, args.salida, args.cantidad, args.semilla)
        else:
            resultado = detectar(datos, args.corte, args.umbral)
            args.salida.parent.mkdir(parents=True, exist_ok=True)
            with args.salida.open("x", encoding="utf-8") as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)
                f.write("\n")
        print(json.dumps({"estado": resultado["estado"], "salida": str(args.salida)}, ensure_ascii=False))
        # 2 significa abstención por datos insuficientes, no fallo técnico.
        return 2 if resultado["estado"] == "DATOS_INSUFICIENTES" else 0
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
