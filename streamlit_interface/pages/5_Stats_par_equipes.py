import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, vspace, custom_CSS
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.team_stats_utils import get_team_stats
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
vspace(4)

team_stats = get_team_stats()

stats_dict = {
    
    # Regular stats
    'teamTricode' : {'col' : 'text', 'display' : 'Équipe', 'format' : None, 'width' : None, 'help' : None},
    'GP' : {'col' : 'num', 'display' : 'GP', 'format' : None, 'width' : None, 'help' : 'Nombre de matchs joués'},
    'W' : {'col' : 'num', 'display' : 'W', 'format' : None, 'width' : None, 'help' : 'Nombre de matchs gagnés'},
    'L' : {'col' : 'num', 'display' : 'L', 'format' : None, 'width' : None, 'help' : 'Nombre de matchs perdus'},
    'W_PCT' : {'col' : 'num', 'display' : 'W%', 'format' : "%.0f%%", 'width' : None, 'help' : 'Pourcentage de matchs gagnés'},
    'PTS' : {'col' : 'num', 'display' : 'Pts', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de points marqués'},
    'AST' : {'col' : 'num', 'display' : 'Ast', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de passes décisives'},
    'REB' : {'col' : 'num', 'display' : 'Reb', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de rebonds'},
    'OREB' : {'col' : 'num', 'display' : 'Oreb', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de rebonds offensifs'},
    'DREB' : {'col' : 'num', 'display' : 'Dreb', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de rebonds défensifs'},
    'STL' : {'col' : 'num', 'display' : 'Stl', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne d\'interceptions'},
    'BLK' : {'col' : 'num', 'display' : 'Blk', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs contrés'},
    'TOV' : {'col' : 'num', 'display' : 'Tov', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de balles perdues'},
    
    # Advanced stats
    'AST_TO' : {'col' : 'num', 'display' : 'Ast/tov', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de passes décisives divisée par la moyenne de balles perdues'},
    'AST_PCT' : {'col' : 'num', 'display' : 'Ast%', 'format' : "%.0f%%", 'width' : 60, 'help' : 'Pourcentage de tirs marqués après une passe décisive'},
    'REB_PCT' : {'col' : 'num', 'display' : 'Reb%', 'format' : "%.0f%%", 'width' : 60, 'help' : 'Pourcentage de rebonds captés'},
    'OREB_PCT' : {'col' : 'num', 'display' : 'Oreb%', 'format' : "%.0f%%", 'width' : 60, 'help' : 'Pourcentage de rebonds offensifs captés'},
    'DREB_PCT' : {'col' : 'num', 'display' : 'Dreb%', 'format' : "%.0f%%", 'width' : 60, 'help' : 'Pourcentage de rebonds défensifs captés'},
    'Pace' : {'col' : 'num', 'display' : 'Pace', 'format' : '%.1f', 'width' : None, 'help' : 'Nombre de possessions par match'},
    'ORtg' : {'col' : 'num', 'display' : 'ORtg', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de points pour 100 possessions'},
    'DRtg' : {'col' : 'num', 'display' : 'DRtg', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de points marqués par les adversaires pour 100 possessions'},
    'NRtg' : {'col' : 'num', 'display' : 'NRtg', 'format' : '%+.1f', 'width' : None, 'help' : 'Différence entre Ortg et Drtg'},
    'TM_TOV_PCT' : {'col' : 'num', 'display' : 'Tov%', 'format' : "%.1f%%", 'width' : 60, 'help' : 'Pourcentage de possessions qui finissent en balle perdue'},
    'BLKA' : {'col' : 'num', 'display' : 'BlkA', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs tentés qui se sont fait bloquer'},
    'PFD' : {'col' : 'num', 'display' : 'Fa. prov.', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de fautes provoquées'},
    'AST_RATIO' : {'col' : 'num', 'display' : 'Ast ratio', 'format' : '%.1f', 'width' : 60, 'help' : 'Moyenne de passes décisives pour 100 possessions'},
    'FG3_ratio' : {'col' : 'num', 'display' : 'Ratio 3pts', 'format' : "%.1f%%", 'width' : None, 'help' : 'Pourcentage de tirs tentés qui sont des 3 pts'},

    # Shooting stats
    'FGM' : {'col' : 'num', 'display' : 'FG', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs marqués'},
    'FGA' : {'col' : 'num', 'display' : 'FGA', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs tentés'},
    'FG_PCT' : {'col' : 'num', 'display' : 'FG%', 'format' : "%.1f%%", 'width' : None, 'help' : 'Pourcentage de tirs réussis'},
    'FG3M' : {'col' : 'num', 'display' : 'FG3', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs à 3 points marqués'},
    'FG3A' : {'col' : 'num', 'display' : 'FG3A', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs à 3 points tentés'},
    'FG3_PCT' : {'col' : 'num', 'display' : 'FG3%', 'format' : "%.1f%%", 'width' : None, 'help' : 'Pourcentage de tirs à 3 pts réussis'},
    'FTM' : {'col' : 'num', 'display' : 'FT', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de lancers-francs réussis'},
    'FTA' : {'col' : 'num', 'display' : 'FTA', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de lancers-francs tentés'},
    'FT_PCT' : {'col' : 'num', 'display' : 'FT%', 'format' : "%.1f%%", 'width' : None, 'help' : 'Pourcentage de lancers-francs réussis'},
    'FG2M' : {'col' : 'num', 'display' : 'FG2', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs à 2 pts réussis'},
    'FG2A' : {'col' : 'num', 'display' : 'FG2A', 'format' : '%.1f', 'width' : None, 'help' : 'Moyenne de tirs à 2 pts tentés'},
    'FG2_PCT' : {'col' : 'num', 'display' : 'FG2%', 'format' : "%.1f%%", 'width' : None, 'help' : 'Pourcentage de tirs à 2 pts réussis'},
    'EFG_PCT' : {'col' : 'num', 'display' : 'eFG%', 'format' : "%.1f%%", 'width' : None, 'help' : 'Moyenne aux tirs pondérée qui prend en compte que les tirs à 3 points valent plus'},
    'TS_PCT' : {'col' : 'num', 'display' : 'TS%', 'format' : "%.1f%%", 'width' : None, 'help' : 'Moyenne aux tirs pondérée pour prendre en compte les 3 points et les lancers francs'},
    
    # TTFL stats
    'avg_team_TTFL' : {'col' : 'num', 'display' : 'TTFL', 'format' : '%.1f', 'width' : None, 'help' : "Moyenne TTFL de l'équipe"},
    'avg_opp_TTFL' : {'col' : 'num', 'display' : 'TTFL adv.', 'format' : '%.1f', 'width' : None, 'help' : "Moyenne TTFL des adversaires"},
    'net_TTFL' : {'col' : 'num', 'display' : 'ΔTTFL', 'format' : '%+.1f', 'width' : None, 'help' : "Différence entre TTFL et TTFL adv."},
    'rel_team_avg_TTFL' : {'col' : 'num', 'display' : 'TTFL%', 'format' : "%+.1f%%", 'width' : None, 'help' : "Moyenne TTFL de l'équipe par rapport à la moyenne TTFL de toutes les équipes"},
    'rel_opp_avg_TTFL' : {'col' : 'num', 'display' : 'TTFL% adv.', 'format' : "%+.1f%%", 'width' : None, 'help' : "Moyenne TTFL des adversaires par rapport à la moyenne TTFL de toutes les équipes"},
    'net_rel_TTFL' : {'col' : 'num', 'display' : 'ΔTTFL%', 'format' : '%+.1f', 'width' : None, 'help' : "Différence entre TTFL% et TTFL% adv."},
}
for table in team_stats:
    with st.expander(table):
        st.dataframe(team_stats[table], height='content', hide_index=True,
                    column_config={stat : (
                        st.column_config.NumberColumn(
                        stats_dict[stat]['display'],
                        width = stats_dict[stat]['width'],
                        format = stats_dict[stat]['format'],
                        help = stats_dict[stat]['help'])
                        if stats_dict[stat]['col'] == 'num' else 
                        st.column_config.TextColumn(
                        stats_dict[stat]['display'],
                        width = stats_dict[stat]['width'],
                        help = stats_dict[stat]['help']))
                        for stat in team_stats[table]})

vspace(30)

SEO('footer')