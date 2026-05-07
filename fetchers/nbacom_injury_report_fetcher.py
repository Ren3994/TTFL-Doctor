import requests
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
import re

def splitCap(s):
    s_all = re.findall(r"[A-Z][a-z]*", s)
    return ' '.join(s_all)

def get_player_injury_data(splitline, i):
    player = f'{splitline[i].split(",")[1]} {splitline[i].split(",")[0]}'
    status = splitline[i+1]

    if splitline[i+2].endswith(';'):
        injury_type = splitline[i+3]
        injury_location = splitCap(splitline[i+2].split('-')[1].split(';')[0])

    elif ';' in splitline[-2]:
        injury_type = splitline[i+2].split(';')[-1] + ' ' + splitline[i+3]
        injury_location = splitCap(splitline[i+2].split('-')[1].split(';')[0])

    else:
        injury_type = splitCap(splitline[i+2].split('-')[1].split(';')[1])
        injury_location = splitCap(splitline[i+2].split('-')[1].split(';')[0])

    return player, status, injury_type, injury_location

def get_nbacom_injury_report():
    PAGE_URL = "https://official.nba.com/nba-injury-report-2025-26-season/"
    HEADERS = {"User-Agent": "Mozilla/5.0"}

    html = requests.get(PAGE_URL, headers=HEADERS).text
    soup = BeautifulSoup(html, "html.parser")

    pdf_link = next(
        a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].endswith("M.pdf")
    )

    pdf_bytes = requests.get(pdf_link).content
    all_rows = []

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:

        for page in pdf.pages:

            words = page.extract_words()
            h_lines = page.lines

            if not words:
                continue

            row_lines = sorted(
                [l for l in h_lines if abs(l["y0"] - l["y1"]) < 1],
                key=lambda l: l["top"]
            )

            boundaries = [page.bbox[3]] + [l["top"] for l in row_lines] + [page.bbox[1]]
            boundaries = sorted(boundaries)

            for i in range(len(boundaries) - 1):

                bottom = boundaries[i]
                top = boundaries[i + 1]

                row_words = [
                    w for w in words
                    if bottom <= w["top"] <= top
                ]

                if not row_words:
                    continue

                row_words = sorted(row_words, key=lambda w: w["x0"])
                row_text = [w["text"] for w in row_words 
                            if '0' not in w["text"] 
                            and '1' not in w["text"] 
                            and ':' not in w["text"]
                            and '@' not in w["text"]
                            ]

                for keyword in ['GameDate', 'GameTime', 'Matchup', 'Team', 'PlayerName', 'CurrentStatus', 
                    'AM', 'PM', 'Reason', 'Page', 'NOTYETSUBMITTED', 'Injury', 'Report:']:
                    if keyword in row_text:
                        row_text.remove(keyword)
                
                for i, word in enumerate(row_text):
                    if ',' in word:
                        # print('\n', row_text)
                        p, s, t, l = get_player_injury_data(row_text, i)
                        # print(f'{p} | {s} | {t} | {l}')
                        all_rows.append({
                            "player_name": p,
                            "simplified_status": s,
                            "injury_status": f'{l} {t}',
                            "details": ''
                        })

        df = pd.DataFrame(all_rows)
    return df

if __name__ == '__main__':
    print(get_nbacom_injury_report())