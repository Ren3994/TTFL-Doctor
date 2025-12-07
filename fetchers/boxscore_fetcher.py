from nba_api.stats.endpoints import BoxScoreTraditionalV3
from tqdm import tqdm
import pandas as pd
import time

def fetch_boxscores(game_date, game_id, visitor_team, home_team):
    
    boxscore_df = pd.DataFrame()
    if not game_id:
        return boxscore_df

    for attempt in range(5):
        try:
            boxscore = BoxScoreTraditionalV3(
                game_id=game_id,
                start_period=1,
                end_period=10,
                start_range=0,
                end_range=0,
                range_type=0
                )
            
            boxscore_df = boxscore.get_data_frames()[0]

            boxscore_df['homeTeam'] = home_team
            boxscore_df['visitorTeam'] = visitor_team
            boxscore_df['gameDate'] = game_date.strftime('%d/%m/%Y')
            return boxscore_df

        except ValueError:
            tqdm.write(f'Données du boxscore de {home_team}-{visitor_team} du {game_date} malformées chez la source. Réessayer dans quelques heures.')
            return boxscore_df
    
        except Exception as e:
            tqdm.write(f'Erreur lors du téléchargement du boxscore de {home_team}-{visitor_team} du {game_date} : {e}. Nouvel essai dans {30 * (attempt + 1)}s')
            time.sleep(30 * (attempt + 1))
            continue

    return boxscore_df

# if __name__ == '__main__':
#     df = fetch_boxscores(datetime.strptime('10/11/2025', '%d/%m/%Y'), '0022500202', 'CHI', 'SAS')
#     print(df)