from tqdm import tqdm
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import SEASON, LEAGUE_ID, FULLNAME2TRICODE

def get_team_stats():
    from nba_api.stats.endpoints import leaguedashteamstats

    table_types = ['Advanced', 'Base']
    cols_needed = [
        ['TEAM_NAME', 'GP', 'W', 'L', 'W_PCT',
            'OFF_RATING', 'DEF_RATING',
            'NET_RATING', 'AST_PCT', 'AST_TO', 'AST_RATIO', 'OREB_PCT', 'DREB_PCT',
            'REB_PCT', 'TM_TOV_PCT', 'EFG_PCT', 'TS_PCT', 'PACE', 'POSS',
            ], 
        ['TEAM_NAME', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA',
            'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'TOV', 'STL', 'BLK', 'PTS', 'BLKA', 'PFD'
            ]
    ]
    replace_cols = [{
                "TEAM_NAME": "teamTricode",
                "OFF_RATING": "ORtg",
                "DEF_RATING": "DRtg",
                "NET_RATING": "NRtg",
                "PACE": "Pace",
                "POSS": "n_poss",
            }, {"TEAM_NAME": "teamTricode"}]

    tables = [None, None]
    idx = [0, 1]
    t0 = time.time()
    for i, table, table_type, cols, rep_cols in zip(idx, tables, table_types, cols_needed, replace_cols):
        while i == 1 and time.time() - t0 < 0.1:
            time.sleep(0.1)
        for attempt in range(5):
            try :
                table = leaguedashteamstats.LeagueDashTeamStats(
                    season=SEASON,
                    measure_type_detailed_defense=table_type,
                    per_mode_detailed="PerGame",
                    league_id_nullable=LEAGUE_ID
                ).get_data_frames()[0]
                break

            except Exception as e:
                tqdm.write(f'Erreur lors du téléchargement des stats des équipes ({table_type}) : {e}. Nouvel essai dans {30 * (attempt + 1)}s')
                time.sleep(30 * (attempt + 1))
                continue
            
        if table is None:
            tqdm.write(f'Impossible de télécharger les stats des équipes : {table_type}')
            continue

        table = table[cols].copy()
        table['TEAM_NAME'] = table['TEAM_NAME'].replace(FULLNAME2TRICODE)
        table.rename(columns=rep_cols, inplace=True)
        tables[i] = table
    
    full_stats = tables[0].merge(tables[1], left_on=['teamTricode'], right_on=['teamTricode'])
    return full_stats

if __name__ == '__main__':
    team_stats = get_team_stats()
    print(team_stats.columns)