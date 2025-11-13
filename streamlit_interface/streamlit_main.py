from streamlit_js_eval import streamlit_js_eval
from zoneinfo import ZoneInfo
from datetime import datetime
import streamlit as st
import keyboard
import signal
import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.injury_report_manager import update_injury_report
from update_manager.nba_api_manager import update_nba_data
from update_manager.file_manager import cleanup_db
from data.sql_functions import update_tables
from misc.misc import ICON_PATH

st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")

st.markdown(
    f'<link rel="icon" href="{ICON_PATH}" type="image/png">',
    unsafe_allow_html=True
)

# ---------- Initialize session state ----------

env = st.secrets.get("environment", "unknown")
if env == 'local':
    st.session_state.local_instance = True
elif env == 'cloud':
    st.session_state.local_instance = False

if "data_ready" not in st.session_state:
    st.session_state.data_ready = False

if "scr_key" not in st.session_state:
    st.session_state.scr_key = str(uuid.uuid4())

if "screen_width" not in st.session_state:
    width = streamlit_js_eval(js_expressions='screen.width', key=st.session_state.scr_key)
    if width:
        st.session_state.screen_width = width

# --- Sidebar ---
if "last_update" in st.session_state:
    st.sidebar.write(f"MàJ : {datetime.strftime(st.session_state.last_update, '%d %b. à %Hh%M')}")

if st.session_state.local_instance:
    if st.sidebar.button("🛑 Quitter"):
        keyboard.press_and_release('ctrl+w')
        cleanup_db()
        os.kill(os.getpid(), signal.SIGTERM)

if st.session_state.data_ready:
    if st.sidebar.button("Mettre à jour les données"):
        st.session_state.data_ready = False
        st.rerun()

# --- Trigger updates if needed ---

if not st.session_state.data_ready:

    st.title('🏀 TTFL Doctor')

    with st.spinner('Mise à jour des données'):
        progress = st.progress(0)
        status = st.empty()
        status.text("Injury report :\nDonnées NBA :\nTables de calculs :")
        update_injury_report()
        status.text("Injury report : ✅\nDonnées NBA : \nTables de calculs :")
        progress.progress(10/100)
        update_nba_data(progress=progress, status=status)
        status.text("Injury report : ✅\nDonnées NBA : ✅\nTables de calculs :")
        update_tables(progress)
        status.text("Injury report : ✅\nDonnées NBA : ✅\nTables de calculs : ✅")

        st.session_state.data_ready = True
        st.session_state.last_update = datetime.now(ZoneInfo("Europe/Paris"))
        
    st.switch_page('pages/1_classement_TTFL.py')
else:
    st.switch_page('pages/1_classement_TTFL.py')