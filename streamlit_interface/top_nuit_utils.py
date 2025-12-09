from datetime import datetime, timedelta
import streamlit as st
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import df_to_html, get_joueurs_pas_dispo, get_idx_pick
from streamlit_interface.streamlit_utils import conn_db
from streamlit_interface.JDP_utils import match_player
from data.sql_functions import run_sql_query

@st.cache_data(show_spinner=False)
def get_top_de_la_nuit(date, matched_names, byteam, show_my_pick):
    conn = conn_db()                        
    df = run_sql_query(conn,
                    table='boxscores b', 
                    filters=[f"gameDate = '{date}'", 'seconds > 0'],
                    select=['b.playerName', 'b.teamTricode', 'minutes', 'seconds', 'points', 'pat.avg_TTFL', 'reboundsTotal',
                            'assists', 'reboundsOffensive', 'reboundsDefensive', 'steals', 
                            'blocks', 'turnovers', 'fieldGoalsMade', 'fieldGoalsAttempted', 
                            'threePointersMade', 'threePointersAttempted', 'freeThrowsMade', 
                            'freeThrowsAttempted', 'plusMinusPoints',  'TTFL', 'win'],
                    joins=[{
                        'table' : 'player_avg_TTFL pat',
                        'on' : 'b.playerName = pat.playerName'
                    }])
    if df.empty:
        current_date = datetime.today()
        if current_date - datetime.strptime(date, '%d/%m/%Y') < timedelta(days=2):
            return 'hier'
        return None
    
    if isinstance(matched_names, str) and matched_names != '':
        matched_names = [matched_names]
    if len(matched_names) > 0:
        df = df[df['playerName'].isin(matched_names)]
        if df.empty:
            return 'did_not_play'
        
    teams = df['teamTricode'].unique()
    df = df.sort_values(by=['TTFL'], ascending=False).reset_index(drop=True)
    df['FG'] = df['fieldGoalsMade'].astype(str) + '/' + df['fieldGoalsAttempted'].astype(str)
    df['FG3'] = df['threePointersMade'].astype(str) + '/' + df['threePointersAttempted'].astype(str)
    df['FT'] = df['freeThrowsMade'].astype(str) + '/' + df['freeThrowsAttempted'].astype(str)
    df['rebSplit'] = 'Off : ' + df['reboundsOffensive'].astype(str) + ' - Def : ' + df['reboundsDefensive'].astype(str)

    df['FGpct'] = np.select([df['fieldGoalsAttempted'] == 0, df['fieldGoalsAttempted'] == df['fieldGoalsMade']], 
                            ['', '100%'], 
                (100 * df['fieldGoalsMade'] / df['fieldGoalsAttempted']).round(1).astype(str) + '%')
    df['FG3pct'] = np.select([df['threePointersAttempted'] == 0, df['threePointersAttempted'] == df['threePointersMade']], 
                             ['', '100%'], 
                (100 * df['threePointersMade'] / df['threePointersAttempted']).round(1).astype(str) + '%')
    df['FTpct'] = np.select([df['freeThrowsAttempted'] == 0, df['freeThrowsAttempted'] == df['freeThrowsMade']], 
                            ['', '100%'], 
                (100 * df['freeThrowsMade'] / df['freeThrowsAttempted']).round(1).astype(str) + '%')

    df['Win'] = np.where(df['win'] == 1, 'W', 'L')
    df['plusMinusPoints'] = np.select([df['plusMinusPoints'] < 0], [df['plusMinusPoints'].astype(int)],
                                      '+' + df['plusMinusPoints'].astype(int).astype(str))
    
    df['perf'] = np.select([df['avg_TTFL'] == 0, df['TTFL'] < df['avg_TTFL']],
                           ['0', (100 * (df['TTFL'] - df['avg_TTFL']) / df['avg_TTFL']).round(1).astype(str) + '%'], 
                           '+' + (100 * (df['TTFL'] - df['avg_TTFL']) / df['avg_TTFL']).round(1).astype(str) + '%')
    
    df['perf_str'] = np.select([df['perf'] == '0'], 
                               ['<span style="text-decoration:overline">TTFL</span> : 0'],
                               '<span style="text-decoration:overline">TTFL</span> : ' + 
                               df['avg_TTFL'].astype(str) + ' (' + df['perf'] + ')')
    
    df['ttfl_per_min'] = 'TTFL/min : ' + (df['TTFL'] / (df['seconds'] / 60)).round(1).astype(str)
        
    df = df.drop(columns=['fieldGoalsMade', 
                          'fieldGoalsAttempted', 'threePointersMade', 
                          'threePointersAttempted', 'freeThrowsMade', 
                          'freeThrowsAttempted', 'win', 'seconds'])
    df.rename(columns={
                "playerName": "Joueur",
                "minutes": "Mins",
                "points": "Pts",
                "assists": "Ast",
                "reboundsTotal": "Reb",
                "steals": "Stl",
                "blocks": "Blk",
                "turnovers": "Tov",
                "plusMinusPoints": "Pm"
            }, inplace=True)
    
    joueurs_pas_dispo = get_joueurs_pas_dispo(conn, date)

    if len(joueurs_pas_dispo) > 0:
        df['Dispo'] = np.where(df['Joueur'].isin(joueurs_pas_dispo), '❌', '✅')
        show_cols = ['Joueur', 'TTFL', 'Mins', 'Pts', 'Ast', 'Reb', 'Stl', 
                                        'Blk', 'Tov', 'FG', 'FG3', 'FT', 'Win', 'Pm', 'Dispo']
    else:
        show_cols = ['Joueur', 'TTFL', 'Mins', 'Pts', 'Ast', 'Reb', 'Stl', 
                                        'Blk', 'Tov', 'FG', 'FG3', 'FT', 'Win', 'Pm']
    
    dfs = {}
    if byteam:
        for team in teams:
            dfs[team] = df[df['teamTricode'] == team].reset_index(drop=True)
    else:
        dfs['all'] = df
    
    html_dfs = {}
    for team, dfteam in dfs.items():
        idx_pick = get_idx_pick(dfteam, date, 'Joueur')

        html_df = df_to_html(dfteam, show_cols=show_cols, 
                             tooltips={
                                        'FG' : 'FGpct',
                                        'FG3' : 'FG3pct',
                                        'FT' : 'FTpct',
                                        'TTFL' : 'perf_str',
                                        'Reb' : 'rebSplit',
                                        'Mins' : 'ttfl_per_min'
                                    },
                             col_header_tooltips=[],
                             image_tooltips=[],
                             color_tooltip_pct=False,
                             highlight_index=idx_pick,
                             col_header_labels = {'FG3' : '3FG', 'Pm' : '±', 'Win' : 'W/L'},
                             best_pick_allowed = not byteam and not show_my_pick
                             )
            
        html_dfs[team] = html_df
        
    if 'all' in html_dfs.keys():
        return html_dfs['all']
    else:
        return html_dfs

def on_text_change_nuit():
    """Parse text input into a date object."""
    text_value = st.session_state.date_text_nuit.strip()
    try:
        new_date = datetime.strptime(text_value, "%d/%m/%Y").date()
        st.session_state.selected_date_nuit = new_date
        st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
        st.session_state.text_parse_error_nuit = False
        clear_search()
        update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), 
                        st.session_state.get('matched_players_nuit', ''),
                        st.session_state.get('byteam', False),
                        st.session_state.get('show_my_pick', False))
        clear_boxscore_vars()
    except ValueError:
        st.session_state.text_parse_error_nuit = True

def prev_date_nuit():
    st.session_state.selected_date_nuit -= timedelta(days=1)
    st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
    clear_search()
    update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), 
                    st.session_state.get('matched_players_nuit', ''),
                    st.session_state.get('byteam', False),
                    st.session_state.get('show_my_pick', False))
    clear_boxscore_vars()

def next_date_nuit():
    st.session_state.selected_date_nuit += timedelta(days=1)
    st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
    clear_search()
    update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), 
                    st.session_state.get('matched_players_nuit', ''),
                    st.session_state.get('byteam', False),
                    st.session_state.get('show_my_pick', False))
    clear_boxscore_vars()

def update_top_nuit(date, name, byteam, show_my_pick):
    st.session_state.top_nuit = get_top_de_la_nuit(date, name, byteam, show_my_pick)

def show_my_pick(pick):
    st.session_state.search_player_nuit = pick
    st.session_state.show_my_pick = True
    on_search_player_nuit()

def on_search_player_nuit():
    player_name = st.session_state.search_player_nuit
    if player_name == '':
        clear_search()
    else:
        matched_players = match_player(player_name, multi=True)
        st.session_state.matched_players_nuit = matched_players
        if len(matched_players) == 1:
            st.session_state.search_player_nuit = matched_players[0]
        
def clear_search():
    st.session_state.search_player_nuit = ''
    st.session_state.matched_players_nuit = ''
    st.session_state.show_my_pick = False

def clear_boxscore_vars():
    for key in list(st.session_state.keys()):
        if key.startswith('boxscore_nuit_'):
            st.session_state[key] = False