from nba_api.stats.endpoints import commonplayerinfo, leaguegamelog, leaguedashplayerbiostats
from nba_api.stats.static import players
from tqdm import tqdm
import pandas as pd
import random
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.boxscores_manager import normalize_name, normalize_position
from misc.misc import SEASON, LEAGUE_ID

def fetch_player_positions():

    active_players = players.get_active_players()
    player_ids = [player['id'] for player in active_players]

    player_positions = {'playerName' : [], 'position'  : [], 'country' : [], 'height_ft' : [], 'weight_lbs' : [], 'jersey' : []}
    for player_id in tqdm(player_ids, desc = 'Téléchargement des postes des joueurs (une seule fois)', ncols = 100) :
        for attempt in range(5):
            try:
                player_info = commonplayerinfo.CommonPlayerInfo(player_id, timeout=3).get_data_frames()[0]
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
    df_positions["height_cm"] = df_positions["height_ft"].apply(
        lambda x: int(x.split("-")[0]) * 30.48 + int(x.split("-")[1]) * 2.54)
    df_positions["weight_kg"] = pd.to_numeric(df_positions["weight_lbs"], errors="coerce") * 0.453592

    return df_positions

if __name__ == '__main__':
    a = fetch_player_positions()
    print(a)