import streamlit as st

# Entry point: defines the app pages and the sidebar navigation.
# Page content lives in Pages/; the hub landing page is Pages/Home.py.
st.set_page_config(page_title="Functionality Hub", layout="wide")

home = st.Page("Pages/Home.py", title="Home", icon=":material/home:", default=True)
edi_vw = st.Page("Pages/EDI_VW_view.py", title="EDI VW View", icon=":material/insights:")
press_capacity = st.Page("Pages/Press_capacity.py", title="Press Capacity", icon=":material/precision_manufacturing:")
goods_receipt = st.Page("Pages/Receiving_mat.py", title="Goods Receipt", icon=":material/local_shipping:")
coil_storage = st.Page("Pages/Coil_Storage.py", title="Coil Storage", icon=":material/warehouse:")
fifo_report = st.Page("Pages/FIFO_Report.py", title="FIFO Report - Beta", icon=":material/fact_check:")

pg = st.navigation({
    "Início": [home],
    "Demanda & Produção": [edi_vw, press_capacity],
    "Materiais & Armazém": [goods_receipt, coil_storage, fifo_report],
})
pg.run()
