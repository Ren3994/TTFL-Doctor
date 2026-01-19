from tqdm import tqdm
import time

def fetch_boxscores(game_date, game_id, visitor_team, home_team):
    from nba_api.stats.endpoints import BoxScoreTraditionalV3
    from datetime import timedelta
    import pandas as pd
    
    boxscore_df = pd.DataFrame()
    if not game_id:
        return boxscore_df

    for attempt in range(3):
        try:
            boxscore = BoxScoreTraditionalV3(
                game_id=game_id,
                start_period=1,
                end_period=10,
                start_range=0,
                end_range=0,
                range_type=0,
                timeout=5
                )
            
            boxscore_df = boxscore.get_data_frames()[0]

            boxscore_df['homeTeam'] = home_team
            boxscore_df['visitorTeam'] = visitor_team
            boxscore_df['gameDate'] = game_date.strftime('%d/%m/%Y')
            boxscore_df['gameDate_ymd'] = game_date.strftime('%Y-%m-%d')
            prev_date = game_date - timedelta(days=1)
            boxscore_df['prev_gameDate_ymd'] = prev_date.strftime('%Y-%m-%d')
            return boxscore_df

        except ValueError:
            tqdm.write(f'Données du boxscore de {game_id} : {home_team}-{visitor_team} du {game_date} malformées chez la source. Réessayer dans quelques heures.')
            return boxscore_df
        
        except AttributeError:
            tqdm.write(f'Données du boxscore de {game_id} : {home_team}-{visitor_team} du {game_date} malformées chez la source. Réessayer dans quelques heures.')
            return boxscore_df
    
        except Exception as e:
            tqdm.write(f'Erreur lors du téléchargement du boxscore de {game_id} : {home_team}-{visitor_team} du {game_date} : {e}. Nouvel essai dans {30 * (attempt + 1)}s')
            time.sleep(30 * (attempt + 1))
            continue

    return boxscore_df

if __name__ == '__main__':
    from datetime import datetime
    df = fetch_boxscores(datetime.strptime('15/12/2025', '%d/%m/%Y'), '0022501227', 'TOR', 'MIA')
    print(df)