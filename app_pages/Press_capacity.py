import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page configuration - must be the first Streamlit call
st.set_page_config(
    layout="wide",
    page_title="Press Capacity Calculation",
    page_icon="🏋🏻‍♀️"
)

# Custom CSS to adjust font sizes
st.markdown("""
<style>
    body {
        font-size: 18px;
    }
    .stSelectbox, .stRadio, .stDateInput {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# Paths to folders with Excel files and master data
EXCEL_FOLDER = r"\\CH2-PYTHON\PowerBI\DATA\Demand\EDI_Converted\sent_email"
MASTER_DATA_FILE = r"\\CH2-PYTHON\PowerBI\DATA\Demand\EDI_Converted\MasterData\Masterdata.xlsx"

# Dictionary to map specific parts to car models
CAR_MODELS = {
    '11K 809 605': 'MEB',
    '3CM 809 605': 'Coupe',
    '3CN 809 605 C': 'Atlas',
    '3CR 809 605': 'Atlas NF',
    '3CS 809 605': 'Coupe NF'
}

def load_excel_file(file_path):
    """Loads the specified Excel file."""
    return pd.read_excel(file_path, sheet_name='PivotData')

def load_master_data():
    """Loads master data from Excel file."""
    try:
        master_df = pd.read_excel(MASTER_DATA_FILE)
        return master_df
    except Exception as e:
        st.error(f"Error loading master data file: {str(e)}")
        return None

def map_part_to_model(part):
    """Maps the part number to the corresponding car model."""
    for key, value in CAR_MODELS.items():
        if key in part:
            return value
    return None

def process_data(df):
    """Processes data from the DataFrame."""
    if 'Date From' not in df.columns:
        st.error("'Date From' column not found in Excel file.")
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
    
    return df

def get_week_number(date):
    """
    Calculates the week number starting on Sunday.
    For American standard, week 1 is the first week with a Sunday in the year.
    
    Args:
        date: datetime.date or datetime.datetime - the date to calculate the week
    Returns:
        int: week number
    """
    # Convert to datetime if date
    if isinstance(date, datetime):
        date = date.date()
    
    # Ensure first_day is a date
    first_day = datetime(date.year, 1, 1).date()
    
    # Adjust to the first Sunday of the year
    if first_day.weekday() != 6:  # If not Sunday
        first_day = first_day - timedelta(days=first_day.weekday() + 1)
    
    days_diff = (date - first_day).days
    return (days_diff // 7) + 1

def get_all_year_week_combinations(df):
    """
    Get all year-week combinations from the dataframe sorted chronologically.
    
    Args:
        df: DataFrame with Year and Week columns
    
    Returns:
        List of tuples with (Year, Week) combinations
    """
    # Create a list of tuples (Year, Week) from unique combinations in the dataframe
    year_week_combinations = df[['Year', 'Week']].drop_duplicates()
    
    # Sort by Year and Week
    year_week_combinations = year_week_combinations.sort_values(by=['Year', 'Week'])
    
    # Convert to list of tuples
    return [tuple(x) for x in year_week_combinations.values]

def calculate_volume(weekly_data, master_data):
    """
    Calculates the total volume by model and week based on master data.
    
    Args:
        weekly_data: DataFrame with weekly data by model (Car Model and Release Qty)
        master_data: DataFrame with master data (PROJECT, PRESS, REF STAMP PN and % columns)
        
    Returns:
        DataFrame with calculated volume by model, week and press
    """
    # Check if the necessary columns exist in the master data
    required_columns = ['PROJECT', '%', 'PRESS', 'REF STAMP PN']
    missing_columns = [col for col in required_columns if col not in master_data.columns]
    if missing_columns:
        st.error(f"Required columns not found in master data file: {missing_columns}")
        st.write("Available columns:", master_data.columns)
        return None
    
    # Create a dictionary to map car model to project
    model_to_project = {
        'MEB': 'MEB',
        'Coupe': 'Coupe',
        'Coupe NF': 'Coupe NF',
        'Atlas': 'Atlas',
        'Atlas NF': 'Atlas NF'
    }
    
    # Create a DataFrame to store results
    results = []
    
    # Process standard projects
    for _, row in weekly_data.iterrows():
        car_model = row['Car Model']
        release_qty = row['Release Qty']
        year = row['Year']
        week = row['Week']
        
        # Get the project corresponding to the car model
        project = model_to_project.get(car_model)
        
        if project:
            # Filter the master_data rows for the specific project
            project_data = master_data[master_data['PROJECT'] == project]
            
            if not project_data.empty:
                # Calculate volume for each project row
                for _, proj_row in project_data.iterrows():
                    percentage = proj_row['%']
                    press = proj_row['PRESS']
                    ref_stamp_pn = proj_row['REF STAMP PN']
                    
                    # Calculate volume and round up to the nearest integer
                    volume = np.ceil(release_qty * percentage)
                    
                    # Add the results
                    results.append({
                        'Year': year,
                        'Week': week,
                        'Car Model': car_model,
                        'PRESS': press,
                        'REF STAMP PN': ref_stamp_pn,
                        'Release Qty': release_qty,
                        'Volume': volume
                    })
    
    # Process MQB project separately
    # Filter rows for the MQB project in the master file
    mqb_data = master_data[master_data['PROJECT'] == 'MQB']
    
    if not mqb_data.empty:
        # Group data by week to get the total of Atlas and Coupe
        weekly_data_combined = weekly_data.copy()
        
        # Filter only Atlas and Coupe
        atlas_coupe_data = weekly_data_combined[weekly_data_combined['Car Model'].isin(['Atlas', 'Coupe'])]
        
        # Group by week to get the combined total by week
        combined_by_week = atlas_coupe_data.groupby(['Year', 'Week'])['Release Qty'].sum().reset_index()
        
        # For each year-week combination, calculate MQB volume
        for _, row in combined_by_week.iterrows():
            year = row['Year']
            week = row['Week']
            total_qty = row['Release Qty']  # Sum of Atlas + Coupe
            
            # For each MQB row in the master file
            for _, mqb_row in mqb_data.iterrows():
                percentage = mqb_row['%']
                press = mqb_row['PRESS']
                ref_stamp_pn = mqb_row['REF STAMP PN']
                
                # Calculate volume and round up
                volume = np.ceil(total_qty * percentage)
                
                # Add the results
                results.append({
                    'Year': year,
                    'Week': week,
                    'Car Model': 'MQB',
                    'PRESS': press,
                    'REF STAMP PN': ref_stamp_pn,
                    'Release Qty': total_qty,
                    'Volume': volume
                })
    
    # Convert to DataFrame
    volume_df = pd.DataFrame(results)
    
    # Create PRESS3 by combining PRESS1 and PRESS2
    # First, get all unique year-week combinations
    year_week_combinations = volume_df[['Year', 'Week']].drop_duplicates().reset_index(drop=True)
    
    # For each year-week, create PRESS3 entries by combining PRESS1 and PRESS2
    for _, yw_row in year_week_combinations.iterrows():
        year = yw_row['Year']
        week = yw_row['Week']
        
        # Get all car models for this year-week
        car_models = volume_df[(volume_df['Year'] == year) & 
                               (volume_df['Week'] == week)]['Car Model'].unique()
        
        for car_model in car_models:
            # Get PRESS1 and PRESS2 volumes for this car model and year-week
            press1_data = volume_df[(volume_df['Year'] == year) & 
                                   (volume_df['Week'] == week) & 
                                   (volume_df['Car Model'] == car_model) & 
                                   (volume_df['PRESS'] == 'PRESS1')]
            
            press2_data = volume_df[(volume_df['Year'] == year) & 
                                   (volume_df['Week'] == week) & 
                                   (volume_df['Car Model'] == car_model) & 
                                   (volume_df['PRESS'] == 'PRESS2')]
            
            # Only create PRESS3 if both PRESS1 and PRESS2 exist for this car model
            if not press1_data.empty and not press2_data.empty:
                # Sum volumes from PRESS1 and PRESS2
                press1_volume = press1_data['Volume'].sum()
                press2_volume = press2_data['Volume'].sum()
                release_qty = press1_data['Release Qty'].iloc[0]  # Same release qty
                ref_stamp_pn = "COMBINED"  # Mark as combined
                
                # Add PRESS3 entry
                results.append({
                    'Year': year,
                    'Week': week,
                    'Car Model': car_model,
                    'PRESS': 'PRESS3',
                    'REF STAMP PN': ref_stamp_pn,
                    'Release Qty': release_qty,
                    'Volume': press1_volume + press2_volume
                })
    
    # Update the DataFrame with PRESS3 entries
    volume_df = pd.DataFrame(results)
    
    return volume_df

def calculate_saturation(volume_data, press_sph, manual_demands=None):
    """
    Calculates press saturation based on weekly volume and capacity.
    Simplified version with direct PRESS3 calculation.
    """
    # Calculate weekly capacity for each press
    press_capacity = {press: sph * 168 for press, sph in press_sph.items()}
    
    # Group volume by week and press
    volume_by_press = volume_data.groupby(['Year', 'Week', 'PRESS'])['Volume'].sum().reset_index()
    
    # Handle manual demands
    if manual_demands is not None and not manual_demands.empty:
        # Group manual demands by year, week, and press
        manual_demands_grouped = manual_demands.groupby(['Year', 'Week', 'PRESS'])['Volume'].sum().reset_index()
        
        # Merge with automatic volume data
        volume_by_press = pd.merge(
            volume_by_press,
            manual_demands_grouped,
            on=['Year', 'Week', 'PRESS'],
            how='outer',
            suffixes=('_auto', '_manual')
        )
        
        # Fill NaN values with 0
        volume_by_press['Volume_auto'] = volume_by_press['Volume_auto'].fillna(0)
        volume_by_press['Volume_manual'] = volume_by_press['Volume_manual'].fillna(0)
        
        # Sum volumes
        volume_by_press['Volume'] = volume_by_press['Volume_auto'] + volume_by_press['Volume_manual']
        volume_by_press['Manual_Volume'] = volume_by_press['Volume_manual']
    else:
        volume_by_press['Manual_Volume'] = 0
    
    # Calculate saturation for each press and week
    saturations = []
    
    # Get all unique year-week combinations
    year_weeks = volume_by_press[['Year', 'Week']].drop_duplicates().reset_index(drop=True)
    
    # Process each year-week
    for _, yw in year_weeks.iterrows():
        year = yw['Year']
        week = yw['Week']
        
        # Filter data for this year-week
        week_data = volume_by_press[(volume_by_press['Year'] == year) & (volume_by_press['Week'] == week)]
        
        # Process each press for this year-week
        for press in ['PRESS1', 'PRESS2', 'BLNK', 'PRESS3']:
            # Find if this press exists in the week data
            press_rows = week_data[week_data['PRESS'] == press]
            
            # Variables to calculate
            total_volume = 0
            manual_volume = 0
            
            # For PRESS3, calculate as sum of PRESS1 and PRESS2
            if press == 'PRESS3':
                # Get PRESS1 data
                press1_rows = week_data[week_data['PRESS'] == 'PRESS1']
                if not press1_rows.empty:
                    press1_volume = press1_rows['Volume'].sum()
                    press1_manual = press1_rows['Manual_Volume'].sum()
                else:
                    press1_volume = 0
                    press1_manual = 0
                
                # Get PRESS2 data
                press2_rows = week_data[week_data['PRESS'] == 'PRESS2']
                if not press2_rows.empty:
                    press2_volume = press2_rows['Volume'].sum()
                    press2_manual = press2_rows['Manual_Volume'].sum()
                else:
                    press2_volume = 0
                    press2_manual = 0
                
                # Calculate totals for PRESS3
                total_volume = press1_volume + press2_volume
                manual_volume = press1_manual + press2_manual
                
                # Only add PRESS3 if both PRESS1 and PRESS2 have data
                if press1_rows.empty and press2_rows.empty:
                    continue
            
            # For other presses, use the existing data
            elif not press_rows.empty:
                total_volume = press_rows['Volume'].sum()
                manual_volume = press_rows['Manual_Volume'].sum()
            else:
                # Skip if press doesn't exist for this week
                continue
            
            # Get press capacity
            capacity = press_capacity.get(press, 0)
            
            # Calculate saturation
            if capacity > 0:
                saturation = (total_volume / capacity)
                saturation_pct = saturation * 100
            else:
                saturation = 0
                saturation_pct = 0
            
            # Calculate required shifts
            shifts_needed = np.round(saturation * 21, 2)
            
            # Add to results
            saturations.append({
                'Year': year,
                'Week': week,
                'PRESS': press,
                'Volume': total_volume,
                'Manual_Volume': manual_volume,
                'Capacity': capacity,
                'Saturation': saturation,
                'Saturation (%)': saturation_pct,
                'Shifts Needed': shifts_needed
            })
    
    # Convert to DataFrame
    saturation_df = pd.DataFrame(saturations)
    
    # Create PRESS3 capacity if it doesn't exist
    if 'PRESS3' not in press_capacity:
        if 'PRESS1' in press_capacity and 'PRESS2' in press_capacity:
            press_capacity['PRESS3'] = press_capacity['PRESS1'] + press_capacity['PRESS2']
    
    return saturation_df

def create_combined_machine_chart(saturation_data, machine, selected_year_weeks=None):
    """
    Creates a combined chart for a specific machine, showing volume, saturation, 
    capacity and required shifts in a single chart.
    """
    # Filter data for the specific machine
    machine_data = saturation_data[saturation_data['PRESS'] == machine].copy()
    
    if machine_data.empty:
        st.warning(f"No data available for machine {machine}")
        return
    
    # Filter by selected year-weeks if provided
    if selected_year_weeks:
        # Create a boolean mask for filtering
        mask = False
        for year, week in selected_year_weeks:
            mask = mask | ((machine_data['Year'] == year) & (machine_data['Week'] == week))
        
        machine_data = machine_data[mask]
        
        # Sort by year and week
        machine_data = machine_data.sort_values(by=['Year', 'Week'])
    
    if machine_data.empty:
        st.warning(f"No data available for machine {machine} in the selected date range")
        return
    
    # Create labels for weeks in sequential numeric format
    week_numbers = list(range(1, len(machine_data) + 1))
    week_labels = [f"{row['Year']}-W{row['Week']:02d}" for _, row in machine_data.iterrows()]
    
    # Create figure with secondary Y axis
    fig = go.Figure()
    
    # Add bars for volume (automatic)
    automatic_volume = machine_data['Volume'] - machine_data['Manual_Volume']
    fig.add_trace(
        go.Bar(
            x=week_numbers,
            y=automatic_volume.values,
            name='Automatic Volume',
            marker_color='rgba(58, 130, 238, 0.6)',
            text=automatic_volume.values.astype(int),
            textposition='inside',
            textfont=dict(color='white', size=14),
            hovertemplate='Automatic Volume: %{y}<extra></extra>',
            width=0.6  # Wider bars
        )
    )
    
    # Add bars for manual volume
    fig.add_trace(
        go.Bar(
            x=week_numbers,
            y=machine_data['Manual_Volume'].values,
            name='Manual Volume',
            marker_color='rgba(255, 165, 0, 0.7)',
            text=machine_data['Manual_Volume'].values.astype(int),
            textposition='inside',
            textfont=dict(color='white', size=14),
            hovertemplate='Manual Volume: %{y}<extra></extra>',
            width=0.6  # Wider bars
        )
    )
    
    # Add line for capacity
    fig.add_trace(
        go.Scatter(
            x=week_numbers,
            y=machine_data['Capacity'].values,
            name='Capacity',
            mode='lines+markers',  # Removed +text to avoid duplication
            line=dict(color='red', width=3, dash='dot'),
            marker=dict(size=8, color='red'),
            yaxis='y',
            hovertemplate='Capacity: %{y}<extra></extra>'
        )
    )
    
    # Create secondary Y axis for saturation (%)
    fig.add_trace(
        go.Scatter(
            x=week_numbers,
            y=machine_data['Saturation'].values * 100,  # Convert to percentage
            name='Saturation (%)',
            mode='text',
            text=[f"{val:.0f}%" for val in machine_data['Saturation'].values * 100],
            textposition='top center',
            textfont=dict(color='white', size=14, family='Arial Black'),
            yaxis='y2',
            hovertemplate='Saturation: %{y:.1f}%<extra></extra>'
        )
    )
    
    # Configure a dark background for the chart
    bg_color = 'black'
    grid_color = '#333333'
    text_color = 'white'
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f"Line {machine}",
            font=dict(size=24, color=text_color),
            x=0.5
        ),
        xaxis=dict(
            # Remove the "Week" title to avoid duplication with "Shifts per Week"
            title=None,
            titlefont=dict(size=14, color=text_color),
            tickmode='array',
            tickvals=week_numbers,
            ticktext=week_labels,
            tickangle=45,
            tickfont=dict(size=12, color=text_color),
            gridcolor=grid_color,
            showgrid=True
        ),
        yaxis=dict(
            title="Volume (units)",
            titlefont=dict(size=14, color=text_color),
            tickfont=dict(size=12, color=text_color),
            rangemode='nonnegative',
            side='left',
            gridcolor=grid_color,
            showgrid=True
        ),
        yaxis2=dict(
            title="Saturation (%)",
            titlefont=dict(size=14, color=text_color),
            tickfont=dict(size=12, color=text_color),
            rangemode='nonnegative',
            overlaying='y',
            side='right',
            range=[0, 100],
            showgrid=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=text_color)
        ),
        barmode='stack',
        height=600,
        width=1200,
        margin=dict(t=100, b=130, l=50, r=80),
        hovermode="x unified",
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        showlegend=True
    )
    
    # Add a single capacity label far to the right side
    capacity_value = machine_data['Capacity'].values[0]
    fig.add_annotation(
        x=len(week_numbers),
        y=capacity_value,
        text=f"{int(capacity_value)}",
        showarrow=False,
        font=dict(size=14, color="red"),
        xshift=75,  # Increased shift to move further right
        yshift=0,
        xanchor="left"  # Align to the left of the annotation position
    )
    
    # Add horizontal capacity line
    fig.add_shape(
        type="line",
        x0=0.5,  
        x1=len(week_numbers) + 0.5,
        y0=capacity_value,
        y1=capacity_value,
        line=dict(
            color="red",
            width=2,
            dash="dot",
        ),
    )
    
    # Add shift text at bottom as yellow boxes
    turns_list = machine_data['Shifts Needed'].values
    y_pos = -max(machine_data['Volume']) * 0.15  # Vertical position for shifts
    for i in range(len(week_numbers)):
        # Add yellow rectangle
        fig.add_shape(
            type="rect",
            x0=i + 0.7,
            x1=i + 1.3,
            y0=y_pos - max(machine_data['Volume']) * 0.05,
            y1=y_pos + max(machine_data['Volume']) * 0.05,
            fillcolor='rgba(255, 220, 0, 0.9)',
            opacity=1,
            line=dict(color='white', width=1),
        )
        
        # Add shift value inside rectangle
        fig.add_annotation(
            x=i + 1,
            y=y_pos,
            text=f"{turns_list[i]:.1f}",
            showarrow=False,
            font=dict(size=14, color='black'),
        )
    
    # Add "Shifts per Week" text further below chart
    fig.add_annotation(
        x=0.5,
        y=-0.25,  # Moved further down
        xref="paper",
        yref="paper",
        text="<b>Shifts per Week</b>",  # Using HTML bold tag instead of weight property
        showarrow=False,
        font=dict(size=14, color=text_color, family="Arial"),
        align="center"
    )
    
    # Adjust Y axis limits to include shifts and increase bottom margin
    fig.update_layout(
        yaxis=dict(
            range=[y_pos - max(machine_data['Volume']) * 0.1, max(machine_data['Volume']) * 1.1]
        )
    )
    
    return fig

def main():
    # Initialize state variables for tracking recalculation
    if 'needs_recalculation' not in st.session_state:
        st.session_state.needs_recalculation = False
    
    # Initialize calculation ID for forcing complete refresh
    if 'calculation_id' not in st.session_state:
        st.session_state.calculation_id = 0
    
    # Force recalculation if needed
    if st.session_state.needs_recalculation:
        st.session_state.needs_recalculation = False
        st.session_state.calculation_id += 1  # Increment ID to force complete refresh
        st.rerun()
    
    # Hidden element with calculation ID - forces refresh when ID changes
    st.markdown(f'<div style="display:none">{st.session_state.calculation_id}</div>', unsafe_allow_html=True)
    
    st.title("EDI VW Analysis - Weekly Calculations and Volume")

    # Check if folder exists and list Excel files
    try:
        # Create list of full paths to Excel files
        excel_paths = [os.path.join(EXCEL_FOLDER, f) for f in os.listdir(EXCEL_FOLDER) if f.endswith('.xlsx')]
        
        # Sort files by modification date (newest first)
        excel_paths.sort(key=os.path.getmtime, reverse=True)
        
        # Extract only filenames (without full path)
        excel_files = [os.path.basename(path) for path in excel_paths]
    except Exception as e:
        st.error(f"Error accessing folder: {str(e)}")
        excel_files = []
        
    if not excel_files:
        st.error(f"No Excel files found in folder: {EXCEL_FOLDER}")
        return
    
    # Interface for file selection, pre-selecting the newest (index 0)
    selected_file = st.selectbox("Select Excel file", excel_files, index=0)
    
    # SPH values configuration for each press
    st.subheader("Press Capacity Configuration")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sph_press1 = st.number_input("SPH PRESS1", min_value=1, value=200)
    with col2:
        sph_press2 = st.number_input("SPH PRESS2", min_value=1, value=220)
    with col3:
        sph_blnk = st.number_input("SPH BLNK", min_value=1, value=750)
    
    # Create dictionary with SPH values
    press_sph = {
        'PRESS1': sph_press1,
        'PRESS2': sph_press2,
        'BLNK': sph_blnk
    }
    
    # Calculate PRESS3 SPH as sum of PRESS1 and PRESS2
    press_sph['PRESS3'] = sph_press1 + sph_press2
    
    # Show weekly capacity for each press
    st.write("Weekly capacity for each press (SPH × 168):")
    capacity_df = pd.DataFrame({
        'Press': press_sph.keys(),
        'SPH': press_sph.values(),
        'Weekly Capacity': [sph * 168 for sph in press_sph.values()]
    })
    st.dataframe(capacity_df, width=800)
    
    # Load master data
    master_data = load_master_data()
    if master_data is None:
        return
    
    if selected_file:
        file_path = Path(EXCEL_FOLDER) / selected_file
        try:
            df = load_excel_file(file_path)
            df = process_data(df)
            if df is None:
                return
        except Exception as e:
            st.error(f"Error loading or processing file: {str(e)}")
            return

        # Calculate week for each date
        df['Week'] = df['Date'].apply(lambda x: get_week_number(x))
        df['Year'] = df['Date'].dt.year
        
        # Create a combined column to correctly sort year-week
        df['YearWeek'] = df['Year'].astype(str) + df['Week'].astype(str).str.zfill(2)
        
        # Identify the first year-week combination in the file
        first_year_week = df['YearWeek'].min()
        
        # Filter data to ignore first week
        df_filtered = df[df['YearWeek'] > first_year_week]
        
        if df_filtered.empty:
            st.warning("No data available after removing first week.")
            return
            
        # Group data by week and model
        weekly_data = (df_filtered.groupby(['Year', 'Week', 'Car Model'])['Release Qty']
                     .sum()
                     .reset_index())
        
        # Create representative date for each week (starting on Sunday)
        def get_week_start_date(row):
            # Ensure we work with date
            first_day = datetime(row['Year'], 1, 1).date()
            if first_day.weekday() != 6:  # If not Sunday
                first_day = first_day - timedelta(days=first_day.weekday() + 1)
            days_to_add = (row['Week'] - 1) * 7
            return datetime.combine(first_day + timedelta(days=days_to_add), datetime.min.time())
        
        weekly_data['DateForSort'] = weekly_data.apply(get_week_start_date, axis=1)
        
        # Calculate volume based on master data
        volume_data = calculate_volume(weekly_data, master_data)
        
        if volume_data is not None:
            # Manual demand section - simplified version
            st.markdown("---")
            st.subheader("Add Manual Demand")
            
            # Initialize session state for manual demands if not exists
            if 'manual_demands_entries' not in st.session_state:
                st.session_state.manual_demands_entries = []
            
            # Get current week as default
            current_date = datetime.now()
            current_week_num = get_week_number(current_date)
            current_week_str = f"{current_date.year}-W{current_week_num:02d}"
            
            # Create options for year-week selection (only up to 1 year ahead)
            year_week_options = []
            
            # Start from current week
            temp_date = current_date
            for _ in range(52):  # 1 year worth of weeks
                year = temp_date.year
                week = get_week_number(temp_date)
                year_week_options.append(f"{year}-W{week:02d}")
                temp_date += timedelta(weeks=1)
            
            # Single entry form
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            
            with col1:
                manual_press = st.selectbox("Press", ['PRESS1', 'PRESS2', 'BLNK'])
            
            with col2:
                start_year_week = st.selectbox(
                    "Start Week", 
                    year_week_options,
                    index=0  # Current week
                )
            
            with col3:
                end_year_week = st.selectbox(
                    "End Week", 
                    year_week_options,
                    index=0  # Current week
                )
            
            with col4:
                manual_volume = st.number_input(
                    "Weekly Volume", 
                    min_value=0, 
                    value=0, 
                    step=100
                )
            
            with col5:
                if st.button("Add", key="add_manual_demand"):
                    if manual_volume > 0:
                        # Add to session state
                        st.session_state.manual_demands_entries.append({
                            'Press': manual_press,
                            'Start Week': start_year_week,
                            'End Week': end_year_week,
                            'Weekly Volume': manual_volume
                        })
                        st.success(f"✓ Added demand for {manual_press}")
            
            # Show current entries
            if st.session_state.manual_demands_entries:
                st.markdown("### Manual Demands")
                entries_df = pd.DataFrame(st.session_state.manual_demands_entries)
                
                # Display table with remove option
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.dataframe(entries_df, width="stretch")
                
                with col2:
                    if st.button("Clear All"):
                        st.session_state.manual_demands_entries = []
                        st.rerun()
                
                # Calculate button
                if st.button("Recalculate Graphs", type="primary"):
                    # Convert entries to manual demands format
                    manual_demands = []
                    
                    for entry in st.session_state.manual_demands_entries:
                        start_year = int(entry['Start Week'].split('-')[0])
                        start_week = int(entry['Start Week'].split('-')[1][1:])
                        end_year = int(entry['End Week'].split('-')[0])
                        end_week = int(entry['End Week'].split('-')[1][1:])
                        
                        start_date = datetime(start_year, 1, 1) + timedelta(weeks=start_week-1)
                        end_date = datetime(end_year, 1, 1) + timedelta(weeks=end_week-1)
                        
                        if start_date <= end_date:
                            current_date = start_date
                            while current_date <= end_date:
                                current_year = current_date.year
                                current_week = get_week_number(current_date)
                                
                                manual_demands.append({
                                    'Year': current_year,
                                    'Week': current_week,
                                    'PRESS': entry['Press'],
                                    'Volume': entry['Weekly Volume']
                                })
                                
                                current_date += timedelta(weeks=1)
                    
                    # Convert to DataFrame
                    manual_demands_df = pd.DataFrame(manual_demands) if manual_demands else None
                    
                    # Calculate press saturation with manual demands
                    saturation_data = calculate_saturation(volume_data, press_sph, manual_demands_df)
                    
                    # Store in session state for use in charts
                    st.session_state.calculated_saturation_data = saturation_data
                    
                    # Flag that we need a full recalculation to update all graphs
                    st.session_state.needs_recalculation = True
                    
                    st.success("✓ Graphs updated with manual demands!")
                    st.rerun()
            else:
                st.info("No manual demands added. Using only automatic demands.")
                # Calculate without manual demands
                saturation_data = calculate_saturation(volume_data, press_sph, None)
                st.session_state.calculated_saturation_data = saturation_data
            
            # Use the calculated saturation data
            if 'calculated_saturation_data' in st.session_state:
                saturation_data = st.session_state.calculated_saturation_data
            else:
                saturation_data = calculate_saturation(volume_data, press_sph, None)
            
            # Sort saturation data
            saturation_data_sorted = saturation_data.sort_values(by=['Year', 'Week', 'PRESS'])
            
            # Get all year-week combinations for the selection
            all_year_weeks = get_all_year_week_combinations(saturation_data_sorted)
            
            # Create a string representation for each year-week for display
            year_week_strings = [f"{year}-W{week:02d}" for year, week in all_year_weeks]
            
            # Create "From" and "To" selectors for date range
            st.subheader("Select Date Range")
            col1, col2 = st.columns(2)
            
            with col1:
                start_index = 0  # Default to first week
                from_week = st.selectbox("From Week/Year", 
                                        options=year_week_strings,
                                        index=start_index,
                                        key="from_week")
                
            with col2:
                end_index = min(10, len(year_week_strings) - 1)  # Default to show 10 weeks or all if less
                to_week = st.selectbox("To Week/Year", 
                                      options=year_week_strings,
                                      index=end_index,
                                      key="to_week")
            
            # Get indices of selected weeks
            from_index = year_week_strings.index(from_week)
            to_index = year_week_strings.index(to_week)
            
            # Ensure from_index is not greater than to_index
            if from_index > to_index:
                st.warning("'From' date is after 'To' date. Adjusting selection.")
                from_index, to_index = to_index, from_index
            
            # Get the selected year-week combinations
            selected_year_weeks = all_year_weeks[from_index:to_index+1]
            
            # Display number of weeks selected
            st.info(f"Selected {len(selected_year_weeks)} weeks from {from_week} to {to_week}")
            
            # Get unique machines list and order them as requested
            machines = ['BLNK', 'PRESS3', 'PRESS1', 'PRESS2']
            
            # For each machine, create a combined chart
            for machine in machines:
                # Check if the machine exists in the data
                if machine in saturation_data_sorted['PRESS'].unique():
                    st.markdown(f"### Analysis for Machine {machine}")
                    fig = create_combined_machine_chart(saturation_data_sorted, machine, selected_year_weeks)
                    st.plotly_chart(fig, width="stretch")
                    st.markdown("---")  # Separator between charts

if __name__ == "__main__":
    main()