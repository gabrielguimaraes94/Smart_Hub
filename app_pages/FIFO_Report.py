import streamlit as st
import pandas as pd
from datetime import datetime
import os
import glob
import plotly.graph_objects as go

from config import FIFO_FOLDER
from ui import CHART_FONT, GRID_COLOR, footer, kpi_card, page_header

AGE_BANDS = ["<30", "30-60", "60-90", "90-120", ">120"]
AGE_LABELS = {"<30": "< 30 days", "30-60": "30–60 days", "60-90": "60–90 days",
              "90-120": "90–120 days", ">120": "> 120 days"}
# Green (fresh) to red (oldest)
AGE_COLORS = {"<30": "#2E7D4F", "30-60": "#8BBF5A", "60-90": "#E9B949",
              "90-120": "#E07B39", ">120": "#C0392B"}

# ---------- Helpers ----------
def get_latest_file(directory_path):
    try:
        files = glob.glob(os.path.join(directory_path, "*"))
        if not files:
            st.error(f"No files found in: {directory_path}")
            return None
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    except PermissionError:
        st.error(f"Permission denied accessing: {directory_path}")
        return None
    except Exception as e:
        st.error(f"Error finding file: {str(e)}")
        return None


def load_data():
    try:
        directory = FIFO_FOLDER
        latest_file = get_latest_file(directory)

        if latest_file is None:
            return None, None

        try:
            df = pd.read_excel(latest_file)
        except UnicodeDecodeError:
            df = pd.read_excel(latest_file, encoding="latin1")
        except Exception as e:
            st.error(f"Error reading {latest_file}: {str(e)}")
            return None, None

        updated_ts = datetime.fromtimestamp(os.path.getmtime(latest_file))
        return df, updated_ts

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None


def preprocess(df):
    if df is None:
        return None

    df.columns = df.columns.str.strip()

    possible_date_cols = [
        "Data de criacao", "Data de criação", "DataCriacao", "DATA_CRIA",
        "Creation Date", "Date", "DATA", "Created On", "DataCriacaoEtiqueta"
    ]

    date_col = next((c for c in possible_date_cols if c in df.columns), None)

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df["idade_dias"] = (pd.Timestamp(datetime.now().date()) - df[date_col].dt.floor("D")).dt.days

    mapping = {
        "Material": ["Material", "MATNR", "material", "MATERIAL"],
        "Descricao": ["Descricao", "Descrição", "DESC", "DESCRIPTION"],
        "Lote": ["Lote", "LOT", "lote", "LOTES"],
        "Etiqueta": ["Numero da etiqueta", "Etiqueta", "LENUM", "etiqueta", "LABEL"],
        "Quantidade": ["Quantidade", "QTD", "quantidade", "AMOUNT", "QUANT"]
    }

    for std, options in mapping.items():
        for col in options:
            if col in df.columns:
                df[std] = df[col]
                break

    return df


def categorize_age(df):
    if df is None or "idade_dias" not in df.columns:
        return df

    bins = [-1, 30, 60, 90, 120, float("inf")]
    labels = ["<30", "30-60", "60-90", "90-120", ">120"]

    df["faixa_idade"] = pd.cut(df["idade_dias"], bins=bins, labels=labels)
    return df


# ---------- Main interface ----------
def main():
    page_header("FIFO Report", "Age of every label in shipping stock, to check FIFO. Data refreshes every 5 minutes.")
    live_view()


# Re-reads the file and redraws everything every 5 minutes without reloading the page
# (replaces the old <meta refresh>; the selected filters are kept).
@st.fragment(run_every="5m")
def live_view():
    df_raw, updated_ts = load_data()
    df = preprocess(df_raw)
    df = categorize_age(df)

    # -------------- Filters --------------
    col1, col2 = st.columns(2)

    material_options = df["Material"].dropna().unique().tolist() if df is not None and "Material" in df.columns else []
    lote_options = df["Lote"].dropna().unique().tolist() if df is not None and "Lote" in df.columns else []

    selected_materials = col1.multiselect("Material", material_options, placeholder="All materials",
                                          key="fifo_materials")
    selected_lotes = col2.multiselect("Lot", lote_options, placeholder="All lots", key="fifo_lots")

    # Apply filters
    if df is not None:
        df_filtered = df.copy()
        if selected_materials:
            df_filtered = df_filtered[df_filtered["Material"].isin(selected_materials)]
        if selected_lotes:
            df_filtered = df_filtered[df_filtered["Lote"].isin(selected_lotes)]
    else:
        df_filtered = None

    # ---------- KPIs ----------
    if df_filtered is not None and "faixa_idade" in df_filtered.columns:
        total = len(df_filtered)
        faixa_counts = df_filtered["faixa_idade"].value_counts().reindex(
            ["<30", "30-60", "60-90", "90-120", ">120"], fill_value=0
        )
        faixa_perc = (faixa_counts / total * 100).round(1)
    else:
        total = 0
        faixa_counts = pd.Series([0, 0, 0, 0, 0], index=["<30", "30-60", "60-90", "90-120", ">120"])
        faixa_perc = faixa_counts

    kpis = st.columns(6)
    with kpis[0]:
        kpi_card("Total labels", f"{total:,}")
    for i, band in enumerate(AGE_BANDS):
        with kpis[i + 1]:
            kpi_card(AGE_LABELS[band], f"{faixa_perc[band]}%", help=f"{faixa_counts[band]:,} labels")

    # ---------- Charts ----------
    if df_filtered is not None and len(df_filtered) > 0:
        colg1, colg2 = st.columns(2)
        names = [AGE_LABELS[b] for b in AGE_BANDS]
        colors = [AGE_COLORS[b] for b in AGE_BANDS]
        layout = dict(font=CHART_FONT,
                      plot_bgcolor='#FFFFFF', paper_bgcolor='rgba(0,0,0,0)', height=380)

        with colg1:
            st.subheader("Labels by age band")
            fig_bar = go.Figure(go.Bar(
                x=names, y=faixa_counts.values, marker_color=colors,
                text=[f"{v:,}" for v in faixa_counts.values], textposition='outside',
                hovertemplate="%{x}<br>%{y:,} labels<extra></extra>",
            ))
            fig_bar.update_layout(**layout, margin=dict(t=20, b=10, l=10, r=10),
                                  yaxis=dict(title="Labels", gridcolor=GRID_COLOR,
                                             range=[0, max(faixa_counts.max(), 1) * 1.15]))
            st.plotly_chart(fig_bar, width="stretch")

        with colg2:
            st.subheader("Share by age band")
            fig_pie = go.Figure(go.Pie(
                labels=names, values=faixa_counts.values, hole=0.55, sort=False,
                marker=dict(colors=colors, line=dict(color='#FFFFFF', width=2)),
                hovertemplate="%{label}<br>%{value:,} labels (%{percent})<extra></extra>",
            ))
            fig_pie.update_layout(**layout, margin=dict(t=20, b=10, l=10, r=10),
                                  legend=dict(traceorder='normal'))
            st.plotly_chart(fig_pie, width="stretch")

    # ---------- Detail table ----------
    st.subheader("Stock detail")

    if df_filtered is not None and len(df_filtered) > 0:
        cols_to_show = [
            "Material", "Descricao", "Lote", "Etiqueta",
            "Quantidade", "idade_dias", "faixa_idade"
        ]
        cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]

        st.dataframe(
            df_filtered[cols_to_show].sort_values("idade_dias", ascending=False),
            hide_index=True,
            column_config={
                "Descricao": "Description",
                "Lote": "Lot",
                "Etiqueta": "Label",
                "Quantidade": st.column_config.NumberColumn("Quantity", format="localized"),
                "idade_dias": st.column_config.NumberColumn("Age (days)"),
                "faixa_idade": "Age band",
            },
        )
    else:
        st.info("No data found for the selected filters.")

    footer(updated_ts)


if __name__ == "__main__":
    main()
