from pathlib import Path

import streamlit as st

from config import USE_SAMPLE_DATA
from ui import apply_base_style, apply_tv_style, is_tv_mode, sample_data_notice

# Entry point: defines the app pages and the sidebar navigation.
# Page content lives in app_pages/; the hub landing page is app_pages/Home.py.
st.set_page_config(layout="wide")  # tab title comes from each st.Page title

# Logo at the top of the sidebar on every page (local asset if present, else the public URL)
LOGO_FILE = Path(__file__).parent / "assets" / "gestamp_logo.png"
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Gestamp_Logo.png/500px-Gestamp_Logo.png"
st.logo(str(LOGO_FILE) if LOGO_FILE.exists() else LOGO_URL, size="large")

apply_base_style()
tv = is_tv_mode()  # ?tv=1: hide navigation and chrome for shop-floor TVs
if tv:
    apply_tv_style()

home = st.Page("app_pages/Home.py", title="Home", icon=":material/home:", default=True)
edi_vw = st.Page("app_pages/EDI_VW_view.py", title="EDI VW View", icon=":material/insights:")
press_capacity = st.Page("app_pages/Press_capacity.py", title="Press Capacity", icon=":material/precision_manufacturing:")
goods_receipt = st.Page("app_pages/Receiving_mat.py", title="Goods Receipt", icon=":material/local_shipping:")
coil_storage = st.Page("app_pages/Coil_Storage.py", title="Coil Storage", icon=":material/warehouse:")
fifo_report = st.Page("app_pages/FIFO_Report.py", title="FIFO Report - Beta", icon=":material/fact_check:")

pg = st.navigation({
    "Overview": [home],
    "Demand & Production": [edi_vw, press_capacity],
    "Materials & Warehouse": [goods_receipt, coil_storage, fifo_report],
}, position="hidden" if tv else "sidebar")
if USE_SAMPLE_DATA:
    sample_data_notice()
pg.run()
