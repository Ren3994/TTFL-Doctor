import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, vspace, get_sc, custom_error, st_image_crisp, custom_button_css, custom_CSS, custom_mobile_CSS
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.live_scores_utils import get_live_games
from streamlit_interface.classement_TTFL_utils import get_pick
from streamlit_interface.top_nuit_utils import *
from streamlit_interface.sidebar import sidebar
from misc.misc import RESIZED_LOGOS_PATH

# ---------- Initialize session state ----------
PAGENAME = 'top_nuit'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)
sc = get_sc()

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Scores TTFL de la nuit</div>', unsafe_allow_html=True)

if st.session_state.mobile_layout:
    st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
    cont = st.container(horizontal_alignment='center', gap='medium')
    cont_date_obj = cont.container(horizontal=True, horizontal_alignment='center')
    cont_left = cont.container(horizontal_alignment='center')
    cont_lower = cont.container(horizontal=True, horizontal_alignment='center')
    buttons_per_row = 4
else:
    cont = st.container(horizontal_alignment='center')
    cont_upper = cont.container(horizontal=True, horizontal_alignment='center', gap="small")
    cont_lower = cont.container(horizontal=True, gap='medium')
    cont_left = cont_upper.container(horizontal_alignment='center', width=300)
    cont_center = cont_upper.container(horizontal_alignment='center')
    cont_right = cont_upper.container(horizontal_alignment='center', width=300)
    cont_date_obj = cont_center.container(horizontal=True, horizontal_alignment='center')
    buttons_per_row = 8
    
cont_date_obj.button("◀️", on_click=prev_date_nuit, key='prev_button_nuit')

cont_date_obj.text_input(
    label="date top nuit",
    key="date_text_nuit",
    on_change=on_text_change_nuit,
    label_visibility="collapsed",
    width=120)
if st.session_state.get("text_parse_error_nuit", False):
    custom_error('Format invalide<br>JJ/MM/AAAA', fontsize=13, container=cont_date_obj)

cont_date_obj.button("▶️", on_click=next_date_nuit, key='next_button_nuit')

cont_left.toggle('Boxscores par équipes', key='byteam', on_change=clear_boxscore_vars)
spoiler = cont_right.toggle('Éviter les spoilers')
if spoiler:
    cont_right.toggle('Montrer TTFL', key='show_TTFL')

update_top_nuit(st.session_state.date_text_nuit, 
                st.session_state.get('matched_players_nuit', ''), 
                st.session_state.get('byteam', False),
                st.session_state.get('show_my_pick', False),
                spoiler, 
                st.session_state.get('show_TTFL', False))

if st.session_state.top_nuit is None:
    st.subheader(f"Pas de matchs NBA le {st.session_state.date_text_nuit}")
    vspace(50)
elif st.session_state.top_nuit == 'hier':
    live_data = get_live_games()
    pending_games = live_data['pending_games']
    if pending_games:
        st.subheader('Des matchs sont en cours actuellement')
        vspace(3)
        cont_see_live_games = st.container(horizontal_alignment='center')
        
        if cont_see_live_games.button('Voir les scores en direct'):
            # st.session_state.global_boxscores = True
            st.switch_page('pages/4_Scores_TTFL_en_direct.py')
    else:
        st.subheader(f"Pas encore de données pour les matchs du {st.session_state.date_text_nuit}")

    vspace(50)
else:
    cont_lower.text_input(label='Rechercher joueur', 
                          placeholder='Rechercher joueur', 
                          key='search_player_nuit', 
                          on_change=on_search_player_nuit,
                          label_visibility="collapsed",
                          width=200)
    cont_lower.button('OK')
    cont_lower.button('Clear', on_click=clear_search)

    pick, pick_team = get_pick(date=st.session_state.date_text_nuit, team=True)
    if pick is not None:
        cont_lower.button('Mon pick', on_click=show_my_pick, args=(pick, ))
            
    if st.session_state.top_nuit == 'did_not_play':
        st.subheader(f'Pas de boxscores pour {st.session_state.matched_players_nuit[0]} '
                     f'le {st.session_state.date_text_nuit}')
        vspace(50)
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
                                st.session_state[f'boxscore_nuit_{team}'], 
                                min_width=60, button_team=team, pick_team=pick_team)):
                                
                                st.button(f'![icon](data:image/png;base64,{logo}) {team}', 
                                          key=f'button_nuit_{team}', 
                                          width=60,
                                          on_click=lambda k=team: st.session_state.update(
                                                   {f"boxscore_nuit_{k}": 
                                                    not st.session_state[f"boxscore_nuit_{k}"]}))
                                
            for team, top in st.session_state.top_nuit.items():
                if st.session_state[f'boxscore_nuit_{team}']:
                    st.markdown(top, unsafe_allow_html=True)

SEO('footer')