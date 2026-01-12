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

if 'slider_gp' not in st.session_state:
    set_filters_default()
    reset_filters()

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Statistiques des joueurs</div>', unsafe_allow_html=True)

cont_search = st.container(horizontal=True)
cont_show_compared_players = st.container(horizontal=True)
vspace()

# Player(s) search box
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

# Update tables to account for searched players and filters
update_player_stats(players_to_show)

# Filters
filter_exp_str, filter_exp_bool = filter_expander_vars()
with st.expander(filter_exp_str, expanded=filter_exp_bool):
    cont_exp_filters = st.container(horizontal_alignment='center')
    cont_check = cont_exp_filters.container(horizontal_alignment='center', horizontal=True, gap="large")
    cont_check_left = cont_check.container(horizontal_alignment='center')
    cont_check_left.checkbox('Stats historiques', key='player_alltime_stats', on_change=alltime_checked,
                             help='Toutes les stats de tous les joueurs depuis la saison 1946-47. Certaines données sont manquantes ou erronnées, surtout pour les vieilles saisons (stl, tov, min, ...). Pour avoir un score TTFL approximatif, ils ont été mis à 0.')
    if st.session_state.player_alltime_stats:
        cont_check_left.checkbox('Juste joueurs actifs', key='only_active_players')

    cont_check.segmented_control('Aggregation', ['Moyennes', 'Totaux', 'Moyennes par 36 min'], 
                                 key = 'player_stats_agg', 
                                 label_visibility='collapsed')
    
    disable_color_chkbox = st.session_state.massive_tables
    help_str_color = 'Les tableaux sont trop gros' if disable_color_chkbox else None
    cont_check.checkbox('Colorer cases', key='color_cells', disabled=disable_color_chkbox, help=help_str_color)
    cont_check.button('Reset filtres', on_click=reset_filters)
    cont_sliders = cont_exp_filters.container(horizontal=True, horizontal_alignment='center')
    cont_sliders.slider('Nombre de matchs', key='slider_gp', min_value=0, step=1,
                        max_value=st.session_state.max_games)
    cont_sliders.slider('Minutes par match', key='slider_min', min_value=0, step=1,
                        max_value=st.session_state.max_min)
    cont_sliders.slider('Tirs', key='slider_fg', min_value=0, step=1,
                        max_value=st.session_state.max_fg)
    cont_sliders.slider('Tirs à 3 points', key='slider_fg3', min_value=0, step=1,
                        max_value=st.session_state.max_fg3)
    cont_sliders.slider('Lancers francs', key='slider_ft', min_value=0, step=1,
                        max_value=st.session_state.max_ft)
        
    st.write('NB : Colorer les cases va faire lagger si les tableaux sont gros')

# Display stats tables
for table in st.session_state.player_stats:
    df = st.session_state.player_stats[table]
    if df.empty:
        if table == 'Statistiques basiques':
            st.write("Aucun joueur trouvé. Essayez de cocher 'Stats historiques' ou bien de modifier les filtres")
    else:
        table_str = table
        if table == 'Statistiques du joueur par adversaire':
            table_str = table.replace('du joueur', f'de {players_to_show[0]}')
        elif (table in ['Statistiques basiques', 'Statistiques de tir/avancées'] and 
            st.session_state.player_stats_agg != 'Moyennes'):
            table_str +=  f' {uspace(2)} ● {uspace(2)} {st.session_state.player_stats_agg}'
        with st.expander(table_str, expanded=len(players_to_show) >= 1):
            show_df = df
            excluded_cols = ['playerName', 'teamTricode', 'MINUTES', 'GP', 'TOT_MINUTES', 'opponent']
            negative_cols = ['Tov', 'TOT_Tov', 'stddev_TTFL']
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

# Display individual stats tables
onlyone = len(players_to_show) == 1

with st.expander('Graphiques des performances', expanded=onlyone):
    cont = st.container(horizontal_alignment='center', horizontal=True)
    cont.segmented_control('Stats à montrer', ['TTFL', 'Pts', 'Reb', 'Ast', 'Stl', 'Blk', 'Tov', 'FG', 'FGA', 'FG3', 'FG3A', 'FT', 'FTA', '±'], 
                         key='stats_to_plot', 
                         default='TTFL',
                         selection_mode='multi',
                         label_visibility='collapsed')
    cont_chk = cont.container(horizontal_alignment='center')
    cont_chk.checkbox('Relier les points', key='show_lines', value=True)
    cont_chk.checkbox('Moyennes', key='show_avg', value=True)

    if len(players_to_show) == 1:
        if not st.session_state.stats_to_plot:
            cont.write('Sélectionnez une ou plusieurs stats à afficher')
        else:
            player = players_to_show[0]
            fig = get_plot(player, st.session_state.stats_to_plot, 
                                   st.session_state.show_lines,
                                   st.session_state.show_avg)
            st.plotly_chart(fig)

expander_hist_title = 'Choisissez un joueur pour voir ses stats par match et par adversaire' if not onlyone else f'Lignes de stats de {players_to_show[0]}'
with st.expander(expander_hist_title, expanded=onlyone):
    if len(players_to_show) == 1:
        player = players_to_show[0]
        hist_perfs = historique_des_perfs(player)
        st.markdown(hist_perfs, unsafe_allow_html=True)

vspace(30)

SEO('footer')