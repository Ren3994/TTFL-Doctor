import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.resource_manager import conn_db
from data.sql_functions import run_sql_query

@st.cache_data(show_spinner=False)
def query_team_stats():
    conn = conn_db()
    team_stats = run_sql_query(conn, table='team_stats ts', joins=[{
        "table" : "rel_avg_opp_TTFL relt",
        "on" : "ts.teamTricode = relt.teamTricode"
    }],
    select=[ # Regular stats
            'ts.teamTricode', 'ts.GP', 'ts.W', 'ts.L', 'ts.W_PCT',
            'ts.PTS', 'ts.AST', 'ts.REB', 'ts.OREB', 'ts.DREB',
            'ts.TOV', 'ts.STL', 'ts.BLK',

            # Advanced stats
            'ts.ORtg', 'ts.DRtg', 'ts.NRtg', 'ts.AST_PCT', 'ts.AST_TO', 'ts.OREB_PCT',
            'ts.DREB_PCT', 'ts.REB_PCT', 'ts.Pace', 'ts.TM_TOV_PCT',
            'ts.AST_RATIO', 'ts.BLKA', 'ts.PFD',

            # Shooting stats
            'ts.FGM', 'ts.FGA', 'ts.FG_PCT', 'ts.FG3M', 'ts.FG3A', 'ts.FG3_PCT', 
            'ts.FTM', 'ts.FTA', 'ts.FT_PCT', 'ts.EFG_PCT', 'ts.TS_PCT',

            # TTFL stats
            'relt.rel_team_avg_TTFL', 'relt.rel_opp_avg_TTFL',
            'relt.rel_team_avg_TTFL - relt.rel_opp_avg_TTFL AS net_rel_TTFL',
            'relt.avg_team_TTFL', 'relt.avg_opp_TTFL',
            'relt.avg_team_TTFL - relt.avg_opp_TTFL AS net_TTFL'
            ])
    return team_stats

def get_team_stats(selected_teams=[]):
    
    team_stats = query_team_stats()
    
    if len(selected_teams) > 0:
        team_stats = team_stats[team_stats['teamTricode'].isin(selected_teams)]
        
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

    team_stats = team_stats.sort_values(by=['W', 'W_PCT'], ascending=[False, False])
    
    reg_stats = team_stats[['teamTricode', 'GP', 'W', 'L', 'W_PCT','PTS', 'AST', 'REB', 
                            'OREB', 'DREB', 'STL', 'BLK', 'TOV']]
    
    adv_stats = team_stats[['teamTricode', 'ORtg', 'DRtg', 'NRtg', 'FG3_ratio', 'Pace', 'AST_TO',
                             'REB_PCT','OREB_PCT', 'DREB_PCT', 'TM_TOV_PCT',
                            'AST_PCT', 'AST_RATIO', 'BLKA', 'PFD']]
    
    shooting_stats = team_stats[['teamTricode', 'FGM', 'FGA', 'FG_PCT', 'FG2M', 'FG2A', 'FG2_PCT', 
                                'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'EFG_PCT', 'TS_PCT']]
    
    ttfl_stats = team_stats[['teamTricode', 'avg_team_TTFL', 'avg_opp_TTFL', 'net_TTFL',
                            'rel_team_avg_TTFL', 'rel_opp_avg_TTFL', 'net_rel_TTFL']]
    
    all_stats = {'Statistiques basiques' : reg_stats,
                 'Statistiques de tir' : shooting_stats,
                 'Statistiques avancées' : adv_stats,
                 'Statistiques TTFL' : ttfl_stats}

    return all_stats

def clear_team_stats_vars():
    for key in list(st.session_state.keys()):
        if key.startswith('team_stats_button_'):
            st.session_state[key] = False

    st.session_state.team_stats_color_cells = False

if __name__ == '__main__':
    a = get_team_stats()