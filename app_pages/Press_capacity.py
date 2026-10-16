import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import EDI_FOLDER, PRESS_MASTER_DATA_FILE
from ui import PRIMARY, footer, kpi_card, page_header

# Chart colors
AUTO_COLOR = PRIMARY        # volume from the EDI
MANUAL_COLOR = '#D9701E'    # manual (what-if) volume
CAPACITY_COLOR = '#C0392B'  # weekly capacity line


def saturation_color(pct):
    """Green below 85 %, amber up to 100 %, red above (display only)."""
    return '#2E7D4F' if pct < 85 else ('#B7791F' if pct <= 100 else '#C0392B')

# Paths to folders with Excel files and master data
EXCEL_FOLDER = EDI_FOLDER
MASTER_DATA_FILE = PRESS_MASTER_DATA_FILE

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
            name='EDI volume',
            marker_color=AUTO_COLOR,
            text=[f"{v:,.0f}" for v in automatic_volume.values],
            textposition='inside',
            textfont=dict(color='white', size=13),
            textangle=0,
            hovertemplate='EDI volume: %{y:,.0f}<extra></extra>',
            width=0.6
        )
    )

    # Add bars for manual volume
    fig.add_trace(
        go.Bar(
            x=week_numbers,
            y=machine_data['Manual_Volume'].values,
            name='Manual volume',
            marker_color=MANUAL_COLOR,
            text=[f"{v:,.0f}" if v else "" for v in machine_data['Manual_Volume'].values],
            textposition='inside',
            textfont=dict(color='white', size=13),
            textangle=0,
            hovertemplate='Manual volume: %{y:,.0f}<extra></extra>',
            width=0.6
        )
    )

    # Add line for capacity
    fig.add_trace(
        go.Scatter(
            x=week_numbers,
            y=machine_data['Capacity'].values,
            name='Capacity',
            mode='lines+markers',
            line=dict(color=CAPACITY_COLOR, width=2, dash='dot'),
            marker=dict(size=6, color=CAPACITY_COLOR),
            yaxis='y',
            hovertemplate='Capacity: %{y:,.0f}<extra></extra>'
        )
    )

    # Saturation label above each bar, colored by level
    # (placed on the volume axis, so a week over 100 % is never cut off)
    saturation_pct = machine_data['Saturation'].values * 100
    fig.add_trace(
        go.Scatter(
            x=week_numbers,
            y=machine_data['Volume'].values,
            name='Saturation (%)',
            mode='text',
            text=[f"<b>{val:.0f}%</b>" for val in saturation_pct],
            textposition='top center',
            textfont=dict(color=[saturation_color(v) for v in saturation_pct], size=14),
            customdata=saturation_pct,
            showlegend=False,
            hovertemplate='Saturation: %{customdata:.1f}%<extra></extra>'
        )
    )

    text_color = '#1F2933'
    grid_color = '#E6EAF0'

    # Update layout
    fig.update_layout(
        xaxis=dict(
            title=None,
            tickmode='array',
            tickvals=week_numbers,
            ticktext=week_labels,
            tickangle=45,
            tickfont=dict(size=12),
            showgrid=False
        ),
        yaxis=dict(
            title=dict(text="Volume (units)", font=dict(size=13)),
            tickformat=',',
            rangemode='nonnegative',
            side='left',
            gridcolor=grid_color,
            showgrid=True
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        barmode='stack',
        height=560,
        margin=dict(t=40, b=110, l=50, r=70),
        hovermode="x unified",
        font=dict(family='Inter, sans-serif', color=text_color),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        showlegend=True
    )

    # Add a single capacity label far to the right side
    capacity_value = machine_data['Capacity'].values[0]
    fig.add_annotation(
        x=len(week_numbers),
        y=capacity_value,
        text=f"{int(capacity_value):,}",
        showarrow=False,
        font=dict(size=13, color=CAPACITY_COLOR),
        xshift=40,
        yshift=0,
        xanchor="left"
    )

    # Add horizontal capacity line
    fig.add_shape(
        type="line",
        x0=0.5,
        x1=len(week_numbers) + 0.5,
        y0=capacity_value,
        y1=capacity_value,
        line=dict(
            color=CAPACITY_COLOR,
            width=2,
            dash="dot",
        ),
    )

    # Shifts needed per week, in small boxes under the bars
    turns_list = machine_data['Shifts Needed'].values
    y_pos = -max(machine_data['Volume']) * 0.15  # Vertical position for shifts
    for i in range(len(week_numbers)):
        fig.add_shape(
            type="rect",
            x0=i + 0.7,
            x1=i + 1.3,
            y0=y_pos - max(machine_data['Volume']) * 0.05,
            y1=y_pos + max(machine_data['Volume']) * 0.05,
            fillcolor='#FFF1D6',
            opacity=1,
            line=dict(color='#E9B949', width=1),
        )

        fig.add_annotation(
            x=i + 1,
            y=y_pos,
            text=f"{turns_list[i]:.1f}",
            showarrow=False,
            font=dict(size=13, color=text_color),
        )

    fig.add_annotation(
        x=0.5,
        y=-0.24,
        xref="paper",
        yref="paper",
        text="<b>Shifts per week</b>",
        showarrow=False,
        font=dict(size=13, color=text_color),
        align="center"
    )

    # Y axis: room below for the shift boxes, and on top for the capacity line and the saturation labels
    top = max(max(machine_data['Volume']), capacity_value) * 1.12
    fig.update_layout(
        yaxis=dict(
            range=[y_pos - max(machine_data['Volume']) * 0.1, top]
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
    
    page_header("Press Capacity", "Weekly volume, saturation and shifts needed per press, from the VW EDI and the master data.")

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
    
    # Settings in one row: EDI file (newest pre-selected) | SPH per press
    c_file, col1, col2, col3 = st.columns([3, 1, 1, 1], vertical_alignment="bottom")
    with c_file:
        selected_file = st.selectbox("EDI file", excel_files, index=0)
    with col1:
        sph_press1 = st.number_input("SPH PRESS1", min_value=1, value=200, help="Strokes per hour")
    with col2:
        sph_press2 = st.number_input("SPH PRESS2", min_value=1, value=220, help="Strokes per hour")
    with col3:
        sph_blnk = st.number_input("SPH BLNK", min_value=1, value=750, help="Strokes per hour")
    
    # Create dictionary with SPH values
    press_sph = {
        'PRESS1': sph_press1,
        'PRESS2': sph_press2,
        'BLNK': sph_blnk
    }
    
    # Calculate PRESS3 SPH as sum of PRESS1 and PRESS2
    press_sph['PRESS3'] = sph_press1 + sph_press2
    
    # Weekly capacity for each press (SPH × 168)
    machines = ['BLNK', 'PRESS3', 'PRESS1', 'PRESS2']
    cap_cols = st.columns(len(machines))
    for col, press in zip(cap_cols, machines):
        with col:
            kpi_card(f"{press} weekly capacity", f"{press_sph[press] * 168:,}",
                     help=f"SPH {press_sph[press]:,} × 168 h" + (" (PRESS1 + PRESS2)" if press == 'PRESS3' else ""))

    # Week range selectors are drawn here, filled in once the weeks are known
    range_box = st.container()

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
        
        if volume_data is None:
            return

        # Manual demand (what-if) section
        with st.expander("What-if: manual demand", icon=":material/edit_note:",
                         expanded=bool(st.session_state.get('manual_demands_entries'))):
            st.caption("Add extra weekly volume to a press for a range of weeks; it is stacked on top of the EDI volume.")

            # Initialize session state for manual demands if not exists
            if 'manual_demands_entries' not in st.session_state:
                st.session_state.manual_demands_entries = []

            # Get current week as default
            current_date = datetime.now()

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
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1], vertical_alignment="bottom")

            with col1:
                manual_press = st.selectbox("Press", ['PRESS1', 'PRESS2', 'BLNK'])

            with col2:
                start_year_week = st.selectbox("Start week", year_week_options, index=0)

            with col3:
                end_year_week = st.selectbox("End week", year_week_options, index=0)

            with col4:
                manual_volume = st.number_input("Weekly volume", min_value=0, value=0, step=100)

            with col5:
                if st.button("Add", key="add_manual_demand", icon=":material/add:", width="stretch"):
                    if manual_volume > 0:
                        # Add to session state
                        st.session_state.manual_demands_entries.append({
                            'Press': manual_press,
                            'Start Week': start_year_week,
                            'End Week': end_year_week,
                            'Weekly Volume': manual_volume
                        })
                        st.toast(f"Added demand for {manual_press}", icon=":material/check:")

            # Show current entries
            if st.session_state.manual_demands_entries:
                entries_df = pd.DataFrame(st.session_state.manual_demands_entries)
                st.dataframe(entries_df, hide_index=True)

                b1, b2, _ = st.columns([2, 1, 4])
                with b1:
                    recalculate = st.button("Recalculate charts", type="primary", icon=":material/refresh:",
                                            width="stretch")
                with b2:
                    if st.button("Clear all", width="stretch"):
                        st.session_state.manual_demands_entries = []
                        st.rerun()

                if recalculate:
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

                    st.rerun()
            else:
                st.caption("No manual demand added: the charts use the EDI volume only.")
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

        # "From" and "To" week selectors, shown under the capacity cards
        with range_box:
            col1, col2, col3 = st.columns([1, 1, 2], vertical_alignment="bottom")

            with col1:
                from_week = st.selectbox("From week", options=year_week_strings, index=0, key="from_week")

            with col2:
                end_index = min(10, len(year_week_strings) - 1)  # Default to show 10 weeks or all if less
                to_week = st.selectbox("To week", options=year_week_strings, index=end_index, key="to_week")

            # Get indices of selected weeks
            from_index = year_week_strings.index(from_week)
            to_index = year_week_strings.index(to_week)

            # Ensure from_index is not greater than to_index
            if from_index > to_index:
                st.warning("'From' week is after 'To' week. Adjusting selection.")
                from_index, to_index = to_index, from_index

            # Get the selected year-week combinations
            selected_year_weeks = all_year_weeks[from_index:to_index+1]

            with col3:
                st.caption(f"{len(selected_year_weeks)} weeks selected · file {selected_file}")

        # One combined chart per machine
        for machine in machines:
            # Check if the machine exists in the data
            if machine in saturation_data_sorted['PRESS'].unique():
                st.subheader(machine)
                fig = create_combined_machine_chart(saturation_data_sorted, machine, selected_year_weeks)
                if fig is not None:
                    st.plotly_chart(fig, width="stretch")

        st.caption("Saturation = weekly volume ÷ weekly capacity (SPH × 168 h); shifts needed = saturation × 21. "
                   "PRESS3 = PRESS1 + PRESS2. The first week of the EDI file is left out.")
        footer(datetime.fromtimestamp(os.path.getmtime(file_path)))


if __name__ == "__main__":
    main()