from datetime import datetime
from tqdm import tqdm
import streamlit as st
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.ttfl_data import save_boxscores, refresh_reference_data, get_missing_gameids, season_for_date
from fetchers.helpers import normalize_name, normalize_position, log_failure
from fetchers.net_utils import RateLimiter, nba_frames, NBA_API
from misc.misc import NAME2TRICODE

BOXSCORE_POLICY = NBA_API.replace(max_attempts=3, wait_base=30, wait_max=60,
                                  give_up_on=(ValueError, AttributeError))

def add_columns(df) :
    import numpy as np
    df['season'] = df['gameDate_ymd'].map(season_for_date)
    df['playerName'] = df['firstName'] + ' ' + df['familyName']
    df['playerName'] = df['playerName'].apply(normalize_name)

    df['isHome'] = (df['teamTricode'] == df['homeTeam']).astype(int)

    df['opponent'] = np.where(df['isHome'] == 1, df['visitorTeam'], df['homeTeam'])

    df['minutes'] = df['minutes'].astype('string')

    s = df['minutes'].fillna('0').replace('', '0')

    mmss = s.str.contains(':')
    df['seconds'] = (
        s.where(mmss, s + ':0')
        .str.split(':', expand=True)
        .astype(int)
        .pipe(lambda x: x[0] * 60 + x[1])
    )
    
    df['TTFL'] = (
            df['points'] +
            df['assists'] +
            df['reboundsTotal'] +
            df['steals'] +
            df['blocks'] +
            df['fieldGoalsMade'] +
            df['threePointersMade'] +
            df['freeThrowsMade'] -
            df['turnovers'] -
            (df['fieldGoalsAttempted'] - df['fieldGoalsMade']) -
            (df['threePointersAttempted'] - df['threePointersMade']) -
            (df['freeThrowsAttempted'] - df['freeThrowsMade'])
            )
    
    team_points = df.groupby(['gameId', 'teamTricode'])['points'].transform('sum')
    df['teamPoints'] = team_points

    df['opponentPoints'] = df.groupby('gameId')['teamPoints'].transform(lambda x: x.max() + x.min() - x)

    df['win'] = (df['teamPoints'] > df['opponentPoints']).astype(int)

    df['teamTTFL'] = df.groupby(['gameId', 'teamTricode'])['TTFL'].transform('sum')
    df['opponentTTFL'] = df.groupby('gameId')['TTFL'].transform('sum') - df['teamTTFL']

    return df

def clean_boxscores(df):
    cols_to_keep = [
        'gameId', 'teamTricode', 'isHome', 'opponent',
        'playerName', 'minutes', 'points', 'assists',
        'reboundsTotal', 'steals', 'blocks', 'turnovers', 'fieldGoalsMade',
        'fieldGoalsAttempted', 'threePointersMade', 'threePointersAttempted',
        'freeThrowsMade', 'freeThrowsAttempted', 'plusMinusPoints', 'TTFL',
        'teamPoints', 'opponentPoints', 'win', 'teamTTFL', 'opponentTTFL',
        'homeTeam', 'visitorTeam', 'seconds', 'gameDate', 'gameDate_ymd',
        'reboundsOffensive', 'reboundsDefensive', 'position', 'season', 'prev_gameDate_ymd'
    ]    
    cols_to_remap = ['opponent', 'homeTeam', 'visitorTeam']
    
    int_cols = [
        'points', 'assists', 'reboundsTotal', 'steals', 'blocks', 'turnovers',
        'fieldGoalsMade', 'fieldGoalsAttempted', 'threePointersMade', 'threePointersAttempted',
        'freeThrowsMade', 'freeThrowsAttempted', 'TTFL', 'teamPoints', 'opponentPoints',
        'win', 'teamTTFL', 'opponentTTFL', 'plusMinusPoints'
    ]
    
    df_clean = df[cols_to_keep].copy()
    df_clean[cols_to_remap] = df_clean[cols_to_remap].replace(NAME2TRICODE)
    df_clean.loc[:, int_cols] = df_clean[int_cols].astype(int)
    df_clean['position'] = df_clean['position'].apply(normalize_position)
    df_clean.rename(columns={'position' : 'position_boxscores'}, inplace=True)
    
    return df_clean

def _pacing_for(n_missing):
    """(low, high) seconds between boxscore requests, by backlog size."""
    if n_missing < 5:
        return (0.2, 0.5)
    if n_missing < 15:
        return (0.6, 1.0)
    if n_missing > 100:
        return (3.0, 5.0)
    return (1.5, 2.5)


def _download_missing_games(missing_df, proxy, progress, status):
    """One pass over the missing games. No retry loop here: fetch_boxscores already
    retries each game once (the old code stacked 5 x 3 attempts)."""
    import pandas as pd

    games = missing_df.to_pandas()
    total = len(games)
    limiter = RateLimiter(_pacing_for(total))   # replaces sleep(uniform(...)) after success

    for i, game_info in games.iterrows():
        game_id = game_info['gameId']
        game_date = datetime.strptime(game_info['gameDate'], '%d/%m/%Y')
        visitor_team = game_info['awayTeam']
        home_team = game_info['homeTeam']
        if status is not None:
            status.text(f"Téléchargement du match {i+1}/{total} ({home_team} - {visitor_team})")

        try:
            boxscore = get_boxscores(game_date, game_id, visitor_team, home_team,
                                     proxy=proxy, limiter=limiter)
        except Exception as e:      # noqa: BLE001
            # add_columns / clean_boxscores bug on ONE game: isolate it, don't retry
            # (not transient) and don't kill the whole run.
            tqdm.write(f"Erreur lors du traitement du match {game_id}: {type(e).__name__}: {e}")
            log_failure(game_date, game_id, str(e))
            boxscore = None

        if boxscore is not None and not boxscore.empty and game_id in boxscore['gameId'].values:
            save_boxscores(pd.DataFrame(boxscore.to_dict(orient="records")))

        if progress is not None:
            progress.progress((i + 1) / total)


def update_nba_data(proxy=None, update_attempt=1, max_update_attempts=3,
                    init_database=True, progress=None, status=None):
    if init_database:
        refresh_reference_data(proxy=proxy)

    missing_gameIds_df = get_missing_gameids()
    if missing_gameIds_df.is_empty():
        return False                                    # new_games_found

    if progress is None:
        progress = st.progress(0)
        status = st.empty()

    # The recursion became a loop: same rounds, same 10s pause, same messages.
    while True:
        _download_missing_games(missing_gameIds_df, proxy, progress, status)

        missing_gameIds_df = get_missing_gameids()
        if missing_gameIds_df.is_empty():
            break
        if update_attempt >= max_update_attempts:
            tqdm.write(f'Still missing {len(missing_gameIds_df)} but they could not be fetched.')
            break
        update_attempt += 1
        tqdm.write(f'Retry {update_attempt}/{max_update_attempts} for '
                   f'{len(missing_gameIds_df)} missing games...')
        time.sleep(10)

    if progress is not None:
        progress.progress(1.0)
    return True                                         # new_games_found


def get_boxscores(game_date, game_id, visitor_team, home_team, proxy=None, limiter=None):
    import pandas as pd

    boxscores = fetch_boxscores(game_date, game_id, visitor_team, home_team,
                                proxy=proxy, limiter=limiter)
    if boxscores.empty:
        return pd.DataFrame()
    full_boxscores = add_columns(boxscores)
    return clean_boxscores(full_boxscores)


def fetch_boxscores(game_date, game_id, visitor_team, home_team, proxy=None, limiter=None):
    from nba_api.stats.endpoints import BoxScoreTraditionalV3
    from datetime import timedelta
    import pandas as pd

    if not game_id:
        return pd.DataFrame()

    def on_final_failure(exc):
        if isinstance(exc, (ValueError, AttributeError)):
            tqdm.write(f'Données du boxscore de {game_id} : {home_team}-{visitor_team} '
                       f'du {game_date} malformées chez la source. Réessayer dans quelques heures.')
        else:                                   # network trouble that outlasted the retries
            log_failure(game_date, game_id, f"{type(exc).__name__}: {exc}")

    boxscore_df = nba_frames(
        BoxScoreTraditionalV3,
        label=f"boxscore {game_id} ({home_team}-{visitor_team})",
        policy=BOXSCORE_POLICY, limiter=limiter, on_final_failure=on_final_failure,
        game_id=game_id, start_period=1, end_period=10,
        start_range=0, end_range=0, range_type=0, timeout=5, proxy=proxy)

    if boxscore_df is None:
        return pd.DataFrame()

    boxscore_df['homeTeam'] = home_team
    boxscore_df['visitorTeam'] = visitor_team
    boxscore_df['gameDate'] = game_date.strftime('%d/%m/%Y')
    boxscore_df['gameDate_ymd'] = game_date.strftime('%Y-%m-%d')
    boxscore_df['prev_gameDate_ymd'] = (game_date - timedelta(days=1)).strftime('%Y-%m-%d')
    return boxscore_df