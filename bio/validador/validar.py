#!/usr/bin/env python3
"""Controles técnicos + revisión humana; nunca una prueba de verdad científica."""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

CAMPOS = ('id', 'falsable', 'prueba', 'costo', 'alcance', 'fuentes', 'estado')
ALCANCE_OK = {'defensa', 'preparacion', 'vigilancia', 'evals'}
MAX_DOCUMENTO = 256_000
MAX_FUENTE = 1_000_000
# Lista cerrada: no se consultan hosts aportados arbitrariamente por candidatos.
HOSTS_FUENTES = frozenset({
    'www.who.int', 'www.cdc.gov', 'www.ecdc.europa.eu',
    'pubmed.ncbi.nlm.nih.gov', 'pmc.ncbi.nlm.nih.gov',
    'www.nature.com', 'www.science.org', 'www.microsoft.com',
    'www.cidrap.umn.edu', 'www.nti.org', 'ibbis.bio',
})


def leer_texto(path: pathlib.Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError('archivo ausente o enlace simbólico')
    with path.open('rb') as f:
        raw = f.read(MAX_DOCUMENTO + 1)
    if not raw or len(raw) > MAX_DOCUMENTO:
        raise ValueError('archivo vacío o demasiado grande')
    return raw.decode('utf-8')


def frontmatter(texto: str) -> dict:
    """Subconjunto explícito de YAML: claves únicas y valores de una línea."""
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', texto, re.S)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if ':' not in line:
            raise ValueError('frontmatter debe usar valores de una línea')
        key, value = line.split(':', 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r'[a-z_]+', key) or key in result:
            raise ValueError('clave inválida o duplicada en frontmatter')
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '\"\'':
            value = value[1:-1]
        result[key] = value
    return result


def parse_fuentes(value: str) -> list[str]:
    try:
        urls = json.loads(value)
    except (ValueError, TypeError):
        return []
    if (not isinstance(urls, list) or not 1 <= len(urls) <= 10
            or any(not isinstance(u, str) for u in urls)):
        return []
    return urls if len(set(urls)) == len(urls) else []


def url_permitida(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        return (parsed.scheme == 'https' and parsed.hostname in HOSTS_FUENTES
                and parsed.port in (None, 443) and not parsed.username
                and not parsed.password and not any(c.isspace() for c in url))
    except (ValueError, TypeError):
        return False


class RedireccionSegura(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not url_permitida(newurl):
            raise ValueError('redirección fuera de la lista de fuentes permitidas')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class TextoHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def texto_fuente(url: str) -> str:
    if not url_permitida(url):
        raise ValueError('URL no permitida')
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), RedireccionSegura())
    req = urllib.request.Request(url, headers={'User-Agent': 'bio-humanidad/0.2'})
    with opener.open(req, timeout=5) as response:
        if not url_permitida(response.geturl()):
            raise ValueError('URL final no permitida')
        kind = response.headers.get_content_type()
        if kind not in ('text/html', 'text/plain'):
            raise ValueError('solo se verifica texto/HTML; PDF requiere revisión aparte')
        raw = response.read(MAX_FUENTE + 1)
        if len(raw) > MAX_FUENTE:
            raise ValueError('fuente supera el límite de lectura')
        text = raw.decode(response.headers.get_content_charset() or 'utf-8', 'replace')
    if kind == 'text/html':
        parser = TextoHTML()
        parser.feed(text)
        return ' '.join(parser.parts)
    return text


def normalizar(text: str) -> str:
    return ' '.join(text.casefold().split())


def firma_contenido(text: str) -> str:
    fm = frontmatter(text)
    # Compara predicción y cuerpo, excluyendo ID, revisión y coste.
    body = re.sub(r'\A---\r?\n.*?\r?\n---', '', text, count=1, flags=re.S)
    return normalizar(fm.get('falsable', '') + ' ' + body)


def evaluar(path: pathlib.Path, verificar_red: bool = True,
            revisiones: pathlib.Path | None = None, comparar=()) -> dict:
    result = {'archivo': path.name, 'sha256': None, 'estado': 'RECHAZADA',
              'motivos': [], 'fuentes_consultadas': 0}

    def salida(estado, *motivos):
        result.update(estado=estado, motivos=list(motivos))
        return result

    try:
        text = leer_texto(path)
        digest = hashlib.sha256(text.encode()).hexdigest()
        result['sha256'] = digest
        fm = frontmatter(text)
        missing = [key for key in CAMPOS if not fm.get(key)]
        if missing:
            return salida('RECHAZADA', 'faltan campos: ' + ', '.join(missing))
        if fm['alcance'] not in ALCANCE_OK:
            return salida('ESCALAR_HUMANO', 'alcance no aprobado')
        if fm['estado'] != 'propuesta':
            return salida('RECHAZADA', 'solo se procesan candidatos en estado propuesta')
        if len(fm['falsable']) < 20 or len(fm['prueba']) < 20 or len(fm['costo']) < 5:
            return salida('RECHAZADA', 'predicción, prueba o coste incompletos')
        urls = parse_fuentes(fm['fuentes'])
        if not urls:
            return salida('RECHAZADA', 'fuentes debe ser una lista JSON de 1-10 URLs únicas')
        if not all(url_permitida(url) for url in urls):
            return salida('ESCALAR_HUMANO', 'fuente fuera de lista HTTPS permitida')
        current = firma_contenido(text)
        for other in comparar:
            previous = leer_texto(pathlib.Path(other))
            if (fm['id'] == frontmatter(previous).get('id')
                    or difflib.SequenceMatcher(None, current, firma_contenido(previous),
                                               autojunk=False).ratio() >= 0.90):
                return salida('DUPLICADA', 'ID o contenido léxico ya aceptado')
        review_path = (revisiones / (digest + '.json')) if revisiones else None
        if review_path is None or not review_path.exists():
            return salida('PENDIENTE_HUMANO', 'falta revisión humana ligada al hash del candidato')
        review = json.loads(leer_texto(review_path))
        if not isinstance(review, dict):
            return salida('PENDIENTE_HUMANO', 'revisión inválida')
        if (review.get('sha256') != digest or review.get('origen') != 'humano'
                or not isinstance(review.get('revisor'), str) or not review['revisor'].strip()):
            return salida('PENDIENTE_HUMANO', 'revisión sin procedencia o hash vigente')
        dt.date.fromisoformat(review.get('fecha_revision', ''))
        if review.get('decision') == 'rechazar':
            return salida('RECHAZADA', 'rechazo registrado por revisor humano')
        checks = ('alcance_seguro', 'falsable', 'prueba_viable',
                  'novedad_revisada', 'fuentes_respaldan')
        if review.get('decision') != 'aprobar' or any(review.get(k) is not True for k in checks):
            return salida('PENDIENTE_HUMANO', 'revisión no aprueba todas las comprobaciones')
        citations = review.get('citas')
        if (not isinstance(citations, list) or len(citations) != len(urls)
                or any(not isinstance(c, dict) or not isinstance(c.get('texto'), str)
                       or len(c['texto'].strip()) < 20 or c.get('url') not in urls for c in citations)
                or {c['url'] for c in citations} != set(urls)):
            return salida('PENDIENTE_HUMANO', 'se requiere una cita textual revisada por cada URL')
        if not verificar_red:
            return salida('PENDIENTE_RED', 'sin red no se certifica revalidación de fuentes')
        for citation in citations:
            result['fuentes_consultadas'] += 1
            try:
                source = texto_fuente(citation['url'])
            except (OSError, ValueError, LookupError) as exc:
                return salida('FUENTE_NO_VERIFICABLE', type(exc).__name__)
            if normalizar(citation['texto']) not in normalizar(source):
                return salida('FUENTE_NO_VERIFICABLE', 'cita textual no encontrada')
        return salida('ACEPTADA', 'revisión humana registrada y controles técnicos superados; no prueba científica')
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        return salida('RECHAZADA', 'entrada inválida: ' + type(exc).__name__)


def valida(path: pathlib.Path, verificar_red: bool) -> tuple[bool, list[str]]:
    """Compatibilidad; sin registro humano una hipótesis nunca se acepta."""
    result = evaluar(path, verificar_red=verificar_red)
    return result['estado'] == 'ACEPTADA', result['motivos']


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ruta', type=pathlib.Path)
    parser.add_argument('--rubrica', action='store_true', help='compatibilidad; siempre se aplican controles')
    parser.add_argument('--sin-red', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--revisiones', type=pathlib.Path, default=pathlib.Path('datos/revisiones'))
    parser.add_argument('--comparar', action='append', type=pathlib.Path, default=[])
    args = parser.parse_args()
    files = sorted(args.ruta.glob('*.md')) if args.ruta.is_dir() else ([args.ruta] if args.ruta.is_file() else [])
    accepted = list(args.comparar)
    results = []
    for path in files:
        result = evaluar(path, not args.sin_red, args.revisiones, accepted)
        results.append(result)
        if result['estado'] == 'ACEPTADA':
            accepted.append(path)
    count = sum(r['estado'] == 'ACEPTADA' for r in results)
    if args.json:
        print(json.dumps({'aceptadas': count, 'total': len(results), 'resultados': results}, ensure_ascii=False))
    else:
        for result in results:
            print(f"{result['estado']}: {result['archivo']} -> {'; '.join(result['motivos'])}")
        print(f'cobertura_tecnica = {count}/{len(results)}; no mide verdad científica')
    return 0 if results and count == len(results) else 2


if __name__ == '__main__':
    sys.exit(main())
