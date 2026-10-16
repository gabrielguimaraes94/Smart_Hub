import streamlit as st
import pandas as pd
from datetime import datetime
import os
import glob
import plotly.express as px

# ---------- Configuração da Página ----------
st.set_page_config(
    page_title="Controle FIFO - Shipping",
    layout="wide"
)

# ---------- Funções auxiliares ----------
def get_latest_file(directory_path):
    try:
        files = glob.glob(os.path.join(directory_path, "*"))
        if not files:
            st.error(f"Nenhum arquivo encontrado em: {directory_path}")
            return None
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    except PermissionError:
        st.error(f"Permissão negada ao acessar: {directory_path}")
        return None
    except Exception as e:
        st.error(f"Erro buscando arquivo: {str(e)}")
        return None


def load_data():
    try:
        directory = r"\\ch2-python\powerBI\Data\GC2\FIFO"
        latest_file = get_latest_file(directory)

        if latest_file is None:
            return None, None

        try:
            df = pd.read_excel(latest_file)
        except UnicodeDecodeError:
            df = pd.read_excel(latest_file, encoding="latin1")
        except Exception as e:
            st.error(f"Erro ao ler {latest_file}: {str(e)}")
            return None, None

        updated_ts = datetime.fromtimestamp(os.path.getmtime(latest_file))
        return df, updated_ts

    except Exception as e:
        st.error(f"Erro geral ao carregar dados: {str(e)}")
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


# ---------- Interface principal ----------
def main():
    st.title("📦 Controle FIFO de Materiais - Shipping")

    df_raw, updated_ts = load_data()
    df = preprocess(df_raw)
    df = categorize_age(df)

    # -------------- Filtros --------------
    with st.expander("🔎 Filtros"):
        col1, col2 = st.columns(2)

        material_options = df["Material"].dropna().unique().tolist() if df is not None and "Material" in df.columns else []
        lote_options = df["Lote"].dropna().unique().tolist() if df is not None and "Lote" in df.columns else []

        selected_materials = col1.multiselect("Material", material_options)
        selected_lotes = col2.multiselect("Lote", lote_options)

    # Aplicar filtros
    if df is not None:
        df_filtered = df.copy()
        if selected_materials:
            df_filtered = df_filtered[df_filtered["Material"].isin(selected_materials)]
        if selected_lotes:
            df_filtered = df_filtered[df_filtered["Lote"].isin(selected_lotes)]
    else:
        df_filtered = None

    # ---------- KPIs ----------
    st.markdown("## 📊 Indicadores FIFO")

    kpi1, kpi2 = st.columns([3, 2])

    with kpi2:
        if updated_ts:
            st.success(f"Última atualização: {updated_ts.strftime('%d/%m/%Y %H:%M:%S')}")

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
    kpis[0].metric("Total etiquetas", total)

    labels = ["<30", "30-60", "60-90", "90-120", ">120"]
    for i, l in enumerate(labels):
        kpis[i + 1].metric(l, f"{faixa_perc[l]}%")

    # ---------- Gráficos ----------
    if df_filtered is not None and len(df_filtered) > 0:
        st.markdown("## 📈 Gráficos")

        colg1, colg2 = st.columns(2)

        # Gráfico de barras
        fig_bar = px.bar(
            faixa_counts,
            title="Distribuição por Faixa de Idade",
            labels={"value": "Quantidade", "index": "Faixa"},
            text=faixa_counts,
        )
        colg1.plotly_chart(fig_bar, width="stretch")

        # Gráfico de pizza
        fig_pie = px.pie(
            values=faixa_counts,
            names=faixa_counts.index,
            title="Percentual por Faixa de Idade",
        )
        colg2.plotly_chart(fig_pie, width="stretch")

    # ---------- Tabela Detalhada ----------
    st.markdown("## 📋 Detalhes do Estoque")

    if df_filtered is not None and len(df_filtered) > 0:
        cols_to_show = [
            "Material", "Descricao", "Lote", "Etiqueta",
            "Quantidade", "idade_dias", "faixa_idade"
        ]
        cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]

        st.dataframe(df_filtered[cols_to_show].sort_values("idade_dias", ascending=False), width="content")
    else:
        st.info("Nenhum dado encontrado com os filtros selecionados.")

    # ---------- Auto refresh ----------
    st.markdown(
        """
        <meta http-equiv="refresh" content="300">
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
