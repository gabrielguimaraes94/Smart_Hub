# -*- coding: utf-8 -*-
"""
GC2 - Finished Goods Stock, DOH & Sales (Power BI interim replacement)
Optimized for factory TV display: all columns visible, no horizontal scroll.

GENERATED FILE - do not edit by hand. Source: the modules of the DOH_Report
repository, built with scripts/build_single_file.py.

Sources:
  1) Latest STOCK_GC2_DDMMYYYY_HHMM.csv (PS1)
  2) Demand_master_Data.xlsx (fixed) -> CPN, Daily Pull, EDI Req., Program (column C)
  3) GC2_SALES.XLSX (current day, hourly) + GC2_SALES_TOTAL.XLSX (history)

How to run:
    pip install streamlit==1.66.0 pandas==2.2.3 openpyxl==3.1.5 plotly==7.1.0
    streamlit run Finish_Goods_DOH.py --theme.base light --server.headless true
"""

import os
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import html
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, date, timedelta


# ======================================================================
# config.py
# ======================================================================
BASE_DIR = Path(__file__).resolve().parent

# ----------------------------------------------------------------------
# DATA PATHS (network shares)
# A host app can point them elsewhere with these environment variables: the Smart Hub sets
# them from its own config.py (network shares, or its sample data with USE_SAMPLE_DATA=1).
# ----------------------------------------------------------------------
STOCK_FOLDER = os.environ.get("DOH_STOCK_FOLDER", r"\\ch2-file3.us.gestamp.com\PowerBI\DATA\Demand\GC2\PS1")
DEMAND_FILE = os.environ.get("DOH_DEMAND_FILE", r"\\ch2-file3\PowerBI\DATA\Demand\Demand_master_Data.xlsx")
SALES_FOLDER = os.environ.get("DOH_SALES_FOLDER", r"\\ch2-file3.us.gestamp.com\PowerBI\DATA\Demand\SALES")

DEMO_MODE = False

PLANT = "GC2"

STOCK_PATTERN = re.compile(r"STOCK_GC2_(\d{8})_(\d{4})\.csv$", re.IGNORECASE)
CSV_SEPARATOR = ";"

# ----------------------------------------------------------------------
# CALCULATION CONSTANTS (same as the Power BI report - do not change)
# ----------------------------------------------------------------------
LGORT_COLUMNS = {
    "SAP Inventory": ["FG", "FGWH"],
    "Metal Finish":  ["GMFI"],
    "GP12":          ["GP12"],
    "Incomplete":    ["INCO"],
    "INAD":          ["INAD"],
    "PART":          ["PART"],
    "SORT":          ["SORT"],
    "Q HOLD":        ["QHLD"],
}
LGORT_DOH = ["FG", "FGWH"]                                                        # CalDOH
LGORT_DOH_TOTAL = ["FGWH", "GP12", "GMFI", "INCO", "FG", "SORT", "INAD", "PART"]  # CalDOHTotal

WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
EDI_WORKING_DAYS = 5.5

DOH_RED = 0.5
DOH_GREEN = 1.0

# ----------------------------------------------------------------------
# COLORS (Smart Hub palette: the same bands as the hub's FIFO and Press Capacity pages)
# Surfaces and text use the hub's --hub-* CSS tokens, which follow its light/dark theme;
# the fallback after each token is the light value, used when the app runs on its own.
# ----------------------------------------------------------------------
COLOR_RED = "#C0392B"
COLOR_YELLOW = "#E9B949"
COLOR_GREEN = "#2E7D4F"
BAND_TEXT = {"red": "#FFFFFF", "yellow": "#1F2933", "green": "#FFFFFF"}   # readable on each band

# ----------------------------------------------------------------------
# TV DISPLAY TUNING
# ----------------------------------------------------------------------
TABLE_FONT_SIZE = "13px"     # shrink/grow to fit the TV resolution
TABLE_HEIGHT = "62vh"        # vertical space used by the table
AUTO_REFRESH_MINUTES = 5     # full page reload for TV displays (0 = off)
FILE_SCAN_TTL = 60           # seconds between scans of the network folders


# ======================================================================
# data_loader.py
# ======================================================================
# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------
def _to_number(series: pd.Series) -> pd.Series:
    """SAP extracts use DOT as decimal ('84.000 ' = 84). Comma = BR/EU format."""
    s = series.astype(str).str.strip()
    has_comma = s.str.contains(",", na=False)
    s = s.where(
        ~has_comma,
        s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    return pd.to_numeric(s, errors="coerce").fillna(0)


def _find_column(columns, *terms):
    for c in columns:
        cl = str(c).lower()
        if all(t.lower() in cl for t in terms):
            return c
    return None


def _find_file(folder: Path, name: str) -> Path | None:
    if not folder.exists():
        return None
    target = name.lower()
    for f in folder.iterdir():
        if f.name.lower() == target:
            return f
    return None


def _mtime(path: Path | None) -> float:
    return path.stat().st_mtime if path is not None else 0


# ----------------------------------------------------------------------
# FILE SCAN (cached: avoids listing the network share on every click)
# ----------------------------------------------------------------------
def find_latest_stock_file(folder: str):
    p = Path(folder)
    if not p.exists():
        return None, None
    candidates = []
    for f in p.glob("STOCK_GC2_*.csv"):
        m = STOCK_PATTERN.search(f.name)
        if m:
            try:
                ts = datetime.strptime(m.group(1) + m.group(2), "%d%m%Y%H%M")
                candidates.append((ts, f))
            except ValueError:
                continue
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1], candidates[0][0]


@st.cache_data(ttl=FILE_SCAN_TTL, show_spinner=False)
def scan_sources() -> dict:
    """Locates every source file and its mtime (mtimes are the cache keys downstream)."""
    stock_file, _ = find_latest_stock_file(STOCK_FOLDER)
    p_dem = Path(DEMAND_FILE)
    p_sales = Path(SALES_FOLDER)
    f_hourly = _find_file(p_sales, "GC2_SALES.XLSX")
    f_total = _find_file(p_sales, "GC2_SALES_TOTAL.XLSX")
    return {
        "stock_file": str(stock_file) if stock_file else None,
        "stock_mtime": _mtime(stock_file),
        "demand_exists": p_dem.exists(),
        "demand_mtime": _mtime(p_dem) if p_dem.exists() else 0,
        "sales_hourly_mtime": _mtime(f_hourly),
        "sales_total_mtime": _mtime(f_total),
    }


# ----------------------------------------------------------------------
# STOCK (PS1)
# ----------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Loading stock file...")
def load_stock(path: str, mtime: float) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, sep=CSV_SEPARATOR, encoding=enc, dtype=str)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Could not decode the CSV file.")

    df.columns = [c.strip() for c in df.columns]
    rename = {}
    for c in df.columns:
        cu = c.upper()
        if cu in ("MATNR", "MATERIAL"):
            rename[c] = "MATNR"
        elif cu in ("WERKS", "LGORT", "MAKTX", "LABST", "INSME"):
            rename[c] = cu
    df = df.rename(columns=rename)

    missing = {"WERKS", "MATNR", "MAKTX", "LGORT", "LABST", "INSME"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in stock file: {', '.join(sorted(missing))}")

    df = df.dropna(subset=["WERKS", "MATNR", "LGORT"])
    df["LABST"] = _to_number(df["LABST"])
    df["INSME"] = _to_number(df["INSME"])
    df["LGORT"] = df["LGORT"].str.strip().str.upper()
    df["WERKS"] = df["WERKS"].str.strip()
    df["MATNR"] = df["MATNR"].str.strip()
    df["MAKTX"] = df["MAKTX"].fillna("").str.strip()
    df["QTY"] = df["LABST"] + df["INSME"]
    return df


# ----------------------------------------------------------------------
# DEMAND MASTER DATA
# ----------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Loading Demand Master Data...")
def load_demand(path: str, mtime: float) -> pd.DataFrame:
    dm = pd.read_excel(path, dtype=str)
    dm.columns = [str(c).strip() for c in dm.columns]

    mat_col = _find_column(dm.columns, "material") or dm.columns[0]
    cpn_col = _find_column(dm.columns, "client", "part")
    pull_col = _find_column(dm.columns, "daily", "pull")
    edi_col = _find_column(dm.columns, "edi")
    # Program comes from COLUMN C (third column) of the master data file
    prog_col = dm.columns[2] if len(dm.columns) >= 3 else None

    out = pd.DataFrame()
    out["MATNR"] = dm[mat_col].astype(str).str.strip()
    out["Client Part Number"] = dm[cpn_col].astype(str).str.strip() if cpn_col else ""
    out["Daily Pull"] = _to_number(dm[pull_col]) if pull_col else 0.0
    out["EDI Requirement"] = _to_number(dm[edi_col]) if edi_col else 0.0
    out["Program"] = dm[prog_col].fillna("").astype(str).str.strip() if prog_col else ""

    out = out.groupby("MATNR", as_index=False).agg(
        {"Client Part Number": "first", "Daily Pull": "sum",
         "EDI Requirement": "sum", "Program": "first"}
    )
    return out


# ----------------------------------------------------------------------
# SALES
# ----------------------------------------------------------------------
def _read_sales(path: Path) -> pd.DataFrame:
    """Accepts both SAP header layouts (e.g. 'Posting Date' or 'Pstng Date')."""
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]

    mat_col = "Material" if "Material" in df.columns else _find_column(df.columns, "material")
    qty_col = "Quantity" if "Quantity" in df.columns else _find_column(df.columns, "quantity")
    date_col = (
        _find_column(df.columns, "posting", "date")
        or _find_column(df.columns, "pstng", "date")
    )
    if not all([mat_col, qty_col, date_col]):
        raise ValueError(
            f"Sales columns not found in {path.name}. Columns: {list(df.columns)}"
        )

    v = pd.DataFrame()
    v["MATNR"] = df[mat_col].astype(str).str.strip()
    v["Quantity"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
    v["Posting Date"] = pd.to_datetime(df[date_col], errors="coerce")
    return v.dropna(subset=["Posting Date"])


@st.cache_data(ttl=300, show_spinner="Loading sales files...")
def load_sales(folder: str, mtime_hourly: float, mtime_total: float) -> pd.DataFrame:
    """Hourly file wins for any date it contains; other dates come from TOTAL."""
    p = Path(folder)
    f_hourly = _find_file(p, "GC2_SALES.XLSX")
    f_total = _find_file(p, "GC2_SALES_TOTAL.XLSX")

    parts = []
    hourly_dates = set()
    if f_hourly is not None:
        vh = _read_sales(f_hourly)
        hourly_dates = set(vh["Posting Date"].dt.date.unique())
        parts.append(vh)
    if f_total is not None:
        vt = _read_sales(f_total)
        if hourly_dates:
            vt = vt[~vt["Posting Date"].dt.date.isin(hourly_dates)]
        parts.append(vt)

    if not parts:
        return pd.DataFrame(columns=["MATNR", "Quantity", "Posting Date"])
    return pd.concat(parts, ignore_index=True)


# ======================================================================
# calculations.py
# ======================================================================
# ----------------------------------------------------------------------
# WEEKS
# ----------------------------------------------------------------------
def week_start(d: date) -> date:
    """Sunday of the week containing d (week starts Sunday, as WEEKDAY(...,1))."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def week_number(d: date) -> int:
    """Excel-style WEEKNUM (Sunday as first day)."""
    return int(d.strftime("%U")) + 1


# ----------------------------------------------------------------------
# SALES PIVOT
# ----------------------------------------------------------------------
def pivot_week_sales(sales: pd.DataFrame, start: date) -> pd.DataFrame:
    end = start + timedelta(days=6)
    v = sales[
        (sales["Posting Date"].dt.date >= start) & (sales["Posting Date"].dt.date <= end)
    ].copy()
    if v.empty:
        cols = ["MATNR"] + [f"Sales {d}" for d in WEEKDAYS] + ["_SalesWeek"]
        return pd.DataFrame(columns=cols)

    sun_idx = (v["Posting Date"].dt.weekday + 1) % 7  # Sunday=0
    v["Day"] = sun_idx.map(dict(enumerate(WEEKDAYS)))

    piv = (
        v.pivot_table(index="MATNR", columns="Day", values="Quantity", aggfunc="sum")
        .reindex(columns=WEEKDAYS)
        .fillna(0)
    )
    piv.columns = [f"Sales {c}" for c in piv.columns]
    piv["_SalesWeek"] = piv.sum(axis=1)
    return piv.reset_index()


# ----------------------------------------------------------------------
# FINAL TABLE
# ----------------------------------------------------------------------
def build_table(df, demand, week_sales) -> pd.DataFrame:
    rows = df[["WERKS", "MATNR", "MAKTX"]].drop_duplicates()

    def sum_by(lgorts, name):
        return (
            df[df["LGORT"].isin(lgorts)]
            .groupby(["WERKS", "MATNR", "MAKTX"], as_index=False)["QTY"]
            .sum()
            .rename(columns={"QTY": name})
        )

    for name, lgs in LGORT_COLUMNS.items():
        rows = rows.merge(sum_by(lgs, name), on=["WERKS", "MATNR", "MAKTX"], how="left")
    rows = rows.merge(
        sum_by(LGORT_DOH_TOTAL, "_TotalInv"), on=["WERKS", "MATNR", "MAKTX"], how="left"
    )
    rows[list(LGORT_COLUMNS.keys()) + ["_TotalInv"]] = rows[
        list(LGORT_COLUMNS.keys()) + ["_TotalInv"]
    ].fillna(0)

    if demand is not None and not demand.empty:
        rows = rows.merge(demand, on="MATNR", how="left")
        rows["Client Part Number"] = rows["Client Part Number"].fillna("")
        rows["Program"] = rows["Program"].fillna("")
        rows[["Daily Pull", "EDI Requirement"]] = rows[
            ["Daily Pull", "EDI Requirement"]
        ].fillna(0)
    else:
        rows["Client Part Number"] = ""
        rows["Program"] = ""
        rows["Daily Pull"] = 0.0
        rows["EDI Requirement"] = 0.0

    if week_sales is not None and not week_sales.empty:
        rows = rows.merge(week_sales, on="MATNR", how="left")
    for d in WEEKDAYS:
        if f"Sales {d}" not in rows.columns:
            rows[f"Sales {d}"] = 0.0
    if "_SalesWeek" not in rows.columns:
        rows["_SalesWeek"] = 0.0
    sales_cols = [f"Sales {d}" for d in WEEKDAYS] + ["_SalesWeek"]
    rows[sales_cols] = rows[sales_cols].fillna(0)

    rows["DOH"] = (rows["SAP Inventory"] / rows["Daily Pull"]).where(rows["Daily Pull"] > 0)
    rows["Total Inv DOH"] = (rows["_TotalInv"] / rows["Daily Pull"]).where(
        rows["Daily Pull"] > 0
    )
    rows["Total Parts"] = rows["_TotalInv"]
    rows["Total Parts Shipped"] = rows["_SalesWeek"]
    rows["EDI Sales Calc"] = rows["EDI Requirement"] - rows["_SalesWeek"]
    # QTY Shipped: DOH-equivalent shipped to the client (e.g. 1.2)
    rows["QTY Shipped"] = (
        rows["_SalesWeek"] / (rows["EDI Requirement"] / EDI_WORKING_DAYS)
    ).where(rows["EDI Requirement"] > 0)

    rows = rows.rename(
        columns={"WERKS": "Plant", "MATNR": "Material", "MAKTX": "Material Description"}
    )
    order = (
        ["Plant", "Material", "Material Description", "Client Part Number",
         "SAP Inventory", "DOH", "Metal Finish", "GP12", "Incomplete",
         "INAD", "PART", "SORT", "Total Parts", "Q HOLD", "Total Inv DOH",
         "EDI Requirement"]
        + [f"Sales {d}" for d in WEEKDAYS]
        + ["Total Parts Shipped", "EDI Sales Calc", "QTY Shipped"]
    )
    return rows[order + ["Program", "Daily Pull", "_SalesWeek"]].sort_values(
        "SAP Inventory", ascending=False
    ).reset_index(drop=True)


# ----------------------------------------------------------------------
# FILTERS
# ----------------------------------------------------------------------
def filter_table(table: pd.DataFrame, program: str | None, search: str,
                 only_with_stock: bool) -> pd.DataFrame:
    filtered = table
    if program and program != "Select all":
        filtered = filtered[filtered["Program"] == program]
    if search:
        b = search.strip().upper()
        filtered = filtered[
            filtered["Material"].str.upper().str.contains(b, na=False)
            | filtered["Material Description"].str.upper().str.contains(b, na=False)
            | filtered["Client Part Number"].str.upper().str.contains(b, na=False)
        ]
    if only_with_stock:
        filtered = filtered[filtered[list(LGORT_COLUMNS.keys())].sum(axis=1) > 0]
    return filtered


# ----------------------------------------------------------------------
# TOTALS (sum / sum, like Power BI)
# ----------------------------------------------------------------------
def compute_totals(filtered: pd.DataFrame) -> dict:
    tot_pull = filtered["Daily Pull"].sum()
    tot_sap = filtered["SAP Inventory"].sum()
    tot_inv = filtered["Total Parts"].sum()
    tot_sales = filtered["_SalesWeek"].sum()
    tot_edi = filtered["EDI Requirement"].sum()
    doh_total = tot_sap / tot_pull if tot_pull > 0 else None
    doh_inv_total = tot_inv / tot_pull if tot_pull > 0 else None
    shipped_total = tot_sales / (tot_edi / EDI_WORKING_DAYS) if tot_edi > 0 else None
    return {
        "doh_total": doh_total,
        "doh_inv_total": doh_inv_total,
        "shipped_total": shipped_total,
    }


# ----------------------------------------------------------------------
# DOH BANDS (same thresholds as the table colors)
# ----------------------------------------------------------------------
def doh_band(v) -> str | None:
    if v is None or pd.isna(v):
        return None
    if v < DOH_RED:
        return "red"
    if v <= DOH_GREEN:
        return "yellow"
    return "green"


# ======================================================================
# ui/styles.py
# ======================================================================
def inject_css():
    # st.html with only a <style> takes no space in the layout (st.markdown would add a gap)
    st.html(
        f"""<style>
    /* the zero-height auto-refresh iframe takes no space either */
    div[data-testid="stElementContainer"]:has(> iframe[height="0"]) {{ display: none; }}

    /* ---- KPI cards (same look as the hub's bordered st.metric) ---- */
    .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; }}
    .kpi {{ border: 1px solid var(--hub-border, #D9DEE5); border-left-width: 4px;
           border-radius: 0.5rem; padding: 0.6rem 1rem;
           background: var(--hub-surface, #FFFFFF); }}
    .kpi .label {{ font-size: 0.875rem; color: var(--hub-muted, #5B6776); }}
    .kpi .value {{ font-size: 1.75rem; font-weight: 600; line-height: 1.25;
                  color: var(--hub-text, #1F2933); }}
    .kpi .sub {{ font-size: 0.75rem; color: var(--hub-muted, #5B6776); }}
    .kpi.filled .label, .kpi.filled .value, .kpi.filled .sub {{ color: inherit; }}

    /* ---- table ---- */
    /* scrolls sideways when the hub sidebar is open; with ?tv=1 (no sidebar) everything fits */
    .fgwrap {{ max-height: {TABLE_HEIGHT}; overflow: auto; border-radius: 0.5rem;
              border: 1px solid var(--hub-border, #D9DEE5);
              background: var(--hub-surface, #FFFFFF); }}
    .fgtable {{ width: 100%; border-collapse: collapse;
               font-size: {TABLE_FONT_SIZE}; line-height: 1.25;
               color: var(--hub-text, #1F2933); }}
    .fgtable thead th {{ position: sticky; top: 0; z-index: 2;
                        background: var(--hub-head-bg, #EAF1FB); color: var(--hub-text, #1F2933);
                        padding: 4px 3px; text-align: center; font-weight: 600;
                        font-size: calc({TABLE_FONT_SIZE} - 1px);
                        border-bottom: 1px solid var(--hub-border, #D9DEE5); }}
    .fgtable td {{ padding: 2px 4px; border-right: 1px solid var(--hub-border, #D9DEE5);
                  text-align: right; white-space: nowrap; }}
    .fgtable td.col0, .fgtable td.col1, .fgtable td.col2, .fgtable td.col3
        {{ text-align: left; }}
    .fgtable td.col2 {{ max-width: 220px; overflow: hidden; text-overflow: ellipsis; }}
    .fgtable tbody tr {{ background: var(--hub-surface, #FFFFFF); }}
    .fgtable tbody tr:nth-child(even) {{ background: var(--hub-zebra, #F6F8FB); }}
    .fgtable tfoot td {{ position: sticky; bottom: 0; background: var(--hub-surface, #FFFFFF);
                        font-weight: 600; border-top: 2px solid var(--hub-muted, #5B6776);
                        padding: 4px 6px; }}
    </style>"""
    )


def inject_tv_css():
    """TV mode (?tv=1) when the page runs on its own: no toolbar, sidebar or side padding.
    Inside the Smart Hub, its entry point already does this (ui.apply_tv_style)."""
    st.html(
        """<style>
    header[data-testid="stHeader"], section[data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
    [data-testid="stMainBlockContainer"] { padding-top: 1rem !important; padding-bottom: 0.5rem !important;
                                            max-width: 100% !important; }
    </style>"""
    )


def auto_refresh():
    """Full page reload for TV mode (filters survive via the URL query string)."""
    if AUTO_REFRESH_MINUTES > 0:
        components.html(
            f"<script>setTimeout(function(){{window.parent.location.reload();}},"
            f"{AUTO_REFRESH_MINUTES * 60 * 1000});</script>",
            height=0,
        )


# ======================================================================
# ui/table.py
# ======================================================================
BAND_COLORS = {"red": COLOR_RED, "yellow": COLOR_YELLOW, "green": COLOR_GREEN}


def _fmt_qty_blank_zero(v):
    return "" if (pd.isna(v) or v == 0) else f"{v:,.0f}"


def _fmt_qty(v):
    return "" if pd.isna(v) else f"{v:,.0f}"


def _fmt_doh(v):
    return "" if pd.isna(v) else f"{v:.1f}"


def doh_css(v):
    band = doh_band(v)
    return f"background-color:{BAND_COLORS[band]};color:{BAND_TEXT[band]}" if band else ""


def _column_defs(columns):
    col_defs = []  # (column, header_html, formatter, is_doh)
    for c in columns:
        if c.startswith("Sales "):
            head = c.replace("Sales ", "")[:3]           # Sun, Mon, ...
            col_defs.append((c, f"Sales<br>{head}", _fmt_qty_blank_zero, False))
        elif c in ("DOH", "Total Inv DOH"):
            col_defs.append((c, c.replace(" ", "<br>", 1), _fmt_doh, True))
        elif c == "QTY Shipped":
            col_defs.append((c, "QTY<br>Shipped", _fmt_doh, True))
        elif c in ("Metal Finish", "GP12", "Incomplete", "INAD", "PART", "SORT", "Q HOLD"):
            col_defs.append((c, c.replace(" ", "<br>"), _fmt_qty_blank_zero, False))
        elif c in ("SAP Inventory", "Total Parts", "EDI Requirement",
                   "Total Parts Shipped", "EDI Sales Calc"):
            col_defs.append((c, c.replace(" ", "<br>"), _fmt_qty, False))
        else:
            col_defs.append((c, c, None, False))
    return col_defs


def render_table(display: pd.DataFrame, totals: dict) -> str:
    col_defs = _column_defs(display.columns)
    head_html = "".join(f"<th>{h}</th>" for _, h, _, _ in col_defs)

    # Built column by column (faster than iterrows on large tables)
    cells_by_col = []
    for i, (c, _, f, is_doh) in enumerate(col_defs):
        cls = f' class="col{i}"' if i <= 3 else ""
        cells = []
        for v in display[c].tolist():
            css = f' style="{doh_css(v)}"' if is_doh else ""
            txt = f(v) if f else ("" if pd.isna(v) else html.escape(str(v)))
            cells.append(f"<td{cls}{css}>{txt}</td>")
        cells_by_col.append(cells)
    body_html = "".join("<tr>" + "".join(row) + "</tr>" for row in zip(*cells_by_col))

    # Totals row (aggregates like the Power BI report: sum / sum for DOH)
    foot_cells = []
    for c, _, f, is_doh in col_defs:
        if c == "Plant":
            foot_cells.append("<td class='col0'>Total</td>")
        elif c in ("Material", "Material Description", "Client Part Number"):
            foot_cells.append("<td></td>")
        elif c == "DOH":
            foot_cells.append(f"<td>{_fmt_doh(totals.get('doh_total'))}</td>")
        elif c == "Total Inv DOH":
            foot_cells.append(f"<td>{_fmt_doh(totals.get('doh_inv_total'))}</td>")
        elif c == "QTY Shipped":
            foot_cells.append(f"<td>{_fmt_doh(totals.get('shipped_total'))}</td>")
        else:
            s = display[c].sum()
            foot_cells.append(f"<td>{_fmt_qty_blank_zero(s)}</td>")
    foot_html = "<tr>" + "".join(foot_cells) + "</tr>"

    return (
        '<div class="fgwrap"><table class="fgtable">'
        f"<thead><tr>{head_html}</tr></thead>"
        f"<tbody>{body_html}</tbody>"
        f"<tfoot>{foot_html}</tfoot>"
        "</table></div>"
    )


# ======================================================================
# ui/kpis.py
# ======================================================================
BAND_COLORS = {"red": COLOR_RED, "yellow": COLOR_YELLOW, "green": COLOR_GREEN}


def _card(label, value, sub, accent, fill=None, text=None):
    style = f"border-left-color:{accent};"
    cls = "kpi"
    if fill:
        style += f"background:{fill};border-color:{fill};color:{text};"
        cls += " filled"
    return (
        f'<div class="{cls}" style="{style}"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="sub">{sub}</div></div>'
    )


def render_kpis(filtered: pd.DataFrame, totals: dict) -> str:
    bands = filtered["DOH"].map(doh_band)
    n_red = int((bands == "red").sum())
    n_yellow = int((bands == "yellow").sum())
    n_green = int((bands == "green").sum())
    n_rated = n_red + n_yellow + n_green

    doh = totals.get("doh_total")
    doh_txt = "-" if doh is None else f"{doh:.1f}"
    band = doh_band(doh)
    doh_color = BAND_COLORS.get(band, "#8A94A3")

    cards = [
        _card("Plant DOH", doh_txt, "SAP Inventory / Daily Pull", doh_color, doh_color,
              BAND_TEXT.get(band, "#FFFFFF")),
        _card(f"Critical &lt; {DOH_RED}", n_red, f"of {n_rated} items", COLOR_RED),
        _card(f"Warning {DOH_RED} – {DOH_GREEN}", n_yellow, f"of {n_rated} items", COLOR_YELLOW),
        _card(f"On target &gt; {DOH_GREEN}", n_green, f"of {n_rated} items", COLOR_GREEN),
    ]
    return '<div class="kpis">' + "".join(cards) + "</div>"


# ======================================================================
# ui/charts.py
# ======================================================================
BANDS = [("red", "Critical", COLOR_RED),
         ("yellow", "Warning", COLOR_YELLOW),
         ("green", "On target", COLOR_GREEN)]


def program_bands_chart(table: pd.DataFrame, selected: str | None) -> go.Figure:
    t = table[table["Program"] != ""].assign(Band=table["DOH"].map(doh_band))
    counts = (
        t.dropna(subset=["Band"])
        .groupby(["Program", "Band"]).size()
        .unstack(fill_value=0)
        .reindex(columns=[b for b, _, _ in BANDS], fill_value=0)
    )
    # Worst programs on top
    counts = counts.sort_values(["red", "yellow"], ascending=True)
    labels = [
        f"<b>{p}</b>" if selected and p == selected else p for p in counts.index
    ]

    fig = go.Figure()
    for band, name, color in BANDS:
        fig.add_bar(
            y=labels, x=counts[band], name=name, orientation="h",
            marker=dict(color=color, line=dict(width=0)),
            text=counts[band].where(counts[band] > 0, None),
            textposition="inside", insidetextanchor="middle", textangle=0,
            insidetextfont=dict(color=BAND_TEXT[band], size=14),
            hovertemplate="%{y}<br>" + name + ": %{x} items<extra></extra>",
        )
    fig.update_layout(
        barmode="stack", height=max(130, 30 * len(counts) + 40),
        uniformtext=dict(minsize=14, mode="show"),
        margin=dict(l=0, r=0, t=24, b=0),
        title=dict(text="Items per DOH band by Program", font=dict(size=14), x=0, y=0.98),
        legend=dict(orientation="h", y=1.0, yanchor="bottom", x=1, xanchor="right",
                    font=dict(size=11), traceorder="normal"),
        xaxis=dict(visible=False), yaxis=dict(tickfont=dict(size=12)),
        # transparent: in the hub, its CSS themes the plot area; text colors follow the Streamlit theme
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ======================================================================
# app.py
# ======================================================================
WEEK_OPTIONS = ["Current Week", "Previous Week"]


# ----------------------------------------------------------------------
# URL QUERY STRING (filters survive the TV auto-refresh)
# ----------------------------------------------------------------------
def qp_get(name: str, default: str) -> str:
    return st.query_params.get(name, default)


def qp_set(**kwargs):
    for k, v in kwargs.items():
        st.query_params[k] = v


# ----------------------------------------------------------------------
# DATA (cached by file mtimes + week: clicks only filter the ready table)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Building table...", max_entries=8)
def get_table(stock_path: str, stock_mtime: float, demand_mtime: float,
              sales_hourly_mtime: float, sales_total_mtime: float, start: date):
    df_raw = load_stock(stock_path, stock_mtime)
    demand = load_demand(DEMAND_FILE, demand_mtime) if demand_mtime else None
    sales = load_sales(SALES_FOLDER, sales_hourly_mtime, sales_total_mtime)
    week_sales = pivot_week_sales(sales, start) if not sales.empty else None
    return build_table(df_raw, demand, week_sales)


def check_sources(src: dict) -> dict:
    """Stops the page if the stock file is unusable; warns about demand problems."""
    if src["stock_file"] is None:
        st.error(f"No `STOCK_GC2_*.csv` file found in `{STOCK_FOLDER}`.")
        st.stop()
    try:
        load_stock(src["stock_file"], src["stock_mtime"])
    except Exception as e:
        st.error(f"Error reading `{src['stock_file']}`: {e}")
        st.stop()

    if not src["demand_exists"]:
        st.warning(f"Demand file not found: `{DEMAND_FILE}`")
    else:
        try:
            load_demand(DEMAND_FILE, src["demand_mtime"])
        except Exception as e:
            st.warning(f"Demand Master Data could not be read ({e}).")
            src = {**src, "demand_mtime": 0}
    return src


# ----------------------------------------------------------------------
# PAGE
# ----------------------------------------------------------------------
def is_tv_mode() -> bool:
    return st.query_params.get("tv") == "1"


def page_header(week_no: int, start: date, last_update: datetime):
    """Standard Smart Hub header: page title + one caption line with the report context."""
    st.title("Finished Goods DOH")
    demo = " · DEMO DATA" if DEMO_MODE else ""
    st.caption(
        f"Plant {PLANT} · Week {week_no} ({start:%m/%d} – {(start + timedelta(days=6)):%m/%d})"
        f" · Last update {last_update:%m/%d/%Y %I:%M:%S %p}{demo}"
    )


@st.fragment
def dashboard(src: dict):
    """Everything that reacts to clicks: reruns alone, without reloading the page."""
    header = st.container()
    c_prog, c_week, c_search, c_stock, c_reload, c_tv = st.columns(
        [4.2, 2.2, 1.8, 1.3, 1.0, 0.75], vertical_alignment="center"
    )

    with c_week:
        saved_week = qp_get("week", WEEK_OPTIONS[0])
        week_choice = st.radio(
            "Week", WEEK_OPTIONS, horizontal=True,
            index=WEEK_OPTIONS.index(saved_week) if saved_week in WEEK_OPTIONS else 0,
            label_visibility="collapsed",
        )
    current_start = week_start(date.today())
    selected_start = (current_start if week_choice == WEEK_OPTIONS[0]
                      else current_start - timedelta(days=7))

    table = get_table(
        src["stock_file"], src["stock_mtime"], src["demand_mtime"],
        src["sales_hourly_mtime"], src["sales_total_mtime"], selected_start,
    )

    with c_prog:
        programs = sorted(p for p in table["Program"].unique() if p)
        options = ["Select all"] + programs
        saved_prog = qp_get("program", "Select all")
        sel_program = st.segmented_control(
            "Program", options,
            default=saved_prog if saved_prog in options else "Select all",
            label_visibility="collapsed",
        ) or "Select all"
    with c_search:
        search = st.text_input(
            "Search", value=qp_get("search", ""),
            placeholder="Material / Description / CPN",
            label_visibility="collapsed",
        )
    with c_stock:
        only_with_stock = st.toggle("Only with stock", value=qp_get("stock", "1") == "1")
    with c_reload:
        if st.button("Refresh", icon=":material/refresh:",
                     help="Reload the files now (the page also refreshes "
                     f"by itself every {AUTO_REFRESH_MINUTES} min)",
                     type="primary", width="stretch"):
            st.cache_data.clear()
            st.rerun()
    with c_tv:
        # ?tv=1: the Smart Hub hides its menu and toolbar; on its own the page applies inject_tv_css.
        # st.rerun() reruns the whole app (not just this fragment), so the TV layout is applied.
        tv = is_tv_mode()
        if st.button("Exit TV" if tv else "TV", icon=":material/tv_off:" if tv else ":material/tv:",
                     help="Leave TV mode" if tv else "TV mode: full screen width, no menu or toolbar",
                     width="stretch"):
            if tv:
                del st.query_params["tv"]
            else:
                st.query_params["tv"] = "1"
            st.rerun()

    qp_set(
        week=week_choice,
        program=sel_program,
        search=search or "",
        stock="1" if only_with_stock else "0",
    )

    last_update = datetime.fromtimestamp(src["stock_mtime"])
    with header:
        page_header(week_number(selected_start), selected_start, last_update)

    filtered = filter_table(table, sel_program, search, only_with_stock)
    totals = compute_totals(filtered)

    # ---- KPI cards + Program chart (chart ignores the Program filter) ----
    k_left, k_right = st.columns([3, 2])
    with k_left:
        st.markdown(render_kpis(filtered, totals), unsafe_allow_html=True)
    with k_right:
        st.plotly_chart(
            program_bands_chart(filter_table(table, None, search, only_with_stock),
                                sel_program),
            config={"displayModeBar": False}, width="stretch",
        )

    # ---- Table ----
    display = filtered.drop(columns=["Program", "Daily Pull", "_SalesWeek"])
    st.markdown(render_table(display, totals), unsafe_allow_html=True)

    csv_export = display.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        "Download filtered CSV", icon=":material/download:",
        data=csv_export,
        file_name=f"finished_goods_doh_gc2_{last_update:%m%d%Y_%H%M}.csv",
        mime="text/csv",
    )

    # Standard Smart Hub footer
    st.divider()
    st.caption(f"Gestamp NAFTA – {PLANT} | updated {last_update:%b %d, %Y %H:%M}")


def main():
    st.set_page_config(
        page_title="Finished Goods DOH",
        page_icon=":material/inventory_2:",
        layout="wide",
    )
    inject_css()
    if is_tv_mode():
        inject_tv_css()
    auto_refresh()
    src = check_sources(scan_sources())
    dashboard(src)


if __name__ == "__main__":
    main()
