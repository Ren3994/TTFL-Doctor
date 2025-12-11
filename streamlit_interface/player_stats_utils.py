import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.resource_manager import conn_db
from streamlit_interface.JDP_utils import match_player
from data.sql_functions import run_sql_query
from misc.misc import FRENCHIES

@st.cache_data(show_spinner=False)
def query_player_stats():
    conn = conn_db()
    player_stats = run_sql_query(conn, table='boxscores', filters='seconds > 0',
                   select=['playerName', 'teamTricode',
                           'ROUND(AVG(seconds), 1) AS SECONDS',
                           'SUM(seconds) AS TOT_SECONDS',
                           'COUNT(*) AS GP',
                           'AVG(points) AS Pts',
                           'SUM(points) AS TOT_Pts',
                           'AVG(assists) AS Ast',
                           'SUM(assists) AS TOT_Ast',
                           'AVG(steals) AS Stl',
                           'SUM(steals) AS TOT_Stl',
                           'AVG(blocks) AS Blk',
                           'SUM(blocks) AS TOT_Blk',
                           '(AVG(steals) + AVG(blocks)) AS Stk',
                           '(SUM(steals) + SUM(blocks)) AS TOT_Stk',
                           'AVG(reboundsTotal) AS Reb',
                           'SUM(reboundsTotal) AS TOT_Reb',
                           'AVG(reboundsOffensive) AS Oreb',
                           'SUM(reboundsOffensive) AS TOT_Oreb',
                           'AVG(reboundsDefensive) AS Dreb',
                           'SUM(reboundsDefensive) AS TOT_Dreb',
                           'AVG(turnovers) AS Tov',
                           'SUM(turnovers) AS TOT_Tov',
                           'AVG(fieldGoalsMade) AS FGM',
                           'SUM(fieldGoalsMade) AS TOT_FGM',
                           'AVG(fieldGoalsAttempted) AS FGA',
                           'SUM(fieldGoalsAttempted) AS TOT_FGA',
                           'AVG(threePointersMade) AS FG3M',
                           'SUM(threePointersMade) AS TOT_FG3M',
                           'AVG(threePointersAttempted) AS FG3A',
                           'SUM(threePointersAttempted) AS TOT_FG3A',
                           'AVG(freeThrowsMade) AS FTM',
                           'SUM(freeThrowsMade) AS TOT_FTM',
                           'AVG(freeThrowsAttempted) AS FTA',
                           'SUM(freeThrowsAttempted) AS TOT_FTA',
                           '(AVG(fieldGoalsMade) / AVG(fieldGoalsAttempted)) AS FG_PCT',
                           '(AVG(threePointersMade) / AVG(threePointersAttempted)) AS FG3_PCT',
                           '(AVG(freeThrowsMade) / AVG(freeThrowsAttempted)) AS FT_PCT',
                           'AVG(plusMinusPoints) AS PM',
                           'SUM(plusMinusPoints) AS TOT_PM',
                           '((AVG(fieldGoalsMade) + 0.5 * AVG(threePointersMade)) / AVG(fieldGoalsAttempted)) AS EFG',
                           '(SUM(points) / (2 * (SUM(fieldGoalsAttempted) + 0.44 * SUM(freeThrowsAttempted)))) AS TS',
                           '(AVG(assists) / NULLIF(AVG(turnovers), 0)) AS ast_to_tov',
                           'AVG(TTFL) AS TTFL',
                           'SUM(TTFL) AS TOT_TTFL',
                           'AVG(TTFL) / (AVG(seconds) / 60) AS ttfl_per_min'],
                           group_by=['playerName', 'teamTricode'],
                           order_by='AVG(TTFL) DESC')
    return player_stats

def get_all_player_stats(min_games=5, min_min_per_game=0, matched=[], totals=False): 

    player_stats = query_player_stats()

    player_stats = player_stats[player_stats['GP'] >= min_games]
    player_stats = player_stats[player_stats['SECONDS'] // 60 >= min_min_per_game]

    if len(matched) > 0:
        player_stats = player_stats[player_stats['playerName'].isin(matched)]

    player_stats['MINUTES'] = (player_stats['SECONDS'].apply(
                               lambda s: f"{s // 60:02.0f}:{s % 60:02.0f}"))
    
    player_stats['TOT_MINUTES'] = (player_stats['TOT_SECONDS'].apply(
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
    player_stats['TOT_FG2M'] = player_stats['TOT_FGM'] - player_stats['TOT_FG3M']
    player_stats['TOT_FG2A'] = player_stats['TOT_FGA'] - player_stats['TOT_FG3A']
    player_stats['FG2_PCT'] = (100 * player_stats['FG2M'] / player_stats['FG2A']).round(1)

    player_stats['FG3_ratio'] = (100 * player_stats['FG3A'] / player_stats['FGA']).fillna(0).round(1)

    player_stats.loc[player_stats['playerName'].isin(FRENCHIES), 'playerName'] = (
        player_stats.loc[player_stats['playerName'].isin(FRENCHIES), 'playerName'] + ' 🇫🇷')
    
    if not totals :
        reg_cols = ['playerName', 'teamTricode', 'GP', 'MINUTES', 'TTFL', 'ttfl_per_min',
                                   'Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Stk', 'Tov', 'PM']
        reg_sort_col = 'TTFL'

        shoot_cols = ['playerName', 'FGM', 'FGA', 'FG_PCT', 'FG2M', 'FG2A', 'FG2_PCT',
                                   'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT',
                                   'TOT_FGM', 'TOT_FG3M', 'TOT_FTM']
        shoot_sort_col = 'FG_PCT'
    else:
        reg_cols = ['playerName', 'teamTricode', 'GP', 'TOT_MINUTES', 'TOT_TTFL', 'ttfl_per_min',
                                   'TOT_Pts', 'TOT_Ast', 'TOT_Reb', 'TOT_Oreb', 'TOT_Dreb', 'TOT_Stl', 
                                   'TOT_Blk', 'TOT_Stk', 'TOT_Tov', 'TOT_PM']
        reg_sort_col = 'TOT_TTFL'

        shoot_cols = ['playerName', 'TOT_FGM', 'TOT_FGA', 'FG_PCT', 'TOT_FG2M', 'TOT_FG2A', 'FG2_PCT',
                                   'TOT_FG3M', 'TOT_FG3A', 'FG3_PCT', 'TOT_FTM', 'TOT_FTA', 'FT_PCT']
        shoot_sort_col = 'TOT_FGM'
    
    regular_stats = (player_stats[reg_cols].sort_values(by=reg_sort_col, ascending=False))
    
    advanced_stats = (player_stats[['playerName', 'MINUTES', 'EFG', 'TS', 'ast_to_tov', 'FG3_ratio',
                                   'TOT_FGM', 'TOT_FG3M', 'TOT_FTM']]
                                    .sort_values(by='TS', ascending=False))
    
    shooting_stats = (player_stats[shoot_cols].sort_values(by=shoot_sort_col, ascending=False))
    
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