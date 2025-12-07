from nba_api.stats.endpoints import ScheduleLeagueV2
from tqdm import tqdm
import pandas as pd
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import SEASON, LEAGUE_ID, NAME2TRICODE

def get_schedule():

    schedule = None
    for attempt in range(5):
        try :
            full_schedule = ScheduleLeagueV2(
                league_id=LEAGUE_ID,
                season=SEASON
            )

            schedule_df = full_schedule.get_data_frames()[0]

            columns_needed = [
                "gameDate",
                "gameId",
                "gameStatus",
                "homeTeam_teamName",
                "awayTeam_teamName",
                "awayTeam_wins",
                "awayTeam_losses",
                "homeTeam_wins",
                "homeTeam_losses",
                "gameDateTimeUTC"
            ]

            schedule = schedule_df[columns_needed].copy()

            schedule['gameDate'] = pd.to_datetime(schedule['gameDate'], errors='coerce')
            schedule['gameDateTimeUTC'] = pd.to_datetime(schedule['gameDateTimeUTC'], errors='coerce')

            schedule['gameDate'] = schedule['gameDate'].dt.strftime('%d/%m/%Y')
            schedule['gameDateTime'] = schedule['gameDateTimeUTC'].dt.tz_convert('Europe/Paris')

            schedule.rename(columns={
                "homeTeam_teamName": "homeTeam",
                "awayTeam_teamName": "awayTeam"
            }, inplace=True)

            schedule['homeTeam'] = schedule['homeTeam'].replace(NAME2TRICODE)
            schedule['awayTeam'] = schedule['awayTeam'].replace(NAME2TRICODE)

            # schedule_reg_season = schedule[schedule['gameId'].astype(str).str.startswith('006')].copy()

            break

        except Exception as e:
            tqdm.write(f'Erreur lors du téléchargement du calendrier : {e}. Nouvel essai dans {3 * (attempt + 1)}s')
            time.sleep(3 * (attempt + 1))
            continue
        
    if schedule is None:
        tqdm.write('Impossible de télécharger le calendrier')
        return None

    return schedule

# Game IDs : starting with 001 : preseason, 002 : regular season, 003 : all-star game, 004 : playoffs, 005 : play-in tournament, 006 : IST finals

if __name__ == '__main__':
    df = get_schedule()
    for i, row in df.iterrows():
        print(row['homeTeam'], row['awayTeam'], row['gameDate'], type(row['gameTime']))
        # print(row['gameDate'] == row['dateEST'], row['gameDate'] == row['dateUTC'])