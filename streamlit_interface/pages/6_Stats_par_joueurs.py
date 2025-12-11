import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, vspace, custom_CSS
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.player_stats_utils import *
from streamlit_interface.sidebar import sidebar
from misc.misc import FRENCHIES

# ---------- Initialize session state ----------
PAGENAME = 'stats_joueurs'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Statistiques des joueurs</div>', unsafe_allow_html=True)

TEAM_STATS_COLUMN_DEF = {
    
    # Regular stats
    'playerName' : {'col' : 'text', 'display' : 'Joueur', 'format' : None, 'width' : 150, 'help' : None},
    'teamTricode' : {'col' : 'text', 'display' : 'Équipe', 'format' : None, 'width' : 45, 'help' : None},
    'GP' : {'col' : 'num', 'display' : 'GP', 'format' : None, 'width' : 35, 'help' : 'Nombre de matchs joués'},
    'Pts' : {'col' : 'num', 'display' : 'Pts', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de points marqués'},
    'Ast' : {'col' : 'num', 'display' : 'Ast', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de passes décisives'},
    'Reb' : {'col' : 'num', 'display' : 'Reb', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de rebonds'},
    'Oreb' : {'col' : 'num', 'display' : 'Oreb', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de rebonds offensifs'},
    'Dreb' : {'col' : 'num', 'display' : 'Dreb', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de rebonds défensifs'},
    'Stl' : {'col' : 'num', 'display' : 'Stl', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne d\'interceptions'},
    'Blk' : {'col' : 'num', 'display' : 'Blk', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de tirs contrés'},
    'Tov' : {'col' : 'num', 'display' : 'Tov', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne de balles perdues'},
    'Stk' : {'col' : 'num', 'display' : 'Stk', 'format' : '%.1f', 'width' : 35, 'help' : 'Stocks : steals + blocks'},
    'TTFL' : {'col' : 'num', 'display' : 'TTFL', 'format' : '%.1f', 'width' : 35, 'help' : 'Moyenne TTFL'},
    'ttfl_per_min' : {'col' : 'num', 'display' : 'TTFL/min', 'format' : '%.2f', 'width' : 70, 'help' : 'Moyenne TTFL par minute'},
    'PM' : {'col' : 'num', 'display' : '±', 'format' : '%+.1f', 'width' : 40, 'help' : 'Plus/minus'},
    
    # Advanced stats
    'ast_to_tov' : {'col' : 'num', 'display' : 'Ast/tov', 'format' : '%.2f', 'width' : 60, 'help' : 'Moyenne de passes décisives divisée par la moyenne de balles perdues'},
    'FG3_ratio' : {'col' : 'num', 'display' : 'Ratio 3pts', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs tentés qui sont des 3 pts'},
    'MINUTES' : {'col' : 'text', 'display' : 'Min', 'format' : None, 'width' : 45, 'help' : 'Moyenne de minutes jouées par match'},
    'EFG' : {'col' : 'num', 'display' : 'eFG%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Moyenne aux tirs pondérée qui prend en compte que les tirs à 3 points valent plus'},
    'TS' : {'col' : 'num', 'display' : 'TS%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Moyenne aux tirs pondérée pour prendre en compte les 3 points et les lancers francs'},

    # Shooting stats
    'FGM' : {'col' : 'num', 'display' : 'FG', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs marqués'},
    'FGA' : {'col' : 'num', 'display' : 'FGA', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs tentés'},
    'FG_PCT' : {'col' : 'num', 'display' : 'FG%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs réussis'},
    'FG3M' : {'col' : 'num', 'display' : 'FG3', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 3 points marqués'},
    'FG3A' : {'col' : 'num', 'display' : 'FG3A', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 3 points tentés'},
    'FG3_PCT' : {'col' : 'num', 'display' : 'FG3%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs à 3 pts réussis'},
    'FTM' : {'col' : 'num', 'display' : 'FT', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de lancers-francs réussis'},
    'FTA' : {'col' : 'num', 'display' : 'FTA', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de lancers-francs tentés'},
    'FT_PCT' : {'col' : 'num', 'display' : 'FT%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de lancers-francs réussis'},
    'FG2M' : {'col' : 'num', 'display' : 'FG2', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 2 pts réussis'},
    'FG2A' : {'col' : 'num', 'display' : 'FG2A', 'format' : '%.1f', 'width' : 50, 'help' : 'Moyenne de tirs à 2 pts tentés'},
    'FG2_PCT' : {'col' : 'num', 'display' : 'FG2%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de tirs à 2 pts réussis'},
}

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
vspace(container=cont_sliders)

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
if cont_search.button('Les Frenchies'):
    st.session_state.player_stats_matched = FRENCHIES


players_to_show = []
if len(st.session_state.compare_players) > 0:
    players_to_show = st.session_state.compare_players
elif st.session_state.player_stats_matched != '':
    players_to_show = st.session_state.player_stats_matched

st.session_state.player_stats = get_all_player_stats(slider_gp, slider_min, players_to_show)

for table in st.session_state.player_stats:
    with st.expander(table, expanded=len(players_to_show) > 0):
        st.dataframe(st.session_state.player_stats[table], height='content', hide_index=True,
                    column_config={stat : (
                        st.column_config.NumberColumn(
                        TEAM_STATS_COLUMN_DEF[stat]['display'],
                        width = TEAM_STATS_COLUMN_DEF[stat]['width'],
                        format = TEAM_STATS_COLUMN_DEF[stat]['format'],
                        help = TEAM_STATS_COLUMN_DEF[stat]['help'])
                        if TEAM_STATS_COLUMN_DEF[stat]['col'] == 'num' else 
                        st.column_config.TextColumn(
                        TEAM_STATS_COLUMN_DEF[stat]['display'],
                        width = TEAM_STATS_COLUMN_DEF[stat]['width'],
                        help = TEAM_STATS_COLUMN_DEF[stat]['help']))
                        for stat in st.session_state.player_stats[table]})

vspace(30)

SEO('footer')