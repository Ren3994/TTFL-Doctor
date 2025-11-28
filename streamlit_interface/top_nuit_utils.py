from datetime import datetime, timedelta
import streamlit as st
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import df_to_html, get_joueurs_pas_dispo
from streamlit_interface.streamlit_utils import conn_db
from streamlit_interface.JDP_utils import match_player
from data.sql_functions import run_sql_query

@st.cache_data(show_spinner=False)
def get_top_de_la_nuit(date, name):
    conn = conn_db()                        
    df = run_sql_query(conn,
                    table='boxscores b', 
                    filters=[f"gameDate = '{date}'"], 
                    select=['b.playerName', 'minutes', 'seconds', 'points', 'pat.avg_TTFL', 'reboundsTotal',
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
    
    if name != '':
        df = df[df['playerName'] == name]
        if df.empty:
            return 'did_not_play'
    
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
        
    picks = st.session_state.get('jdp_df', None)
    idx_pick = None
    if picks is not None and not (picks['Joueur'] == '').all():
        series = picks.loc[picks['Date du pick'] == date, 'Joueur']
        pick = series.iloc[0] if not series.empty else None
        if pick is not None and pick != '' and pick in df['Joueur'].tolist():
            idx_pick = df.index[df['Joueur'] == pick] + 1            
   
    html_df = df_to_html(df, show_cols=show_cols, 
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
                             col_header_labels = {'FG3' : '3FG', 'Pm' : '±', 'Win' : 'W/L'}
                                                #   'ttfl_per_min' : 'TTFL/min'}
                                                #   'teamTricode' : 'Équipe', 
                             )
    
    return html_df

def on_text_change_nuit():
    """Parse text input into a date object."""
    text_value = st.session_state.date_text_nuit.strip()
    try:
        new_date = datetime.strptime(text_value, "%d/%m/%Y").date()
        st.session_state.selected_date_nuit = new_date
        st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
        st.session_state.text_parse_error_nuit = False
        update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), 
                        st.session_state.get('search_player_nuit', ''))
    except ValueError:
        st.session_state.text_parse_error_nuit = True

def prev_date_nuit():
    st.session_state.selected_date_nuit -= timedelta(days=1)
    st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
    update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), 
                    st.session_state.get('search_player_nuit', ''))

def next_date_nuit():
    st.session_state.selected_date_nuit += timedelta(days=1)
    st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
    update_top_nuit(st.session_state.selected_date_nuit.strftime("%d/%m/%Y"), 
                    st.session_state.get('search_player_nuit', ''))

def update_top_nuit(date, name):
    st.session_state.top_nuit = get_top_de_la_nuit(date, name)

def on_search_player_nuit():
    player_name = st.session_state.search_player_nuit
    if player_name == '':
        st.session_state.search_player_nuit = ''
    else:
        st.session_state.search_player_nuit = match_player(player_name)

def clear_search():
    st.session_state.search_player_nuit = ''