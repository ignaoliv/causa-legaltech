#!/usr/bin/env python3
"""Lee noticias.json, baja cada `imagen_origen` a img/<id>.jpg (máx 1200 px de ancho)
y deja `imagen` apuntando al archivo local. Se puede correr las veces que haga falta:
salta las que ya están bajadas."""
import json, os, re, subprocess, sys, unicodedata, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON = os.path.join(RAIZ, 'noticias.json')
IMG = os.path.join(RAIZ, 'img')
os.makedirs(IMG, exist_ok=True)

def slug(txt):
    txt = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', txt.lower()).strip('-')[:60]

data = json.load(open(JSON, encoding='utf-8'))
for n in data['notas']:
    n.setdefault('id', slug(n['titulo']))
    origen = n.get('imagen_origen')
    destino = os.path.join(IMG, n['id'] + '.jpg')
    if not origen:
        continue
    if os.path.exists(destino):
        n['imagen'] = '/img/' + n['id'] + '.jpg'; continue
    try:
        req = urllib.request.Request(origen, headers={'User-Agent': 'Mozilla/5.0 (Macintosh) FUERO/1.0'})
        raw = urllib.request.urlopen(req, timeout=25).read()
        tmp = destino + '.tmp'
        open(tmp, 'wb').write(raw)
        # convierte a jpg y limita ancho; sips viene con macOS
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82',
                        '--resampleWidth', '1200', tmp, '--out', destino],
                       check=True, capture_output=True)
        os.remove(tmp)
        n['imagen'] = '/img/' + n['id'] + '.jpg'
        print('ok  ', n['id'], len(raw)//1024, 'KB ->', os.path.getsize(destino)//1024, 'KB')
    except Exception as e:
        print('FALLO', n['id'], e, file=sys.stderr)
        n['imagen'] = None

json.dump(data, open(JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
