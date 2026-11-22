from tqdm import tqdm
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.net_utils import nba_frames, NBA_API, not_empty, RateLimiter
from misc.misc import LEAGUE_ID, FULLNAME2TRICODE
from data.ttfl_data import latest_season

STATS_LIMITER = RateLimiter(0.5)

def get_team_stats(proxy=None):
    from nba_api.stats.endpoints import leaguedashteamstats

    table_types = ['Advanced', 'Base']
    cols_needed = [
        ['TEAM_NAME', 'GP', 'W', 'L', 'W_PCT',
         'OFF_RATING', 'DEF_RATING',
         'NET_RATING', 'AST_PCT', 'AST_TO', 'AST_RATIO', 'OREB_PCT', 'DREB_PCT',
         'REB_PCT', 'TM_TOV_PCT', 'EFG_PCT', 'TS_PCT', 'PACE', 'POSS'],
        ['TEAM_NAME', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA',
         'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'TOV', 'STL', 'BLK', 'PTS', 'BLKA', 'PFD'],
    ]
    replace_cols = [{
        "TEAM_NAME": "teamTricode", "OFF_RATING": "ORtg", "DEF_RATING": "DRtg",
        "NET_RATING": "NRtg", "PACE": "Pace", "POSS": "n_poss",
    }, {"TEAM_NAME": "teamTricode"}]

    season = latest_season()                 # once, not once per attempt
    tables = []
    for table_type, cols, rep_cols in zip(table_types, cols_needed, replace_cols):
        table = nba_frames(
            leaguedashteamstats.LeagueDashTeamStats,
            label=f"stats des équipes ({table_type})",
            policy=NBA_API, validate=not_empty,
            limiter=STATS_LIMITER,           # replaces the `while time.time() - t0 < 0.1` hack
            season=season,
            measure_type_detailed_defense=table_type,
            per_mode_detailed="PerGame",
            league_id_nullable=LEAGUE_ID,
            proxy=proxy)

        if table is None:                    # fail fast: no point downloading the 2nd table
            tqdm.write('Stats des équipes : une des deux tables a échoué, on garde les anciennes')
            return None

        table = table[cols].copy()
        table['TEAM_NAME'] = table['TEAM_NAME'].replace(FULLNAME2TRICODE)
        table.rename(columns=rep_cols, inplace=True)
        tables.append(table)

    return tables[0].merge(tables[1], on=['teamTricode'])

if __name__ == '__main__':
    team_stats = get_team_stats()
    print(team_stats.columns)