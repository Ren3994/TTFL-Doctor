import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.plotting_utils import team_standings
from misc.misc import CONFERENCES
from data.ttfl_stats import query_team_stats, query_opp_team_avgs, scan_boxscores
from data.ttfl_data import latest_season

@st.cache_data(show_spinner=False)
def cached_query_team_stats():
    team_stats = query_team_stats()
    return team_stats

def get_team_stats(selected_teams=[]):
    
    team_stats = cached_query_team_stats()
    opp_stats = get_cached_opp_team_stats()

    if team_stats.empty:
        return {'Statistiques basiques' : team_stats,
                'Statistiques de tir' : team_stats,
                'Statistiques avancées' : team_stats,
                'Statistiques TTFL' : team_stats,
                'Statistiques des adversaires' : opp_stats}

    opp_stats = opp_stats.sort_values(by='wins').drop(columns='wins')
    
    if len(selected_teams) > 0:
        team_stats = team_stats[team_stats['teamTricode'].isin(selected_teams)]
        opp_stats = opp_stats[opp_stats['teamTricode'].isin(selected_teams)]
        
    team_stats['DREB_PCT'] = (team_stats['DREB_PCT'] * 100)
    team_stats['OREB_PCT'] = (team_stats['OREB_PCT'] * 100)
    team_stats['EFG_PCT'] = (team_stats['EFG_PCT'] * 100)
    team_stats['TS_PCT'] = (team_stats['TS_PCT'] * 100)
    team_stats['W_PCT'] = (team_stats['W_PCT'] * 100)
    team_stats['AST_PCT'] = (team_stats['AST_PCT'] * 100)
    team_stats['REB_PCT'] = (team_stats['REB_PCT'] * 100)
    team_stats['TM_TOV_PCT'] = (team_stats['TM_TOV_PCT'] * 100)
    team_stats['FG_PCT'] = (team_stats['FG_PCT'] * 100)
    team_stats['FG3_PCT'] = (team_stats['FG3_PCT'] * 100)
    team_stats['FT_PCT'] = (team_stats['FT_PCT'] * 100)

    team_stats['FG2M'] = team_stats['FGM'] - team_stats['FG3M']
    team_stats['FG2A'] = team_stats['FGA'] - team_stats['FG3A']
    team_stats['FG2_PCT'] = (100 * team_stats['FG2M'] / team_stats['FG2A']).round(1)

    team_stats['FG3_ratio'] = (100 * team_stats['FG3A'] / team_stats['FGA']).round(1)

    team_stats = team_stats.sort_values(by=['W_PCT', 'W'], ascending=[False, False]).reset_index(drop=True)
    team_stats['rank'] = team_stats.index + 1
    
    reg_stats = team_stats[['rank', 'teamTricode', 'GP', 'W', 'L', 'W_PCT','PTS', 'AST', 'REB', 
                            'OREB', 'DREB', 'STL', 'BLK', 'TOV']]
    
    adv_stats = team_stats[['rank', 'teamTricode', 'ORtg', 'DRtg', 'NRtg', 'FG3_ratio', 'Pace', 'AST_TO',
                             'REB_PCT','OREB_PCT', 'DREB_PCT', 'TM_TOV_PCT',
                            'AST_PCT', 'AST_RATIO', 'BLKA', 'PFD']]
    
    shooting_stats = team_stats[['rank', 'teamTricode', 'FGM', 'FGA', 'FG_PCT', 'FG2M', 'FG2A', 'FG2_PCT', 
                                'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'EFG_PCT', 'TS_PCT']]
    
    ttfl_stats = team_stats[['rank', 'teamTricode', 'avg_team_TTFL', 'avg_opp_TTFL', 'net_TTFL',
                            'rel_team_avg_TTFL', 'rel_opp_avg_TTFL', 'net_rel_TTFL']]
        
    all_stats = {'Statistiques basiques' : reg_stats,
                 'Statistiques de tir' : shooting_stats,
                 'Statistiques avancées' : adv_stats,
                 'Statistiques TTFL' : ttfl_stats,
                 'Statistiques des adversaires' : opp_stats}

    return all_stats

@st.cache_data(show_spinner=False)
def get_cached_opp_team_stats():
    df = query_opp_team_avgs()
    return df

@st.cache_data(show_spinner=False)
def standings_progress_plot():
    import polars as pl
    df = (scan_boxscores(latest_season())
         .group_by(['teamTricode', 'gameDate_ymd'])
         .agg(pl.mean('win'))
         .sort(['teamTricode', 'gameDate_ymd'])
         .collect()
         .to_pandas())

    df['cum_wins'] = df.groupby('teamTricode')['win'].cumsum()

    fig = team_standings(df)
    
    return fig

def clear_team_stats_vars():
    for key in list(st.session_state.keys()):
        if key.startswith('team_stats_button_'):
            st.session_state[key] = False

    st.session_state.team_stats_color_cells = False

@st.cache_data(show_spinner=False)
def get_teams_from_conf(df, conf, name):
    if conf != 'Global':
        df = df[df['teamTricode'].isin(CONFERENCES[conf.split(' ')[1]])]
        if name != 'Statistiques des adversaires':
            df = df.reset_index(drop=True)
            df['rank'] = df.index + 1
    
    return df

# if __name__ == '__main__':
#     # a = get_team_stats()
#     # a = query_team_stats()
#     # b = qts2()

#     # print(a)
#     # print(b)

#     from data.sql_functions import run_sql_query
#     from data.ttfl_data import scan_boxscores
#     from misc.misc import SEASON
#     import polars as pl

#     a = run_sql_query(conn_db(), table='boxscores', select=['DISTINCT teamTricode', 'gameDate_ymd', 'win'],
#                    order_by='teamTricode, gameDate_ymd ASC', filters='gameDate_ymd IS NOT NULL')
    
#     print(a)

#     b = (scan_boxscores(SEASON)
#          .group_by(['teamTricode', 'gameDate_ymd'])
#          .agg(pl.mean('win'))
#          .sort(['teamTricode', 'gameDate_ymd'])
#          .collect())
    
#     print(b)