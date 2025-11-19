import streamlit as st
from datetime import date, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.streamlit_utils import config, custom_error
from streamlit_interface.classement_TTFL_utils import *
from streamlit_interface.player_stats_utils import *
# from streamlit_interface.top_nuit_utils import *
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'stats_equipes'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Statistiques des équipes</div>', unsafe_allow_html=True)

st.subheader('Work in progress...')