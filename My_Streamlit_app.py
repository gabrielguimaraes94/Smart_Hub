import streamlit as st

# Page configuration
st.set_page_config(page_title="Functionality Hub", layout="wide")

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
    .functionality {
        background-color: white;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        transition: all 0.3s cubic-bezier(.25,.8,.25,1);
    }
    .functionality:hover {
        box-shadow: 0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22);
    }
    .icon {
        font-size: 24px;
        margin-right: 10px;
    }
    .title {
        font-weight: bold;
        color: #333;
        font-size: 18px;
    }
    .subtitle {
        color: #666;
        font-size: 14px;
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

# Function to create a functionality
def create_functionality(icon, title, subtitle, page):
    st.markdown(f"""
    <a href="{page}" target="_self" style="text-decoration: none; color: inherit;">
        <div class="functionality">
            <span class="icon">{icon}</span>
            <span class="title">{title}</span><br>
            <span class="subtitle">{subtitle}</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

# Creating functionalities
create_functionality("📊", "EDI VW View", "EDI VW Visualization", "EDI_VW_view")
create_functionality("🏋🏻‍♀️", "Press Capacity Calculation", "Press Capacity", "Press_capacity")
create_functionality("📝", "Storage Bin - Coils", "Storage Bin - Coils", "Coil_Storage")
create_functionality("📦", "Goods Receipt Dashboard", "Goods Receipt Dashboard", "Receiving_mat")
create_functionality("🔍", "Advanced Search", "Information filtering", "Advanced_Search")
create_functionality("⚙️", "Settings", "Customize the system", "Settings")
