"""RSS/Atom públicos: metadatos y procedencia, no alertas ni etiquetas humanas.

python3 -m bio.recolector.multifuente --salida salidas/fuentes/primera --fuentes cdc ecdc
Cada petición se aísla en un hijo con plazo de15s, también para DNS/lecturas lentas.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from bio.preparacion import escribir_json, jsonl
from bio.radar import fecha_utc, normalizar, url_canonica
from bio.vigilar import Reloj, ruta_segura

MAX_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 500
TIMEOUT = 15
RAIZ = Path(__file__).resolve().parents[2]
FUENTES = {
    'oms': {'nombre': 'OMS-noticias', 'url': 'https://www.who.int/rss-feeds/news-english.xml'},
    'cdc': {'nombre': 'CDC-noticias', 'url': 'https://tools.cdc.gov/api/v2/resources/media/132608.rss'},
    'ecdc': {'nombre': 'ECDC-CDTR', 'url': 'https://www.ecdc.europa.eu/en/taxonomy/term/1505/feed'},
}


def validar_url(url, hosts):
    p = urllib.parse.urlsplit(url)
    if (p.scheme != 'https' or p.hostname not in hosts or p.username or p.password
            or p.port not in (None, 443)):
        raise ValueError('destino remoto no permitido')


class Redirecciones(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validar_url(newurl, self.hosts)
        # urllib leería sin límite el cuerpo de una redirección antes de seguirla.
        # Los endpoints comprobados son directos; un cambio requiere revisión explícita.
        raise ValueError('redirección no permitida; revisar endpoint de la fuente')


def descargar(fuente):
    url = FUENTES[fuente]['url']
    hosts = {urllib.parse.urlsplit(url).hostname}
    validar_url(url, hosts)
    opener = urllib.request.build_opener(Redirecciones(hosts))
    req = urllib.request.Request(url, headers={
        'User-Agent': 'bio-humanidad/0.2 (+https://github.com/javiercamarapp/bio-humanidad)',
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml',
        'Accept-Encoding': 'identity',
    })
    with opener.open(req, timeout=TIMEOUT) as response:
        validar_url(response.geturl(), hosts)
        raw = response.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('feed vacío o superior a2MiB')
    return raw


def descargar_acotado(fuente):
    if fuente not in FUENTES:
        raise ValueError('fuente no soportada')
    reloj = Reloj()
    result = subprocess.run([sys.executable, '-m', 'bio.recolector.multifuente',
                             '--descargar', fuente, '--padre', str(os.getpid())],
                            cwd=RAIZ, capture_output=True, timeout=TIMEOUT,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    if reloj.segundos() >= TIMEOUT or reloj.retrocedio:
        raise subprocess.TimeoutExpired('descarga', TIMEOUT)
    if result.returncode != 0:
        raise ValueError('falló descarga: ' + result.stderr.decode('utf-8', 'replace')[:500])
    if not result.stdout or len(result.stdout) > MAX_BYTES:
        raise ValueError('descarga vacía o demasiado grande')
    return result.stdout


def parsear_feed(raw, fuente, observado):
    if fuente not in FUENTES or not raw or len(raw) > MAX_BYTES:
        raise ValueError('fuente o tamaño inválido')
    obs = fecha_utc(observado)
    text = raw.decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD y entidades declaradas no permitidas')
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError('XML inválido') from exc
    stack, count = [(root, 0)], 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if depth > 64 or count > 30000:
            raise ValueError('XML excesivamente complejo')
        stack.extend((child, depth + 1) for child in node)
    atom = '{http://www.w3.org/2005/Atom}'
    if root.tag == 'rss':
        items = root.findall('./channel/item')
    elif root.tag == atom + 'feed':
        items = root.findall(atom + 'entry')
    else:
        raise ValueError('solo RSS2 o Atom; no HTML ni otros formatos')
    rows, errors = [], []
    for index, item in enumerate(items[:MAX_ITEMS], 1):
        try:
            if root.tag == 'rss':
                title = item.find('title')
                url = (item.findtext('link') or '').strip()
                published = parsedate_to_datetime((item.findtext('pubDate') or '').strip())
            else:
                title = item.find(atom + 'title')
                links = [e.get('href') for e in item.findall(atom + 'link')
                         if e.get('rel', 'alternate') == 'alternate']
                url = links[0] if links else ''
                published = datetime.fromisoformat((item.findtext(atom + 'published') or '').replace('Z', '+00:00'))
            if published.tzinfo is None:
                raise ValueError('fecha de publicación sin zona horaria')
            if published.astimezone(timezone.utc) > obs:
                raise ValueError('instante de publicación posterior a la observación')
            literal = ''.join(title.itertext()).strip() if title is not None else ''
            if not 0 < len(literal) <= 4096:
                raise ValueError('titular vacío o demasiado largo')
            url = url_canonica(url)
            row = dict(id=hashlib.sha256(url.encode()).hexdigest()[:16],
                       fuente=FUENTES[fuente]['nombre'],
                       fecha=published.astimezone(timezone.utc).date().isoformat(),
                       claim_literal=literal, url=url, recolectado_en=observado)
            normalizar([row])
            rows.append(row)
        except (ValueError, TypeError, OverflowError) as exc:
            errors.append(dict(item=index, error=str(exc)[:200]))
    newest = max((row['fecha'] for row in rows), default=None)
    age = (obs.date() - datetime.fromisoformat(newest).date()).days if newest else None
    return normalizar(rows), dict(items_feed=len(items), procesadas=min(len(items), MAX_ITEMS),
        omitidas_por_limite=max(0, len(items)-MAX_ITEMS), descartadas=len(errors),
        errores=errors, cobertura_exhaustiva=False,
        publicacion_mas_reciente_procesada=newest, dias_desde_publicacion_mas_reciente=age,
        advertencias=['SIN_PUBLICACIONES_RECIENTES'] if age is not None and age > 30 else [])


def ejecutar(salida, fuentes=None):
    fuentes = ['cdc', 'ecdc'] if fuentes is None else list(fuentes)
    if not fuentes or len(set(fuentes)) != len(fuentes) or any(f not in FUENTES for f in fuentes):
        raise ValueError('seleccionar fuentes soportadas sin duplicados')
    salida = ruta_segura(salida)
    salida.mkdir(parents=True, exist_ok=False)
    rows, details, errors = [], {}, 0
    for name in fuentes:
        detail = dict(url=FUENTES[name]['url'], nombre=FUENTES[name]['nombre'], estado='ERROR')
        try:
            raw = descargar_acotado(name)
            observed = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            with (salida / (name + '.xml')).open('xb') as stream:
                stream.write(raw)
            parsed, meta = parsear_feed(raw, name, observed)
            detail.update(meta, recolectado_en=observed, sha256=hashlib.sha256(raw).hexdigest(),
                          senales=len(parsed), estado='PARCIAL' if meta['descartadas'] else 'LEIDO')
            rows.extend(parsed)
            errors += int(meta['descartadas'] > 0)
        except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            detail['error'] = type(exc).__name__ + ': ' + str(exc)[:500]
            errors += 1
        details[name] = detail
    rows = normalizar(rows)
    with (salida / 'senales.jsonl').open('x', encoding='utf-8') as stream:
        stream.write(jsonl(rows))
    result = dict(version=1, estado='RECOLECCION_PARCIAL' if errors else (
                      'RECOLECCION_COMPLETA' if rows else 'SIN_SENALES'),
                  publicable=False, etiquetas_humanas_generadas=0, gasto_api_usd=0,
                  senales_unicas=len(rows), errores=errors, fuentes=details,
                  cobertura_exhaustiva=False,
                  artefactos_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in salida.iterdir() if p.is_file()})
    escribir_json(salida / 'manifest.json', result)
    return result


def vigilar_descarga(padre):
    """El hijo también se termina a sí mismo si muere el recolector supervisor.

    No mata PIDs ajenos. Evita dejar una petición huérfana tras STOP/SIGKILL del padre.
    Solo se inicia en el proceso dedicado de descarga, nunca en el proceso importador.
    """
    if padre != os.getppid():
        raise ValueError('supervisor de descarga ausente')
    reloj = Reloj()
    def observar():
        while True:
            if (os.getppid() != padre or reloj.segundos() >= TIMEOUT or reloj.retrocedio):
                os._exit(2)  # Solo este hijo dedicado; nunca el CLI del operador.
            time.sleep(0.1)
    threading.Thread(target=observar, daemon=True).start()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, help='carpeta NUEVA, no se sobrescribe')
    parser.add_argument('--fuentes', nargs='+', choices=sorted(FUENTES), default=None)
    parser.add_argument('--descargar', choices=sorted(FUENTES), help=argparse.SUPPRESS)
    parser.add_argument('--padre', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.descargar:
            vigilar_descarga(args.padre if args.padre is not None else os.getppid())
            sys.stdout.buffer.write(descargar(args.descargar))
            return 0
        if args.salida is None:
            raise ValueError('--salida es obligatorio')
        result = ejecutar(args.salida, args.fuentes)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['estado'] == 'RECOLECCION_COMPLETA' else 2
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
