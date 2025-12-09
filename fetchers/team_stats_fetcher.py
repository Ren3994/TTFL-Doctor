from tqdm import tqdm
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import SEASON, LEAGUE_ID, FULLNAME2TRICODE

def get_team_stats():
    from nba_api.stats.endpoints import leaguedashteamstats

    team_stats=None
    for attempt in range(5):
        try :
            team_stats = leaguedashteamstats.LeagueDashTeamStats(
                season=SEASON,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="Per100Possessions",
                league_id_nullable=LEAGUE_ID
            ).get_data_frames()[0]

        except Exception as e:
            tqdm.write(f'Erreur lors du téléchargement des stats des équipes : {e}. Nouvel essai dans {30 * (attempt + 1)}s')
            time.sleep(30 * (attempt + 1))
            continue
        
    if team_stats is None:
        tqdm.write('Impossible de télécharger les stats des équipes')
        return team_stats
    
    columns_needed = [
        'TEAM_NAME', 'GP', 'W', 'L', 'W_PCT',
        'OFF_RATING', 'DEF_RATING',
        'NET_RATING', 'AST_PCT', 'AST_TO', 'AST_RATIO', 'OREB_PCT', 'DREB_PCT',
        'REB_PCT', 'TM_TOV_PCT', 'EFG_PCT', 'TS_PCT', 'PACE', 'POSS'
    ]

    team_stats = team_stats[columns_needed].copy()
    team_stats['TEAM_NAME'] = team_stats['TEAM_NAME'].replace(FULLNAME2TRICODE)

    team_stats.rename(columns={
                "TEAM_NAME": "teamTricode",
                "OFF_RATING": "ORtg",
                "DEF_RATING": "DRtg",
                "NET_RATING": "NRtg",
                "PACE": "Pace",
                "POSS": "n_poss",
            }, inplace=True)

    return team_stats

if __name__ == '__main__':
    team_stats = get_team_stats()
    print(team_stats)