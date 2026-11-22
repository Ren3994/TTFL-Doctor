from tqdm import tqdm
import random
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.net_utils import RateLimiter, nba_frames, NBA_API, not_empty
from fetchers.helpers import normalize_name, normalize_position, height2cm

def fetch_player_positions():
    from nba_api.stats.endpoints import commonplayerinfo
    from nba_api.stats.static import players
    import pandas as pd
    import numpy as np

    player_ids = [p['id'] for p in players.get_active_players()]
    limiter = RateLimiter((0.3, 0.6))        # before every attempt, retries included

    # One record per player, appended only once the whole row is read. (The old code
    # appended column by column: an error halfway through left the lists with
    # different lengths and the retry then appended the early columns AGAIN.)
    records = []
    for player_id in tqdm(player_ids, desc='Téléchargement des postes des joueurs (une seule fois)', ncols=100):
        info = nba_frames(
            commonplayerinfo.CommonPlayerInfo, label=f"poste du joueur {player_id}",
            policy=NBA_API, validate=not_empty, limiter=limiter,
            player_id=player_id, timeout=3)
        if info is None:                     # already logged by net_utils; skip this player
            continue
        row = info.iloc[0]
        records.append({'playerName': row['DISPLAY_FIRST_LAST'], 'position': row['POSITION'],
                        'country': row['COUNTRY'], 'height_ft': row['HEIGHT'],
                        'weight_lbs': row['WEIGHT'], 'jersey': row['JERSEY']})

    df_positions = pd.DataFrame(records, columns=['playerName', 'position', 'country',
                                                  'height_ft', 'weight_lbs', 'jersey'])
    df_positions['playerName'] = df_positions['playerName'].apply(normalize_name)
    df_positions['position'] = df_positions['position'].apply(normalize_position)
    df_positions["height_cm"] = df_positions["height_ft"].apply(height2cm)
    df_positions["weight_kg"] = pd.to_numeric(df_positions["weight_lbs"], errors="coerce") * 0.453592
    df_positions['height_ft'] = df_positions['height_ft'].replace('', np.nan)

    return df_positions

if __name__ == '__main__':
    a = fetch_player_positions()
    print(a)