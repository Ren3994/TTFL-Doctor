import requests
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.ttfl_data import scan_rosters
from misc.misc import SEASON

def clean_name(name: str) -> str:
    name = name.strip()
    # 1. Split lowercase prefixes glued to the next part: deLarrea -> de Larrea
    name = re.sub(r'\b([a-z]+)(?=[A-Z])', r'\1 ', name)
    # 2. Split suffixes glued to the last name: PippenJr. -> Pippen Jr.
    name = re.sub(r'(?<=[a-z])(Jr\.|Sr\.|III|II|IV)$', r' \1', name)
    return name

STATUSES = {"Out", "Questionable", "Doubtful", "Day-To-Day", "GTD", "Probable"}
KEYWORDS = ['GameDate','GameTime','Matchup','Team','PlayerName','CurrentStatus',
            'AM','PM','Reason','Page','NOTYETSUBMITTED','Injury','Report:']

def get_nbacom_injury_report():
    import polars as pl

    rosters = (scan_rosters(SEASON)
                .with_columns(
                    nocomma=pl.col('playerName').str.replace(',', '')
                )
               .select('nocomma')
               .collect()
               .to_series()
               .to_list())
    
    cols = ['player_name', 'simplified_status', 'injury_status', 'details', 'dt_fetch', 'source']
    dt_fetch = datetime.now(ZoneInfo("Europe/Paris"))
    try:
        soup = BeautifulSoup(requests.get(
            f"https://official.nba.com/nba-injury-report-{SEASON}-season/",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15).text, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith("M.pdf")]
    except Exception:
        return pd.DataFrame(columns=cols)

    pdf_bytes = None
    for link in reversed(links):                    # newest first, walk back on 404
        try:
            r = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code == 200 and r.content[:4] == b'%PDF':
                pdf_bytes = r.content; break
        except Exception:
            continue
    if pdf_bytes is None:
        return pd.DataFrame(columns=cols)

    rows = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                words = page.extract_words() or []
                h_lines = sorted([l for l in page.lines if abs(l["y0"]-l["y1"]) < 1], key=lambda l: l["top"])
                bounds = sorted([page.bbox[3]] + [l["top"] for l in h_lines] + [page.bbox[1]])
                for i in range(len(bounds) - 1):
                    row = sorted((w for w in words if bounds[i] <= w["top"] <= bounds[i+1]), key=lambda w: w["x0"])
                    text = [w["text"] for w in row
                            if '0' not in w["text"] and '1' not in w["text"]
                            and ':' not in w["text"] and '@' not in w["text"]]
                    for kw in KEYWORDS:
                        if kw in text: text.remove(kw)
                    pi = next((j for j, w in enumerate(text) if ',' in w), None)
                    if pi is None or pi + 1 >= len(text) or text[pi+1] not in STATUSES:
                        continue                     # layout drift: skip row, never crash
                    last, _, first = text[pi].partition(',')
                    reason = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ',
                                    " ".join(text[pi+2:])).lstrip('- ').strip()
                    
                    name = f"{first.strip()} {last.strip()}"
                    if name not in rosters:
                        name = clean_name(name)
                        if name not in rosters:
                            print(f'This name is weird : before strip : {first.strip()} {last.strip()}' +
                                  f' -> after strip : {name} still not found')

                    rows.append({"player_name": name,
                                 "simplified_status": text[pi+1],
                                 "injury_status": f'{dt_fetch:%d/%m}: {text[pi+1]}',
                                 "details": reason,
                                 "dt_fetch": dt_fetch,
                                 "source": "NBA.com"})
    except Exception as e:
        print(f"nbacom PDF parse failed: {e}")
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows).drop_duplicates(subset=['player_name', 'simplified_status'])
    return df.reset_index(drop=True) if not df.empty else pd.DataFrame(columns=cols)

if __name__ == '__main__':
#     # rosters = (scan_rosters(SEASON)
#     #            .select('playerName')
#     #            .collect()
#     #            .to_series()
#     #            .to_list())
    
#     # print(rosters)

    a = get_nbacom_injury_report()
    print(a)
    from data.ttfl_data import save_injuries
    save_injuries(a)

#     print('hi')