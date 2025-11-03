from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.static import players
from tqdm import tqdm
import pandas as pd
import random
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.utils import normalize_name, normalize_position

def fetch_player_positions():

    active_players = players.get_active_players()
    player_ids = [player['id'] for player in active_players]

    player_positions = {}
    for player_id in tqdm(player_ids, desc = 'Téléchargement des postes des joueurs', ncols = 100) :
        
        for attempt in range(5):
                try:
                    player_info = commonplayerinfo.CommonPlayerInfo(player_id).get_data_frames()[0]
                    player_positions[player_info['DISPLAY_FIRST_LAST'][0]] = player_info['POSITION'][0]
                    time.sleep(random.uniform(0.3, 0.6))
                    break 

                except Exception as e:
                    tqdm.write(f"Error fetching player_id {player_id}: {e}")
                    time.sleep(30 * (attempt + 1))
        
    df_positions = pd.DataFrame(list(player_positions.items()), columns=['playerName', 'position'])
    df_positions['playerName'] = df_positions['playerName'].apply(normalize_name)
    df_positions['position'] = df_positions['position'].apply(normalize_position)

    return df_positions
