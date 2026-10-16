import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import glob
import os
from datetime import datetime, timedelta

from config import RECEIVING_FOLDER
from ui import PRIMARY, footer, kpi_card, page_header

# Supplier donut colors: Gestamp blues first, then neutral tones; "Others" in grey
SUPPLIER_COLORS = ['#20416C', '#3F7CC4', '#93B9E6', '#D9701E', '#F2B27A',
                   '#2E7D4F', '#8BBF5A', '#6B7A8F', '#B8C2CF', '#E9B949']
OTHERS_COLOR = '#D9DEE5'
CHART_LAYOUT = dict(font=dict(family='Inter, sans-serif', color='#1F2933'),
                    plot_bgcolor='#FFFFFF', paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=10, l=10, r=10))

page_header("Goods Receipt", "Material receipts by supplier, warehouse and date. Each invoice number counts as one delivery.")

# Function to load data
@st.cache_data(ttl=timedelta(hours=1))
def load_data():
    # Path to files
    folder_path = RECEIVING_FOLDER

    # Check if folder exists and is accessible
    if not os.path.exists(folder_path):
        st.error(f"Unable to access folder: {folder_path}")
        return pd.DataFrame()

    # Find all Excel files in the folder
    files = glob.glob(os.path.join(folder_path, '*.xlsx'))

    if not files:
        st.warning("No Excel files found in the folder.")
        return pd.DataFrame()

    # List to store dataframes
    dfs = []

    # Load each file
    for file in files:
        try:
            # Load only necessary columns
            df_temp = pd.read_excel(
                file,
                usecols=[3, 4, 5, 6, 8, 10, 11],  # D, E, F, G, I, K, L
                names=['Warehouse', 'Delivery_Date', 'Material', 'Quantity', 'Invoice_Number', 'Supplier_Code', 'Supplier_Name']
            )

            # Add filename as a column for traceability
            df_temp['Source_File'] = os.path.basename(file)

            # Add to list
            dfs.append(df_temp)
        except Exception as e:
            st.error(f"Error loading file {os.path.basename(file)}: {e}")

    # Check if any dataframe was loaded
    if not dfs:
        st.error("Could not load any files.")
        return pd.DataFrame()

    # Concatenate all dataframes
    df_final = pd.concat(dfs, ignore_index=True)

    # Convert date column to datetime
    df_final['Delivery_Date'] = pd.to_datetime(df_final['Delivery_Date'], errors='coerce')

    # Remove rows with invalid data
    df_final = df_final.dropna(subset=['Invoice_Number', 'Material', 'Delivery_Date'])

    # Creating a unique ID for each delivery
    df_final['Delivery_ID'] = df_final['Invoice_Number']

    return df_final

# Load data
with st.spinner('Loading data...'):
    df = load_data()
loaded_at = datetime.now()

# Check if data was loaded successfully
if df.empty:
    st.error("Could not load data. Check network connections and folder access permissions.")
    st.stop()

# Filters in one row: start | end | warehouse | supplier | material
min_date = df['Delivery_Date'].min().date()
max_date = df['Delivery_Date'].max().date()
warehouses = sorted(df['Warehouse'].unique())
suppliers = sorted(df['Supplier_Name'].unique())
materials = sorted(df['Material'].unique())

c_start, c_end, c_wh, c_sup, c_mat = st.columns([1.2, 1.2, 2, 2.5, 2.5])
with c_start:
    start_date = st.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
with c_end:
    end_date = st.date_input("End date", max_date, min_value=min_date, max_value=max_date)
with c_wh:
    selected_warehouses = st.multiselect("Warehouse", warehouses, default=warehouses)
with c_sup:
    selected_suppliers = st.multiselect("Supplier", suppliers, placeholder="All suppliers")
with c_mat:
    selected_materials = st.multiselect("Material", materials, placeholder="All materials")

# Apply filters
df_filtered = df.copy()

# Date filter
df_filtered = df_filtered[(df_filtered['Delivery_Date'].dt.date >= start_date) &
                          (df_filtered['Delivery_Date'].dt.date <= end_date)]

# Warehouse filter
if selected_warehouses:
    df_filtered = df_filtered[df_filtered['Warehouse'].isin(selected_warehouses)]

# Supplier filter
if selected_suppliers:
    df_filtered = df_filtered[df_filtered['Supplier_Name'].isin(selected_suppliers)]

# Material filter
if selected_materials:
    df_filtered = df_filtered[df_filtered['Material'].isin(selected_materials)]

# Main dashboard
if df_filtered.empty:
    st.warning("No data found for the selected filters.")
else:
    # Counts for KPIs
    total_deliveries = df_filtered['Delivery_ID'].nunique()
    total_materials = df_filtered['Material'].nunique()
    total_quantity = df_filtered['Quantity'].sum()
    total_suppliers = df_filtered['Supplier_Name'].nunique()

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Deliveries", f"{total_deliveries:,}", help="Unique invoice numbers")
    with col2:
        kpi_card("Materials", f"{total_materials:,}")
    with col3:
        kpi_card("Quantity", f"{total_quantity:,.0f}")
    with col4:
        kpi_card("Suppliers", f"{total_suppliers:,}")

    # Layout with two columns for charts
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Deliveries by supplier")

        # Data for pie chart - Deliveries by supplier
        deliveries_by_supplier = df_filtered.groupby('Supplier_Name')['Delivery_ID'].nunique().reset_index()
        deliveries_by_supplier = deliveries_by_supplier.rename(columns={'Delivery_ID': 'Total_Deliveries'})
        deliveries_by_supplier = deliveries_by_supplier.sort_values('Total_Deliveries', ascending=False)

        # Get top 10 suppliers and group the rest as "Others"
        if len(deliveries_by_supplier) > 10:
            top_suppliers = deliveries_by_supplier.head(10)
            others = pd.DataFrame({
                'Supplier_Name': ['Others'],
                'Total_Deliveries': [deliveries_by_supplier.iloc[10:]['Total_Deliveries'].sum()]
            })
            deliveries_by_supplier = pd.concat([top_suppliers, others])

        # Donut chart
        names = deliveries_by_supplier['Supplier_Name'].tolist()
        colors = [OTHERS_COLOR if n == 'Others' else SUPPLIER_COLORS[i % len(SUPPLIER_COLORS)]
                  for i, n in enumerate(names)]
        fig_pie = go.Figure(go.Pie(
            labels=names, values=deliveries_by_supplier['Total_Deliveries'], hole=0.55, sort=False,
            marker=dict(colors=colors, line=dict(color='#FFFFFF', width=2)),
            textposition='inside', textinfo='percent',
            hovertemplate="%{label}<br>%{value:,} deliveries (%{percent})<extra></extra>",
        ))
        fig_pie.update_layout(**CHART_LAYOUT, height=380,
                              annotations=[dict(text=f"<b>{total_deliveries:,}</b><br>deliveries",
                                                showarrow=False, font=dict(size=15))])
        st.plotly_chart(fig_pie, width="stretch")

    with col_right:
        st.subheader("Deliveries per day")

        # Group by date and count unique deliveries
        deliveries_by_day = df_filtered.groupby(df_filtered['Delivery_Date'].dt.date)['Delivery_ID'].nunique().reset_index()
        deliveries_by_day = deliveries_by_day.rename(columns={'Delivery_ID': 'Total_Deliveries'})

        # Line chart
        fig_line = go.Figure(go.Scatter(
            x=deliveries_by_day['Delivery_Date'], y=deliveries_by_day['Total_Deliveries'],
            mode='lines+markers', line=dict(color=PRIMARY, width=2), marker=dict(size=6),
            fill='tozeroy', fillcolor='rgba(32, 65, 108, 0.08)',
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,} deliveries<extra></extra>",
        ))
        fig_line.update_layout(**CHART_LAYOUT, height=380,
                               yaxis=dict(title="Deliveries", gridcolor='#E6EAF0', rangemode='tozero'),
                               xaxis=dict(gridcolor='#F1F3F5'))
        st.plotly_chart(fig_line, width="stretch")

    # Delivery details table
    st.subheader("Delivery details")

    # Create a summary table by delivery
    deliveries_summary = df_filtered.groupby(['Delivery_ID', 'Invoice_Number', 'Supplier_Code', 'Supplier_Name', 'Delivery_Date', 'Warehouse']).agg({
        'Material': 'count',
        'Quantity': 'sum'
    }).reset_index()

    deliveries_summary = deliveries_summary.rename(columns={
        'Material': 'Material_Count',
        'Quantity': 'Total_Quantity'
    })

    # Sort by delivery date (most recent first); the date stays a real date so the order is chronological
    deliveries_summary = deliveries_summary.sort_values('Delivery_Date', ascending=False)

    # Select and rename columns for display
    deliveries_summary_display = deliveries_summary[[
        'Delivery_Date',
        'Delivery_ID',
        'Supplier_Name',
        'Warehouse',
        'Material_Count',
        'Total_Quantity'
    ]].rename(columns={
        'Delivery_Date': 'Date',
        'Delivery_ID': 'Delivery Number',
        'Supplier_Name': 'Supplier',
        'Material_Count': 'Material Qty',
        'Total_Quantity': 'Total Quantity'
    })

    st.dataframe(
        deliveries_summary_display, hide_index=True,
        column_config={
            'Date': st.column_config.DateColumn(format="MMM DD, YYYY"),
            'Delivery Number': st.column_config.TextColumn(),
            'Total Quantity': st.column_config.NumberColumn(format="localized"),
        },
    )

    # Option to download filtered data
    st.download_button(
        label="Download filtered data (CSV)",
        data=df_filtered.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig'),
        file_name=f"material_receiving_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        icon=":material/download:",
    )

    # Material details
    with st.expander("Material details"):
        # Group by material
        materials_summary = df_filtered.groupby('Material').agg({
            'Quantity': 'sum',
            'Delivery_ID': 'nunique'
        }).reset_index()

        materials_summary = materials_summary.rename(columns={
            'Delivery_ID': 'Delivery_Count'
        })

        materials_summary = materials_summary.sort_values('Delivery_Count', ascending=False)

        # Display materials table
        st.dataframe(
            materials_summary, hide_index=True,
            column_config={
                'Quantity': st.column_config.NumberColumn("Total quantity", format="localized"),
                'Delivery_Count': st.column_config.NumberColumn("Deliveries"),
            },
        )

        # Top 10 materials chart
        top_materials = materials_summary.head(10)

        st.markdown("**Top 10 materials by number of deliveries**")
        fig_top_materials = go.Figure(go.Bar(
            x=top_materials['Material'], y=top_materials['Delivery_Count'],
            marker=dict(color=top_materials['Quantity'], colorscale=[[0, '#93B9E6'], [1, PRIMARY]],
                        colorbar=dict(title="Total qty", tickformat=',')),
            text=top_materials['Delivery_Count'], textposition='outside',
            hovertemplate="%{x}<br>%{y} deliveries<br>%{marker.color:,} pcs<extra></extra>",
        ))
        fig_top_materials.update_layout(**CHART_LAYOUT, height=400,
                                        yaxis=dict(title="Number of deliveries", gridcolor='#E6EAF0',
                                                   range=[0, max(top_materials['Delivery_Count'].max(), 1) * 1.15]))
        st.plotly_chart(fig_top_materials, width="stretch")

st.caption("Data comes from every Excel file in the goods receipt folder and is cached for 1 hour. "
           "Each invoice number counts as one delivery.")
footer(loaded_at)
