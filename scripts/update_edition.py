#!/usr/bin/env python3
"""
Radar IA · 9dieciséis — generador semanal de la revista.

Cada semana:
  1. Busca noticias reales de IA (audiovisual, marketing/estrategia, project
     management) con la herramienta de búsqueda web de Claude.
  2. Las redacta en español y marca las relevantes para 9dieciséis.
  3. Reescribe SOLO el bloque de noticias y la fecha de index.html (entre los
     marcadores <!--FEED_START-->/<!--FEED_END--> y <!--EDITION_START-->/…END).

Uso:
  ANTHROPIC_API_KEY=... python scripts/update_edition.py
  RADAR_MOCK=1 python scripts/update_edition.py       # prueba sin API (datos falsos)
  RADAR_TARGET=/ruta/index.html                        # fichero destino (por defecto index.html)
"""
import os
import re
import json
import html
import datetime

TARGET = os.environ.get("RADAR_TARGET", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html"))
MODEL = os.environ.get("RADAR_MODEL", "claude-opus-5")

SECTIONS = [
    ("av",   "Audiovisual",   "Vídeo generativo · herramientas de producción", "var(--c-av)"),
    ("vert", "Vídeo 9:16",    "El formato vertical · vuestro terreno",          "var(--c-vert)"),
    ("mkt",  "Marketing",     "Estrategia · publicidad · IA aplicada",          "var(--c-mkt)"),
    ("pm",   "Project Mgmt",  "Gestión de proyectos con IA",                    "var(--c-pm)"),
]
SEC_ORDER = [s[0] for s in SECTIONS]
SEC_META = {s[0]: s for s in SECTIONS}

MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

RADAR_BADGE = ('<span class="badge916"><svg viewBox="0 0 24 24" fill="none" '
               'stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/>'
               '<circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" '
               'fill="currentColor" stroke="none"/></svg>Prioridad 916</span>')

WHY_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
            '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/></svg>')


# --------------------------------------------------------------------------- #
#  Búsqueda + redacción con Claude
# --------------------------------------------------------------------------- #
def fetch_edition(date_label, edition_number):
    import anthropic
    client = anthropic.Anthropic()

    schema_hint = json.dumps({
        "articles": [{
            "section": "av | vert | mkt | pm",
            "cat_label": "kicker corto, p.ej. 'Vídeo generativo'",
            "title": "titular",
            "standfirst": "entradilla de 1-2 frases",
            "body": ["párrafo 1 (puede llevar <b>)", "párrafo 2"],
            "sources": [{"label": "Medio", "url": "https://..."}],
            "when": "12 AGO 2026",
            "p916": False,
            "why916": "solo si p916=true: qué significa para 9dieciséis",
            "lead": False,
        }],
    }, ensure_ascii=False, indent=2)

    prompt = f"""Eres el redactor de "Radar IA · 9dieciséis", una revista-briefing semanal.
Hoy es {date_label}. Busca en la web las noticias MÁS relevantes y RECIENTES (de esta semana o los últimos días) sobre inteligencia artificial aplicada a estos tres campos, priorizando fuentes en español:

- AUDIOVISUAL: vídeo generativo (Runway, Veo, Kling, Sora, Adobe Firefly…), herramientas de producción y post.
- MARKETING y ESTRATEGIA: publicidad con IA, agentes, regulación europea (AI Act), transparencia de marca.
- PROJECT MANAGEMENT: IA en gestión de proyectos (Motion, Asana, ClickUp, Monday, PMI…).
- Además, VÍDEO VERTICAL 9:16 y creadores (TikTok, Reels, Shorts, CapCut, OpusClip): esto es la especialidad de la productora 9dieciséis.

Selecciona entre 6 y 9 noticias. Redáctalas en ESPAÑOL, tono editorial, claro y útil. Reparte por sección con estos códigos: av (audiovisual), vert (vídeo 9:16), mkt (marketing), pm (project management).

Marca p916=true (2 o 3 como mucho) SOLO en las noticias con impacto directo para una productora de vídeo vertical en Barcelona; en esas incluye 'why916' (1-2 frases: qué significa para 9dieciséis). Marca lead=true en UNA sola noticia, la más importante (idealmente una p916).

Incluye 1-2 fuentes reales (con URL) por noticia. 'when' es una fecha corta tipo "12 AGO 2026" o "2026".

Devuelve EXCLUSIVAMENTE un objeto JSON válido con esta forma (sin texto alrededor, sin ```):
{schema_hint}
"""

    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]
    messages = [{"role": "user", "content": prompt}]

    final = None
    for _ in range(6):  # reanuda pause_turn de la búsqueda server-side
        with client.messages.stream(
            model=MODEL,
            max_tokens=32000,
            output_config={"effort": "high"},
            tools=tools,
            messages=messages,
        ) as stream:
            final = stream.get_final_message()
        if final.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": final.content})
            continue
        break

    text = "".join(b.text for b in final.content if getattr(b, "type", None) == "text").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    data = json.loads(text)
    articles = data["articles"] if isinstance(data, dict) else data
    if not articles:
        raise SystemExit("El modelo no devolvió noticias.")
    return articles


def mock_edition():
    return [
        {"section": "mkt", "cat_label": "Regulación", "title": "Titular de prueba (mock)",
         "standfirst": "Entradilla de ejemplo para validar el renderizado.",
         "body": ["Primer párrafo de <b>prueba</b>.", "Segundo párrafo."],
         "sources": [{"label": "Fuente", "url": "https://example.com"}],
         "when": "12 AGO 2026", "p916": True,
         "why916": "Qué significa para 9dieciséis (mock).", "lead": True},
        {"section": "av", "cat_label": "Vídeo generativo", "title": "Otra noticia de prueba",
         "standfirst": "Segunda entradilla.",
         "body": ["Cuerpo de la segunda noticia."],
         "sources": [{"label": "Medio", "url": "https://example.org"}],
         "when": "2026", "p916": False, "why916": None, "lead": False},
        {"section": "vert", "cat_label": "Creadores", "title": "Vertical de prueba",
         "standfirst": "Tercera entradilla.", "body": ["Texto."],
         "sources": [{"label": "Medio", "url": "https://example.net"}],
         "when": "2026", "p916": True, "why916": "Relevante 916 (mock).", "lead": False},
        {"section": "pm", "cat_label": "Gestión", "title": "PM de prueba",
         "standfirst": "Cuarta entradilla.", "body": ["Texto."],
         "sources": [{"label": "Medio", "url": "https://example.com/pm"}],
         "when": "2026", "p916": False, "why916": None, "lead": False},
    ]


# --------------------------------------------------------------------------- #
#  Renderizado a HTML (clases idénticas a la edición 01)
# --------------------------------------------------------------------------- #
def _sources_html(art):
    out = []
    for s in art.get("sources", []):
        label = html.escape(str(s.get("label", "Fuente")))
        url = html.escape(str(s.get("url", "#")), quote=True)
        out.append(f'<a class="src" href="{url}" target="_blank" rel="noopener">{label}</a>')
    when = html.escape(str(art.get("when", "")))
    out.append(f'<span class="when">{when}</span>')
    return "".join(out)


def _body_html(art):
    return "".join(f'<p class="txt">{p}</p>' for p in art.get("body", []))


def _why_html(art):
    if not art.get("p916"):
        return ""
    why = art.get("why916") or ""
    return (f'<div class="why916"><div class="h">{WHY_ICON}Qué significa para '
            f'9dieciséis</div><p>{why}</p></div>')


def render_lead(art):
    art_svg = (
        '<svg viewBox="0 0 400 180" preserveAspectRatio="xMidYMid slice">'
        '<g fill="none" stroke="rgba(255,255,255,.18)" stroke-width="1">'
        '<circle cx="320" cy="60" r="30"/><circle cx="320" cy="60" r="55"/>'
        '<circle cx="320" cy="60" r="82"/></g>'
        '<circle cx="320" cy="60" r="5" fill="#DB2251"/>'
        '<g font-family="ui-monospace,monospace" fill="rgba(255,255,255,.9)" font-size="13">'
        '<rect x="24" y="34" width="180" height="26" rx="5" fill="rgba(219,34,81,.9)"/>'
        '<text x="34" y="51" fill="#fff" font-weight="700">RADAR 916 · DESTACADO</text></g>'
        '<g fill="rgba(255,255,255,.14)"><rect x="26" y="100" width="26" height="58" rx="3"/>'
        '<rect x="58" y="112" width="26" height="46" rx="3"/>'
        '<rect x="90" y="92" width="26" height="66" rx="3"/></g></svg>')
    sec = art.get("section", "mkt")
    p916 = 1 if art.get("p916") else 0
    return f'''<article class="lead" data-cat="{sec}" data-p916="{p916}">
      <div class="lead-cover"><div class="art" aria-hidden="true">{art_svg}</div></div>
      <div class="lead-body body">
        {RADAR_BADGE if p916 else ''}
        <p class="kicker" style="margin-top:12px">Portada · {html.escape(str(art.get("cat_label","")))}</p>
        <h3>{art.get("title","")}</h3>
        <p class="standfirst">{art.get("standfirst","")}</p>
        {_body_html(art)}
        {_why_html(art)}
        <div class="meta">{_sources_html(art)}</div>
      </div>
    </article>'''


def render_card(art):
    sec = art.get("section", "mkt")
    color = SEC_META.get(sec, SEC_META["mkt"])[3]
    p916 = art.get("p916")
    cls = "card p916" if p916 else "card"
    head = RADAR_BADGE if p916 else (
        f'<span class="cat"><span class="d" style="background:{color}"></span>'
        f'{html.escape(str(art.get("cat_label","")))}</span>')
    return f'''<article class="{cls}" data-cat="{sec}" data-p916="{1 if p916 else 0}">
        <div class="head">{head}</div>
        <h4>{art.get("title","")}</h4>
        <p class="sf">{art.get("standfirst","")}</p>
        {_body_html(art)}
        {_why_html(art)}
        <div class="meta">{_sources_html(art)}</div>
      </article>'''


def render_feed(articles):
    parts = ["\n"]
    lead = next((a for a in articles if a.get("lead")), None)
    if lead:
        parts.append("    <!-- LEAD -->\n    " + render_lead(lead) + "\n\n")
    for sec, name, sub, color in SECTIONS:
        cards = [a for a in articles if a.get("section") == sec and a is not lead]
        if not cards:
            continue
        parts.append(
            f'    <div class="sec-head" data-sec><span class="tag" style="background:{color}"></span>'
            f'<h2>{name}</h2><span class="rule"></span></div>\n'
            f'    <p class="sec-sub">{sub}</p>\n'
            f'    <div class="grid">\n')
        for c in cards:
            parts.append("      " + render_card(c) + "\n\n")
        parts.append("    </div>\n\n")
    parts.append('    <p class="empty" id="empty">— Sin noticias en este filtro —</p>\n\n    ')
    return "".join(parts)


# --------------------------------------------------------------------------- #
def main():
    with open(TARGET, encoding="utf-8") as f:
        page = f.read()

    m = re.search(r"Edici[oó]n\s+(\d+)", page)
    edition_number = (int(m.group(1)) + 1) if m else 2

    today = datetime.datetime.utcnow().date()
    date_label = f"{today.day:02d} {MESES[today.month-1]} {today.year}"

    if os.environ.get("RADAR_MOCK") == "1":
        articles = mock_edition()
    else:
        articles = fetch_edition(date_label, edition_number)

    edition_html = f"Edición {edition_number:02d} · <b>{date_label}</b>"
    page = re.sub(r"<!--EDITION_START-->.*?<!--EDITION_END-->",
                  f"<!--EDITION_START-->{edition_html}<!--EDITION_END-->",
                  page, count=1, flags=re.S)

    feed_html = render_feed(articles)
    page = re.sub(r"<!--FEED_START-->.*?<!--FEED_END-->",
                  "<!--FEED_START-->" + feed_html + "<!--FEED_END-->",
                  page, count=1, flags=re.S)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"OK · edición {edition_number:02d} · {date_label} · {len(articles)} noticias")


if __name__ == "__main__":
    main()
