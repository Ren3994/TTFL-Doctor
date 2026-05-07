from datetime import datetime
from tqdm import tqdm
import time

def get_cbs_injury_report():
    from bs4 import BeautifulSoup
    import pandas as pd
    import requests

    df = None
    for attempt in range(2) :
        try :
            url = "https://www.cbssports.com/nba/injuries/"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
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
                    # position = cells[1].get_text(strip=True)
                    last_update = cells[2].get_text(strip=True)
                    short_info = cells[3].get_text(strip=True)
                    info = cells[4].get_text(strip=True)
                    
                    try:
                        player_fmt = f"{player.split(' ')[1][len(player.split(' ')[-1]):]} {player.split(' ')[-1]}"
                    except:
                        player_fmt = player

                    try:
                        est_return_fmt = (datetime.strptime(
                            f"{info.split(' ')[-2]} {info.split(' ')[-1]} {datetime.now().year}", '%b %d %Y')
                            .strftime("%d/%m"))
                    except Exception:
                        est_return_fmt = '??'

                    try:
                        last_update_fmt = (datetime.strptime(
                            f'{last_update.split(', ')[-1]} {datetime.now().year}', "%b %d %Y")
                            .strftime("%d/%m"))
                    except:
                        last_update_fmt = '?'

                    records.append({
                        "player_name": player_fmt,
                        "simplified_status": short_info,
                        "injury_status": f'{last_update_fmt}: {short_info} (retour est. : {est_return_fmt})',
                        "details": info
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
    print(get_cbs_injury_report())