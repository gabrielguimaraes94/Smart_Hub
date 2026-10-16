import streamlit as st
import pandas as pd
from datetime import datetime
import os
import glob

from config import COIL_STOCK_FOLDER
from ui import footer, fullscreen_button, is_tv_mode, kpi_card, legend, page_header, rail_title, slot_card

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
        directory = COIL_STOCK_FOLDER
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
def create_rail_layout(df, rail_letters, num_positions, query=""):
    # Create columns for each rail
    columns = st.columns(len(rail_letters))

    for col, rail_letter in zip(columns, rail_letters):
        with col:
            rail_title(f"Rail {rail_letter}")
            for i in range(num_positions):
                position = f"R{rail_letter}-{str(i+1).zfill(2)}"
                position_data = get_position_data(df, position)

                if not position_data.empty:
                    for _, material_info in position_data.iterrows():
                        slot_card(position, occupied=True, lines=[
                            ("Material", material_info['MATNR']),
                            ("Label", material_info['LENUM']),
                            ("Weight", format_weight(material_info['VERME'])),
                        ], highlight=slot_matches(query, position, material_info) if query else None)
                else:
                    slot_card(position, occupied=False,
                              highlight=slot_matches(query, position) if query else None)


def slot_matches(query, position, material_info=None):
    """Display-only search: case-insensitive match on position, material (MATNR) or label (LENUM)."""
    q = query.strip().lower()
    fields = [position]
    if material_info is not None:
        fields += [material_info['MATNR'], material_info['LENUM']]
    return any(q in str(f).lower() for f in fields)


def format_weight(value):
    """Display-only formatting of the VERME weight (kg); falls back to the raw value."""
    try:
        return f"{float(value):,.0f} kg"
    except (TypeError, ValueError):
        return value

DISPLAY_POSITIONS = 7  # positions drawn per rail (rail F has 8 in rail_positions; only 7 are shown)


# Main interface
def main():
    tv = is_tv_mode()

    # Header row: title + search + fullscreen / TV-mode controls.
    # The search is kept in the URL (?q=) so a bookmarked or kiosk URL can carry it.
    if tv:
        t, s, b = st.columns([2, 3, 1], vertical_alignment="bottom")
        with t:
            st.title("Coil Storage")
    else:
        page_header("Coil Storage", "Coil positions by rail in the coil warehouse. Data refreshes every 5 minutes.")
        s, b = st.columns([5, 1], vertical_alignment="bottom")
    with s:
        if "coil_search" not in st.session_state:
            st.session_state.coil_search = st.query_params.get("q", "")
        query = st.text_input(
            "Search", key="coil_search",
            placeholder="Material, label or position (e.g. DX54, 9912…, RA-01)",
            icon=":material/search:",
        ).strip()
        if query:
            st.query_params["q"] = query
        elif "q" in st.query_params:
            del st.query_params["q"]
    with b:
        fullscreen_button()
        if not tv:
            st.page_link("app_pages/Coil_Storage.py", label="TV mode", icon=":material/tv:",
                         query_params={"tv": "1"})

    live_view(query)


# Re-reads the file and redraws KPIs + map every 5 minutes without reloading the page,
# so fullscreen and the typed search are kept.
@st.fragment(run_every="5m")
def live_view(query):
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

    # KPI row
    free_positions = total_positions - occupied_positions
    occupancy = occupied_positions / total_positions if total_positions else 0
    k1, k2, k3 = st.columns(3)
    with k1:
        kpi_card("Occupied positions", f"{occupied_positions}/{total_positions}")
    with k2:
        kpi_card("Free positions", free_positions)
    with k3:
        kpi_card("Occupancy", f"{occupancy:.0%}")

    # Create visualization for all rails
    if df is not None:
        if query:
            found = []
            for rail in rail_positions:
                for i in range(1, DISPLAY_POSITIONS + 1):  # only positions drawn on screen
                    position = f"R{rail}-{str(i).zfill(2)}"
                    rows = get_position_data(df, position)
                    if rows.empty:
                        if slot_matches(query, position):
                            found.append(f"{position} (empty)")
                    elif any(slot_matches(query, position, row) for _, row in rows.iterrows()):
                        found.append(position)
            if found:
                st.success(f"**{len(found)}** match(es) for “{query}”: " + ", ".join(found), icon=":material/location_on:")
            else:
                st.warning(f"No coil matches “{query}”.", icon=":material/search_off:")
        legend([("Occupied", "#2E7D4F"), ("Empty", "#C5CCD5"), ("Search match", "#EAF1FB; box-shadow: inset 0 0 0 2px #20416C")])
        create_rail_layout(df, rail_positions.keys(), DISPLAY_POSITIONS, query)

    footer()


if __name__ == "__main__":
    main()
