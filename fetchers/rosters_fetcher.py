from nba_api.stats.endpoints import CommonAllPlayers
from tqdm import tqdm
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import SEASON, LEAGUE_ID
from fetchers.utils import normalize_name

def get_rosters():
    rosters_df = None
    for attempt in range(3) :
        try:
            allPlayers = CommonAllPlayers(is_only_current_season=1, league_id= LEAGUE_ID, season=SEASON).get_data_frames()[0]

            allPlayers['teamTricode'] = allPlayers['TEAM_ABBREVIATION']
            allPlayers['playerName'] = allPlayers['DISPLAY_FIRST_LAST']
            allPlayers['playerName'] = allPlayers['playerName'].apply(normalize_name)

            rosters_df = allPlayers[['playerName', 'teamTricode']]
            break

        except Exception as e:
            tqdm.write(f'Error fetching roster : {e}. Retrying in 30s')
            time.wait(30)
            continue
    
    if rosters_df is None:
        tqdm.write('Could not update roster')
        return rosters_df

    return rosters_df

if __name__ == "__main__":
    get_rosters()