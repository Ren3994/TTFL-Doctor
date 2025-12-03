from supabase import create_client
import streamlit as st
import pandas as pd
import subprocess
import sqlite3
import base64
import deepl
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

@st.cache_resource(show_spinner=False)
def conn_deepl():
    api_key = st.secrets.get("DEEPL_API_KEY", "unknown")
    return deepl.DeepLClient(api_key)

@st.cache_data(show_spinner=False, ttl=60)
def deepl_api_limit_reached():
    deepl_client = conn_deepl()
    usage = deepl_client.get_usage()

    limit_reached = usage.any_limit_reached
    used_count = usage.character.count
    limit = usage.character.limit

    remaining = f'{used_count}/{limit}'

    return limit_reached, remaining

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
    
def SEO(loc):
    header_text = ("TTFL Doctor : "
                   "Tableau des picks du soir, récaps des stats par jour, scores TTFL en direct, et tous types de statistiques avancées pour la TrashTalk Fantasy League. "
                   "Optimisez vos picks et évitez les 🥕 !")
    
    footer_text = ("App développée par Renaud Génin | © 2025<br>"
                   "Mot-clés : trashtalk, trashtalk fantasy league, ttfl, best pick, fantasy nba, "
                   "fantasy league, statistiques ttfl, stats ttfl, picks fantasy, blessures")
    
    if loc == 'header':
        st.markdown(header_text)
    elif loc == 'footer':
        st.markdown(footer_text, unsafe_allow_html=True)

@st.dialog('Requêtes / Bugs')
def requests_form():
    request_type = st.segmented_control('Vous voulez...', ['Signaler un bug', 'Demander une nouvelle fonctionnalité'])
    description = st.text_input('request_description', placeholder='Description', label_visibility='collapsed')
    contact = st.text_input('contact', label_visibility='collapsed', placeholder='Contact (optionnel)')
    if st.button('OK'):
        supabase = conn_supabase()
        insert = (supabase.table("requests")
                          .insert({"username" : st.session_state.get('username', 'no user'),
                                   "request_type" : request_type,
                                   "request_description" : description,
                                   "contact" : contact})
                          .execute())
        st.success('Requête enregistrée ✅')

def custom_button_css(selected, fontsize=18):
    bkg_color = "#44454E" if selected else '#131720'
    hover_color = "#53555C" if selected else '#262831'
    fontsize = f'{fontsize}px'
    text_color = "#FFFFFF"
    button_css = [f"""
        div.stButton button {{
            background-color: {bkg_color};
        }}""", f"""
        div.stButton > button > div > p {{
            font-size: {fontsize} !important;
            color: {text_color} !important;
        }}""", f"""
        div.stButton > button > div > p > img {{
            width: 50px !important;
            height: 50px !important;
        }}""", f"""
        div.stButton button:hover {{
            background-color: {hover_color};
        }}
    """]
    return button_css

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