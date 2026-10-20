import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Loading, part → model mapping and week numbering come from the EDI VW View page,
# so both pages read and group the EDI files the same way.
from app_pages.EDI_VW_view import (CAR_MODELS, EXCEL_FOLDER, get_file_creation_date,
                                   get_week_number, load_excel_file, process_data)
from ui import CHART_FONT, GRID_COLOR, LINE_COLOR, PRIMARY, footer, kpi_card, page_header

BASE_COLOR = "#A9B4C2"  # grey for the base (older) file, Gestamp blue for the compare file
DEFAULT_MODELS = ["Atlas NF", "Coupe NF"]  # pre-selected car models


def list_edi_files():
    """EDI files newest first (by creation date, like EDI VW View) as (name, received datetime)."""
    files = [f for f in os.listdir(EXCEL_FOLDER) if f.endswith('.xlsx')]
    dated = [(f, datetime.fromtimestamp(get_file_creation_date(os.path.join(EXCEL_FOLDER, f)))) for f in files]
    return sorted(dated, key=lambda x: x[1], reverse=True)


def file_label(name, received):
    return f"W{get_week_number(received):02d} · {received:%b %d, %Y} · {name}"


def week_start(day):
    """Sunday that starts the week of `day` (weeks run Sunday–Saturday, as in EDI VW View)."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def weekly_totals(df, lo, hi, models):
    """Release Qty per (week start, model) over [lo, hi] for the chosen models."""
    d = df[(df['Date'].dt.date >= lo) & (df['Date'].dt.date <= hi) & df['Car Model'].isin(models)].copy()
    d['Week start'] = d['Date'].dt.date.map(week_start)
    return d.groupby(['Week start', 'Car Model'])['Release Qty'].sum()


def daily_totals(df, lo, hi, models):
    """Release Qty per delivery date over [lo, hi] for the chosen models."""
    d = df[(df['Date'].dt.date >= lo) & (df['Date'].dt.date <= hi) & df['Car Model'].isin(models)]
    return d.groupby(d['Date'].dt.date)['Release Qty'].sum()


def week_label(start, lo, hi):
    """'2026-W43', with '*' when only part of the week falls in the compared dates."""
    partial = start < lo or start + timedelta(days=6) > hi
    return f"{start.year}-W{get_week_number(start):02d}" + ("*" if partial else "")


def pct(new, base):
    return (new - base) / base if base else None


def main():
    page_header("EDI Compare", "Compare two VW EDI releases week by week: what changed between them.")

    try:
        files = list_edi_files()
    except OSError as e:
        st.error(f"Could not open the EDI folder {EXCEL_FOLDER}: {e}")
        return
    if len(files) < 2:
        st.info("At least two EDI files are needed to compare.")
        return

    received = dict(files)
    names = [f for f, _ in files]
    c_base, c_new, c_models = st.columns([3, 3, 3], vertical_alignment="bottom")
    with c_base:
        base_name = st.selectbox("Base file", names, index=1,
                                 format_func=lambda f: file_label(f, received[f]))
    with c_new:
        new_name = st.selectbox("Compare file", names, index=0,
                                format_func=lambda f: file_label(f, received[f]))
    with c_models:
        models = st.multiselect("Car models", list(CAR_MODELS.values()),
                                default=[m for m in DEFAULT_MODELS if m in CAR_MODELS.values()])

    if base_name == new_name:
        st.warning("Pick two different files to compare.")
        return
    if not models:
        st.warning("Pick at least one car model.")
        return

    try:
        base = process_data(load_excel_file(Path(EXCEL_FOLDER) / base_name))
        new = process_data(load_excel_file(Path(EXCEL_FOLDER) / new_name))
    except Exception as e:
        st.error(f"Error loading or processing the files: {e}")
        return
    if base is None or new is None or base.empty or new.empty:
        st.error("One of the files has no usable data.")
        return

    # Only the delivery dates both files cover are compared
    lo = max(base['Date'].min().date(), new['Date'].min().date())
    hi = min(base['Date'].max().date(), new['Date'].max().date())
    if lo > hi:
        st.warning("The two files have no delivery dates in common.")
        return

    # Week range: any span of the weeks both files cover (default: all of them)
    common_weeks = []
    start = week_start(lo)
    while start <= hi:
        common_weeks.append(start)
        start += timedelta(days=7)
    c_from, c_to, c_info = st.columns([3, 3, 3], vertical_alignment="bottom")
    with c_from:
        w_from = st.selectbox("From week", common_weeks, index=0,
                              format_func=lambda s: week_label(s, lo, hi))
    with c_to:
        w_to = st.selectbox("To week", common_weeks, index=len(common_weeks) - 1,
                            format_func=lambda s: week_label(s, lo, hi))
    if w_from > w_to:
        st.warning("“From week” must not be after “To week”.")
        return
    lo, hi = max(lo, w_from), min(hi, w_to + timedelta(days=6))
    with c_info:
        n_weeks = common_weeks.index(w_to) - common_weeks.index(w_from) + 1
        st.caption(f"{n_weeks} of {len(common_weeks)} weeks selected")

    weekly = pd.DataFrame({'Base': weekly_totals(base, lo, hi, models),
                           'Compare': weekly_totals(new, lo, hi, models)}).fillna(0).reset_index()
    weekly['Change'] = weekly['Compare'] - weekly['Base']
    weekly['Week'] = weekly['Week start'].map(lambda s: week_label(s, lo, hi))

    # KPI cards
    tb, tn = weekly['Base'].sum(), weekly['Compare'].sum()
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Base total", f"{tb:,.0f}", help=base_name)
    with k2:
        kpi_card("Compare total", f"{tn:,.0f}", help=new_name)
    with k3:
        kpi_card("Change", f"{tn - tb:+,.0f}")
    with k4:
        p = pct(tn, tb)
        kpi_card("Change %", f"{p:+.1%}" if p is not None else "–")
    st.caption(f"Compared delivery dates (covered by both files): {lo:%b %d} – {hi:%b %d, %Y}. "
               "* = partial week (only some of its days are compared).")

    week_order = sorted(weekly['Week start'].unique())
    week_names = [week_label(s, lo, hi) for s in week_order]
    model_order = [m for m in CAR_MODELS.values() if m in models]

    # Line: base file vs compare file over the compared dates (the first comparison)
    c_title, c_view = st.columns([3, 1], vertical_alignment="bottom")
    with c_title:
        st.subheader("Base vs compare")
    with c_view:
        line_view = st.radio("Line view", ("Daily", "Weekly"), horizontal=True, label_visibility="collapsed")
    if line_view == "Daily":
        series = pd.DataFrame({'Base': daily_totals(base, lo, hi, models),
                               'Compare': daily_totals(new, lo, hi, models)}).fillna(0).sort_index()
        x_vals, x_hover = list(series.index), "%{x|%a %b %d, %Y}"
    else:
        series = weekly.groupby('Week start')[['Base', 'Compare']].sum().sort_index()
        x_vals, x_hover = [week_label(s, lo, hi) for s in series.index], "%{x}"
    line = go.Figure()
    for col, color, dash, name in (('Base', BASE_COLOR, 'dot', f"Base · {base_name}"),
                                   ('Compare', LINE_COLOR, 'solid', f"Compare · {new_name}")):
        line.add_trace(go.Scatter(
            x=x_vals, y=series[col], name=name, mode='lines+markers',
            line=dict(color=color, width=3, dash=dash), marker=dict(size=6),
            hovertemplate=f"<b>{col}</b> · {x_hover}<br>%{{y:,}} pcs<extra></extra>",
        ))
    line.update_layout(
        height=380, hovermode='x unified',
        yaxis=dict(title="Release quantity (pcs)", gridcolor=GRID_COLOR, tickformat=',', rangemode='tozero'),
        xaxis=dict(gridcolor=GRID_COLOR),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        margin=dict(t=40, b=10, l=10, r=10),
        font=CHART_FONT,
        plot_bgcolor='#FFFFFF', paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(line, width="stretch")

    # Heatmap: change per model × delivery week (green = more, red = less)
    st.subheader("Change by model and week")
    grid = (weekly.pivot(index='Car Model', columns='Week start', values='Change')
            .reindex(index=model_order, columns=week_order).fillna(0))
    zmax = max(abs(grid.values).max(), 1)
    heat = go.Figure(go.Heatmap(
        z=grid.values, x=week_names, y=model_order,
        colorscale=[[0, '#C0392B'], [0.5, '#FFFFFF'], [1, '#2E7D4F']], zmid=0, zmin=-zmax, zmax=zmax,
        text=[[f"{v:+,.0f}" if v else "0" for v in row] for row in grid.values],
        texttemplate="%{text}", textfont=dict(size=12),
        hovertemplate="<b>%{y}</b> · %{x}<br>Change: %{text} pcs<extra></extra>",
        xgap=2, ygap=2, colorbar=dict(title="Δ pcs", tickformat=','),
    ))
    heat.update_layout(
        height=90 + 48 * len(model_order), margin=dict(t=10, b=10, l=10, r=10),
        font=CHART_FONT,
        plot_bgcolor='#FFFFFF', paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(autorange='reversed'), xaxis=dict(side='top'),
    )
    st.plotly_chart(heat, width="stretch")

    # Weekly totals, base vs compare
    st.subheader("Weekly totals")
    totals = weekly.groupby('Week start')[['Base', 'Compare']].sum().reindex(week_order)
    bars = go.Figure()
    for col, color, name in (('Base', BASE_COLOR, f"Base · {base_name}"),
                             ('Compare', PRIMARY, f"Compare · {new_name}")):
        bars.add_trace(go.Bar(
            x=week_names, y=totals[col], name=name, marker_color=color,
            text=[f"{v:,.0f}" for v in totals[col]], textposition='outside',
            hovertemplate=f"<b>{col}</b> · %{{x}}<br>%{{y:,}} pcs<extra></extra>",
        ))
    bars.update_layout(
        barmode='group', height=440, bargap=0.25,
        yaxis=dict(title="Release quantity (pcs)", gridcolor=GRID_COLOR, tickformat=',',
                   range=[0, max(totals.max().max(), 1) * 1.12]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        margin=dict(t=40, b=10, l=10, r=10),
        font=CHART_FONT,
        plot_bgcolor='#FFFFFF', paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(bars, width="stretch")

    # Detail table + CSV
    with st.expander("Detail by week and model (table)"):
        table = weekly.assign(**{'Change %': [pct(n, b) for n, b in zip(weekly['Compare'], weekly['Base'])]})
        table['Car Model'] = pd.Categorical(table['Car Model'], categories=model_order, ordered=True)
        table = (table.sort_values(['Week start', 'Car Model'])
                 [['Week', 'Week start', 'Car Model', 'Base', 'Compare', 'Change', 'Change %']])
        st.dataframe(
            table, hide_index=True,
            column_config={
                'Week start': st.column_config.DateColumn('Week start (Sun)', format="MMM DD, YYYY"),
                'Base': st.column_config.NumberColumn(format="localized"),
                'Compare': st.column_config.NumberColumn(format="localized"),
                'Change': st.column_config.NumberColumn(format="%+d"),
                'Change %': st.column_config.NumberColumn(format="percent"),
            },
        )
        st.download_button(
            "Download CSV", table.to_csv(index=False).encode('utf-8'),
            file_name=f"EDI_compare_{Path(base_name).stem}_vs_{Path(new_name).stem}.csv",
            mime="text/csv", icon=":material/download:",
        )

    footer(received[new_name])


if __name__ == "__main__":
    main()
