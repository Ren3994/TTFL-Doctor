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

cont_search = st.container(horizontal=True)
cont_show_compared_players = st.container(horizontal=True)
vspace()

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
    filters_to_zero()

players_to_show = []
if len(st.session_state.compare_players) > 0:
    players_to_show = st.session_state.compare_players
elif st.session_state.player_stats_matched != '':
    players_to_show = st.session_state.player_stats_matched

if 'slider_gp' not in st.session_state:
    reset_filters()

st.session_state.player_stats, maximums = get_all_player_stats(
    matched=players_to_show,
    min_games = st.session_state.slider_gp,
    min_min_per_game = st.session_state.slider_min,
    fg_min = st.session_state.slider_fg,
    fg3_min = st.session_state.slider_fg3,
    ft_min = st.session_state.slider_ft,
    totals = st.session_state.player_stats_agg)

if 'max_games' not in st.session_state:
    st.session_state.max_games = maximums['GP']
    st.session_state.max_fg = maximums['FG']
    st.session_state.max_fg3 = maximums['FG3']
    st.session_state.max_ft = maximums['FT']

with st.expander('Filtrer les résultats'):
    cont_sliders = st.container(horizontal=True, horizontal_alignment='center')
    cont_sliders.slider('Nombre de matchs', 
                        key='slider_gp',     
                        min_value=0, 
                        max_value=st.session_state.max_games, 
                        step=1)
    cont_sliders.slider('Minutes par match', 
                        key='slider_min',
                        min_value=0, 
                        max_value=48, 
                        step=1)
    cont_sliders.slider('Tirs', 
                        key='slider_fg',
                        min_value=0, 
                        max_value=st.session_state.max_fg, 
                        step=1)
    cont_sliders.slider('Tirs à 3 points', 
                        key='slider_fg3',
                        min_value=0, 
                        max_value=st.session_state.max_fg3, 
                        step=1)
    cont_sliders.slider('Lancers francs', 
                        key='slider_ft',
                        min_value=0, 
                        max_value=st.session_state.max_ft, 
                        step=1)
    
    cont_check = cont_sliders.container(horizontal_alignment='center')

    cont_check.checkbox('Voir les totaux', key='player_stats_agg')
    cont_check.checkbox('Colorer cases', key='color_cells')
    cont_check.button('Reset', on_click=reset_filters)

for table in st.session_state.player_stats:
    df = st.session_state.player_stats[table]
    if df.empty:
        if table == 'Statistiques basiques':
            st.write('Aucun joueur recherché ne correspond aux filtres')
    else:
        table_str = table
        if table == 'Statistiques du joueur par adversaire':
            table_str = table.replace('du joueur', f'de {players_to_show[0]}')
        with st.expander(table_str, expanded=len(players_to_show) > 1):
            show_df = df
            excluded_cols = ['playerName', 'teamTricode', 'MINUTES', 'GP', 'TOT_MINUTES', 'opponent']
            negative_cols = ['Tov', 'TOT_Tov']
            positive_in_df = [col for col in df.columns if col not in negative_cols and col not in excluded_cols]
            negative_in_df = [col for col in df.columns if col in negative_cols and col not in excluded_cols]

            if st.session_state.color_cells:
                show_df = (df.style
                       .background_gradient(
                            subset=positive_in_df,
                            cmap="YlGn")
                       .background_gradient(
                            subset=negative_in_df,
                            cmap="YlGn_r"))
                
            st.dataframe(show_df, height='content', hide_index=True,
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
                            help = PLAYER_STATS_COLUMN_DEF[stat]['help'],
                            pinned = True if stat == 'playerName' and 
                            st.session_state.mobile_layout else False))
                            for stat in df})

onlyone = len(players_to_show) == 1
expander_hist_title = 'Choisissez un joueur pour voir ses stats par match et par adversaire' if not onlyone else f'Lignes de stats de {players_to_show[0]}'
with st.expander(expander_hist_title, expanded=onlyone):
    if len(players_to_show) == 1:
        player = players_to_show[0]
        hist_perfs = historique_des_perfs(player)
        st.markdown(hist_perfs, unsafe_allow_html=True)

vspace(30)

SEO('footer')