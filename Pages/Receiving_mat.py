import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import os
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Goods Receipt Dashboard",
    page_icon="📦",
    layout="wide"
)

# Page styling
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .title {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .filter {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Dashboard title
st.markdown('<p class="title">Goods Receipt Dashboard</p>', unsafe_allow_html=True)

# Function to load data
@st.cache_data(ttl=timedelta(hours=1))
def load_data():
    # Path to files
    folder_path = r'\\ch2-file2.us.gestamp.com\PowerBI\DATA\GC2\Receiving_materials'
    
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

# Check if data was loaded successfully
if df.empty:
    st.error("Could not load data. Check network connections and folder access permissions.")
    st.stop()

# Display last update information
st.info(f"Data updated on: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# Sidebar with filters
st.sidebar.markdown('<p class="subtitle">Filters</p>', unsafe_allow_html=True)

# Date filter
min_date = df['Delivery_Date'].min().date()
max_date = df['Delivery_Date'].max().date()

with st.sidebar.container():
    st.markdown('<div class="filter">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    st.markdown('</div>', unsafe_allow_html=True)

# Warehouse filter
warehouses = sorted(df['Warehouse'].unique())
with st.sidebar.container():
    st.markdown('<div class="filter">', unsafe_allow_html=True)
    selected_warehouses = st.multiselect("Warehouse", warehouses, default=warehouses)
    st.markdown('</div>', unsafe_allow_html=True)

# Supplier filter
suppliers = sorted(df['Supplier_Name'].unique())
with st.sidebar.container():
    st.markdown('<div class="filter">', unsafe_allow_html=True)
    selected_suppliers = st.multiselect("Supplier", suppliers)
    st.markdown('</div>', unsafe_allow_html=True)

# Material filter
materials = sorted(df['Material'].unique())
with st.sidebar.container():
    st.markdown('<div class="filter">', unsafe_allow_html=True)
    selected_materials = st.multiselect("Material", materials)
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.metric("Total Deliveries", f"{total_deliveries}")
    
    with col2:
        st.metric("Total Materials", f"{total_materials}")
    
    with col3:
        st.metric("Total Quantity", f"{total_quantity:,.2f}")
    
    with col4:
        st.metric("Total Suppliers", f"{total_suppliers}")
    
    # Layout with two columns for charts
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown('<p class="subtitle">Deliveries by Supplier</p>', unsafe_allow_html=True)
        
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
        
        # Pie chart
        fig_pie = px.pie(
            deliveries_by_supplier, 
            names='Supplier_Name', 
            values='Total_Deliveries',
            title=f'Delivery Distribution by Supplier ({total_deliveries} deliveries)',
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, width="stretch")
    
    with col_right:
        st.markdown('<p class="subtitle">Deliveries Over Time</p>', unsafe_allow_html=True)
        
        # Group by date and count unique deliveries
        deliveries_by_day = df_filtered.groupby(df_filtered['Delivery_Date'].dt.date)['Delivery_ID'].nunique().reset_index()
        deliveries_by_day = deliveries_by_day.rename(columns={'Delivery_ID': 'Total_Deliveries'})
        
        # Line chart
        fig_line = px.line(
            deliveries_by_day,
            x='Delivery_Date',
            y='Total_Deliveries',
            title='Delivery Evolution Over Time',
            markers=True
        )
        st.plotly_chart(fig_line, width="stretch")
    
    # Delivery details table
    st.markdown('<p class="subtitle">Delivery Details</p>', unsafe_allow_html=True)
    
    # Create a summary table by delivery
    deliveries_summary = df_filtered.groupby(['Delivery_ID', 'Invoice_Number', 'Supplier_Code', 'Supplier_Name', 'Delivery_Date', 'Warehouse']).agg({
        'Material': 'count',
        'Quantity': 'sum'
    }).reset_index()
    
    deliveries_summary = deliveries_summary.rename(columns={
        'Material': 'Material_Count',
        'Quantity': 'Total_Quantity'
    })
    
    # Format the date
    deliveries_summary['Delivery_Date'] = deliveries_summary['Delivery_Date'].dt.strftime('%d/%m/%Y')
    
    # Sort by delivery date (most recent first)
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
    
    st.dataframe(deliveries_summary_display, width="stretch")
    
    # Option to download filtered data
    st.download_button(
        label="Download Filtered Data",
        data=df_filtered.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig'),
        file_name=f"material_receiving_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )
    
    # Material details
    with st.expander("View Material Details"):
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
        st.dataframe(materials_summary, width="stretch")
        
        # Top 10 materials chart
        top_materials = materials_summary.head(10)
        
        fig_top_materials = px.bar(
            top_materials,
            x='Material',
            y='Delivery_Count',
            title='Top 10 Materials by Number of Deliveries',
            color='Quantity',
            labels={'Delivery_Count': 'Number of Deliveries', 'Quantity': 'Total Quantity'}
        )
        
        st.plotly_chart(fig_top_materials, width="stretch")

# Additional information at the end of the page
st.markdown("""
---
### Information
* Data is loaded from Excel files in the folder `\\ch2-file2.us.gestamp.com\PowerBI\DATA\GC2\Receiving_materials\`
* Each Invoice Number is considered a unique delivery
* To refresh the data, reload the page
""")