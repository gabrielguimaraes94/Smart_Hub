import streamlit as st
import pandas as pd
from datetime import datetime
import os
import glob

# Page configuration
st.set_page_config(
    page_title="Storage Bin - Coils",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar starts collapsed
)

# Function to find the latest file in folder
def get_latest_file(directory_path):
    try:
        files = glob.glob(os.path.join(directory_path, "*"))
        if not files:
            st.error(f"No files found in directory: {directory_path}")
            return None
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    except PermissionError:
        st.error(f"Permission denied accessing directory: {directory_path}")
        return None
    except Exception as e:
        st.error(f"Error finding file: {str(e)}")
        return None

# Function to read Excel file
def load_data():
    try:
        directory = r"\\ch2-python\powerBI\Data\GC2\Stock_coil"
        latest_file = get_latest_file(directory)
        if latest_file is None:
            return None
        try:
            df = pd.read_excel(latest_file)
        except UnicodeDecodeError:
            df = pd.read_excel(latest_file, encoding='latin1')
        except Exception as e:
            st.error(f"Error reading file {latest_file}: {str(e)}")
            return None
        return df
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return None

# Function to check if position is occupied
def get_position_data(df, rail_position):
    if df is not None:
        return df[df['LGPLA'] == rail_position]
    return pd.DataFrame()

# Function to create rail visualization in vertical columns
def create_rail_layout(df, rail_letters, num_positions):
    # Create columns for each rail
    columns = st.columns(len(rail_letters))

    for col, rail_letter in zip(columns, rail_letters):
        with col:
            st.write(f"### Rail {rail_letter}")
            for i in range(num_positions):
                position = f"R{rail_letter}-{str(i+1).zfill(2)}"
                position_data = get_position_data(df, position)

                if not position_data.empty:
                    for _, material_info in position_data.iterrows():
                        st.markdown(
                            f"""
                            <div style="background: linear-gradient(135deg, #28a745, #218838); 
                                        color: white; padding: 10px; 
                                        border-radius: 5px; 
                                        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); 
                                        text-align: center; margin-bottom: 10px;">
                                <strong>{position}</strong><br>
                                Material: {material_info['MATNR']}<br>
                                Label: {material_info['LENUM']}<br>
                                Weight(KG): {material_info['VERME']}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, #dc3545, #c82333); 
                                    color: white; padding: 10px; 
                                    border-radius: 5px; 
                                    box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); 
                                    text-align: center; margin-bottom: 10px;">
                            <strong>{position}</strong><br>
                            Empty
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# Main interface
def main():
    st.title("Storage Bin - Coils Control")
    
    # Header section for important information
    rail_positions = {
        'A': 7, 'B': 7, 'C': 7, 'D': 7, 'E': 7, 'F': 8, 'G': 7, 'H': 7
    }
    total_positions = sum(rail_positions.values())
    df = load_data()
    occupied_positions = 0
    if df is not None:
        occupied_positions = sum(
            1 for rail, num_positions in rail_positions.items()
            for i in range(1, num_positions + 1)
            if not get_position_data(df, f"R{rail}-{str(i).zfill(2)}").empty
        )
    
    # Display metrics in the top-right corner
    col1, col2 = st.columns([8, 2])
    with col2:
        st.metric("Occupied Positions", f"{occupied_positions}/{total_positions}")
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        st.write(f"**Last update:** {current_time}")
    
    # Create visualization for all rails
    if df is not None:
        create_rail_layout(df, rail_positions.keys(), 7)  # Adjust the number of positions as needed
    
    # Add auto-refresh using HTML meta tag
    st.markdown(
        """
        <meta http-equiv="refresh" content="300">
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
