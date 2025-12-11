import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, vspace, custom_CSS
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from misc.misc import FRENCHIES, PLAYER_STATS_COLUMN_DEF
from streamlit_interface.player_stats_utils import *
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'stats_joueurs'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Statistiques des joueurs</div>', unsafe_allow_html=True)

cont_sliders = st.container(horizontal=True, horizontal_alignment='center')
cont_search = st.container(horizontal=True)
cont_show_compared_players = st.container(horizontal=True)
vspace()

vspace(container=cont_sliders)
slider_gp = cont_sliders.slider('Nombre de matchs minimum', key='slider_gp',
                                min_value=0, max_value=82, value=10, step=1, width=300)
vspace(container=cont_sliders)
slider_min = cont_sliders.slider('Minutes par match minimum', key='slider_min',
                                 min_value=0, max_value=48, value=10, step=1, width=300)
totals = cont_sliders.toggle('Voir les totaux', key='player_stats_agg')

cont_search.text_input(label='Rechercher joueur', 
                          placeholder='Rechercher joueur', 
                          key='search_player_indiv_stats', 
                          on_change=on_search_player_stats,
                          label_visibility="collapsed",
                          width=200)

cont_search.button('OK')
cont_search.button('Clear', on_click=clear_search)
cont_search.button('Ajouter au comparateur', on_click=add_compare)
cont_search.button('Vider le comparateur', on_click=clear_compare)
if cont_search.button('🇫🇷 Les Frenchies 🇫🇷'):
    st.session_state.player_stats_matched = FRENCHIES


players_to_show = []
if len(st.session_state.compare_players) > 0:
    players_to_show = st.session_state.compare_players
elif st.session_state.player_stats_matched != '':
    players_to_show = st.session_state.player_stats_matched

st.session_state.player_stats = get_all_player_stats(slider_gp, slider_min, players_to_show, totals)

for table in st.session_state.player_stats:
    df = st.session_state.player_stats[table]
    with st.expander(table, expanded=len(players_to_show) > 0):
        if table in ['Statistiques avancées', 'Statistiques de tir']:
            cont_sliders_fg = st.container(horizontal=True, horizontal_alignment='center')
            fg = cont_sliders_fg.slider('FG minimum', value=0, min_value=0, 
                                        max_value=df['TOT_FGM'].max(),
                                        key=f'slider_fg_{table}')
            fg3 = cont_sliders_fg.slider('FG3 minimum', value=0, min_value=0, 
                                         max_value=df['TOT_FG3M'].max(),
                                        key=f'slider_fg3_{table}')
            ft = cont_sliders_fg.slider('FT minimum', value=0, min_value=0, 
                                        max_value=df['TOT_FTM'].max(),
                                        key=f'slider_ft_{table}')
            df = df[df['TOT_FGM'] > fg]
            df = df[df['TOT_FG3M'] > fg3]
            df = df[df['TOT_FTM'] > ft]
            if not totals:
                df = df.drop(columns=['TOT_FGM', 'TOT_FG3M', 'TOT_FTM'])
        st.dataframe(df, height='content', hide_index=True,
                    column_config={stat : (
                        st.column_config.NumberColumn(
                        PLAYER_STATS_COLUMN_DEF[stat]['display'],
                        width = PLAYER_STATS_COLUMN_DEF[stat]['width'],
                        format = PLAYER_STATS_COLUMN_DEF[stat]['format'],
                        help = PLAYER_STATS_COLUMN_DEF[stat]['help'])
                        if PLAYER_STATS_COLUMN_DEF[stat]['col'] == 'num' else 
                        st.column_config.TextColumn(
                        PLAYER_STATS_COLUMN_DEF[stat]['display'],
                        width = PLAYER_STATS_COLUMN_DEF[stat]['width'],
                        help = PLAYER_STATS_COLUMN_DEF[stat]['help']))
                        for stat in df})

vspace(30)

SEO('footer')