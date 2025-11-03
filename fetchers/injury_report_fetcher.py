from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm
import pandas as pd
import requests
import time

def get_injury_report() -> pd.DataFrame:
    df = None
    for attempt in range(3) :
        try :

            url = "https://www.espn.com/nba/injuries"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            }

            r = requests.get(url, headers=headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            records = []

            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        continue  # skip header rows

                    player = cells[0].get_text(strip=True)
                    est_return = cells[2].get_text(strip=True)
                    status = cells[3].get_text(strip=True)
                    info = cells[4].get_text(strip=True)

                    # Parse ESPN date (e.g. "Oct 3")
                    try:
                        est_return_dt = datetime.strptime(est_return, "%b %d")
                        est_return_dt = est_return_dt.replace(year=datetime.now().year)
                    except Exception:
                        est_return_dt = None

                    # Simplify status logic
                    text_lower = info.lower()
                    simplified = status
                    if status.lower() == "day-to-day":
                        if any(x in text_lower for x in ["will not suit up", "won't suit up", "isn't warming up", "is not warming up", "not participating", "will be rested", "ruled out", "won't play", "will not play", "is out", "personal", "is not starting", "is not in the starting", "no timetable", "will not be available", "won't be available"]):
                            simplified = "Out"
                        elif "questionable" in text_lower:
                            simplified = "Questionable"
                        elif "probable" in text_lower:
                            simplified = "Probable"

                    # Parse last update
                    last_update = datetime.strptime(info.split(':')[0], "%b %d")
                    last_update = last_update.replace(year=datetime.now().year)

                    # Remove date from info string
                    short_info = info.split(':')[1]

                    records.append({
                        "player_name": player,
                        "simplified_status": simplified,
                        "injury_status": f'{last_update.strftime("%d/%m")}: {simplified} (retour est. : {est_return_dt.strftime("%d/%m")})',
                        "details": short_info
                    })

            df = pd.DataFrame(records)
            break

        except Exception as e:
            tqdm.write(f'Error fetching injury report : {e}. Retrying in 5s')
            time.wait(5)
            continue
        
    if df is None:
        tqdm.write('Could not fetch injury report')
        return df

    return df