from streamlit_extras.add_vertical_space  import add_vertical_space as vspace
from streamlit_extras.stylable_container import stylable_container as sc
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import config, custom_error, st_image_crisp, custom_button_css, custom_CSS, custom_mobile_CSS
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.top_nuit_utils import *
from streamlit_interface.sidebar import sidebar
from misc.misc import RESIZED_LOGOS_PATH

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
    col_toggle = st.columns([1])[0]
    col_search, col_ok, col_clear = st.columns([10, 1, 1], gap="small")
    buttons_per_row = 4
else:
    cols_top = st.columns([4, 0.7, 1.5, 0.7, 4], gap="small")
    col_prev, col_date, col_next = cols_top[1], cols_top[2], cols_top[3]
    col_search, col_ok, col_clear, col_spacer = st.columns([7, 2.5, 3, 8], gap='small', width=500)
    col_toggle = cols_top[0]
    buttons_per_row = 8
    
with col_prev:
    st.button("◀️", on_click=prev_date_nuit, key='prev_button_nuit')

with col_next:
    st.button("▶️", on_click=next_date_nuit, key='next_button_nuit')

with col_date:
    st.text_input(
        label="date top nuit",
        key="date_text_nuit",
        on_change=on_text_change_nuit,
        label_visibility="collapsed",
        width=120)
    if st.session_state.get("text_parse_error_nuit", False):
        custom_error('Format invalide<br>JJ/MM/AAAA', fontsize=13)

with col_toggle:
    st.toggle('Boxscores par équipes', key='byteam', on_change=clear_boxscore_vars)

update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), st.session_state.get('search_player_nuit', ''), st.session_state.byteam)

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
        if not st.session_state.byteam:
            st.markdown(st.session_state.top_nuit, unsafe_allow_html=True)
        else:
            teams = list(st.session_state.top_nuit.keys())
            for i in range(0, len(teams), buttons_per_row):
                cols = st.columns(buttons_per_row, gap="small")
                vspace()
                row_items = teams[i:i + buttons_per_row]
                for col, team in zip(cols, row_items):
                    logo = st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, f"{team}.png"), raw = True)
                    st.session_state.setdefault(f"boxscore_nuit_{team}", False)
                    if i < len(st.session_state.top_nuit):
                        with col:
                            with sc(key=f"custom_button_css_{team}", css_styles=custom_button_css(
                                st.session_state[f'boxscore_nuit_{team}'])):
                                st.button(f'![icon](data:image/png;base64,{logo}) {team}', key=f'button_nuit_{team}', 
                                        on_click=lambda k=team: st.session_state.update(
                                        {f"boxscore_nuit_{k}": not st.session_state[f"boxscore_nuit_{k}"]}),
                                        width=80)
                                
            for team, top in st.session_state.top_nuit.items():
                if st.session_state[f'boxscore_nuit_{team}']:
                    st.markdown(top, unsafe_allow_html=True)