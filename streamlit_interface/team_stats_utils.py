from datetime import datetime, timedelta
import streamlit as st
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import df_to_html
from streamlit_interface.streamlit_utils import conn_db
from streamlit_interface.JDP_utils import match_player
from data.sql_functions import run_sql_query

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
    
    # team_stats['net_TTFL'] = np.select([team_stats['net_TTFL'] < 0], 
    #                                   [team_stats['net_TTFL'].astype(int).astype(str)],
    #                                   '+' + team_stats['net_TTFL'].astype(int).astype(str))
    
    # team_stats['net_rel_TTFL'] = np.select([team_stats['net_rel_TTFL'] < 0], 
    #                                       [team_stats['net_rel_TTFL'].astype(int).astype(str) + '%'],
    #                                       '+' + team_stats['net_rel_TTFL'].astype(int).astype(str) + '%')
    
    # team_stats['ORtg'] = team_stats['ORtg'].astype(int).astype(int)
    # team_stats['DRtg'] = team_stats['DRtg'].astype(int).astype(int)
    # team_stats['NRtg'] = team_stats['NRtg'].round(0).astype(int)
    # team_stats['NRtg'] = np.select([team_stats['NRtg'] < 0], 
    #                                   [team_stats['NRtg'].astype(int).astype(str)],
    #                                   '+' + team_stats['NRtg'].astype(int).astype(str))
    
    # team_stats['AST_TO'] = team_stats['AST_TO'].round(1)
    team_stats['DREB_PCT'] = (team_stats['DREB_PCT'] * 100)
    team_stats['OREB_PCT'] = (team_stats['OREB_PCT'] * 100)
    team_stats['EFG_PCT'] = (team_stats['EFG_PCT'] * 100)
    team_stats['TS_PCT'] = (team_stats['TS_PCT'] * 100)
    # team_stats['Pace'] = team_stats['Pace'].astype(int)

    return team_stats
    
    # show_cols = ['teamTricode', 'GP', 'W', 'L', 'net_TTFL', 'net_rel_TTFL', 'ORtg', 'DRtg', 'NRtg', 'AST_TO',
    #              'DREB_PCT', 'OREB_PCT', 'EFG_PCT', 'TS_PCT', 'Pace']

    # html_df = df_to_html(team_stats, show_cols=show_cols, 
    #                         #  tooltips={
    #                         #      'FG' : 'FGpct',
    #                         #      'FG3' : 'FG3pct',
    #                         #      'FT' : 'FTpct',
    #                         #      'TTFL' : 'perf_str',
    #                         #      'Reb' : 'rebSplit'
    #                         #  },
    #                          col_header_tooltips=[],
    #                          image_tooltips=[],
    #                          color_tooltip_pct=False,
    #                         #  highlight_index=idx_pick,
    #                          col_header_labels = {'AST_TO' : 'Ast/tov', 
    #                                               'REB_PCT' : 'Reb%',
    #                                               'OREB_PCT' : 'OReb%',
    #                                               'DREB_PCT' : 'DReb%',
    #                                               'EFG_PCT'  :'EFG%',
    #                                               'TS_PCT' : 'TS%',
    #                                               'teamTricode' : 'Équipe',
    #                                               'net_TTFL' : 'ΔTTFL',
    #                                               'net_rel_TTFL' : 'ΔTTFL%'}
    #                          )
    
    # return html_df

if __name__ == '__main__':
    a = get_team_stats()
    print(a)
    print(a.columns)