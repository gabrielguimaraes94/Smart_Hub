"""Shared UI building blocks for the Smart Hub pages (layout only, no data logic)."""
from datetime import datetime
from html import escape

import streamlit as st

FOOTER_TEXT = "Gestamp NAFTA – GC2"
PRIMARY = "#20416C"  # keep in sync with primaryColor in .streamlit/config.toml

_BASE_CSS = f"""
<style>
/* ---- Hero banner (Home) ---- */
.hub-hero {{
    background: linear-gradient(120deg, {PRIMARY} 0%, #2E5C96 100%);
    color: #FFFFFF;
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 8px;
    box-shadow: 0 6px 20px rgba(32, 65, 108, 0.18);
}}
.hub-hero .eyebrow {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    opacity: 0.75;
    margin-bottom: 6px;
}}
.hub-hero .title {{
    font-size: 1.75rem;
    font-weight: 650;
    line-height: 1.2;
    margin: 0;
}}
.hub-hero .subtitle {{
    font-size: 0.95rem;
    opacity: 0.85;
    margin-top: 6px;
}}

/* ---- Section label ---- */
.hub-section {{
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #5B6776;
    margin: 18px 0 2px 0;
}}

/* ---- Navigation cards: st.container(border=True, key="card_...") ---- */
div[class*="st-key-card_"] {{
    position: relative;
    background: #FFFFFF;
    min-height: 160px;
    transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}}
div[class*="st-key-card_"]:hover {{
    box-shadow: 0 10px 24px rgba(31, 41, 51, 0.12);
    transform: translateY(-2px);
    border-color: {PRIMARY};
}}
div[class*="st-key-card_"] a,
div[class*="st-key-card_"] a p,
div[class*="st-key-card_"] a span {{
    font-size: 1.05rem;
    font-weight: 600;
    color: {PRIMARY};
}}
/* stretch the page link over the whole card so any click opens the page */
div[class*="st-key-card_"] a::after {{
    content: "";
    position: absolute;
    inset: 0;
}}
/* ---- Storage slots (e.g. coil rails): rail_title / slot_card / legend ---- */
.rail-title {{
    text-align: center;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 2px 0 6px 0;
    margin-bottom: 8px;
    border-bottom: 2px solid {PRIMARY};
}}
.slot {{
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
    min-height: 112px;   /* same height for every slot so rails line up as rows */
    box-sizing: border-box;
    transition: opacity .2s ease, box-shadow .2s ease;
    font-size: 0.78rem;
    line-height: 1.4;
}}
.slot.occupied {{
    background: #FFFFFF;
    border: 1px solid #D9DEE5;
    border-left: 4px solid #2E7D4F;
}}
.slot.empty {{
    background: #F1F3F5;
    border: 1px dashed #C5CCD5;
    color: #8A94A3;
}}
.slot.match {{
    background: #EAF1FB;
    border-color: {PRIMARY};
    box-shadow: 0 0 0 3px rgba(32, 65, 108, 0.35);
}}
.slot.dim {{ opacity: 0.35; }}
.slot .pos {{ font-weight: 650; font-size: 0.85rem; }}
.slot .line {{ color: #5B6776; overflow-wrap: anywhere; }}
.slot .line:first-of-type {{ color: #1F2933; font-weight: 600; }}
.legend {{ display: flex; gap: 18px; font-size: 0.82rem; color: #5B6776; margin: 4px 0 10px 0; }}
.legend .swatch {{ display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }}

.hub-badge {{
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: #8A5A00;
    background: #FFF1D6;
    border-radius: 999px;
    padding: 1px 8px;
    margin-left: 6px;
    vertical-align: middle;
}}
</style>
"""


def apply_base_style():
    """Inject the shared CSS. Called once per run from the entry point."""
    st.html(_BASE_CSS)


def hero(titulo, subtitulo=None, eyebrow=FOOTER_TEXT):
    """Large branded banner, used on the Home page."""
    sub = f'<div class="subtitle">{escape(subtitulo)}</div>' if subtitulo else ""
    st.html(
        f'<div class="hub-hero"><div class="eyebrow">{escape(eyebrow)}</div>'
        f'<p class="title">{escape(titulo)}</p>{sub}</div>'
    )


def section_label(texto):
    """Small uppercase label that groups content (e.g. the Home card sections)."""
    st.html(f'<div class="hub-section">{escape(texto)}</div>')


def nav_card(key, page, titulo, descricao, icon, badge=None):
    """Clickable card that opens a page registered in st.navigation."""
    with st.container(border=True, key=f"card_{key}"):
        st.page_link(page, label=titulo, icon=icon)
        badge_html = f'<span class="hub-badge">{escape(badge)}</span>' if badge else ""
        st.html(f'<div style="color:#5B6776;font-size:0.9rem;line-height:1.4">{escape(descricao)}{badge_html}</div>')


def rail_title(texto):
    """Centered column title with a primary-color underline (storage rails)."""
    st.html(f'<div class="rail-title">{escape(texto)}</div>')


def slot_card(position, occupied, lines=(), highlight=None):
    """Compact storage slot. `lines` is a list of (label, value) shown when occupied.

    Only the values are printed (the first one emphasized); the label is the hover tooltip,
    so narrow columns never truncate the data.
    `highlight`: None (no search active), True (search match) or False (dimmed).
    """
    state = "" if highlight is None else (" match" if highlight else " dim")
    if occupied:
        body = "".join(
            f'<div class="line" title="{escape(k)}: {escape(str(v))}">{escape(str(v))}</div>'
            for k, v in lines
        )
        st.html(f'<div class="slot occupied{state}"><div class="pos">{escape(position)}</div>{body}</div>')
    else:
        st.html(f'<div class="slot empty{state}"><div class="pos">{escape(position)}</div><div>Empty</div></div>')


def legend(items):
    """Inline color legend. `items` is a list of (label, css_background)."""
    spans = "".join(
        f'<span><span class="swatch" style="background:{bg}"></span>{escape(label)}</span>' for label, bg in items
    )
    st.html(f'<div class="legend">{spans}</div>')


def sample_data_notice():
    """Discreet banner shown on every page while USE_SAMPLE_DATA is on."""
    st.html(
        '<div style="display:inline-block;font-size:0.8rem;font-weight:500;color:#8A5A00;'
        'background:#FFF1D6;border:1px solid #F3D9A4;border-radius:999px;padding:3px 12px;margin-bottom:4px">'
        "Sample data mode: all figures are fictitious, not plant data</div>"
    )


def page_header(titulo, subtitulo=None):
    """Standard page title with an optional subtitle line."""
    st.title(titulo)
    if subtitulo:
        st.caption(subtitulo)


def kpi_card(label, value, delta=None, help=None, delta_color="normal"):
    """Standard KPI card: a bordered st.metric."""
    st.metric(label, value, delta=delta, delta_color=delta_color, help=help, border=True)


def footer(atualizado_em=None):
    """Standard footer. `atualizado_em` is the data timestamp (datetime); defaults to now."""
    atualizado_em = atualizado_em or datetime.now()
    st.divider()
    st.caption(f"{FOOTER_TEXT} | updated {atualizado_em:%b %d, %Y %H:%M}")
