import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.streamlit_utils import config, SEO

# ---------- Initialize session state ----------
PAGENAME = 'main'
init_session_state(PAGENAME)
config(page=PAGENAME)
SEO()

st.switch_page('pages/1_Classement_TTFL.py')