#!/usr/bin/env python3
"""Avisa a los buscadores que hay URLs nuevas o actualizadas, vía IndexNow.

IndexNow es el protocolo abierto que usan Bing, Yandex, Seznam y Naver. Importa
para los asistentes de IA porque varios de ellos buscan sobre el índice de Bing.
Google no participa: a Google se le avisa dando de alta el sitio en Search Console.

Uso:
  python3 scripts/indexnow.py            envía todas las URLs del sitemap
  python3 scripts/indexnow.py <url> ...  envía solo esas
"""
import json
import os
import re
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITIO = "fuero.com.ar"
CLAVE = "3f1c8a24b7e04d59ac6e2b8f5d0a71c6"
ENDPOINT = "https://api.indexnow.org/IndexNow"


def urls_del_sitemap():
    ruta = os.path.join(RAIZ, "sitemap.xml")
    return re.findall(r"<loc>([^<]+)</loc>", open(ruta, encoding="utf-8").read())


def main():
    # el archivo con la clave tiene que estar publicado en la raíz del dominio
    archivo_clave = os.path.join(RAIZ, f"{CLAVE}.txt")
    if not os.path.exists(archivo_clave):
        open(archivo_clave, "w").write(CLAVE)
        print("creado", os.path.basename(archivo_clave), "(subilo antes de avisar)")

    urls = sys.argv[1:] or urls_del_sitemap()
    cuerpo = json.dumps({
        "host": SITIO,
        "key": CLAVE,
        "keyLocation": f"https://{SITIO}/{CLAVE}.txt",
        "urlList": urls,
    }).encode()
    pedido = urllib.request.Request(
        ENDPOINT, data=cuerpo,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            print(f"IndexNow respondió {r.status} para {len(urls)} URLs")
    except urllib.error.HTTPError as ex:
        print(f"IndexNow rechazó el envío: {ex.code} {ex.read()[:200]!r}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
