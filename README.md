# FUERO

Portal de noticias de derecho, inteligencia artificial y tecnología para abogados en
Argentina. Publicado en https://fuero.com.ar sobre Vercel (proyecto `fuero`).

El sitio es estático: no hay servidor ni base de datos. Un generador en Python arma
todo el HTML a partir de dos fuentes de datos, y Vercel sirve los archivos.

## Cómo está organizado

```
noticias.json        metadatos de cada nota (fuente, fecha, tema, imagen, slug)
cuerpos/*.json       el artículo reescrito: título, sumario, cuerpo, FAQ, keywords
img/                 fotos de las notas, ya comprimidas
og/                  imagen social por nota y favicons
plantillas/          la portada, con marcadores <!--FUERO:x--> que rellena el build
scripts/             build.py, og.py, bajar-imagenes.py, indexnow.py
assets/pagina.css    estilos de notas, secciones y quiénes somos
donna/               el sitio anterior, fuera del índice
```

Lo que genera el build y no conviene editar a mano: `index.html`, `nota/`, `seccion/`,
`sobre-fuero/`, `sitemap.xml`, `sitemap-noticias.xml`, `rss.xml`, `robots.txt`,
`llms.txt`, `site.webmanifest`.

## Publicar una nota nueva

1. Agregar el objeto en `noticias.json`. Campos mínimos:

```json
{
  "id": "identificador-unico",
  "titulo": "...", "bajada": "...",
  "url": "https://medio.com/la-nota-original",
  "fuente": "vía Diario Judicial",
  "fecha": "2026-09-18",
  "tema": "derecho",
  "kicker": "Fallos",
  "imagen_origen": "https://medio.com/foto.jpg",
  "credito_imagen": "Diario Judicial"
}
```

`tema` es uno de `derecho`, `ia`, `tech`, `cripto`. Para que aparezca en la apertura
de la portada se agrega `"destacada": true`, y para la columna del medio `"portada": true`.

2. Escribir el artículo propio en el archivo de su sección dentro de `cuerpos/`, con
   `id`, `titulo`, `bajada`, `meta_description`, `sumario` (3 bullets), `cuerpo_html`,
   `faq` (3 preguntas), `entidades`, `keywords` y `palabras`.

3. Correr:

```bash
python3 scripts/bajar-imagenes.py && python3 scripts/build.py && python3 scripts/og.py
```

4. Publicar y avisar a los buscadores:

```bash
git add -A && git commit -m "Nota: ..." && git push && vercel --prod --yes && python3 scripts/indexnow.py
```

## Reglas de escritura

- Nunca se usa la raya larga. Punto, coma o dos puntos.
- El artículo es propio: no se copia ni se traduce el original. La fuente se cita en el
  texto y se enlaza al pie, en la caja que arma el build.
- Cada dato que no se pudo verificar en su fuente oficial no se publica.
- Las normas se nombran completas (ley 27.423, Comunicación A 8471) porque son el ancla
  que usan los buscadores y los asistentes de IA.

## Verificar antes de publicar

```bash
python3 -m http.server 3017   # y abrir http://localhost:3017
```

Lighthouse en móvil tiene que dar 100 en SEO y en Agentic Browsing, tanto en la portada
como en una nota.

## Pendientes

- Dar de alta el sitio en Google Search Console y subir el sitemap. Requiere la cuenta
  de Google del dueño del dominio.
- El boletín se pide por correo, todavía no hay lista automatizada.
- Las secciones de datos judiciales y de inversión se quitaron porque tenían cifras de
  muestra. Vuelven cuando haya una fuente real.
