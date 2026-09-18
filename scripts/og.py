#!/usr/bin/env python3
"""Genera la imagen social (1200x630) de cada nota en og/nota-<slug>.png.

Arma un HTML por nota con la foto arriba y el titular abajo, y lo captura con
Chrome headless. Solo regenera las que faltan, salvo que se pase --todas.
"""
import html
import json
import os
import subprocess
from PIL import Image
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(RAIZ, ".og-tmp")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SECCIONES = {"derecho": "Derecho", "ia": "Inteligencia artificial",
             "tech": "Tecnología", "cripto": "Cripto"}

PLANTILLA = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1200px;height:630px;background:#fff;font-family:'Libre Franklin',sans-serif;
display:flex;flex-direction:column;overflow:hidden}}
.foto{{height:318px;width:100%;overflow:hidden;position:relative;background:#f7f7f5;flex:none}}
.foto img{{width:100%;height:100%;object-fit:cover;display:block}}
.sinfoto{{height:318px;background:#121212;display:flex;align-items:center;justify-content:center;flex:none}}
.sinfoto span{{font-family:'Newsreader',serif;font-size:108px;letter-spacing:.14em;color:#fff;text-indent:.14em}}
.txt{{flex:1;padding:30px 60px 0;display:flex;flex-direction:column;justify-content:center}}
.kicker{{font-size:19px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
color:#d0021b;margin-bottom:16px}}
h1{{font-family:'Newsreader',serif;font-weight:600;font-size:{tam}px;line-height:1.14;
letter-spacing:-.015em;color:#121212;display:-webkit-box;-webkit-line-clamp:3;
-webkit-box-orient:vertical;overflow:hidden}}
.pie{{flex:none;display:flex;align-items:center;justify-content:space-between;
padding:22px 60px 26px;border-top:1px solid #e2e2e2;margin-top:24px}}
.marca{{font-family:'Newsreader',serif;font-size:31px;letter-spacing:.13em;color:#121212;text-indent:.13em}}
.meta{{font-size:17px;font-weight:600;letter-spacing:.11em;text-transform:uppercase;color:#8b8b8b}}
</style></head><body>
{figura}
<div class="txt"><div class="kicker">{kicker}</div><h1>{titulo}</h1></div>
<div class="pie"><div class="marca">FUERO</div><div class="meta">{seccion}</div></div>
</body></html>"""


def main():
    todas = "--todas" in sys.argv
    datos = json.load(open(os.path.join(RAIZ, "noticias.json"), encoding="utf-8"))
    cuerpos = {}
    dir_cuerpos = os.path.join(RAIZ, "cuerpos")
    if os.path.isdir(dir_cuerpos):
        for arch in os.listdir(dir_cuerpos):
            if arch.endswith(".json"):
                for item in json.load(open(os.path.join(dir_cuerpos, arch), encoding="utf-8")):
                    cuerpos[item["id"]] = item

    os.makedirs(TMP, exist_ok=True)
    os.makedirs(os.path.join(RAIZ, "og"), exist_ok=True)
    hechas = 0
    for n in datos["notas"]:
        slug = n.get("slug")
        if not slug:
            continue
        destino = os.path.join(RAIZ, "og", f"nota-{slug}.jpg")
        crudo = destino + ".png"
        if os.path.exists(destino) and not todas:
            continue
        titulo = cuerpos.get(n["id"], {}).get("titulo", n["titulo"])
        tam = 52 if len(titulo) < 60 else (46 if len(titulo) < 85 else 41)
        if n.get("imagen"):
            ruta = os.path.join(RAIZ, n["imagen"].lstrip("/"))
            figura = f'<div class="foto"><img src="file://{ruta}"></div>'
        else:
            figura = '<div class="sinfoto"><span>FUERO</span></div>'
        pagina = PLANTILLA.format(
            figura=figura, kicker=html.escape(n["kicker"]),
            titulo=html.escape(titulo), seccion=SECCIONES[n["tema"]], tam=tam)
        tmp_html = os.path.join(TMP, f"{slug}.html")
        open(tmp_html, "w", encoding="utf-8").write(pagina)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", "--virtual-time-budget=5000",
                        f"--screenshot={crudo}", "--window-size=1200,630",
                        f"file://{tmp_html}"],
                       capture_output=True, timeout=90)
        if os.path.exists(crudo):
            Image.open(crudo).convert("RGB").save(destino, "JPEG", quality=84, optimize=True)
            os.remove(crudo)
            hechas += 1
            print("og  ", slug)
        else:
            print("FALLO", slug, file=sys.stderr)
    print(f"{hechas} imágenes sociales generadas")


if __name__ == "__main__":
    main()
