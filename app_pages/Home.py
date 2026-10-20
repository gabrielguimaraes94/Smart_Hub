import streamlit as st

from ui import footer, hero, nav_card, section_label

hero(
    "Functionality Hub",
    "Operational reports for the GC2 stamping plant: customer demand, press capacity, "
    "materials and finished goods. Pick a module below or use the side menu.",
    eyebrow="Gestamp NAFTA · GC2 Plant",
    meta="7 modules · live from the plant shares",
)

section_label("Demand & Production", "01")
col1, col2, col3 = st.columns(3)
with col1:
    nav_card("edi", "app_pages/EDI_VW_view.py", "EDI VW View",
             "VW customer demand and production planning tracking.",
             ":material/insights:", accent="blue")
with col2:
    nav_card("edi_compare", "app_pages/EDI_Compare.py", "EDI Compare",
             "Week-by-week changes between two VW EDI releases.",
             ":material/compare_arrows:", accent="blue")
with col3:
    nav_card("press", "app_pages/Press_capacity.py", "Press Capacity",
             "Capacity and load of each press, week by week.",
             ":material/precision_manufacturing:", accent="blue")

section_label("Materials & Warehouse", "02")
col1, col2, col3 = st.columns(3)
with col1:
    nav_card("receipt", "app_pages/Receiving_mat.py", "Goods Receipt",
             "Material receipts by supplier and period.",
             ":material/local_shipping:", badge="BETA", accent="orange")
with col2:
    nav_card("coil", "app_pages/Coil_Storage.py", "Coil Storage",
             "Position of every coil in the coil warehouse.",
             ":material/warehouse:", accent="orange", tags=("TV",))
with col3:
    nav_card("fifo", "app_pages/FIFO_Report.py", "FIFO Report",
             "Stock age and FIFO compliance check in shipping.",
             ":material/fact_check:", badge="BETA", accent="orange")

section_label("Finished Goods", "03")
col1, col2, col3 = st.columns(3)
with col1:
    nav_card("doh", "app_pages/Finish_Goods_DOH.py", "Finished Goods DOH",
             "Finished goods stock, days on hand and sales of the week.",
             ":material/inventory_2:", accent="green", tags=("TV",))

footer()
