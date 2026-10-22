from tqdm import tqdm
import random
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.boxscores_manager import normalize_name, normalize_position, height2cm
from misc.misc import SEASON, LEAGUE_ID

headers = {
"Host": "stats.nba.com",
"Connection": "keep-alive",
"Accept": "application/json, text/plain, /",
"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
"Referer": "https://www.nba.com/",
"Origin": "https://www.nba.com",
"x-nba-stats-origin": "stats",
"x-nba-stats-token": "true",
"Accept-Language": "en-US,en;q=0.9"
}

def fetch_player_positions():
    from nba_api.stats.endpoints import commonplayerinfo
    from nba_api.stats.static import players
    import pandas as pd
    import numpy as np

    active_players = players.get_active_players()
    player_ids = [player['id'] for player in active_players]

    player_positions = {'playerName' : [], 'position'  : [], 'country' : [], 'height_ft' : [], 'weight_lbs' : [], 'jersey' : []}
    for player_id in tqdm(player_ids, desc = 'Téléchargement des postes des joueurs (une seule fois)', ncols = 100) :
        for attempt in range(5):
            try:
                player_info = commonplayerinfo.CommonPlayerInfo(player_id, timeout=3,
                                                                headers=headers).get_data_frames()[0]
                player_positions['playerName'].append(player_info['DISPLAY_FIRST_LAST'][0])
                player_positions['position'].append(player_info['POSITION'][0])
                player_positions['country'].append(player_info['COUNTRY'][0])
                player_positions['height_ft'].append(player_info['HEIGHT'][0])
                player_positions['weight_lbs'].append(player_info['WEIGHT'][0])
                player_positions['jersey'].append(player_info['JERSEY'][0])
                time.sleep(random.uniform(0.3, 0.6))
                break 

            except Exception as e:
                tqdm.write(f"Erreur lors du téléchargement du poste du joueur d\'id {player_id}: {e}. Nouvel essai dans {30 * (attempt + 1)}s")
                time.sleep(30 * (attempt + 1))
        
    df_positions = pd.DataFrame(player_positions)
    df_positions['playerName'] = df_positions['playerName'].apply(normalize_name)
    df_positions['position'] = df_positions['position'].apply(normalize_position)
    df_positions["height_cm"] = df_positions["height_ft"].apply(height2cm)
    df_positions["weight_kg"] = pd.to_numeric(df_positions["weight_lbs"], errors="coerce") * 0.453592
    df_positions['height_ft'] = df_positions['height_ft'].replace('', np.nan)

    return df_positions

if __name__ == '__main__':
    a = fetch_player_positions()
    print(a)