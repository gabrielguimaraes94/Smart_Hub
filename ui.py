"""Shared UI building blocks for the Smart Hub pages (layout only, no data logic)."""
from datetime import datetime
from html import escape

import streamlit as st

FOOTER_TEXT = "Gestamp NAFTA – GC2"
PRIMARY = "#20416C"  # keep in sync with [theme.light] primaryColor in .streamlit/config.toml

# Colors used by the custom HTML/CSS below. Light values are the default; the dark ones apply when
# _THEME_WATCH_JS marks <html data-hub-theme="dark"> (the app background is dark). Keep them in line
# with [theme.light] / [theme.dark] in .streamlit/config.toml.
_TOKENS = {
    "surface": ("#FFFFFF", "#152131"),        # cards, occupied slots, chart plot area
    "text": ("#1F2933", "#E4E9F0"),
    "muted": ("#5B6776", "#9AA7B8"),          # secondary text
    "border": ("#D9DEE5", "#2C3A4D"),
    "accent": (PRIMARY, "#7FA7DB"),           # brand-blue text and lines (readable on both backgrounds)
    "button": (PRIMARY, "#3A6DB0"),           # = primaryColor of each theme
    "ok": ("#2E7D4F", "#3FA36A"),
    "empty-bg": ("#F1F3F5", "#111A26"),
    "empty-border": ("#C5CCD5", "#3A4A60"),
    "empty-text": ("#8A94A3", "#6F7D90"),
    "match-bg": ("#EAF1FB", "#1E3555"),
    "head-bg": ("#EAF1FB", "#1E3555"),        # table headers (Finished Goods DOH)
    "zebra": ("#F6F8FB", "#182335"),          # alternate table rows
    "badge-bg": ("#FFF1D6", "#3A2E12"),
    "badge-text": ("#8A5A00", "#F2C46B"),
    "badge-border": ("#F3D9A4", "#5C4A1E"),
    "shadow": ("rgba(31, 41, 51, 0.12)", "rgba(0, 0, 0, 0.45)"),
    "page-bg": ("#F8F9FA", "#0E1621"),
}
_LIGHT_VARS = " ".join(f"--hub-{k}: {v[0]};" for k, v in _TOKENS.items())
_DARK_VARS = " ".join(f"--hub-{k}: {v[1]};" for k, v in _TOKENS.items())

# Plotly charts: pages leave the font color unset (st.plotly_chart's theme follows the app) and use
# GRID_COLOR, which reads on both backgrounds. The plot area and pie borders follow the tokens via CSS.
CHART_FONT = dict(family="Inter, sans-serif")
GRID_COLOR = "rgba(128, 128, 128, 0.22)"
LINE_COLOR = "#3F7CC4"  # brand mid-blue for thin lines: PRIMARY is too dark to read on the dark theme

_BASE_CSS = f"""
<style>
:root {{ {_LIGHT_VARS} }}
:root[data-hub-theme="dark"] {{ {_DARK_VARS} }}

/* ---- Plotly: plot area and pie slice borders follow the theme ---- */
.js-plotly-plot .plotly .bg {{ fill: var(--hub-surface) !important; }}
.js-plotly-plot .plotly .pielayer .slice path.surface {{ stroke: var(--hub-page-bg) !important; }}

/* ---- Dark theme: white Gestamp logo; the theme-watch script takes no space ---- */
:root[data-hub-theme="dark"] [data-testid="stSidebarLogo"],
:root[data-hub-theme="dark"] [data-testid="stHeaderLogo"] {{ filter: brightness(0) invert(1); }}
div[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > script:only-child) {{ display: none; }}

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
    color: var(--hub-muted);
    margin: 18px 0 2px 0;
}}

/* ---- Navigation cards: st.container(border=True, key="card_...") ---- */
div[class*="st-key-card_"] {{
    position: relative;
    background: var(--hub-surface);
    min-height: 160px;
    transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}}
div[class*="st-key-card_"]:hover {{
    box-shadow: 0 10px 24px var(--hub-shadow);
    transform: translateY(-2px);
    border-color: var(--hub-accent);
}}
div[class*="st-key-card_"] a,
div[class*="st-key-card_"] a p,
div[class*="st-key-card_"] a span {{
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--hub-accent);
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
    border-bottom: 2px solid var(--hub-accent);
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
    background: var(--hub-surface);
    border: 1px solid var(--hub-border);
    border-left: 4px solid var(--hub-ok);
}}
.slot.empty {{
    background: var(--hub-empty-bg);
    border: 1px dashed var(--hub-empty-border);
    color: var(--hub-empty-text);
}}
.slot.match {{
    background: var(--hub-match-bg);
    border-color: var(--hub-accent);
    box-shadow: 0 0 0 3px rgba(32, 65, 108, 0.35);
}}
.slot.dim {{ opacity: 0.35; }}
.slot .pos {{ font-weight: 650; font-size: 0.85rem; }}
.slot .line {{ color: var(--hub-muted); overflow-wrap: anywhere; }}
.slot .line:first-of-type {{ color: var(--hub-text); font-weight: 600; }}
.legend {{ display: flex; gap: 18px; font-size: 0.82rem; color: var(--hub-muted); margin: 4px 0 10px 0; }}
.legend .swatch {{ display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }}

.hub-badge {{
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--hub-badge-text);
    background: var(--hub-badge-bg);
    border-radius: 999px;
    padding: 1px 8px;
    margin-left: 6px;
    vertical-align: middle;
}}
.hub-card-desc {{ color: var(--hub-muted); font-size: 0.9rem; line-height: 1.4; }}
.hub-sample {{
    display: inline-block; font-size: 0.8rem; font-weight: 500; margin-bottom: 4px;
    color: var(--hub-badge-text); background: var(--hub-badge-bg);
    border: 1px solid var(--hub-badge-border); border-radius: 999px; padding: 3px 12px;
}}
.hub-fs-btn {{
    width: 100%; height: 2.5rem; cursor: pointer; font: inherit; font-size: 0.9rem; font-weight: 500;
    color: #FFFFFF; background: var(--hub-button); border: 1px solid var(--hub-button); border-radius: 0.5rem;
}}
.hub-fs-btn:hover {{ filter: brightness(1.15); }}
</style>
"""


# Streamlit exposes no CSS variables for the theme, so this watches the app background and sets
# <html data-hub-theme="light|dark">; the CSS tokens above switch on it, also when the user changes
# the theme in Settings or the OS (no rerun needed). Installed once per browser tab.
_THEME_WATCH_JS = """
<script>
if (!window.__hubThemeWatch) {
    window.__hubThemeWatch = true;
    const sync = () => {
        const app = document.querySelector('[data-testid="stApp"]') || document.body;
        const m = getComputedStyle(app).backgroundColor.match(/\d+(\.\d+)?/g);
        if (!m) return;
        const lum = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2];
        const theme = lum < 128 ? "dark" : "light";
        if (document.documentElement.dataset.hubTheme !== theme) document.documentElement.dataset.hubTheme = theme;
    };
    sync();
    // A theme switch re-renders the app with new style classes; coalesce bursts into one check per frame.
    let queued = false;
    new MutationObserver(() => {
        if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; sync(); }); }
    }).observe(document.body, { attributes: true, attributeFilter: ["class"], subtree: true });
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => setTimeout(sync, 100));
}
</script>
"""


def apply_base_style():
    """Inject the shared CSS and the theme watcher. Called once per run from the entry point."""
    st.html(_BASE_CSS)
    st.html(_THEME_WATCH_JS, unsafe_allow_javascript=True)


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
        st.html(f'<div class="hub-card-desc">{escape(descricao)}{badge_html}</div>')


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


def is_tv_mode():
    """TV mode is turned on with ?tv=1 in the URL (e.g. a kiosk browser on a shop-floor TV)."""
    return st.query_params.get("tv") == "1"


_TV_CSS = """
<style>
/* TV mode (?tv=1): no sidebar / toolbar, full width, compact slots so a whole map fits a 1080p screen */
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stMainBlockContainer"] {
    padding-top: 1rem !important;
    padding-bottom: 0.5rem !important;
    max-width: 100% !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] { gap: 0.45rem !important; }
.slot { min-height: 84px !important; padding: 4px 8px !important; margin-bottom: 0 !important;
        font-size: 0.74rem !important; line-height: 1.28 !important; }
.slot .pos { font-size: 0.8rem; }
.rail-title { margin-bottom: 2px; padding-bottom: 4px; }
[data-testid="stMetric"] { padding: 6px 14px !important; }
[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
.legend { margin: 0; }
h1 { padding-top: 0 !important; padding-bottom: 0 !important; }
</style>
"""


def apply_tv_style():
    """Inject the TV-mode CSS. Called by the entry point when ?tv=1."""
    st.html(_TV_CSS)


def _toggle_tv_mode():
    if is_tv_mode():
        del st.query_params["tv"]
    else:
        st.query_params["tv"] = "1"


def tv_mode_button():
    """Primary button that turns TV mode on (or off, when already in TV mode); keeps the other URL params."""
    tv = is_tv_mode()
    st.button("Exit TV mode" if tv else "TV mode", icon=":material/tv_off:" if tv else ":material/tv:",
              type="primary", width="stretch", on_click=_toggle_tv_mode, key="tv_mode_toggle")


def fullscreen_button():
    """Button that toggles browser fullscreen (Fullscreen API; needs a click, so it suits monitors).

    For a permanent TV prefer a kiosk browser: chrome --kiosk "<url>?tv=1".
    """
    st.html(
        """
        <button class="hub-fs-btn" type="button">&#x26F6;&nbsp; Fullscreen</button>
        <script>
        // Inline onclick attributes are stripped by st.html, so bind the handler here.
        document.querySelectorAll(".hub-fs-btn").forEach(function (b) {
            b.onclick = function () {
                if (document.fullscreenElement) { document.exitFullscreen(); }
                else { document.documentElement.requestFullscreen(); }
            };
        });
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def sample_data_notice():
    """Discreet banner shown on every page while USE_SAMPLE_DATA is on."""
    st.html('<div class="hub-sample">Sample data mode: all figures are fictitious, not plant data</div>')


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
