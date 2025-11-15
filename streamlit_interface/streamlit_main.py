from zoneinfo import ZoneInfo
from datetime import datetime
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.injury_report_manager import update_injury_report
from update_manager.nba_api_manager import update_nba_data
from streamlit_interface.streamlit_utils import config, conn_db
from streamlit_interface.sidebar import sidebar
from data.sql_functions import update_tables

# ---------- Initialize session state ----------
config(page='main')

if "data_ready" not in st.session_state:
    st.session_state.data_ready = False

env = st.secrets.get("environment", "unknown")
if 'local_instance' not in st.session_state:
    if env == 'local':
        st.session_state.local_instance = True
    elif env == 'cloud':
        st.session_state.local_instance = False

# --- Sidebar ---
sidebar(page='main')

# --- Trigger updates if needed ---
if not st.session_state.data_ready:

    st.title('🏀 TTFL Doctor')
    conn = conn_db()

    with st.spinner('Mise à jour des données'):
        progress = st.progress(0)
        status = st.empty()
        status.text("Injury report :\nDonnées NBA :\nTables de calculs :")
        update_injury_report(conn)
        status.text("Injury report : ✅\nDonnées NBA : \nTables de calculs :")
        progress.progress(10/100)
        update_nba_data(conn=conn, progress=progress, status=status)
        status.text("Injury report : ✅\nDonnées NBA : ✅\nTables de calculs :")
        update_tables(conn, progress)
        status.text("Injury report : ✅\nDonnées NBA : ✅\nTables de calculs : ✅")

        st.session_state.data_ready = True
        st.session_state.last_update = datetime.now(ZoneInfo("Europe/Paris"))
        
    st.switch_page('pages/1_Classement_TTFL.py')
else:
    st.switch_page('pages/1_Classement_TTFL.py')