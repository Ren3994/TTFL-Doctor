import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_db
from data.sql_functions import run_sql_query

@st.cache_data(show_spinner=False)
def get_team_stats():
    conn = conn_db()
    team_stats = run_sql_query(conn, table='team_stats ts', joins=[{
        "table" : "rel_avg_opp_TTFL relt",
        "on" : "ts.teamTricode = relt.teamTricode"
    }],
    select=['ts.teamTricode', 'ts.GP', 'ts.W', 'ts.L', 'ts.W_PCT',
            'ts.ORtg', 'ts.DRtg', 'ts.NRtg', 'ts.AST_PCT', 'ts.AST_TO', 'ts.OREB_PCT',
            'ts.DREB_PCT', 'ts.REB_PCT', 'ts.EFG_PCT', 'ts.TS_PCT', 'ts.Pace', 'ts.TM_TOV_PCT',
            'relt.rel_team_avg_TTFL', 'relt.rel_opp_avg_TTFL',
            'relt.rel_team_avg_TTFL - relt.rel_opp_avg_TTFL AS net_rel_TTFL',
            'relt.avg_team_TTFL', 'relt.avg_opp_TTFL',
            'relt.avg_team_TTFL - relt.avg_opp_TTFL AS net_TTFL',
            ])
    
    team_stats['DREB_PCT'] = (team_stats['DREB_PCT'] * 100)
    team_stats['OREB_PCT'] = (team_stats['OREB_PCT'] * 100)
    team_stats['EFG_PCT'] = (team_stats['EFG_PCT'] * 100)
    team_stats['TS_PCT'] = (team_stats['TS_PCT'] * 100)

    return team_stats

if __name__ == '__main__':
    a = get_team_stats()