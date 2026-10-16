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
