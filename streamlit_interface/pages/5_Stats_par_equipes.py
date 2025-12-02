import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.streamlit_utils import SEO, config, custom_CSS
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

st.subheader('Work in progress...')

team_stats = get_team_stats()
# cols2rename={'teamTricode' : 'Équipe',
#              'GP' : 'MJ',
#              'AST_TO' : 'Ast/tov'}
            #  'OREB_PCT' : 'OReb%',
            #  'DREB_PCT' : 'DReb%',
            #  'EFG_PCT' : 'eFG%',
            #  'TS_PCT' : 'TS%',
            #  'avg_team_TTFL' : 'TTFL',
            #  'avg_opp_TTFL' : 'TTFL adv.',
            #  'net_TTFL' : 'ΔTTFL',
            #  'rel_team_avg_TTFL' : 'TTFL%',
            #  'rel_opp_avg_TTFL' : 'TTFL% adv.',
            #  'net_rel_TTFL' : 'ΔTTFL%'}

# team_stats = team_stats.rename(columns=cols2rename)
cols2hide = ['W_PCT', 'TM_TOV_PCT', 'AST_PCT', 'REB_PCT']
for col in cols2hide:
    team_stats = team_stats.drop(columns=[col])

st.data_editor(team_stats, disabled=True, hide_index=True, 
               column_order=('teamTricode', 'GP', 'W', 'L', 'avg_team_TTFL', 'avg_opp_TTFL', 'net_TTFL',
                             'rel_team_avg_TTFL', 'rel_opp_avg_TTFL', 'net_rel_TTFL',
                             'ORtg', 'DRtg', 'NRtg', 'AST_TO', 'Pace', 'OREB_PCT', 'DREB_PCT', 'EFG_PCT', 'TS_PCT'),
               column_config={
                    'teamTricode' : st.column_config.TextColumn(
                        'Équipe',
                        width=50),
                   'GP' : st.column_config.NumberColumn(
                       width=30
                    ),
                    'W' : st.column_config.NumberColumn(
                       width=30
                    ),
                    'L' : st.column_config.NumberColumn(
                       width=30
                    ),
                    'AST_TO' : st.column_config.NumberColumn(
                       'Ast/tov',
                        format='%.1f',
                        help="Ratio assists/turnovers de l'équipe.",
                   ),
                   'avg_team_TTFL' : st.column_config.NumberColumn(
                        'TTFL',
                        format='%d',
                        help="Moyenne TTFL de l'équipe.",
                   ),
                   'avg_opp_TTFL' : st.column_config.NumberColumn(
                        'TTFL adv.',
                        format='%d',
                        help="Moyenne TTFL de l'équipe adverse.",
                   ),
                   'net_TTFL' : st.column_config.NumberColumn(
                       'ΔTTFL',
                        format='%+d',
                        help="Différence entre la moyenne TTFL de l'équipe et celle de l'équipe adverse.",
                   ),
                   'rel_team_avg_TTFL' : st.column_config.NumberColumn(
                       'TTFL%',
                       format='%.0f%%',
                       help="Moyenne TTFL de l'équipe par rapport à la moyenne TTFL de toutes les équipes.",
                   ),
                   'rel_opp_avg_TTFL' : st.column_config.NumberColumn(
                       'TTFL% adv.',
                       format='%.0f%%',
                       help="Moyenne TTFL de l'équipe adverse par rapport à la moyenne TTFL de toutes les équipes.",
                   ),
                   'net_rel_TTFL' : st.column_config.NumberColumn(
                       'ΔTTFL%',
                       format='%+d%%',
                       help="Différence entre la moyenne TTFL de l'équipe et celle de l'équipe adverse par rapport à la moyenne TTFL de toutes les équipes.",
                   ),
                   'NRtg' : st.column_config.NumberColumn(
                       'NRtg',
                       format='%+f',
                       help="Net Rating : différence entre les points marqués et les points encaissés pour 100 possessions.",
                   ),
                   'ORtg' : st.column_config.NumberColumn(
                       'ORtg',
                       format='%d',
                       help="Offensive Rating : nombre de points marqués par 100 possessions.",
                   ),
                   'DRtg' : st.column_config.NumberColumn(
                       'DRtg',
                       format='%d',
                       help="Defensive Rating : nombre de points encaissés par 100 possessions.",
                   ),
                   'Pace' : st.column_config.NumberColumn(
                       'Pace',
                       format='%d',
                       help="Nombre de possessions par match.",
                   ),
                   'OREB_PCT' : st.column_config.NumberColumn(
                       'OReb%',
                       format="%.0f%%",
                       help="Offensive Rebound Percentage : pourcentage de rebonds offensifs captés par l'équipe lorsqu'elle est en attaque.",
                   ),
                   'DREB_PCT' : st.column_config.NumberColumn(
                       'DReb%',
                       format="%.0f%%",
                       help="Defensive Rebound Percentage : pourcentage de rebonds défensifs captés par l'équipe lorsqu'elle est en défense.",
                   ),
                   'EFG_PCT' : st.column_config.NumberColumn(
                       'eFG%',
                       format="%.0f%%",
                       help="Effective Field Goal Percentage : pourcentage de réussite aux tirs pondéré en faveur des tirs à 3 points.",
                   ),
                   'TS_PCT' : st.column_config.NumberColumn(
                       'TS%',
                       format="%.0f%%",
                       help="True Shooting Percentage : pourcentage de réussite aux tirs prenant en compte les tirs à 3 points et les lancers francs.",
                   ),
               })

SEO('footer')