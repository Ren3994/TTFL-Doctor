import streamlit as st
from datetime import date, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.streamlit_utils import config, custom_error
from streamlit_interface.classement_TTFL_utils import *
from streamlit_interface.top_nuit_utils import *
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'top_nuit'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Scores TTFL de la nuit</div>', unsafe_allow_html=True)

col_spacer1, col_prev, col_date, col_next, col5 = st.columns([4, 0.7, 1.5, 0.7, 4])
with col_prev:
    st.button("◀️", on_click=prev_date_nuit, key='prev_button_nuit')

with col_next:
    st.button("◀️", on_click=next_date_nuit, key='next_button_nuit')

with col_date:
    st.text_input(
        label="date top nuit",
        key="date_text_nuit",
        on_change=on_text_change_nuit,
        label_visibility="collapsed",
        width=120)
    if st.session_state.get("text_parse_error_nuit", False):
        custom_error('Format invalide<br>JJ/MM/AAAA', fontsize=13)

if st.session_state.top_nuit is None:
    st.subheader(f"Pas de matchs NBA le {st.session_state.selected_date_nuit.strftime('%d/%m/%Y')}")
elif st.session_state.top_nuit == 'hier':
    st.subheader(f"Pas encore de données pour les matchs du {st.session_state.selected_date_nuit.strftime('%d/%m/%Y')}")
else:
    st.markdown(st.session_state.top_nuit, unsafe_allow_html=True)