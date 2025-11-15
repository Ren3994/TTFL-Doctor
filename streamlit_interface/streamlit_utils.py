from supabase import create_client
import streamlit as st
import pandas as pd
import subprocess
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import STREAMLIT_MAIN_PY_PATH

@st.cache_resource
def conn_supabase():
    url = st.secrets.get("SUPABASE_URL", "unknown")
    key = st.secrets.get("SUPABASE_KEY", "unknown")
    return create_client(url, key)

@st.cache_data(ttl=300)
def fetch_supabase_users(_supabase):
    data = _supabase.table("ttfl_doctor_user_picks").select("username").execute().data
    return pd.DataFrame(data)['username'].tolist()

def launch_GUI():
    subprocess.run([sys.executable, "-m", "streamlit", "run", STREAMLIT_MAIN_PY_PATH])

def config(page):
    st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")

def custom_error(error_text, fontsize, center_text=True):
    st.markdown(f"""
            <div style="
                background-color: #3e2428; 
                color: #f06666; 
                padding: 10px; 
                border-radius: 5px; 
                font-size: {fontsize}px;
                text-align: {'center' if center_text else 'left'};
            ">
                {error_text}
            </div>
            """, unsafe_allow_html=True)

# if __name__ == '__main__':
#     launch_GUI()