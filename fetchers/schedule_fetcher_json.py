from tqdm import tqdm
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import SEASON

def get_schedule_json(proxy=None):
    from curl_cffi import requests
    import pandas as pd

    url = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'

    session = requests.Session(impersonate="chrome")
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.nba.com",
        "Referer": "https://www.nba.com/",
    })
    
    schedule = None

    for attempt in range(5):
        try :
            r = session.get(url, timeout=5)
            r.raise_for_status()
            response = r
            break
        except Exception as e:
            tqdm.write(f'Error while downloading schedule JSON : {e}')
            if attempt < 4:
                time.sleep(3 * (attempt + 1))
    
    if response is None:
        tqdm.write('Impossible de télécharger le calendrier')
        return None

    schedule_parts = []
    
    for date_dict in response.json()['leagueSchedule']['gameDates']:
        frame = pd.json_normalize(date_dict['games'], )
        frame['gameDate'] = date_dict['gameDate']
        schedule_parts.append(frame)

    schedule = pd.concat(schedule_parts, ignore_index=True)

    columns_needed = [
                "gameDate",
                "gameId",
                "gameStatus",
                "homeTeam.teamTricode",
                "awayTeam.teamTricode",
                "awayTeam.wins",
                "awayTeam.losses",
                "homeTeam.wins",
                "homeTeam.losses",
                "gameDateTimeUTC",
                "postponedStatus",
                "gameSubtype"
            ]

    schedule = schedule[columns_needed]

    schedule['gameDate'] = pd.to_datetime(schedule['gameDate'], errors='coerce')
    schedule['gameDateTimeUTC'] = pd.to_datetime(schedule['gameDateTimeUTC'], utc=True, errors='coerce')
    
    schedule['gameDate_ymd'] = schedule['gameDate'].dt.strftime('%Y-%m-%d')
    schedule['gameDate'] = schedule['gameDate'].dt.strftime('%d/%m/%Y')
    schedule['gameDateTime'] = schedule['gameDateTimeUTC'].dt.tz_convert('Europe/Paris')

    schedule['gameSubtype'] = schedule['gameSubtype'].str.contains('in-season', na=False).astype('int8')
    schedule['postponedStatus'] = (
        schedule['postponedStatus'].map({'Y': 1, 'N': 0}).fillna(0).astype('int8')
    )

    schedule.rename(columns={
        "homeTeam.teamTricode": "homeTeam",
        "awayTeam.teamTricode": "awayTeam",
        "homeTeam.wins": "homeTeam_wins",
        "homeTeam.losses": "homeTeam_losses",
        "awayTeam.wins": "awayTeam_wins",
        "awayTeam.losses": "awayTeam_losses",
        "postponedStatus" : "postponed",
        "gameSubtype" : "IST"
    }, inplace=True)

    schedule['season'] = SEASON
    
    return schedule

if __name__ == '__main__':
    import time
    import pandas as pd
    t0 = time.time()
    # print()
    a = get_schedule_json()
    from fetchers.schedule_fetcher import get_schedule
    
    b = get_schedule()
    b['awayTeam'].replace('Lions', 'LON', inplace=True)

    pd.testing.assert_frame_equal(a, b)
    print(time.time() - t0)