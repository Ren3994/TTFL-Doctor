from datetime import datetime
from tqdm import tqdm
import time

def get_injury_report():
    from bs4 import BeautifulSoup
    import pandas as pd
    import requests

    df = None
    for attempt in range(5) :
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
                    
                    try:
                        est_return_fmt = (datetime.strptime(
                            f'{est_return} {datetime.now().year}', '%b %d %Y')
                            .strftime("%d/%m"))
                    except Exception:
                        est_return_fmt = '??'
                    
                    if info != '' and ':' in info:
                        text_lower = info.lower()
                        simplified = status
                        if status.lower() == "day-to-day":
                            if any(x in text_lower for x in ["will not suit up", 
                                                            "won't suit up", 
                                                            "isn't warming up", 
                                                            "is not warming up", 
                                                            "not participating", 
                                                            "will be rested", 
                                                            "ruled out", 
                                                            "won't play", 
                                                            "will not play",
                                                            "will not return",
                                                            "won't return",
                                                            "is out", 
                                                            "personal", 
                                                            "is not starting", 
                                                            "is not in the starting",
                                                            "won't start",
                                                            "won't be starting",
                                                            "won't be in the starting",
                                                            "no timetable", 
                                                            "will not be available", 
                                                            "won't be available"]):
                                simplified = "Out"
                            elif "questionable" in text_lower:
                                simplified = "Questionable"
                            elif "probable" in text_lower:
                                simplified = "Probable"

                        try:
                            last_update_fmt = (datetime.strptime(
                                f'{info.split(':')[0]} {datetime.now().year}', "%b %d %Y")
                                .strftime("%d/%m"))
                        except:
                            last_update_fmt = '?'

                        short_info = info.split(':')[1]
                    else:
                        last_update_fmt = '?? '
                        simplified = ''
                        short_info = ''

                    records.append({
                        "player_name": player,
                        "simplified_status": simplified,
                        "injury_status": f'{last_update_fmt}: {simplified} (retour est. : {est_return_fmt})',
                        "details": short_info
                    })

            df = pd.DataFrame(records)
            return df

        except Exception as e:
            tqdm.write(f'Erreur lors du téléchargement du injury report : {e}. Nouvel essai dans {3 * (attempt + 1)}s')
            time.sleep(3 * (attempt + 1))
            continue
        
    if df is None:
        tqdm.write('Impossible de télécharger le injury report (espn.com)')
        return df

    return df

if __name__ == '__main__':
    get_injury_report()