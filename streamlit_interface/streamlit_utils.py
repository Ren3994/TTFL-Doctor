from supabase import create_client
import streamlit as st
import pandas as pd
import subprocess
import sqlite3
import base64
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import STREAMLIT_MAIN_PY_PATH, DB_PATH, TBD_LOGO_PATH

@st.cache_resource(show_spinner=False)
def conn_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False) 
    return conn

@st.cache_resource(show_spinner=False)
def conn_supabase():
    url = st.secrets.get("SUPABASE_URL", "unknown")
    key = st.secrets.get("SUPABASE_KEY", "unknown")
    return create_client(url, key)

@st.cache_data(ttl=300, show_spinner=False)
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

@st.cache_data(show_spinner=False)
def st_image_crisp(path, width=40, raw=False):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except:
        with open(TBD_LOGO_PATH, "rb") as f:
            data=f.read()
    encoded = base64.b64encode(data).decode()
    if raw:
        return encoded
    return f"""<img src="data:image/png;base64,{encoded}" style="width:{width}px;height:auto;object-fit:contain;"/>"""

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
    
def SEO():
    SEO_text = """
    <meta name="description" content="TTFL Doctor : Tableau des picks du soir avec statistiques détaillées pour la TrashTalk Fantasy League. Informations sur les blessures, impacts des blessures des coéquipiers et des adversaires, et tous types de statistiques. Optimisez vos picks et évitez les 🥕 !">
    <meta name="keywords" content="trashtalk, trashtalk fantasy league, ttfl, best pick, fantasy nba, fantasy league, statistiques ttfl, stats ttfl, picks fantasy, blessures">
    <meta property="og:title" content="Stats et Données pour la TrashTalk Fantasy League">
    <meta property="og:type" content="website">
    <meta property="og:url" content="ttfl-doctor.streamlit.app">
    <meta name="google-site-verification" content="KU6FOvGrqSJpCQ68nnJeKi0GEDZUF_KSfjKW0nV0Aew" />
    """
    st.markdown(SEO_text, unsafe_allow_html=True)

custom_CSS = """
    <style>
    /* --- Title styling --- */
    .date-title {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: -3rem;
        margin-top: -3.8rem;
        margin-left: -2.5rem
    }
    /* --- Center text inputs --- */
    div[data-testid="stTextInput"] {
        display: flex;
        justify-content: center;
    }
    div[data-testid="stTextInput"] input {
        text-align: center !important;
    }
    </style>
    """

custom_mobile_CSS = """
        <style>
        /* Allow columns to shrink on small screens */
        @media (max-width: 600px) {
            .stColumn {
                flex: 1 !important;
                min-width: 0 !important;
            }
        }
        </style>
        """

# if __name__ == '__main__':
#     launch_GUI()