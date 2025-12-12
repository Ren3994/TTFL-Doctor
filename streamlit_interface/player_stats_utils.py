import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import df_to_html
from streamlit_interface.resource_manager import conn_db
from streamlit_interface.streamlit_utils import uspace
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

def get_all_player_stats(matched=[], min_games=5, min_min_per_game=0, fg_min=0, fg3_min=0, ft_min=0, agg='Moyennes'): 

    player_stats = query_player_stats()
    
    if len(matched) > 1:
        player_stats = player_stats[player_stats['GP'] >= min_games]
        player_stats = player_stats[player_stats['SECONDS'] // 60 >= min_min_per_game]
        player_stats = player_stats[player_stats['TOT_FGM'] >= fg_min]
        player_stats = player_stats[player_stats['TOT_FG3M'] >= fg3_min]
        player_stats = player_stats[player_stats['TOT_FTM'] >= ft_min]

    if len(matched) > 0:
        player_stats = player_stats[player_stats['playerName'].isin(matched)]

    player_stats['MINUTES'] = (player_stats['SECONDS'].apply(
                               lambda s: f"{s // 60:02.0f}:{s % 60:02.0f}"))
    
    player_stats['TOT_MINUTES'] = (player_stats['TOT_SECONDS'].apply(
                               lambda s: f"{s // 60:02.0f}:{s % 60:02.0f}"))
    
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
    player_stats['FG2_PCT'] = (100 * player_stats['FG2M'] / player_stats['FG2A']).round(1).fillna(0)

    player_stats['FG3_ratio'] = (100 * player_stats['FG3A'] / player_stats['FGA']).fillna(0).round(1)

    player_stats.loc[player_stats['playerName'].isin(FRENCHIES), 'playerName'] = (
        player_stats.loc[player_stats['playerName'].isin(FRENCHIES), 'playerName'] + ' 🇫🇷')
    
    if agg == 'Moyennes':
        reg_cols = ['playerName', 'teamTricode', 'GP', 'MINUTES', 'TTFL', 'ttfl_per_min',
                                   'Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Stk', 'Tov', 'PM']
        reg_sort_col = 'TTFL'

        shoot_cols = ['playerName', 'FGM', 'FGA', 'FG_PCT', 'FG2M', 'FG2A', 'FG2_PCT',
                                   'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT',
                                   'EFG', 'TS', 'ast_to_tov', 'FG3_ratio']
        shoot_sort_col = 'FGM'

    elif agg == 'Totaux':
        reg_cols = ['playerName', 'teamTricode', 'GP', 'TOT_MINUTES', 'TOT_TTFL',
                                   'TOT_Pts', 'TOT_Ast', 'TOT_Reb', 'TOT_Oreb', 'TOT_Dreb', 'TOT_Stl', 
                                   'TOT_Blk', 'TOT_Stk', 'TOT_Tov', 'TOT_PM']
        reg_sort_col = 'TOT_TTFL'

        shoot_cols = ['playerName', 'TOT_FGM', 'TOT_FGA', 'FG_PCT', 'TOT_FG2M', 'TOT_FG2A', 'FG2_PCT',
                                   'TOT_FG3M', 'TOT_FG3A', 'FG3_PCT', 'TOT_FTM', 'TOT_FTA', 'FT_PCT',
                                   'EFG', 'TS', 'ast_to_tov', 'FG3_ratio']
        shoot_sort_col = 'TOT_FGM'

    elif agg == 'Moyennes par 36 min':
        per36cols = ['TTFL', 'Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Stk', 'Tov', 'PM',
                     'FGM', 'FGA', 'FG2M', 'FG2A', 'FG3M', 'FG3A', 'FTM', 'FTA']
        
        for col in per36cols:
            player_stats[col] = (player_stats[col] * 2160) / player_stats['SECONDS']
        
        reg_cols = ['playerName', 'teamTricode', 'GP', 'MINUTES', 'TTFL',
                                   'Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Stk', 'Tov', 'PM']
        reg_sort_col = 'TTFL'

        shoot_cols = ['playerName', 'FGM', 'FGA', 'FG_PCT', 'FG2M', 'FG2A', 'FG2_PCT',
                                   'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT',
                                   'EFG', 'TS', 'ast_to_tov', 'FG3_ratio']
        shoot_sort_col = 'FGM'
    
    regular_stats = (player_stats[reg_cols].sort_values(by=reg_sort_col, ascending=False))
    shooting_stats = (player_stats[shoot_cols].sort_values(by=shoot_sort_col, ascending=False))
    player_v_team_df = player_v_team(matched)
    
    all_stats = {'Statistiques basiques' : regular_stats,
                 'Statistiques de tir/avancées' : shooting_stats,
                 'Statistiques du joueur par adversaire' : player_v_team_df}

    return all_stats

@st.cache_data(show_spinner=False)
def get_maximums():
    conn = conn_db()
    df = run_sql_query(conn, table='boxscores', select=['COUNT(*) AS GP',
                                                        'SUM(fieldGoalsMade) as FG',
                                                        'SUM(threePointersMade) as FG3',
                                                        'SUM(freeThrowsMade) as FT',
                                                        ], group_by='playerName')
    maximums = {'GP' : df['GP'].max(),
                'FG' : df['FG'].max(),
                'FG3' : df['FG3'].max(),
                'FT' : df['FT'].max()}
    
    return maximums

@st.cache_data(show_spinner=False)
def player_v_team(player_list):
    import pandas as pd
    conn=conn_db()
    if len(player_list) != 1:
        return pd.DataFrame()
    df = run_sql_query(conn, table='boxscores', filters=['seconds > 0', f"playerName = '{player_list[0]}'"], group_by='opponent',
                       select=['opponent', 'COUNT(*) AS GP', 'AVG(TTFL) AS TTFL', 'AVG(points) AS Pts', 
                               'AVG(assists) AS Ast', 'AVG(reboundsTotal) AS Reb', 'AVG(steals) AS Stl', 
                               'AVG(blocks) AS Blk', 'AVG(turnovers) AS Tov',
                               'AVG(fieldGoalsMade) AS FGM', 'AVG(fieldGoalsAttempted) AS FGA', 
                               'AVG(threePointersMade) AS FG3M', 'AVG(threePointersAttempted) AS FG3A', 
                               'AVG(freeThrowsMade) AS FTM', 'AVG(freeThrowsAttempted) AS FTA',
                               'AVG(plusMinusPoints) AS PM', 'AVG(seconds) AS seconds', 
                               'AVG(reboundsOffensive) AS Oreb', 'AVG(reboundsDefensive) AS Dreb',
                               '(AVG(fieldGoalsMade) / AVG(fieldGoalsAttempted)) AS FG_PCT',
                               '(AVG(threePointersMade) / AVG(threePointersAttempted)) AS FG3_PCT',
                               '(AVG(freeThrowsMade) / AVG(freeThrowsAttempted)) AS FT_PCT',
                               'ROUND((100 * (AVG(fieldGoalsMade) + 0.5 * AVG(threePointersMade)) / AVG(fieldGoalsAttempted)), 1) AS EFG',
                               'ROUND(100 * (SUM(points) / (2 * (SUM(fieldGoalsAttempted) + 0.44 * SUM(freeThrowsAttempted)))), 1) AS TS',
                               'ROUND((AVG(assists) / NULLIF(AVG(turnovers), 0)), 1) AS ast_to_tov'])
    
    df['MINUTES'] = (df['seconds'].apply(
                               lambda s: f"{s // 60:02.0f}:{s % 60:02.0f}"))
    
    df['FG_PCT'] = pd.to_numeric(df['FG_PCT'], errors='coerce').mul(100).fillna(0).round(1)
    df['FG3_PCT'] = pd.to_numeric(df['FG3_PCT'], errors='coerce').mul(100).fillna(0).round(1)
    df['FT_PCT'] = pd.to_numeric(df['FT_PCT'], errors='coerce').mul(100).fillna(0).round(1)

    df['FG2M'] = df['FGM'] - df['FG3M']
    df['FG2A'] = df['FGA'] - df['FG3A']
    df['FG2_PCT'] = (100 * df['FG2M'] / df['FG2A']).round(1).fillna(0)


    df = df[['opponent', 'GP', 'MINUTES', 'TTFL', 'Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Tov',
       'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'PM']]
    
    return df

@st.cache_data(show_spinner=False)
def historique_des_perfs(joueur):
    import pandas as pd
    import numpy as np

    conn = conn_db()
    df = run_sql_query(conn, table='boxscores', filters=['seconds > 0', f"playerName ='{joueur}'"])

    df.rename(columns={
        'playerName' : 'Joueur',
        'minutes' : 'Min',
        'points' : 'Pts',
        'assists' : 'Ast',
        'reboundsTotal' : 'Reb',
        'reboundsOffensive' : 'Oreb', 
        'reboundsDefensive' : 'Dreb',
        'steals' : 'Stl', 
        'blocks' : 'Blk', 
        'turnovers' : 'Tov',
        'fieldGoalsMade' : 'FGM', 
        'fieldGoalsAttempted' : 'FGA', 
        'threePointersMade' : 'FG3M',
        'threePointersAttempted' : 'FG3A', 
        'freeThrowsMade' : 'FTM', 
        'freeThrowsAttempted' : 'FTA',
        'plusMinusPoints' : 'Pm',
        'gameDate' : 'Date'
    }, inplace=True)
    
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df = df.sort_values(by='Date', ascending=False).reset_index(drop=True)
    df['Date'] = df['Date'].dt.strftime('%d %b.')

    df['FG'] = df['FGM'].astype(str) + '/' + df['FGA'].astype(str)
    df['FG3'] = df['FG3M'].astype(str) + '/' + df['FG3A'].astype(str)
    df['FT'] = df['FTM'].astype(str) + '/' + df['FTA'].astype(str)
    df['rebSplit'] = 'Off : ' + df['Oreb'].astype(str) + ' - Def : ' + df['Dreb'].astype(str)

    df['FGpct'] = np.select([df['FGA'] == 0, df['FGA'] == df['FGM']], 
                            ['', '100%'], 
                (100 * df['FGM'] / df['FGA']).round(1).astype(str) + '%')
    df['FG3pct'] = np.select([df['FG3A'] == 0, df['FG3A'] == df['FG3M']], 
                             ['', '100%'], 
                (100 * df['FG3M'] / df['FG3A']).round(1).astype(str) + '%')
    df['FTpct'] = np.select([df['FTA'] == 0, df['FTA'] == df['FTM']], 
                            ['', '100%'], 
                (100 * df['FTM'] / df['FTA']).round(1).astype(str) + '%')
    
    df['win'] = np.where(df['win'] == 1, 'W', 'L')
    df['isHome'] = np.where(df['isHome'] == 1, 'Dom.', 'Ext.')
    df['Pm'] = np.select([df['Pm'] < 0], [df['Pm'].astype(int)],
                        '+' + df['Pm'].astype(int).astype(str))

    show_cols = ['Date', 'teamTricode', 'opponent', 'isHome', 'TTFL', 'Min', 'Pts', 'Ast', 'Reb',
                 'Stl', 'Blk', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'win']

    html_df = df_to_html(df, show_cols=show_cols, 
                             tooltips={
                                        'FG' : 'FGpct',
                                        'FG3' : 'FG3pct',
                                        'FT' : 'FTpct',
                                        'Reb' : 'rebSplit',
                                    },
                             show_index = False,
                             col_header_tooltips=[],
                             image_tooltips=[],
                             color_tooltip_pct=False,
                             highlight_index=None,
                             col_header_labels = {'FG3' : '3FG', 'Pm' : '±', 'win' : 'W/L', 'isHome' : 'Dom/Ext',
                                                  'opponent' : 'Adv.', 'teamTricode' : 'Équipe'},
                             )
    
    return html_df

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

def set_filters_default():
    def set_filt(val, nearest, pct):
        filt_val = val / pct
        return round(filt_val / nearest) * nearest
    
    maximums = get_maximums()
    st.session_state.max_games = maximums['GP']
    st.session_state.max_fg = maximums['FG']
    st.session_state.max_fg3 = maximums['FG3']
    st.session_state.max_ft = maximums['FT']
    
    st.session_state.slider_gp_default = set_filt(st.session_state.max_games, 10, 5)
    st.session_state.slider_fg_default = set_filt(st.session_state.max_fg, 10, 10)
    st.session_state.slider_fg3_default = set_filt(st.session_state.max_fg3, 10, 10)
    st.session_state.slider_ft_default = set_filt(st.session_state.max_ft, 10, 10)
    st.session_state.slider_min_default = 10
    st.session_state.player_stats_agg_default = 'Moyennes'
    st.session_state.color_cells_default = False

def reset_filters():
    st.session_state.slider_gp = st.session_state.slider_gp_default
    st.session_state.slider_fg = st.session_state.slider_fg_default
    st.session_state.slider_fg3 = st.session_state.slider_fg3_default
    st.session_state.slider_ft = st.session_state.slider_ft_default
    st.session_state.slider_min = st.session_state.slider_min_default
    st.session_state.player_stats_agg = st.session_state.player_stats_agg_default
    st.session_state.color_cells = st.session_state.color_cells_default

def filters_to_zero():
    st.session_state.slider_gp = 0
    st.session_state.slider_min = 0
    st.session_state.slider_fg = 0
    st.session_state.slider_fg3 = 0
    st.session_state.slider_ft = 0

def filter_expander_vars():
    label = ('Filtrer les résultats' + 
    (f' {uspace(6)} ● {uspace(6)} {st.session_state.player_stats_agg}') + 
    (f' {uspace(6)} ● {uspace(6)} GP {uspace(1)} ≥ {uspace(1)} {st.session_state.slider_gp}') + 
    (f' {uspace(6)} ● {uspace(6)} min {uspace(1)} ≥ {uspace(1)} {st.session_state.slider_min}') + 
    (f' {uspace(6)} ● {uspace(6)} FG {uspace(1)} ≥ {uspace(1)} {st.session_state.slider_fg}') + 
    (f' {uspace(6)} ● {uspace(6)} FG3 {uspace(1)} ≥ {uspace(1)} {st.session_state.slider_fg3}') + 
    (f' {uspace(6)} ● {uspace(6)} FT {uspace(1)} ≥ {uspace(1)} {st.session_state.slider_ft}'))

    bool = (any([st.session_state.slider_gp != st.session_state.slider_gp_default,
                        st.session_state.slider_min != st.session_state.slider_min_default,
                        st.session_state.slider_fg != st.session_state.slider_fg_default,
                        st.session_state.slider_fg3 != st.session_state.slider_fg3_default,
                        st.session_state.slider_ft != st.session_state.slider_ft_default,
                        st.session_state.player_stats_agg != st.session_state.player_stats_agg_default]) and not
                    all([st.session_state.slider_gp == 0,
                        st.session_state.slider_min == 0,
                        st.session_state.slider_fg == 0,
                        st.session_state.slider_fg3 == 0,
                        st.session_state.slider_ft == 0,
                        st.session_state.player_stats_agg == st.session_state.player_stats_agg_default]))
    
    return label, bool

if __name__ == '__main__':
    get_all_player_stats(0, 0)