from datetime import datetime
from zoneinfo import ZoneInfo
from tqdm import tqdm
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.net_utils import http_json, InvalidResultError, WEB
from fetchers.helpers import normalize_name

URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
COLS = ['player_name', 'simplified_status', 'injury_status', 'details', 'dt_fetch', 'source']
MAX_ATTEMPTS = 3

OUT_PHRASES = [
    "will not suit up",
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
    "won't be available",
]


def _fmt_date(value):
    """Format an ISO date as dd/mm, or '??' if missing."""
    return pd.to_datetime(value).strftime('%d/%m') if value else '??'


def _simplify_status(status, comment_lower):
    """Refine ESPN's generic 'Day-To-Day' status using the short comment."""
    if status.lower() != "day-to-day":
        return status
    if any(phrase in comment_lower for phrase in OUT_PHRASES):
        return "Out"
    if "questionable" in comment_lower:
        return "Questionable"
    if "probable" in comment_lower:
        return "Probable"
    return status


def _parse_injuries(data, dt_fetch):
    rows = []
    for team in data.get('injuries') or []:
        for player in team.get('injuries') or []:
            short_comment = player.get('shortComment') or ''
            simplified = _simplify_status(player.get('status') or '', short_comment.lower())

            update_date_fmt = _fmt_date(player.get('date'))
            est_return_fmt = _fmt_date((player.get('details') or {}).get('returnDate'))

            rows.append({
                "player_name": (player.get('athlete') or {}).get('displayName'),
                "simplified_status": simplified,
                "injury_status": f'{update_date_fmt}: {simplified} (retour est. : {est_return_fmt})',
                "details": short_comment,
                "dt_fetch": dt_fetch,
                "source": 'ESPN'
            })

    df = pd.DataFrame(rows, columns=COLS)
    df['player_name'] = df['player_name'].apply(normalize_name)
    return df


def _check_espn(data):
    if not isinstance(data, dict) or data.get('status') != 'success':
        status = data.get('status') if isinstance(data, dict) else type(data).__name__
        raise InvalidResultError(f"Statut inattendu : {status}")   # retried, with this message
    return True


def get_espn_injury_report_from_json():
    dt_fetch = datetime.now(ZoneInfo("Europe/Paris"))

    data = http_json(
        URL, timeout=10, label="injury report (ESPN JSON)",
        policy=WEB.replace(max_attempts=MAX_ATTEMPTS, wait_base=3),
        validate=_check_espn)

    if data is None:                                   # all attempts failed
        return pd.DataFrame(columns=COLS)

    try:                                               # parsing is not a network error:
        return _parse_injuries(data, dt_fetch)         # one try, degrade gracefully
    except Exception as e:                             # noqa: BLE001
        tqdm.write(f"Injury report (ESPN JSON) : parsing impossible : {type(e).__name__}: {e}")
        return pd.DataFrame(columns=COLS)


if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    from data.ttfl_data import save_injuries, scan_injuries

    # a, b = (scan_injuries().select(['dt_fetch', 'source']).collect().row(0))
    # print(b)

    df = get_espn_injury_report_from_json()
    print(df)
    if not df.empty:
        print(df['dt_fetch'].iloc[0])
        save_injuries(df)
    # print(df[df['player_name'] == 'Walker Kessler'])