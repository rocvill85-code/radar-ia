#!/usr/bin/env python3
"""
Radar IA · 9dieciséis — generador semanal de la revista.

Flujo (2 pasos, robusto):
  1. INVESTIGAR: Claude busca en la web las noticias reales de la semana.
  2. FORMATEAR: Claude convierte esas notas a un JSON garantizado (structured
     outputs) que se renderiza dentro de index.html entre marcadores.

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
SEC_META = {s[0]: s for s in SECTIONS}

MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

RADAR_BADGE = ('<span class="badge916"><svg viewBox="0 0 24 24" fill="none" '
               'stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/>'
               '<circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" '
               'fill="currentColor" stroke="none"/></svg>Prioridad 916</span>')

WHY_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
            '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/></svg>')

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["articles"],
    "properties": {
        "articles": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["section", "cat_label", "title", "standfirst", "body",
                         "sources", "when", "p916", "why916", "lead"],
            "properties": {
                "section": {"type": "string", "enum": ["av", "vert", "mkt", "pm"]},
                "cat_label": {"type": "string"},
                "title": {"type": "string"},
                "standfirst": {"type": "string"},
                "body": {"type": "array", "items": {"type": "string"}},
                "sources": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["label", "url"],
                    "properties": {"label": {"type": "string"}, "url": {"type": "string"}}}},
                "when": {"type": "string"},
                "p916": {"type": "boolean"},
                "why916": {"type": "string"},
                "lead": {"type": "boolean"},
            },
        }},
    },
}


# --------------------------------------------------------------------------- #
def _run(client, *, max_tokens, effort, messages, tools=None, output_format=None):
    """Ejecuta una conversación (con streaming) y reanuda pause_turn de la búsqueda."""
    oc = {"effort": effort}
    if output_format:
        oc["format"] = output_format
    kwargs = dict(model=MODEL, max_tokens=max_tokens, output_config=oc, messages=messages)
    if tools:
        kwargs["tools"] = tools
    final = None
    for _ in range(6):
        with client.messages.stream(**kwargs) as stream:
            final = stream.get_final_message()
        if final.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": final.content})
            continue
        break
    text = "".join(b.text for b in final.content if getattr(b, "type", None) == "text").strip()
    return text, final.stop_reason


def fetch_edition(date_label):
    import anthropic
    client = anthropic.Anthropic()

    # -- Paso 1: investigar --------------------------------------------------
    research_prompt = f"""Hoy es {date_label}. Busca en la web las noticias MÁS relevantes y recientes (esta semana o últimos días) sobre inteligencia artificial en estos campos, priorizando fuentes en español:
- Audiovisual y vídeo generativo (Runway, Veo, Kling, Sora, Adobe Firefly, herramientas de post).
- Vídeo vertical 9:16 y creadores (TikTok, Reels, Shorts, CapCut, OpusClip).
- Marketing, estrategia y publicidad con IA, y regulación europea (AI Act, transparencia).
- Project management con IA (Motion, Asana, ClickUp, Monday, PMI).

Escribe en ESPAÑOL entre 6 y 9 fichas breves. Por cada una: [sección: audiovisual / vertical / marketing / pm], un titular, 2-3 frases de resumen, y 1-2 fuentes reales con su URL. Señala cuáles tienen impacto directo para una productora de vídeo vertical en Barcelona (9dieciséis)."""

    research, sr = _run(
        client, max_tokens=8000, effort="low",
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": research_prompt}])
    print(f"[paso 1] investigación: {len(research)} chars · stop={sr}")
    if not research:
        raise SystemExit(f"Paso 1 sin texto (stop_reason={sr}).")

    # -- Paso 2: formatear a JSON -------------------------------------------
    format_prompt = f"""A partir de estas notas de investigación, redacta la edición de la revista "Radar IA · 9dieciséis" y devuélvela en el formato JSON indicado.

NOTAS:
{research}

Requisitos:
- Entre 6 y 9 noticias. Reparte por sección con estos códigos exactos: av (audiovisual), vert (vídeo 9:16), mkt (marketing/estrategia/regulación), pm (project management).
- Redacta en español, tono editorial claro y útil. 'body' = 1 o 2 párrafos (cadenas; pueden llevar <b>…</b>).
- 'lead' = true en UNA sola noticia (la más importante). En el resto, false.
- 'p916' = true SOLO en 2 o 3 noticias con impacto directo para una productora de vídeo vertical en Barcelona; en esas rellena 'why916' (1-2 frases: qué significa para 9dieciséis). En las demás, 'why916' = "".
- 'when' = fecha corta, p.ej. "12 AGO 2026" o "2026".
- 'sources' = 1 o 2 fuentes reales con su URL por noticia."""

    text, sr = _run(
        client, max_tokens=16000, effort="low",
        output_format={"type": "json_schema", "schema": SCHEMA},
        messages=[{"role": "user", "content": format_prompt}])
    print(f"[paso 2] json: {len(text)} chars · stop={sr}")
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    if not text:
        raise SystemExit(f"Paso 2 sin texto (stop_reason={sr}).")
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
         "when": "2026", "p916": False, "why916": "", "lead": False},
        {"section": "vert", "cat_label": "Creadores", "title": "Vertical de prueba",
         "standfirst": "Tercera entradilla.", "body": ["Texto."],
         "sources": [{"label": "Medio", "url": "https://example.net"}],
         "when": "2026", "p916": True, "why916": "Relevante 916 (mock).", "lead": False},
        {"section": "pm", "cat_label": "Gestión", "title": "PM de prueba",
         "standfirst": "Cuarta entradilla.", "body": ["Texto."],
         "sources": [{"label": "Medio", "url": "https://example.com/pm"}],
         "when": "2026", "p916": False, "why916": "", "lead": False},
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
    out.append(f'<span class="when">{html.escape(str(art.get("when", "")))}</span>')
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

    articles = mock_edition() if os.environ.get("RADAR_MOCK") == "1" else fetch_edition(date_label)

    edition_html = f"Edición {edition_number:02d} · <b>{date_label}</b>"
    page = re.sub(r"<!--EDITION_START-->.*?<!--EDITION_END-->",
                  f"<!--EDITION_START-->{edition_html}<!--EDITION_END-->",
                  page, count=1, flags=re.S)

    page = re.sub(r"<!--FEED_START-->.*?<!--FEED_END-->",
                  "<!--FEED_START-->" + render_feed(articles) + "<!--FEED_END-->",
                  page, count=1, flags=re.S)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"OK · edición {edition_number:02d} · {date_label} · {len(articles)} noticias")


if __name__ == "__main__":
    main()
