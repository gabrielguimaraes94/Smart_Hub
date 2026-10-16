import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from pathlib import Path

from config import EDI_FOLDER
from datetime import datetime, timedelta

from ui import footer, fullscreen_button, kpi_card, page_header, tv_mode_button

# Path to the folder with Excel files
EXCEL_FOLDER = EDI_FOLDER

# Dictionary to map specific parts to car models
CAR_MODELS = {
    '11K 809 605': 'MEB',
    '3CM 809 605': 'Coupe',
    '3CN 809 605 C': 'Atlas',
    '3CR 809 605': 'Atlas NF',
    '3CS 809 605': 'Coupe NF'
}

# Color scheme for each car model: MEB in Gestamp blue, Atlas family in blues, Coupe family in oranges
COLOR_SCHEME = {
    'MEB': '#20416C',
    'Atlas': '#3F7CC4',
    'Atlas NF': '#93B9E6',
    'Coupe': '#D9701E',
    'Coupe NF': '#F2B27A'
}

def load_excel_file(file_path):
    return pd.read_excel(file_path, sheet_name='PivotData')

def map_part_to_model(part):
    for key, value in CAR_MODELS.items():
        if key in part:
            return value
    return None

def process_data(df):
    if 'Date From' not in df.columns:
        st.error("'Date From' column not found in the Excel file.")
        st.write("Available columns:", df.columns)
        return None

    try:
        df['Date'] = pd.to_datetime(df['Date From'], errors='coerce')
        df = df.dropna(subset=['Date'])
    except Exception as e:
        st.error(f"Error converting dates: {str(e)}")
        st.write("First few rows of 'Date From' column:", df['Date From'].head())
        return None

    df['Car Model'] = df['Part'].apply(map_part_to_model)
    df = df[df['Car Model'].notnull()]
    
    # Calculate ISO year and week
    df['ISO_Year'], df['ISO_Week'], _ = zip(*df['Date'].map(lambda x: x.isocalendar()))
    
    return df

def get_week_number(date):
    """
    Calcula o número da semana começando no domingo.
    Para o padrão americano, a semana 1 é a primeira semana com um domingo no ano.
    
    Args:
        date: datetime.date ou datetime.datetime - a data para calcular a semana
    Returns:
        int: número da semana
    """
    # Converter para datetime se for date
    if isinstance(date, datetime):
        date = date.date()
    
    # Garantir que first_day é um date
    first_day = datetime(date.year, 1, 1).date()
    
    # Ajustar para o primeiro domingo do ano
    if first_day.weekday() != 6:  # Se não é domingo
        first_day = first_day - timedelta(days=first_day.weekday() + 1)
    
    days_diff = (date - first_day).days
    return (days_diff // 7) + 1

def create_production_chart(df, view_type='daily', start_date=None, end_date=None):
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    
    # Criar uma cópia explícita do DataFrame
    working_df = df.copy()
    
    # Aplicar o filtro de datas
    mask = (working_df['Date'].dt.date >= start_date) & (working_df['Date'].dt.date <= end_date)
    working_df = working_df.loc[mask].copy()
    
    if view_type == 'weekly':
        # Calcular a semana usando nossa função personalizada
        working_df.loc[:, 'Week'] = working_df['Date'].apply(lambda x: get_week_number(x))
        working_df.loc[:, 'Year'] = working_df['Date'].dt.year
        
        # Criar o chart_data
        chart_data = (working_df.groupby(['Year', 'Week', 'Car Model'])['Release Qty']
                     .sum()
                     .reset_index())
        
        # Criar a data representativa para cada semana (começando no domingo)
        def get_week_start_date(row):
            # Garantir que trabalhamos com date
            first_day = datetime(row['Year'], 1, 1).date()
            if first_day.weekday() != 6:  # Se não é domingo
                first_day = first_day - timedelta(days=first_day.weekday() + 1)
            days_to_add = (row['Week'] - 1) * 7
            return datetime.combine(first_day + timedelta(days=days_to_add), datetime.min.time())
        
        chart_data['DateForSort'] = chart_data.apply(get_week_start_date, axis=1)
        
        x_axis = 'DateForSort'
        x_title = 'Week'
    else:
        chart_data = (working_df.groupby(['Date', 'Car Model'])['Release Qty']
                     .sum()
                     .reset_index())
        x_axis = 'Date'
        x_title = 'Date'
    
    fig = go.Figure()

    for model in CAR_MODELS.values():
        model_data = chart_data[chart_data['Car Model'] == model]
        fig.add_trace(go.Bar(
            x=model_data[x_axis],
            y=model_data['Release Qty'],
            name=model,
            marker_color=COLOR_SCHEME.get(model, 'rgb(204, 204, 204)'),
            text=model_data['Release Qty'],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='#1F2933' if model in ('Atlas NF', 'Coupe NF') else 'white', size=12),
            hovertemplate=f"<b>{model}</b><br>%{{x}}<br>%{{y:,}} pcs<extra></extra>",
        ))

    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title="Release quantity (pcs)",
        height=560,
        barmode='stack',
        bargap=0.25,
        yaxis=dict(rangemode='nonnegative', gridcolor='#E6EAF0', tickformat=','),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
            font=dict(size=14), itemsizing='constant', title_text='', traceorder='normal',
        ),
        uniformtext=dict(minsize=10, mode='hide'),
        margin=dict(t=40, b=10, l=10, r=10),
        font=dict(family='Inter, sans-serif', color='#1F2933'),
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    if view_type == 'weekly':
        all_weeks = sorted(chart_data['DateForSort'].unique())
        fig.update_xaxes(
            tickmode='array',
            tickvals=all_weeks,
            ticktext=[f"{d.year}-W{chart_data[chart_data['DateForSort'] == d]['Week'].iloc[0]:02d}" for d in all_weeks],
            tickangle=45
        )
    else:
        all_dates = sorted(chart_data['Date'].unique())
        fig.update_xaxes(
            tickmode='array',
            tickvals=all_dates,
            ticktext=[d.strftime('%Y-%m-%d') for d in all_dates],
            tickangle=45,
            tickformat='%Y-%m-%d'
        )

    return fig

def get_file_creation_date(file_path):
    """
    Retorna a data de criação do arquivo
    """
    return os.path.getctime(file_path)

def main():
    h, b, m = st.columns([6, 1, 1], vertical_alignment="bottom")
    with h:
        page_header("EDI VW View", "VW customer releases (EDI) by car model.")
    with b:
        fullscreen_button()
    with m:
        tv_mode_button()

    excel_files = [f for f in os.listdir(EXCEL_FOLDER) if f.endswith('.xlsx')]
    if not excel_files:
        st.error(f"No Excel files found in the folder: {EXCEL_FOLDER}")
        return

    # Ordena os arquivos pela data de criação (do mais novo para o mais antigo)
    excel_files_with_dates = [(f, get_file_creation_date(os.path.join(EXCEL_FOLDER, f))) for f in excel_files]
    excel_files_with_dates.sort(key=lambda x: x[1], reverse=True)  # Ordena pelo timestamp (mais recente primeiro)
    excel_files = [f[0] for f in excel_files_with_dates]  # Extrai apenas os nomes dos arquivos ordenados
    
    # Controls in one row: file | view | start | end
    col1, col_view, col_start, col_end = st.columns([3, 2, 2, 2], vertical_alignment="bottom")
    with col1:
        selected_file = st.selectbox("EDI file", excel_files, index=0)
    with col_view:
        view_type = st.radio("View", ('Daily', 'Weekly'), horizontal=True)
    
    if selected_file:
        file_path = Path(EXCEL_FOLDER) / selected_file
        try:
            df = load_excel_file(file_path)
            df = process_data(df)
            if df is None:
                return
        except Exception as e:
            st.error(f"Error loading or processing the file: {str(e)}")
            return

        # Get min and max dates from the data
        min_date = df['Date'].min().date()
        max_date = df['Date'].max().date()

        # Set default end date to one month after start date
        default_end_date = min(max_date, min_date + timedelta(days=30))

        # Date range selection
        with col_start:
            start_date = st.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
        with col_end:
            end_date = st.date_input("End date", default_end_date, min_value=min_date, max_value=max_date)

        if start_date > end_date:
            st.error("Error: End date must fall after start date.")
            return

        received = datetime.fromtimestamp(get_file_creation_date(file_path))
        st.caption(f"Showing {start_date:%b %d, %Y} – {end_date:%b %d, %Y} · "
                   f"file {selected_file}, received {received:%b %d, %Y %H:%M}")

        total_production = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)].groupby('Car Model')['Release Qty'].sum().sort_values(ascending=False)

        # KPI cards: the same totals as the table below, plus their sum
        kpi_cols = st.columns(1 + len(total_production))
        with kpi_cols[0]:
            kpi_card("Total releases", f"{total_production.sum():,.0f}")
        for col, (model, qty) in zip(kpi_cols[1:], total_production.items()):
            with col:
                kpi_card(model, f"{qty:,.0f}")

        chart = create_production_chart(df, view_type.lower(), start_date, end_date)
        st.plotly_chart(chart, width="stretch")

        with st.expander("Total production by model (table)"):
            # Create a DataFrame for better formatting
            total_production_df = pd.DataFrame({'Car Model': total_production.index, 'Total Production': total_production.values})

            # Display the DataFrame as a styled table
            st.dataframe(total_production_df.style
                         .format({'Total Production': '{:,.0f}'})
                         .set_properties(**{'font-size': '16px'}),
                         width=600, hide_index=True)

        footer(received)

if __name__ == "__main__":
    main()