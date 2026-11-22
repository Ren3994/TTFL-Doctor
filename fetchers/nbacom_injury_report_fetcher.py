from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from tqdm import tqdm
import pandas as pd
import pdfplumber
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.ttfl_data import scan_rosters, latest_season
from fetchers.net_utils import http_get, WEB
from fetchers.helpers import normalize_name

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

_UA = {"User-Agent": "Mozilla/5.0"}


def get_nbacom_injury_report():
    import polars as pl

    SEASON = latest_season()
    rosters = (scan_rosters(SEASON)
               .with_columns(nocomma=pl.col('playerName').str.replace(',', ''))
               .select('nocomma')
               .collect()
               .to_series()
               .to_list())

    cols = ['player_name', 'simplified_status', 'injury_status', 'details', 'dt_fetch', 'source']
    dt_fetch = datetime.now(ZoneInfo("Europe/Paris"))

    page = http_get(f"https://official.nba.com/nba-injury-report-{SEASON}-season/",
                    headers=_UA, timeout=15, policy=WEB, label="page injury report NBA.com")
    if page is None:
        return pd.DataFrame(columns=cols)
    try:
        soup = BeautifulSoup(page.text, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith("M.pdf")]
    except Exception:                                   # noqa: BLE001
        return pd.DataFrame(columns=cols)

    # Newest first, walk back on 404. Each link now gets a short retry for timeouts/5xx
    # BEFORE falling back to an older PDF (previously one timeout silently meant stale
    # data). 404/403 are permanent -> immediate next link. log=None: walking back over
    # missing PDFs is normal, not worth a warning per link.
    pdf_policy = WEB.replace(max_attempts=2, wait_base=2)
    pdf_bytes = None
    for link in reversed(links):
        r = http_get(link, headers=_UA, timeout=15, policy=pdf_policy, log=None,
                     validate=lambda resp: resp.content[:4] == b'%PDF')
        if r is not None:
            pdf_bytes = r.content
            break
    if pdf_bytes is None:
        tqdm.write("Injury report NBA.com : aucun PDF téléchargeable")
        return pd.DataFrame(columns=cols)

    # ---- parsing: unchanged from your version ------------------------------
    rows = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page_ in pdf.pages:
                words = page_.extract_words() or []
                h_lines = sorted([l for l in page_.lines if abs(l["y0"]-l["y1"]) < 1],
                                 key=lambda l: l["top"])
                bounds = sorted([page_.bbox[3]] + [l["top"] for l in h_lines] + [page_.bbox[1]])
                for i in range(len(bounds) - 1):
                    row = sorted((w for w in words if bounds[i] <= w["top"] <= bounds[i+1]),
                                 key=lambda w: w["x0"])
                    text = [w["text"] for w in row
                            if '0' not in w["text"] and '1' not in w["text"]
                            and ':' not in w["text"] and '@' not in w["text"]]
                    for kw in KEYWORDS:
                        if kw in text:
                            text.remove(kw)
                    pi = next((j for j, w in enumerate(text) if ',' in w), None)
                    if pi is None or pi + 1 >= len(text) or text[pi+1] not in STATUSES:
                        continue                     # layout drift: skip row, never crash
                    last, _, first = text[pi].partition(',')
                    reason = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ',
                                    " ".join(text[pi+2:])).lstrip('- ').strip()

                    name = f"{first.strip()} {last.strip()}"
                    name = normalize_name(name)
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
    except Exception as e:                              # noqa: BLE001
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