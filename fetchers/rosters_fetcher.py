from tqdm import tqdm
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.net_utils import NBA_API, nba_frames, not_empty, RateLimiter
from fetchers.helpers import normalize_name
from data.ttfl_stats import latest_season
from misc.misc import LEAGUE_ID

def get_rosters(proxy=None):
    from nba_api.stats.endpoints import CommonAllPlayers

    SEASON = latest_season()
    STATS_LIMITER = RateLimiter(0.5)

    allPlayers = nba_frames(
        CommonAllPlayers, label="rosters", policy=NBA_API, validate=not_empty,
        limiter=STATS_LIMITER,
        is_only_current_season=1, league_id=LEAGUE_ID, season=SEASON, proxy=proxy)

    if allPlayers is None:
        tqdm.write('Impossible de télécharger les rosters')
        return None

    # Post-processing is OUTSIDE the retry: a missing column is a bug/schema change
    # and should raise a KeyError right away, not be retried for 2 minutes.
    allPlayers['teamTricode'] = allPlayers['TEAM_ABBREVIATION']
    allPlayers['playerName'] = allPlayers['DISPLAY_FIRST_LAST'].apply(normalize_name)

    rosters_df = allPlayers[['playerName', 'teamTricode']].copy()
    rosters_df['season'] = SEASON
    rosters_df['position'] = '?'
    return rosters_df

if __name__ == "__main__":
    a = get_rosters()
    print(a)