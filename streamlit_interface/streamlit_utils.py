import streamlit as st
import subprocess
import base64
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.resource_manager import conn_supabase
from misc.misc import STREAMLIT_MAIN_PY_PATH, TBD_LOGO_PATH
from streamlit_interface.color_palette import get_palette

def launch_GUI():
    subprocess.run([sys.executable, "-m", "streamlit", "run", STREAMLIT_MAIN_PY_PATH])

def config(page):
    st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout='wide')

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

def custom_error(error_text, fontsize, center_text=True, container=None):
    error = f"""
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
            """
    if container is None:
        st.markdown(error, unsafe_allow_html=True)
    else:
        container.markdown(error, unsafe_allow_html=True)
    
def SEO(loc):
    header_text = ("TTFL Doctor : "
                   "Tableau des picks du soir, récaps des stats par jour, scores TTFL en direct, et tous types de statistiques avancées pour la TrashTalk Fantasy League. "
                   "Optimisez vos picks et évitez les 🥕 !")
    
    footer_text = ("Mot-clés : trashtalk, trashtalk fantasy league, ttfl, best pick, fantasy nba, "
                   "fantasy league, statistiques ttfl, stats ttfl, picks fantasy, blessures<br>"
                   "App développée par Renaud Génin | © 2025")
    
    if loc == 'header':
        st.markdown(header_text)
    elif loc == 'footer':
        st.markdown(footer_text, unsafe_allow_html=True)

def is_mobile_layout():
    MOBILE_KEYWORDS = [
    "iphone", "android", "mobile", "blackberry", "nokia",
    "windows phone", "opera mini", "opera mobi", "kindle fire",
    "silk/", "palm", "symbian", "fennec", "webos"]

    TABLET_KEYWORDS = ["ipad", "tablet", "kindle", "nexus 7", "nexus 10", "sm-t", "silk/"]

    user_agent = st.context.headers.get("User-Agent", '') or ''
    ua_lower = user_agent.lower()

    mobile = any(k in ua_lower for k in MOBILE_KEYWORDS)
    tablet = any(k in ua_lower for k in TABLET_KEYWORDS)

    if "android" in ua_lower and not "mobile" in ua_lower:
        tablet = True

    if mobile and not tablet:
        return True
    
    return False

@st.dialog('Requêtes / Bugs')
def requests_form():
    request_type = st.segmented_control('Vous voulez...', 
                                        ['Signaler un bug', 'Demander une nouvelle fonctionnalité'])
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

def centered(sidebar=False, origin=None):
    if origin is None:
        if sidebar:
            return st.sidebar.container(horizontal_alignment='center')
        else:
            return st.container(horizontal_alignment='center', border=True)
    else:
        return origin.container(horizontal_alignment='center', border=True)
    
def vspace(numlines=1, container=None):
    if container is None:
        for _ in range(numlines):
            st.write('')
    else :
        for _ in range(numlines):
            container.write('')

def uspace(numlines = 1):
    unicode_space = '\u00A0'
    return unicode_space * numlines

@st.cache_resource(show_spinner=False)
def get_sc():
    from streamlit_extras.stylable_container import stylable_container as sc
    return sc

def custom_button_css(selected, fontsize=18, min_width=0, button_team=None, pick_team=None):
    palette = get_palette('button')
    
    bkg_color = palette['bkg_selected'] if selected else palette['bkg']
    hover_color = palette['hover_selected'] if selected else palette['hover']
    text_color = palette['text']

    if pick_team is not None and button_team is not None:
        if pick_team in button_team:
            bkg_color = palette['pick_bkg_selected'] if selected else palette['pick_bkg']
            hover_color = palette['pick_hover_selected'] if selected else palette['pick_hover']
            text_color = palette['pick_text']    

    fontsize = f'{fontsize}px'

    button_css = [f"""
        div.stButton button {{
            background-color: {bkg_color};
            min-width: {min_width};
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
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: -3rem;
        margin-top: -3.8rem;
        margin-left: -2.5rem
    }
    .big-button button {
    font-size: 30px !important;
    font-weight: bold !important;
    }
    .big-text {
        text-align:center;
        font-size:22px;
        font-weight:bold;
        margin-bottom: 3rem;
    }
    .centered-text {
        text-align:center;
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