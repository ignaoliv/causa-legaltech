#!/usr/bin/env python3
"""Generador estático de FUERO.

Lee noticias.json (metadatos) y cuerpos/*.json (artículos reescritos) y produce:
  index.html                     portada con el contenido ya renderizado en HTML
  nota/<slug>/index.html         artículo propio
  seccion/<x>/index.html         listados por sección
  sobre-fuero/index.html         quiénes somos, criterios, correcciones
  sitemap.xml  robots.txt  rss.xml  llms.txt

Todo el contenido va en el HTML, sin depender de JavaScript, para que lo lean
tanto Google como los crawlers de los asistentes de IA.
"""
import html
import json
import os
import re
import shutil
import unicodedata
from datetime import datetime, timezone, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITIO = "https://fuero.com.ar"
MARCA = "FUERO"
LEMA = "Derecho, IA y tecnología"
DESC_SITIO = ("Noticias de derecho, inteligencia artificial y tecnología para abogados "
              "en Argentina. Fallos, normativa, legaltech y cripto, explicados por su "
              "impacto en la práctica profesional.")
META_PORTADA = ("Noticias de derecho, IA y tecnología para abogados en Argentina. Fallos, "
                "normativa, legaltech y cripto, con foco en la práctica diaria.")
ART = timezone(timedelta(hours=-3))

SECCIONES = {
    "derecho": ("Derecho", "derecho",
                "Fallos, acordadas, normativa y vida del Poder Judicial argentino.",
                "Fallos de la Corte, acordadas, honorarios y normativa del Boletín Oficial, "
                "explicados por su efecto en la práctica del abogado."),
    "ia": ("Inteligencia artificial", "inteligencia-artificial",
           "Cómo la inteligencia artificial cambia el trabajo jurídico: fallos, reglas de uso y herramientas.",
           "IA y derecho en Argentina: sanciones por citas inventadas, reglas de uso en la "
           "Justicia y herramientas para estudios jurídicos."),
    "tech": ("Tecnología", "tecnologia",
             "Legaltech, expediente electrónico, ciberseguridad y datos personales en el estudio.",
             "Legaltech, notificaciones electrónicas, ciberseguridad y datos personales: la "
             "tecnología que cambia el día a día de un estudio."),
    "cripto": ("Cripto", "cripto",
               "Criptoactivos y derecho: regulación de la CNV, impuestos, lavado y fallos.",
               "Criptoactivos y derecho argentino: registro de PSAV en la CNV, impuestos de "
               "ARCA, prevención de lavado y fallos del caso LIBRA."),
}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


# ---------------------------------------------------------------- utilidades
def e(x):
    return html.escape(str(x or ""), quote=True)


def slugificar(txt, largo=70):
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-z0-9]+", "-", txt.lower()).strip("-")
    if len(txt) <= largo:
        return txt
    corte = txt[:largo]
    return corte.rsplit("-", 1)[0] if "-" in corte else corte


def dia(iso):
    return datetime.strptime(iso, "%Y-%m-%d").replace(tzinfo=ART)


def fecha_larga(iso):
    d = dia(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(iso):
    d = dia(iso)
    return f"{d.day} {MESES_CORTO[d.month - 1]}"


def relativa(iso, hoy):
    dias = (hoy.date() - dia(iso).date()).days
    if dias <= 0:
        return "Hoy"
    if dias == 1:
        return "Ayer"
    if dias < 7:
        return f"Hace {dias} días"
    return fecha_corta(iso)


def escribir(ruta, contenido):
    destino = os.path.join(RAIZ, ruta)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(contenido)
    return destino


def jsonld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


# ---------------------------------------------------------------- datos
def cargar():
    datos = json.load(open(os.path.join(RAIZ, "noticias.json"), encoding="utf-8"))
    cuerpos = {}
    dir_cuerpos = os.path.join(RAIZ, "cuerpos")
    if os.path.isdir(dir_cuerpos):
        for arch in sorted(os.listdir(dir_cuerpos)):
            if arch.endswith(".json"):
                for item in json.load(open(os.path.join(dir_cuerpos, arch), encoding="utf-8")):
                    cuerpos[item["id"]] = item
    faltaban = [n["id"] for n in datos["notas"] if not n.get("slug")]
    notas = []
    for n in datos["notas"]:
        c = cuerpos.get(n["id"], {})
        n["slug"] = n.get("slug") or slugificar(c.get("titulo") or n["titulo"])
        n["url_nota"] = f"/nota/{n['slug']}/"
        if c:
            n["titulo"] = c.get("titulo", n["titulo"])
            n["bajada"] = c.get("bajada", n["bajada"])
            n["meta_description"] = c.get("meta_description", n["bajada"])
            n["sumario"] = c.get("sumario", [])
            n["cuerpo_html"] = c.get("cuerpo_html", "")
            n["faq"] = c.get("faq", [])
            n["entidades"] = c.get("entidades", [])
            n["keywords"] = c.get("keywords", [])
            n["palabras"] = c.get("palabras", 0)
            n["min"] = max(3, round(c.get("palabras", 700) / 200))
        else:
            n.setdefault("meta_description", n["bajada"])
            for k in ("sumario", "faq", "entidades", "keywords"):
                n.setdefault(k, [])
            n.setdefault("cuerpo_html", "")
        n["seccion"] = SECCIONES[n["tema"]][0]
        n["seccion_slug"] = SECCIONES[n["tema"]][1]
        notas.append(n)
    notas.sort(key=lambda x: (x["fecha"], x.get("destacada", False)), reverse=True)
    # el slug queda fijo en noticias.json para que la URL no cambie si se edita el titular
    if faltaban:
        json.dump(datos, open(os.path.join(RAIZ, "noticias.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return datos, notas


# ---------------------------------------------------------------- bloques
def figura(n, clase=""):
    if n.get("imagen"):
        return (f'<div class="foto {clase}"><img src="{e(n["imagen"])}" '
                f'alt="{e(n["titulo"])}" loading="lazy" width="1200" height="675"></div>')
    return '<div class="marco"><strong>FUERO</strong></div>'


def tarjeta(n, hoy):
    txt = f"{n['titulo']} {n['bajada']} {n['fuente']} {n['kicker']}".lower()
    return f"""<article class="tarjeta" data-tema="{e(n['tema'])}" data-origen="{e(n.get('origen','curado'))}" data-texto="{e(txt)}">
      {figura(n)}
      <span class="kicker">{e(n['kicker'])}</span>
      <h3><a href="{n['url_nota']}">{e(n['titulo'])}</a></h3>
      <p>{e(n['bajada'])}</p>
      <div class="pie-tarjeta">
        <span>{e(n['fuente'])}</span>
        <span>{fecha_corta(n['fecha'])}</span>
        <span>{n['min']} min</span>
      </div>
    </article>"""


def bloque_portada(notas, hoy):
    principal = next((n for n in notas if n.get("destacada")), notas[0])
    secundarias = [n for n in notas if n is not principal and n.get("portada")][:3]
    usadas = {id(principal)} | {id(x) for x in secundarias}
    relacionadas = [n for n in notas if id(n) not in usadas and n["tema"] == principal["tema"]][:3]

    epi = ""
    if principal.get("epigrafe") or principal.get("credito_imagen"):
        epi = (f'<p class="epigrafe">{e(principal.get("epigrafe",""))} '
               f'{"Foto: " + e(principal["credito_imagen"]) if principal.get("credito_imagen") else ""}</p>')
    rel = ""
    if relacionadas:
        rel = ('<ul class="relacionadas">'
               + "".join(f'<li><a href="{r["url_nota"]}">{e(r["titulo"])}</a></li>' for r in relacionadas)
               + "</ul>")
    col_a = f"""<article>
        <div class="figura">{figura(principal)}{epi}</div>
        <span class="kicker">{e(principal['kicker'])}</span>
        <h1 class="titular-principal"><a href="{principal['url_nota']}">{e(principal['titulo'])}</a></h1>
        <p class="bajada">{e(principal['bajada'])}</p>
        <div class="credito">
          <span class="autor">{e(principal['fuente'])}</span>
          <span>{principal['min']} min de lectura</span>
          <span>{relativa(principal['fecha'], hoy)}</span>
        </div>
        {rel}
      </article>"""

    col_b = "".join(f"""<article class="nota-col">
        {'<div class="figura">' + figura(n) + '</div>' if i == 0 else ''}
        <span class="kicker">{e(n['kicker'])}</span>
        <h3><a href="{n['url_nota']}">{e(n['titulo'])}</a></h3>
        <p>{e(n['bajada'])}</p>
        <div class="credito"><span>{e(n['fuente'])}</span><span>{n['min']} min</span><span>{relativa(n['fecha'], hoy)}</span></div>
      </article>""" for i, n in enumerate(secundarias))

    ultimas = "".join(
        f'<li><span class="sello-hora">{fecha_corta(n["fecha"])}</span>'
        f'<a href="{n["url_nota"]}">{e(n["titulo"])}</a></li>' for n in notas[:6])
    return col_a, col_b, ultimas, principal


# ---------------------------------------------------------------- head
def head(titulo, descripcion, url, imagen=None, tipo="website", extra="", noticia=None,
         titulo_social=None, medidas=(1200, 630)):
    imagen = imagen or "/og/fuero.png"
    if not imagen.startswith("http"):
        imagen = SITIO + imagen
    social = titulo_social or titulo
    # los previews sociales cortan cerca de los 125 caracteres en el celular
    desc_social = descripcion
    if len(desc_social) > 125:
        desc_social = desc_social[:122].rsplit(" ", 1)[0] + "…"
    metas = f"""<title>{e(titulo)}</title>
<meta name="description" content="{e(descripcion)}">
<link rel="canonical" href="{e(url)}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<meta property="og:type" content="{tipo}">
<meta property="og:site_name" content="{MARCA}">
<meta property="og:locale" content="es_AR">
<meta property="og:title" content="{e(social)}">
<meta property="og:description" content="{e(desc_social)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(imagen)}">
<meta property="og:image:width" content="{medidas[0]}">
<meta property="og:image:height" content="{medidas[1]}">
<meta property="og:image:alt" content="{e(social)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(social)}">
<meta name="twitter:description" content="{e(desc_social)}">
<meta name="twitter:image" content="{e(imagen)}">
<meta name="theme-color" content="#121212">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/og/favicon-32.png">
<link rel="apple-touch-icon" href="/og/favicon-180.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="{MARCA}" href="/rss.xml">"""
    if noticia:
        metas += f"""
<meta property="article:published_time" content="{noticia['fecha']}T09:00:00-03:00">
<meta property="article:modified_time" content="{noticia['fecha']}T09:00:00-03:00">
<meta property="article:section" content="{e(noticia['seccion'])}">
<meta name="news_keywords" content="{e(', '.join(noticia.get('keywords', [])[:8]))}">"""
    return metas + "\n" + extra


def org_ld():
    return {
        "@type": "NewsMediaOrganization",
        "@id": f"{SITIO}/#organizacion",
        "name": MARCA,
        "url": SITIO + "/",
        "logo": {"@type": "ImageObject", "url": f"{SITIO}/og/favicon-512.png",
                 "width": 512, "height": 512},
        "description": DESC_SITIO,
        "email": "dji.olivieri@gmail.com",
        "areaServed": {"@type": "Country", "name": "Argentina"},
        "knowsLanguage": "es-AR",
        "knowsAbout": ["derecho argentino", "Poder Judicial", "inteligencia artificial aplicada al derecho",
                       "legaltech", "criptoactivos y regulación", "honorarios profesionales"],
    }


def sitio_ld():
    return {
        "@type": "WebSite",
        "@id": f"{SITIO}/#sitio",
        "url": SITIO + "/",
        "name": MARCA,
        "inLanguage": "es-AR",
        "description": DESC_SITIO,
        "publisher": {"@id": f"{SITIO}/#organizacion"},
    }


# ---------------------------------------------------------------- páginas
def render_portada(plantilla, notas, hoy):
    col_a, col_b, ultimas, principal = bloque_portada(notas, hoy)
    rejilla = "".join(tarjeta(n, hoy) for n in notas) + """
    <div class="sin-resultados" id="sinResultados" style="display:none">
      <p>No encontramos notas con ese criterio</p>
      <span>Probá con otro término o volvé a "Todo".</span>
    </div>"""

    lista = {
        "@type": "ItemList",
        "name": "Últimas noticias de FUERO",
        "numberOfItems": len(notas),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": SITIO + n["url_nota"], "name": n["titulo"]}
            for i, n in enumerate(notas[:20])],
    }
    grafo = jsonld({"@context": "https://schema.org", "@graph": [
        org_ld(), sitio_ld(),
        {"@type": "CollectionPage", "@id": SITIO + "/#portada", "url": SITIO + "/",
         "name": f"{MARCA}, {LEMA}", "description": DESC_SITIO, "inLanguage": "es-AR",
         "isPartOf": {"@id": f"{SITIO}/#sitio"}, "about": lista},
        lista]})

    datos_js = json.dumps([{"t": n["titulo"], "min": n["min"], "fuente": n["fuente"]} for n in notas],
                          ensure_ascii=False)
    s = plantilla
    s = s.replace("<!--FUERO:head-->", head(
        f"{MARCA}, noticias de derecho, IA y tecnología para abogados",
        META_PORTADA, SITIO + "/", extra=grafo))
    s = s.replace("<!--FUERO:fecha-->", f"{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}")
    s = s.replace("<!--FUERO:colA-->", col_a)
    s = s.replace("<!--FUERO:colB-->", col_b)
    s = s.replace("<!--FUERO:ultimas-->", ultimas)
    s = s.replace("<!--FUERO:rejilla-->", rejilla)
    s = s.replace("<!--FUERO:datos-->", f"<script>window.FUERO_NOTAS={datos_js};</script>")
    return s


CSS_PAGINA = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--fondo:#fff;--tinta:#121212;--gris:#363636;--gris-claro:#5a5a5a;--gris-tenue:#8b8b8b;
--regla:#e2e2e2;--crema:#f7f7f5;--vivo:#d0021b;
--serif:'Newsreader',Georgia,serif;--sans:'Libre Franklin',-apple-system,sans-serif}
body{background:var(--fondo);color:var(--tinta);font-family:var(--serif);
-webkit-font-smoothing:antialiased;line-height:1.5}
a{color:inherit;text-decoration:none}
img{max-width:100%;display:block}
.cinta{height:4px;background:var(--tinta)}
.barra{border-bottom:1px solid var(--regla);padding:14px 0;margin-bottom:34px}
.barra-in,.envoltorio{max-width:760px;margin:0 auto;padding:0 22px}
.barra-in{display:flex;align-items:center;justify-content:space-between;gap:16px}
.marca{font-family:var(--serif);font-size:27px;letter-spacing:.12em;font-weight:500}
.barra nav{font-family:var(--sans);font-size:12.5px;font-weight:600;letter-spacing:.07em;
text-transform:uppercase;display:flex;gap:17px;color:var(--gris-claro);flex-wrap:wrap}
.barra nav a:hover{color:var(--tinta)}
.miga{font-family:var(--sans);font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;
color:var(--gris-tenue);margin-bottom:15px}
.miga a:hover{color:var(--tinta);text-decoration:underline}
.kicker{font-family:var(--sans);font-size:11.5px;font-weight:700;letter-spacing:.11em;
text-transform:uppercase;color:var(--vivo);display:block;margin-bottom:11px}
h1{font-family:var(--serif);font-size:44px;line-height:1.1;letter-spacing:-.018em;
font-weight:600;margin-bottom:17px}
.bajada{font-size:20.5px;line-height:1.45;color:var(--gris);margin-bottom:19px}
.ficha{font-family:var(--sans);font-size:12.5px;color:var(--gris-tenue);display:flex;
flex-wrap:wrap;gap:15px;padding-bottom:19px;border-bottom:1px solid var(--regla);margin-bottom:23px}
.ficha b{color:var(--gris);font-weight:600}
figure{margin-bottom:26px}
figure img{width:100%;border:1px solid var(--regla)}
figcaption{font-family:var(--sans);font-size:11.5px;color:var(--gris-tenue);margin-top:8px;line-height:1.45}
.clave{background:var(--crema);border-left:3px solid var(--tinta);padding:20px 24px;margin-bottom:30px}
.clave h2{font-family:var(--sans);font-size:11.5px;font-weight:700;letter-spacing:.11em;
text-transform:uppercase;color:var(--gris-claro);margin-bottom:12px}
.clave ul{list-style:none}
.clave li{font-size:17px;line-height:1.5;padding-left:19px;position:relative;margin-bottom:10px}
.clave li:last-child{margin-bottom:0}
.clave li::before{content:'';position:absolute;left:0;top:10px;width:6px;height:6px;
background:var(--vivo);border-radius:50%}
.cuerpo p{font-size:19px;line-height:1.65;margin-bottom:20px}
.cuerpo h2{font-family:var(--serif);font-size:27px;font-weight:600;line-height:1.2;
margin:36px 0 14px;letter-spacing:-.01em}
.cuerpo ul,.cuerpo ol{margin:0 0 20px 22px}
.cuerpo li{font-size:19px;line-height:1.6;margin-bottom:9px}
.cuerpo strong{font-weight:600}
.cuerpo blockquote{border-left:3px solid var(--regla);padding-left:19px;margin:0 0 20px;
font-size:21px;line-height:1.5;color:var(--gris)}
.cuerpo a{text-decoration:underline;text-underline-offset:3px}
.fuente{font-family:var(--sans);font-size:13.5px;line-height:1.6;color:var(--gris-claro);
border:1px solid var(--regla);padding:17px 20px;margin:34px 0}
.fuente a{color:var(--tinta);font-weight:600;text-decoration:underline}
.faq{margin-top:44px;border-top:3px solid var(--tinta);padding-top:22px}
.faq > h2{font-family:var(--sans);font-size:12.5px;font-weight:700;letter-spacing:.11em;
text-transform:uppercase;margin-bottom:19px}
.faq details{border-bottom:1px solid var(--regla);padding:14px 0}
.faq summary{font-family:var(--serif);font-size:20px;font-weight:600;cursor:pointer;line-height:1.3}
.faq summary::marker{color:var(--vivo)}
.faq p{font-size:17px;line-height:1.6;color:var(--gris);margin-top:11px}
.mas{margin-top:48px;border-top:1px solid var(--regla);padding-top:22px}
.mas h2{font-family:var(--sans);font-size:12.5px;font-weight:700;letter-spacing:.11em;
text-transform:uppercase;margin-bottom:17px}
.mas ul{list-style:none;display:grid;gap:15px}
.mas li{border-bottom:1px solid var(--regla);padding-bottom:15px}
.mas li:last-child{border-bottom:none}
.mas .k{font-family:var(--sans);font-size:10.5px;font-weight:700;letter-spacing:.1em;
text-transform:uppercase;color:var(--vivo);display:block;margin-bottom:5px}
.mas h3{font-family:var(--serif);font-size:20px;font-weight:600;line-height:1.24}
.mas h3 a:hover{color:var(--gris)}
.lista{display:grid;gap:26px;margin-bottom:40px}
.item{display:grid;grid-template-columns:200px 1fr;gap:20px;border-bottom:1px solid var(--regla);
padding-bottom:26px}
.item:last-child{border-bottom:none}
.item img{width:200px;height:133px;object-fit:cover;border:1px solid var(--regla)}
.item h2{font-family:var(--serif);font-size:23px;font-weight:600;line-height:1.2;margin-bottom:8px}
.item p{font-size:16px;color:var(--gris);line-height:1.45;margin-bottom:9px}
.item .pie{font-family:var(--sans);font-size:11.5px;color:var(--gris-tenue);display:flex;gap:13px}
.intro{font-size:19px;color:var(--gris);line-height:1.55;margin-bottom:34px;
padding-bottom:26px;border-bottom:1px solid var(--regla)}
.pie-sitio{border-top:3px solid var(--tinta);margin-top:60px;padding:26px 0 50px;
font-family:var(--sans);font-size:12.5px;color:var(--gris-tenue)}
.pie-sitio .envoltorio{display:flex;gap:18px;flex-wrap:wrap;align-items:center}
.pie-sitio a:hover{color:var(--tinta);text-decoration:underline}
@media(max-width:700px){
h1{font-size:33px}.cuerpo p,.cuerpo li{font-size:17.5px}.bajada{font-size:18px}
.item{grid-template-columns:1fr}.item img{width:100%;height:auto}
.barra-in{flex-direction:column;align-items:flex-start;gap:11px}
}
"""


def cascara(titulo_head, descripcion, url, cuerpo, imagen=None, tipo="website",
            extra="", noticia=None, titulo_social=None, medidas=(1200, 630)):
    return f"""<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{head(titulo_head, descripcion, url, imagen, tipo, extra, noticia, titulo_social, medidas)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/pagina.css">
</head>
<body>
<div class="cinta"></div>
<div class="barra"><div class="barra-in">
  <a class="marca" href="/">FUERO</a>
  <nav>
    <a href="/seccion/derecho/">Derecho</a>
    <a href="/seccion/inteligencia-artificial/">IA</a>
    <a href="/seccion/tecnologia/">Tecnología</a>
    <a href="/seccion/cripto/">Cripto</a>
    <a href="/seccion/ultimas/">Últimas</a>
  </nav>
</div></div>
{cuerpo}
<footer class="pie-sitio"><div class="envoltorio">
  <span>© {datetime.now(ART).year} FUERO</span>
  <a href="/">Portada</a>
  <a href="/sobre-fuero/">Quiénes somos</a>
  <a href="/seccion/ultimas/">Todas las noticias</a>
  <a href="/rss.xml">RSS</a>
  <span>Buenos Aires, Argentina</span>
</div></footer>
</body>
</html>"""


def render_nota(n, notas, hoy):
    sumario = ""
    if n.get("sumario"):
        sumario = ('<div class="clave"><h2>Lo que hay que saber</h2><ul>'
                   + "".join(f"<li>{e(b)}</li>" for b in n["sumario"]) + "</ul></div>")
    fig = ""
    if n.get("imagen"):
        credito = f"Foto: {e(n['credito_imagen'])}" if n.get("credito_imagen") else ""
        pie = f"{e(n.get('epigrafe',''))} {credito}".strip()
        fig = (f'<figure><img src="{e(n["imagen"])}" alt="{e(n["titulo"])}" width="1200" height="675">'
               + (f"<figcaption>{pie}</figcaption>" if pie else "") + "</figure>")
    faq = ""
    if n.get("faq"):
        faq = ('<section class="faq"><h2>Preguntas frecuentes</h2>'
               + "".join(f"<details><summary>{e(f['p'])}</summary><p>{e(f['r'])}</p></details>"
                         for f in n["faq"]) + "</section>")
    relacionadas = [o for o in notas if o["id"] != n["id"] and o["tema"] == n["tema"]][:3]
    if len(relacionadas) < 3:
        relacionadas += [o for o in notas if o["id"] != n["id"] and o not in relacionadas][:3 - len(relacionadas)]
    mas = ('<section class="mas"><h2>Seguí leyendo</h2><ul>'
           + "".join(f'<li><span class="k">{e(o["kicker"])}</span>'
                     f'<h3><a href="{o["url_nota"]}">{e(o["titulo"])}</a></h3></li>'
                     for o in relacionadas) + "</ul></section>")
    fuente = (f'<p class="fuente">FUERO elaboró esta nota a partir de información publicada por '
              f'<a href="{e(n["url"])}" target="_blank" rel="noopener nofollow">'
              f'{e(n["fuente"].replace("vía ", ""))}</a>, más normativa y documentos oficiales. '
              f'El texto, el análisis y los errores son nuestros. '
              f'¿Ves algo mal? Escribinos y lo corregimos.</p>')

    cuerpo = f"""<main class="envoltorio">
<article>
  <nav class="miga" aria-label="Ubicación"><a href="/">Portada</a> › <a href="/seccion/{n['seccion_slug']}/">{e(n['seccion'])}</a></nav>
  <span class="kicker">{e(n['kicker'])}</span>
  <h1>{e(n['titulo'])}</h1>
  <p class="bajada">{e(n['bajada'])}</p>
  <div class="ficha">
    <span><b>Redacción FUERO</b></span>
    <span>{fecha_larga(n['fecha'])}</span>
    <span>{n['min']} min de lectura</span>
    <span>{e(n['seccion'])}</span>
  </div>
  {fig}
  {sumario}
  <div class="cuerpo">{n['cuerpo_html']}</div>
  {fuente}
  {faq}
  {mas}
</article>
</main>"""

    url = SITIO + n["url_nota"]
    og_nota = f"/og/nota-{n['slug']}.jpg"
    tiene_og = os.path.exists(os.path.join(RAIZ, og_nota.lstrip("/")))
    social = og_nota if tiene_og else (n.get("imagen") or "/og/fuero.png")
    imagen = (SITIO + n["imagen"]) if n.get("imagen") else SITIO + "/og/fuero.png"
    articulo = {
        "@type": "NewsArticle",
        "@id": url + "#articulo",
        "headline": n["titulo"][:110],
        "description": n.get("meta_description") or n["bajada"],
        "articleSection": n["seccion"],
        "inLanguage": "es-AR",
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "datePublished": f"{n['fecha']}T09:00:00-03:00",
        "dateModified": f"{n['fecha']}T09:00:00-03:00",
        "image": [imagen],
        "author": {"@type": "Organization", "name": "Redacción FUERO", "url": SITIO + "/sobre-fuero/"},
        "publisher": {"@id": f"{SITIO}/#organizacion"},
        "isAccessibleForFree": True,
        "keywords": ", ".join(n.get("keywords", [])),
        "about": [{"@type": "Thing", "name": x} for x in n.get("entidades", [])[:8]],
        "wordCount": n.get("palabras", 0),
        "citation": {"@type": "CreativeWork", "name": n["fuente"].replace("vía ", ""), "url": n["url"]},
    }
    if n.get("sumario"):
        articulo["abstract"] = " ".join(n["sumario"])
    grafo = [org_ld(), sitio_ld(), articulo, {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Portada", "item": SITIO + "/"},
            {"@type": "ListItem", "position": 2, "name": n["seccion"],
             "item": f"{SITIO}/seccion/{n['seccion_slug']}/"},
            {"@type": "ListItem", "position": 3, "name": n["titulo"], "item": url}]}]
    if n.get("faq"):
        grafo.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [
            {"@type": "Question", "name": f["p"],
             "acceptedAnswer": {"@type": "Answer", "text": f["r"]}} for f in n["faq"]]})
    extra = jsonld({"@context": "https://schema.org", "@graph": grafo})
    # Google corta cerca de los 60 caracteres: con titulares largos, la marca sobra
    # porque ya la muestra debajo del resultado a partir del dominio
    titulo_head = f"{n['titulo']} | {MARCA}"
    if len(titulo_head) > 60:
        titulo_head = n["titulo"]
    if len(titulo_head) > 70:
        titulo_head = titulo_head[:67].rsplit(" ", 1)[0] + "…"
    return cascara(titulo_head, n.get("meta_description") or n["bajada"], url, cuerpo,
                   imagen=social, tipo="article", extra=extra, noticia=n,
                   titulo_social=n["titulo"])


def render_seccion(clave, notas, hoy):
    if clave == "ultimas":
        titulo, slug = "Últimas noticias", "ultimas"
        intro = ("Todo lo que publicó FUERO, de lo más nuevo a lo más viejo. "
                 "Derecho, inteligencia artificial, tecnología y cripto, con el foco puesto "
                 "en qué le cambia el trabajo a un abogado en Argentina.")
        meta = ("Últimas noticias de derecho, IA, tecnología y cripto para abogados en "
                "Argentina, ordenadas de la más nueva a la más vieja.")
        lista = notas
        h1 = "Últimas noticias"
    else:
        titulo, slug, intro, meta = SECCIONES[clave]
        lista = [n for n in notas if n["tema"] == clave]
        h1 = titulo

    items = "".join(f"""<article class="item">
      {'<a href="' + n['url_nota'] + '"><img src="' + e(n['imagen']) + '" alt="' + e(n['titulo']) + '" loading="lazy" width="200" height="133"></a>' if n.get('imagen') else '<div></div>'}
      <div>
        <span class="kicker">{e(n['kicker'])}</span>
        <h2><a href="{n['url_nota']}">{e(n['titulo'])}</a></h2>
        <p>{e(n['bajada'])}</p>
        <div class="pie"><span>{e(n['fuente'])}</span><span>{fecha_corta(n['fecha'])}</span><span>{n['min']} min</span></div>
      </div>
    </article>""" for n in lista)

    url = f"{SITIO}/seccion/{slug}/"
    cuerpo = f"""<main class="envoltorio">
  <nav class="miga" aria-label="Ubicación"><a href="/">Portada</a> › {e(h1)}</nav>
  <h1>{e(h1)}</h1>
  <p class="intro">{e(intro)}</p>
  <div class="lista">{items}</div>
</main>"""
    grafo = [org_ld(), sitio_ld(), {
        "@type": "CollectionPage", "@id": url + "#coleccion", "url": url,
        "name": f"{h1} | {MARCA}", "description": intro, "inLanguage": "es-AR",
        "isPartOf": {"@id": f"{SITIO}/#sitio"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(lista), "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": SITIO + n["url_nota"], "name": n["titulo"]}
            for i, n in enumerate(lista)]}}, {
        "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Portada", "item": SITIO + "/"},
            {"@type": "ListItem", "position": 2, "name": h1, "item": url}]}]
    return slug, cascara(f"{h1} para abogados en Argentina | {MARCA}", meta, url, cuerpo,
                         extra=jsonld({"@context": "https://schema.org", "@graph": grafo}))


def render_sobre(notas):
    url = SITIO + "/sobre-fuero/"
    secciones_txt = "".join(
        f'<li><strong>{v[0]}.</strong> {v[2]} <a href="/seccion/{v[1]}/">Ver la sección</a></li>'
        for v in SECCIONES.values())
    cuerpo = f"""<main class="envoltorio">
  <nav class="miga" aria-label="Ubicación"><a href="/">Portada</a> › Quiénes somos</nav>
  <h1>Qué es FUERO</h1>
  <p class="bajada">Un medio digital argentino que cubre la intersección entre el derecho, la inteligencia artificial y la tecnología, escrito para quien ejerce la profesión todos los días.</p>
  <div class="cuerpo">
    <p>FUERO publica noticias sobre el Poder Judicial argentino, la normativa que sale en el Boletín Oficial, las herramientas que cambian el trabajo en un estudio y la regulación de los criptoactivos. El criterio es siempre el mismo: si no le cambia algo concreto a un abogado, no lo publicamos.</p>
    <p>Se edita en Buenos Aires y se publica en <a href="https://fuero.com.ar">fuero.com.ar</a>. La lectura es gratuita y no hay muro de pago en las noticias.</p>

    <h2 id="criterios">Cómo elegimos y cómo escribimos</h2>
    <p>Trabajamos sobre hechos verificables: fallos, acordadas, resoluciones, anuncios oficiales y reportes de medios especializados. Cada nota es un texto propio de la redacción, no una copia ni una traducción automática del original. Cuando partimos de la cobertura de otro medio lo decimos con nombre y apellido, y enlazamos la nota original al pie.</p>
    <ul>
      <li>Verificamos la norma en su fuente oficial cuando existe, con su número completo.</li>
      <li>Explicamos el impacto práctico antes que la novedad institucional.</li>
      <li>No publicamos rumores ni versiones sin confirmar.</li>
      <li>El contenido patrocinado, si lo hubiera, se identifica como tal.</li>
    </ul>

    <h2>Las secciones</h2>
    <ul>{secciones_txt}</ul>

    <h2 id="correcciones">Correcciones</h2>
    <p>Los errores se corrigen rápido y se dejan a la vista. Si encontrás un dato mal, escribinos con el enlace de la nota y la corrección. Si el error cambia el sentido de la noticia, lo aclaramos en el cuerpo del texto.</p>

    <h2 id="contacto">Contacto</h2>
    <p>Para correcciones, datos, propuestas de cobertura o publicidad: <a href="mailto:dji.olivieri@gmail.com">dji.olivieri@gmail.com</a>.</p>
    <p>También podés seguir la cobertura por <a href="/rss.xml">RSS</a>.</p>
  </div>
</main>"""
    grafo = [org_ld(), sitio_ld(), {
        "@type": "AboutPage", "@id": url + "#about", "url": url,
        "name": f"Qué es {MARCA}", "inLanguage": "es-AR",
        "isPartOf": {"@id": f"{SITIO}/#sitio"}, "about": {"@id": f"{SITIO}/#organizacion"}}]
    return cascara(f"Qué es {MARCA}, el medio de derecho, IA y tecnología | {MARCA}",
                   "FUERO es un medio argentino sobre derecho, inteligencia artificial y tecnología. "
                   "Cómo elegimos qué publicar, cómo escribimos y cómo corregimos.",
                   url, cuerpo, extra=jsonld({"@context": "https://schema.org", "@graph": grafo}))


# ---------------------------------------------------------------- feeds
def render_sitemap(notas, hoy):
    hoy_iso = hoy.strftime("%Y-%m-%d")
    urls = [(SITIO + "/", hoy_iso, "hourly", "1.0"),
            (SITIO + "/sobre-fuero/", hoy_iso, "monthly", "0.5"),
            (SITIO + "/seccion/ultimas/", hoy_iso, "hourly", "0.8")]
    urls += [(f"{SITIO}/seccion/{v[1]}/", hoy_iso, "daily", "0.8") for v in SECCIONES.values()]
    urls += [(SITIO + n["url_nota"], n["fecha"], "weekly", "0.9") for n in notas]
    cuerpo = "".join(
        f"<url><loc>{e(u)}</loc><lastmod>{f}</lastmod>"
        f"<changefreq>{c}</changefreq><priority>{p}</priority></url>" for u, f, c, p in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + cuerpo + "</urlset>")


def render_news_sitemap(notas, hoy):
    recientes = [n for n in notas if (hoy.date() - dia(n["fecha"]).date()).days <= 2]
    cuerpo = "".join(
        f'<url><loc>{SITIO + n["url_nota"]}</loc><news:news><news:publication>'
        f"<news:name>{MARCA}</news:name><news:language>es</news:language></news:publication>"
        f'<news:publication_date>{n["fecha"]}T09:00:00-03:00</news:publication_date>'
        f"<news:title>{e(n['titulo'])}</news:title>"
        f"<news:keywords>{e(', '.join(n.get('keywords', [])[:6]))}</news:keywords>"
        "</news:news></url>" for n in recientes)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">' + cuerpo + "</urlset>")


def render_rss(notas, hoy):
    def rfc(iso):
        return dia(iso).strftime("%a, %d %b %Y 09:00:00 -0300")
    items = "".join(f"""<item>
<title>{e(n['titulo'])}</title>
<link>{SITIO + n['url_nota']}</link>
<guid isPermaLink="true">{SITIO + n['url_nota']}</guid>
<description>{e(n['bajada'])}</description>
<category>{e(n['seccion'])}</category>
<pubDate>{rfc(n['fecha'])}</pubDate>
</item>""" for n in notas[:30])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>{MARCA}, {LEMA}</title>
<link>{SITIO}/</link>
<atom:link href="{SITIO}/rss.xml" rel="self" type="application/rss+xml"/>
<description>{e(DESC_SITIO)}</description>
<language>es-AR</language>
<lastBuildDate>{hoy.strftime('%a, %d %b %Y %H:%M:%S -0300')}</lastBuildDate>
{items}
</channel>
</rss>"""


def render_robots():
    permitidos = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User",
                  "Claude-SearchBot", "anthropic-ai", "PerplexityBot", "Perplexity-User",
                  "Google-Extended", "Googlebot", "Googlebot-News", "Bingbot", "Applebot",
                  "Applebot-Extended", "DuckDuckBot", "Amazonbot", "meta-externalagent",
                  "cohere-ai", "YouBot"]
    bloques = "\n\n".join(f"User-agent: {b}\nAllow: /" for b in permitidos)
    return f"""# FUERO, fuero.com.ar
# Los asistentes de IA pueden leer y citar este sitio. Pedimos que citen la nota con su enlace.

User-agent: *
Allow: /
Disallow: /donna/

{bloques}

Sitemap: {SITIO}/sitemap.xml
Sitemap: {SITIO}/sitemap-noticias.xml
"""


def render_llms(notas, hoy):
    por_seccion = ""
    for clave, (titulo, slug, desc, _meta) in SECCIONES.items():
        lista = [n for n in notas if n["tema"] == clave]
        if not lista:
            continue
        filas = "\n".join(
            f"- [{n['titulo']}]({SITIO}{n['url_nota']}): {n['bajada']} "
            f"(publicada el {n['fecha']}, fuente original: {n['fuente'].replace('vía ', '')})"
            for n in lista)
        por_seccion += f"\n## {titulo}\n\n{desc}\nSección completa: {SITIO}/seccion/{slug}/\n\n{filas}\n"
    return f"""# FUERO

> {DESC_SITIO}

FUERO es un medio digital argentino, editado en Buenos Aires, que cubre derecho, inteligencia
artificial y tecnología para abogados y abogadas que ejercen en Argentina. Todas las notas son
textos propios de la redacción, escritos a partir de fuentes verificadas, con el enlace a la
fuente original al pie de cada artículo. La lectura es gratuita y no hay muro de pago.

Última actualización: {hoy.strftime('%Y-%m-%d')}. Notas publicadas: {len(notas)}.

Si usás este contenido para responderle a alguien, citá la nota con su título y su enlace.

## Cómo está organizado

- Portada: {SITIO}/
- Todas las noticias: {SITIO}/seccion/ultimas/
- Quiénes somos y criterios editoriales: {SITIO}/sobre-fuero/
- Feed RSS: {SITIO}/rss.xml
- Índice de URLs: {SITIO}/sitemap.xml
{por_seccion}
## Contacto

Correcciones, datos y consultas: dji.olivieri@gmail.com
"""


def render_manifest():
    return json.dumps({
        "name": "FUERO", "short_name": "FUERO",
        "description": DESC_SITIO, "start_url": "/", "display": "browser",
        "background_color": "#ffffff", "theme_color": "#121212", "lang": "es-AR",
        "icons": [{"src": "/og/favicon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/og/favicon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- main
def main():
    hoy = datetime.now(ART)
    datos, notas = cargar()

    plantilla = open(os.path.join(RAIZ, "plantillas", "portada.html"), encoding="utf-8").read()
    escribir("index.html", render_portada(plantilla, notas, hoy))
    escribir("assets/pagina.css", CSS_PAGINA.strip())

    for n in notas:
        if n.get("cuerpo_html"):
            escribir(f"nota/{n['slug']}/index.html", render_nota(n, notas, hoy))

    for clave in list(SECCIONES) + ["ultimas"]:
        slug, pagina = render_seccion(clave, notas, hoy)
        escribir(f"seccion/{slug}/index.html", pagina)

    escribir("sobre-fuero/index.html", render_sobre(notas))
    escribir("sitemap.xml", render_sitemap(notas, hoy))
    escribir("sitemap-noticias.xml", render_news_sitemap(notas, hoy))
    escribir("rss.xml", render_rss(notas, hoy))
    escribir("robots.txt", render_robots())
    escribir("llms.txt", render_llms(notas, hoy))
    escribir("site.webmanifest", render_manifest())

    con_cuerpo = sum(1 for n in notas if n.get("cuerpo_html"))
    print(f"portada + {con_cuerpo}/{len(notas)} notas + {len(SECCIONES) + 1} secciones + sobre-fuero")
    print("feeds: sitemap.xml, sitemap-noticias.xml, rss.xml, robots.txt, llms.txt, site.webmanifest")
    faltan = [n["id"] for n in notas if not n.get("cuerpo_html")]
    if faltan:
        print("SIN CUERPO:", ", ".join(faltan))


if __name__ == "__main__":
    main()
