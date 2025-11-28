import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_db
from data.sql_functions import run_sql_query

@st.cache_data(show_spinner=False)
def get_all_player_stats():
    conn = conn_db()
    avg_player_stats = run_sql_query(conn, table='boxscores', filters='seconds > 0',
                   select=['playerName', 'teamTricode',
                           'COUNT(*) AS n_games',
                           'AVG(points) AS points',
                           'AVG(assists) AS assists',
                           'AVG(steals) AS steals',
                           'AVG(blocks) AS blocks',
                           '(AVG(steals) + AVG(blocks)) AS stocks',
                           'AVG(reboundsTotal) AS reboundsTotal',
                           'AVG(reboundsOffensive) AS reboundsOffensive',
                           'AVG(reboundsDefensive) AS reboundsDefensive',
                           'AVG(turnovers) AS turnovers',
                           'AVG(fieldGoalsMade) AS fieldGoalsMade',
                           'AVG(fieldGoalsAttempted) AS fieldGoalsAttempted',
                           'AVG(threePointersMade) AS threePointersMade',
                           'AVG(threePointersAttempted) AS threePointersAttempted',
                           'AVG(freeThrowsMade) AS freeThrowsMade',
                           'AVG(freeThrowsAttempted) AS freeThrowsAttempted',
                           '(AVG(fieldGoalsMade) / AVG(fieldGoalsAttempted)) AS fg_pct',
                           '(AVG(threePointersMade) / AVG(threePointersAttempted)) AS three_pct',
                           '(AVG(freeThrowsMade) / AVG(freeThrowsAttempted)) AS ft_pct',
                           'AVG(plusMinusPoints) AS plusMinusPoints',
                           '(AVG(fieldGoalsMade) + 0.5 * AVG(threePointersMade) / AVG(fieldGoalsAttempted)) AS EFG',
                           '(AVG(points) / (2 * (AVG(fieldGoalsAttempted) + 0.44 * AVG(freeThrowsAttempted)))) AS TS',
                           '(AVG(assists) / NULLIF(AVG(turnovers), 0)) AS ast_to_tov',
                           '((AVG(steals) + AVG(blocks)) * 36 * 60 / AVG(seconds)) AS stocks_per36',
                           '(AVG(steals) * 36 * 60 / AVG(seconds)) AS stl_per36',
                           '(AVG(points) * 36 * 60 / AVG(seconds)) AS pts_per36',
                           '(AVG(reboundsTotal) * 36 * 60 / AVG(seconds)) AS reb_per36',
                           '(AVG(assists) * 36 * 60 / AVG(seconds)) AS ast_per36',
                           '(AVG(turnovers) * 36 * 60 / AVG(seconds)) AS tov_per36',
                           'AVG(TTFL) AS TTFL',
                           'AVG(TTFL) / (AVG(seconds) / 60) AS ttfl_per_min',
                           '36 * AVG(TTFL) / (AVG(seconds) / 60) AS ttfl_per_36'],
                           group_by=['playerName', 'teamTricode'],
                           order_by='AVG(TTFL) DESC')
    return avg_player_stats