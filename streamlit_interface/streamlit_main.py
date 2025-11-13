from zoneinfo import ZoneInfo
from datetime import datetime
import streamlit as st
import keyboard
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.injury_report_manager import update_injury_report
from update_manager.nba_api_manager import update_nba_data
from update_manager.file_manager import cleanup_db
from data.sql_functions import update_tables

# --- Check if running local or cloud version ---
env = st.secrets.get("environment", "unknown")
if env == 'local':
    st.session_state.local_instance = True
elif env == 'cloud':
    st.session_state.local_instance = False

st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")
    
# --- Sidebar ---
if "last_update" in st.session_state:
    st.sidebar.write(f"MàJ : {datetime.strftime(st.session_state.last_update, '%d %b. à %Hh%M')}")

if st.session_state.local_instance:
    if st.sidebar.button("🛑 Quitter"):
        keyboard.press_and_release('ctrl+w')
        cleanup_db()
        os.kill(os.getpid(), signal.SIGTERM)

if st.sidebar.button("Mettre à jour les données"):
    st.session_state.data_ready = False
    st.rerun()

# --- Trigger updates if needed ---
if "data_ready" not in st.session_state:
    st.session_state.data_ready = False
    st.session_state.first_update = True

if not st.session_state.data_ready:

    if st.session_state.first_update:
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
        st.session_state.first_update = False
        st.session_state.last_update = datetime.now(ZoneInfo("Europe/Paris"))
        
    st.switch_page('pages/1_classement_TTFL.py')
