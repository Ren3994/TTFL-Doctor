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

mobile = st.session_state.get("screen_width", 1000) <= 500
if mobile:
    st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
    cols_top = st.columns([1, 5, 1], gap="small")
    col_prev, col_date, col_next = cols_top[0], cols_top[1], cols_top[2]
    col_search, col_ok, col_clear, col_spacer = st.columns([6, 1, 1, 1], gap="small")
else:
    cols_top = st.columns([4, 0.7, 1.5, 0.7, 4], gap="small")
    col_prev, col_date, col_next = cols_top[1], cols_top[2], cols_top[3]
    col_search, col_ok, col_clear, col_spacer = st.columns([7, 2.5, 3, 8], gap='small', width=500)
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

update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), st.session_state.get('search_player_nuit', ''))

if st.session_state.top_nuit is None:
    st.subheader(f"Pas de matchs NBA le {st.session_state.selected_date_nuit.strftime('%d/%m/%Y')}")
elif st.session_state.top_nuit == 'hier':
    st.subheader(f"Pas encore de données pour les matchs du {st.session_state.selected_date_nuit.strftime('%d/%m/%Y')}")
else:
    with col_search:
        st.text_input(label='Rechercher joueur', placeholder='Rechercher joueur', key='search_player_nuit', on_change=on_search_player_nuit, width=200, label_visibility="collapsed")
    with col_ok:
        st.button('OK')
    with col_clear:
        st.button('Clear', on_click=clear_search)
            
    if st.session_state.top_nuit == 'did_not_play':
        st.subheader(f'Pas de boxscores pour {st.session_state.search_player_nuit} le {st.session_state.selected_date_nuit.strftime('%d/%m/%Y')}')
    else:
        st.markdown(st.session_state.top_nuit, unsafe_allow_html=True)