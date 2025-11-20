from datetime import datetime
import pandas as pd
import unicodedata
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import FAILED_LOG_PATH, CHAR_MAP, NAME2TRICODE
from fetchers.boxscore_fetcher import fetch_boxscores

def get_boxscores(game_date, game_id, visitor_team, home_team):
    boxscores = fetch_boxscores(game_date, game_id, visitor_team, home_team)
    if boxscores.empty:
        return pd.DataFrame()
    full_boxscores = add_columns(boxscores)
    full_boxscores_clean = clean_boxscores(full_boxscores)
    return full_boxscores_clean

def log_failure(game_date, game_id, error):
    """Append a failed game ID and reason to a log file."""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(FAILED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] GameDate: {game_date} - GameID: {game_id} - Error: {error}\n")

def normalize_name(name: str) -> str:
    """
    Normalize player names:
    - Replace special characters via CHAR_MAP
    - Remove accents using Unicode normalization
    - Strip double spaces, trim, etc.
    """
    if not name:
        return name

    # Step 1: Apply manual mapping
    for src, target in CHAR_MAP.items():
        name = name.replace(src, target)

    # Step 2: Remove diacritics (accents)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(ch for ch in name if unicodedata.category(ch) != 'Mn')

    # Step 3: Cleanup
    name = " ".join(name.split())  # collapse multiple spaces
    return name.strip()

def normalize_position(pos: str) -> str:
    """
    Normalize NBA position strings into abbreviated forms.
    
    Examples:
        'Forward' -> 'F'
        'Center' -> 'C'
        'Guard' -> 'G'
        'Center-Forward' -> 'C-F'
        'Forward-Center' -> 'F-C'
    """
    pos = pos.strip()  # Remove leading/trailing whitespace
    mapping = {
        'Guard': 'G',
        'Forward': 'F',
        'Center': 'C',
    }
    
    if '-' in pos:
        parts = pos.split('-')
        parts = [mapping.get(p, p) for p in parts]  # map to abbreviations
        return '-'.join(parts)
    else:
        return mapping.get(pos, pos)

def add_columns(df) :

    df['playerName'] = df['firstName'] + ' ' + df['familyName']
    df['playerName'] = df['playerName'].apply(normalize_name)

    df['isHome'] = (df['teamTricode'] == df['homeTeam']).astype(int)

    df['opponent'] = np.where(df['isHome'] == 1, df['visitorTeam'], df['homeTeam'])

    df['seconds'] = (
    df['minutes'].replace('', '0:00')
    .str.extract(r'(?:(\d+):(\d+))?', expand=True)
    .fillna(0).astype(int)
    .pipe(lambda x: x[0]*60 + x[1])
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
        'homeTeam', 'visitorTeam', 'seconds', 'gameDate',
        'reboundsOffensive', 'reboundsDefensive'
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
    
    return df_clean