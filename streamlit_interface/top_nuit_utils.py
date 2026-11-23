from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
import polars as pl
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import df_to_html, get_idx_from_pick, get_pick, get_joueurs_pas_dispo, build_plots, _clean_player_name
from streamlit_interface.JDP_utils import match_player, get_cached_avg_TTFL
from data.ttfl_data import scan_boxscores, latest_season

@st.cache_data(show_spinner=False)
def get_top_de_la_nuit(date, matched_names, byteam, show_my_pick, spoiler, 
                       show_TTFL, joueurs_pas_dispo, pick):
    import pandas as pd
    import numpy as np

    date_dt = datetime.strptime(date, '%d/%m/%Y')

    avg_TTFL = get_cached_avg_TTFL(to_pandas=False)
    graph_stats = (scan_boxscores(latest_season())
            .filter([pl.col('seconds') > 0,
                     pl.col('gameDate_ymd') <= date_dt])
            .sort('gameDate_ymd')
            .group_by('playerName', maintain_order=True)
            .agg(graph_dates=pl.col('gameDate_ymd').dt.strftime('%d/%m/%Y'),
                 graph_opps=pl.col('opponent'),
                 graph_TTFLs=pl.col('TTFL'),
                 graph_wins=pl.col('win'),
                 graph_ishome=pl.col('isHome')))

    df = (scan_boxscores(latest_season())
         .with_columns(
             gameDate=pl.col('gameDate_ymd').dt.strftime('%d/%m/%Y'),
             minutes=pl.format(
                 '{}:{}',
                 pl.col('seconds') // 60,
                 (pl.col('seconds') % 60).cast(pl.String).str.pad_start(2, '0')
                ),
             Matchup=pl.format(
                 '{} {} {}',
                 pl.col('teamTricode'),
                 pl.when(pl.col('isHome') != 1)
                   .then(pl.lit('@'))
                   .otherwise(pl.lit('v.')),
                 pl.col('opponent')
                )
             )
         .filter([pl.col('gameDate') == date,
                  pl.col('seconds') > 0])
         .join(avg_TTFL, on='playerName')
         .join(graph_stats, on='playerName', how='left')
         .select([
             'playerName', 'teamTricode', 'minutes', 'seconds', 'points', 'reboundsTotal',
                    'assists', 'reboundsOffensive', 'reboundsDefensive', 'steals', 
                    'blocks', 'turnovers', 'fieldGoalsMade', 'fieldGoalsAttempted', 
                    'threePointersMade', 'threePointersAttempted', 'freeThrowsMade', 
                    'freeThrowsAttempted', 'plusMinusPoints',  'TTFL', 'win', 'Matchup',
                    'avg_TTFL', 'graph_dates', 'graph_TTFLs', 'graph_opps', 'graph_wins', 'graph_ishome'
                    ])
         .collect()
         .to_pandas()
         )
        
    if df.empty:
        current_date = datetime.now(ZoneInfo("Europe/Paris"))
        query_date = datetime.strptime(date, '%d/%m/%Y').replace(tzinfo=current_date.tzinfo)
        if current_date - query_date < timedelta(days=2):
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
    
    if byteam:
        totals = (df.groupby('teamTricode')
                [['points', 'assists', 'reboundsTotal', 'reboundsOffensive', 'reboundsDefensive', 
                    'steals', 'blocks', 'turnovers', 'fieldGoalsMade', 'fieldGoalsAttempted', 
                    'threePointersMade', 'threePointersAttempted', 'freeThrowsMade', 'freeThrowsAttempted', 
                    'TTFL', 'win', 'plusMinusPoints', 'avg_TTFL']]
                    .sum()
                    .reset_index(drop=False))
        totals['playerName'] = 'Totaux'
        totals['minutes'] = ''
        totals['seconds'] = 48 * 60
        totals['win'] = np.where(totals['win'] >= 1, 1, 0)
        
        df = pd.concat([df, totals], ignore_index=True)

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
                "teamTricode" : "Équipe",
                "minutes": "Mins",
                "points": "Pts",
                "assists": "Ast",
                "reboundsTotal": "Reb",
                "steals": "Stl",
                "blocks": "Blk",
                "turnovers": "Tov",
                "plusMinusPoints": "Pm"
            }, inplace=True)
    
    show_cols = ['Joueur', 'TTFL', 'Mins', 'Pts', 'Ast', 'Reb', 'Stl', 
                                'Blk', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'Matchup', 'Win']
    
    if len(joueurs_pas_dispo) > 0:
        df['Dispo'] = np.where(df['Joueur'].isin(joueurs_pas_dispo), '❌', '✅')
        show_cols.append('Dispo')

    plot_keys, plot_assets = build_plots(df, date, avg_col='avg_TTFL')

    if spoiler:
        cols_shown = ['Joueur', 'Dispo']
        cols_hidden = df.columns.difference(cols_shown).tolist()
        if show_TTFL:
            cols_hidden.remove('TTFL')
        df[cols_hidden] = '-'
    
    # spoiler mode hides the plots too (they would reveal the scores)
    df = df.assign(plots=plot_keys if not spoiler else '')

    dfs = {}
    if byteam:
        for team in teams:
            dfs[team] = df[df['Équipe'] == team].reset_index(drop=True)
    else:
        dfs['all'] = df
    
    html_dfs = {}
    for team, dfteam in dfs.items():
        idx_pick = get_idx_from_pick(dfteam, pick, 'Joueur')

        html_df = df_to_html(dfteam, show_cols=show_cols, 
                             tooltips={
                                        'FG' : 'FGpct',
                                        'FG3' : 'FG3pct',
                                        'FT' : 'FTpct',
                                        'TTFL' : 'perf_str',
                                        'Reb' : 'rebSplit',
                                        'Mins' : 'ttfl_per_min'
                                    },
                             show_index = len(dfteam) > 10,
                             col_header_tooltips=[],
                             color_tooltip_pct=False,
                             highlight_index=idx_pick,
                             col_header_labels = {'FG3' : '3FG', 'Pm' : '±', 'Win' : 'W/L'},
                             best_pick_allowed = not byteam and not show_my_pick,
                             cell_links={'Joueur': {'page': '/Stats_par_joueurs',
                                                'param': 'joueur',
                                                'clean': _clean_player_name}}
                             )
            
        html_dfs[team] = html_df
        
    if 'all' in html_dfs.keys():
        return html_dfs['all'], plot_assets
    else:
        return html_dfs, plot_assets

def on_text_change_nuit():
    """Parse text input into a date object."""
    text_value = st.session_state.date_text_nuit.strip()
    try:
        new_date = datetime.strptime(text_value, "%d/%m/%Y").date()
        st.session_state.selected_date_nuit = new_date
        st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
        st.session_state.text_parse_error_nuit = False
        clear_search()
        update_top_nuit()
        clear_boxscore_vars()
    except ValueError:
        st.session_state.text_parse_error_nuit = True

def prev_date_nuit():
    st.session_state.selected_date_nuit -= timedelta(days=1)
    st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
    clear_search()
    update_top_nuit()
    clear_boxscore_vars()

def next_date_nuit():
    st.session_state.selected_date_nuit += timedelta(days=1)
    st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
    clear_search()
    update_top_nuit()
    clear_boxscore_vars()

def update_top_nuit():
    
    date = st.session_state.date_text_nuit
    name = st.session_state.get('matched_players_nuit', '')
    byteam = st.session_state.get('byteam', False)
    show_my_pick = st.session_state.get('show_my_pick', False)
    spoiler = st.session_state.get('top_nuit_spoiler', False)
    show_TTFL = st.session_state.get('show_TTFL', False)
    joueurs_pas_dispo = get_joueurs_pas_dispo(st.session_state.date_text_nuit)
    pick = get_pick(date=st.session_state.date_text_nuit)
    
    st.session_state.top_nuit = get_top_de_la_nuit(date, name, byteam, show_my_pick, spoiler, 
                                                   show_TTFL, joueurs_pas_dispo, pick)

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

# if __name__ == '__main__':
    # a = get_top_de_la_nuit('17/11/2026', matched_names=[], byteam=False, show_my_pick=False)
    # print(a)
#     date = '13/11/2026'
#     a = run_sql_query(conn_db(),
#                     table='boxscores b', 
#                     filters=[f"gameDate = '{date}'", 'seconds > 0'],
#                     select=['b.playerName', 'b.teamTricode', 'minutes', 'seconds', 'points', 'pat.avg_TTFL', 'reboundsTotal',
#                             'assists', 'reboundsOffensive', 'reboundsDefensive', 'steals', 
#                             'blocks', 'turnovers', 'fieldGoalsMade', 'fieldGoalsAttempted', 
#                             'threePointersMade', 'threePointersAttempted', 'freeThrowsMade', 
#                             'freeThrowsAttempted', 'plusMinusPoints',  'TTFL', 'win'],
#                     joins=[{
#                         'table' : 'player_avg_TTFL pat',
#                         'on' : 'b.playerName = pat.playerName'
#                     }],
#                     order_by=['avg_TTFL', 'b.playerName'])
    
#     print(a)
    


#     b = (scan_boxscores(SEASON)
#          .with_columns(
#              gameDate=pl.col('gameDate_ymd').dt.strftime('%d/%m/%Y'),
#              avg_TTFL=pl.mean('TTFL').over('playerName')
#              )
#          .filter([pl.col('gameDate') == date,
#                   pl.col('seconds') > 0])
#          .select([
#              'playerName', 'teamTricode', 'seconds', 'points', 'avg_TTFL', 'reboundsTotal',
#                     'assists', 'reboundsOffensive', 'reboundsDefensive', 'steals', 
#                     'blocks', 'turnovers', 'fieldGoalsMade', 'fieldGoalsAttempted', 
#                     'threePointersMade', 'threePointersAttempted', 'freeThrowsMade', 
#                     'freeThrowsAttempted', 'plusMinusPoints',  'TTFL', 'win'
#                     ])
#          .collect()
#          .to_pandas()
#          )
    
#     print(b)