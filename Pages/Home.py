import streamlit as st

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
        color: #333;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .logo {
        display: block;
        margin: auto;
        max-width: 200px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Logo
st.markdown('<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Gestamp_Logo.png/640px-Gestamp_Logo.png" class="logo">', unsafe_allow_html=True)

# Main title
st.markdown('<p class="big-font">Functionality Hub</p>', unsafe_allow_html=True)

# Function to create a functionality card linking to a page registered in st.navigation
def create_functionality(icon, title, subtitle, page):
    with st.container(border=True):
        st.page_link(page, label=f"**{title}**", icon=icon)
        st.caption(subtitle)

# Creating functionalities
create_functionality(":material/insights:", "EDI VW View", "EDI VW Visualization", "Pages/EDI_VW_view.py")
create_functionality(":material/precision_manufacturing:", "Press Capacity Calculation", "Press Capacity", "Pages/Press_capacity.py")
create_functionality(":material/local_shipping:", "Goods Receipt Dashboard", "Goods Receipt Dashboard", "Pages/Receiving_mat.py")
create_functionality(":material/warehouse:", "Storage Bin - Coils", "Storage Bin - Coils", "Pages/Coil_Storage.py")
create_functionality(":material/fact_check:", "FIFO Report - Beta", "FIFO control - Shipping", "Pages/FIFO_Report.py")
