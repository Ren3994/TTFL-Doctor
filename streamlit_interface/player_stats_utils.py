import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.resource_manager import conn_db
from streamlit_interface.JDP_utils import match_player
from data.sql_functions import run_sql_query
from misc.misc import FRENCHIES

@st.cache_data(show_spinner=False)
def get_all_player_stats(min_games=5, min_min_per_game=0, matched=[]):
    conn = conn_db()
    player_stats = run_sql_query(conn, table='boxscores', filters='seconds > 0',
                   select=['playerName', 'teamTricode',
                           'ROUND(AVG(seconds), 1) AS SECONDS',
                           'COUNT(*) AS GP',
                           'AVG(points) AS Pts',
                           'AVG(assists) AS Ast',
                           'AVG(steals) AS Stl',
                           'AVG(blocks) AS Blk',
                           '(AVG(steals) + AVG(blocks)) AS Stk',
                           'AVG(reboundsTotal) AS Reb',
                           'AVG(reboundsOffensive) AS Oreb',
                           'AVG(reboundsDefensive) AS Dreb',
                           'AVG(turnovers) AS Tov',
                           'AVG(fieldGoalsMade) AS FGM',
                           'AVG(fieldGoalsAttempted) AS FGA',
                           'AVG(threePointersMade) AS FG3M',
                           'AVG(threePointersAttempted) AS FG3A',
                           'AVG(freeThrowsMade) AS FTM',
                           'AVG(freeThrowsAttempted) AS FTA',
                           '(AVG(fieldGoalsMade) / AVG(fieldGoalsAttempted)) AS FG_PCT',
                           '(AVG(threePointersMade) / AVG(threePointersAttempted)) AS FG3_PCT',
                           '(AVG(freeThrowsMade) / AVG(freeThrowsAttempted)) AS FT_PCT',
                           'AVG(plusMinusPoints) AS PM',
                           '((AVG(fieldGoalsMade) + 0.5 * AVG(threePointersMade)) / AVG(fieldGoalsAttempted)) AS EFG',
                           '(SUM(points) / (2 * (SUM(fieldGoalsAttempted) + 0.44 * SUM(freeThrowsAttempted)))) AS TS',
                           '(AVG(assists) / NULLIF(AVG(turnovers), 0)) AS ast_to_tov',
                           'AVG(TTFL) AS TTFL',
                           'AVG(TTFL) / (AVG(seconds) / 60) AS ttfl_per_min'],
                           group_by=['playerName', 'teamTricode'],
                           order_by='AVG(TTFL) DESC')
    
    player_stats = player_stats[player_stats['GP'] >= min_games]
    player_stats = player_stats[player_stats['SECONDS'] // 60 >= min_min_per_game]

    if len(matched) > 0:
        player_stats = player_stats[player_stats['playerName'].isin(matched)]

    player_stats['MINUTES'] = (player_stats['SECONDS'].apply(
                               lambda s: f"{s // 60:02.0f}:{s % 60:02.0f}"))
    
    # player_stats["MINUTES_DT"] = pd.to_datetime(player_stats["SECONDS"], unit='s').dt.strftime('%M:%S')

    player_stats['EFG'] = (player_stats['EFG'] * 100).fillna(0)
    player_stats['TS'] = (player_stats['TS'] * 100).fillna(0)

    player_stats['ast_to_tov'] = player_stats['ast_to_tov'].fillna(0)

    player_stats['FG_PCT'] = (player_stats['FG_PCT'] * 100).fillna(0)
    player_stats['FG3_PCT'] = (player_stats['FG3_PCT'] * 100).fillna(0)
    player_stats['FT_PCT'] = (player_stats['FT_PCT'] * 100).fillna(0)
    
    player_stats['FG2M'] = player_stats['FGM'] - player_stats['FG3M']
    player_stats['FG2A'] = player_stats['FGA'] - player_stats['FG3A']
    player_stats['FG2_PCT'] = (100 * player_stats['FG2M'] / player_stats['FG2A']).round(1)

    player_stats['FG3_ratio'] = (100 * player_stats['FG3A'] / player_stats['FGA']).fillna(0).round(1)

    player_stats.loc[player_stats['playerName'].isin(FRENCHIES), 'playerName'] = (
        player_stats.loc[player_stats['playerName'].isin(FRENCHIES), 'playerName'] + ' 🇫🇷')
    
    regular_stats = (player_stats[['playerName', 'teamTricode', 'GP', 'MINUTES', 'TTFL', 'ttfl_per_min',
                                   'Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Stk', 'Tov', 'PM']]
                                  .sort_values(by='TTFL', ascending=False))
    
    advanced_stats = (player_stats[['playerName', 'MINUTES', 'EFG', 'TS', 'ast_to_tov', 'FG3_ratio']]
                                    .sort_values(by='TS', ascending=False))
    
    shooting_stats = (player_stats[['playerName', 'FGM', 'FGA', 'FG_PCT', 'FG2M', 'FG2A', 'FG2_PCT',
                                   'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT']]
                                   .sort_values(by='FG_PCT', ascending=False))
    
    all_stats = {'Statistiques basiques' : regular_stats,
                 'Statistiques avancées' : advanced_stats,
                 'Statistiques de tir' : shooting_stats}

    return all_stats

def clear_search():
    st.session_state.player_stats_matched = ''
    st.session_state.search_player_indiv_stats = ''

def clear_compare():
    st.session_state.compare_players = []
    clear_search()

def add_compare():
    for player in st.session_state.player_stats_matched:
        if player not in st.session_state.compare_players and player != '':
            st.session_state.compare_players.append(player)

def on_search_player_stats():
    player_name = st.session_state.search_player_indiv_stats
    if player_name == '':
        clear_search()
    else:
        clear_search()
        matched_players = match_player(player_name, multi=True)
        st.session_state.player_stats_matched = matched_players
        if len(matched_players) == 1:
            st.session_state.search_player_indiv_stats = matched_players[0]

if __name__ == '__main__':
    get_all_player_stats(0, 0)