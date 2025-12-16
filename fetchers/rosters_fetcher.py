from tqdm import tqdm
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import SEASON, LEAGUE_ID
from update_manager.boxscores_manager import normalize_name

def get_rosters():
    from nba_api.stats.endpoints import CommonAllPlayers

    rosters_df = None
    for attempt in range(5) :
        try:
            allPlayers = CommonAllPlayers(is_only_current_season=1, 
                                          league_id= LEAGUE_ID, 
                                          season=SEASON).get_data_frames()[0]

            allPlayers['teamTricode'] = allPlayers['TEAM_ABBREVIATION']
            allPlayers['playerName'] = allPlayers['DISPLAY_FIRST_LAST']
            allPlayers['playerName'] = allPlayers['playerName'].apply(normalize_name)

            rosters_df = allPlayers[['playerName', 'teamTricode']]
            rosters_df['season'] = SEASON
            break

        except Exception as e:
            tqdm.write(f'Erreur lors du téléchargement des rosters : {e}. Nouvel essai dans {3 * (attempt + 1)}s')
            time.sleep(3 * (attempt + 1))
            continue
    
    if rosters_df is None:
        tqdm.write('Impossible de télécharger les rosters')
        return rosters_df

    return rosters_df

if __name__ == "__main__":
    get_rosters()