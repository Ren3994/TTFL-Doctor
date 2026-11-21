import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.nbacom_injury_report_fetcher import get_nbacom_injury_report
from fetchers.espn_json_injury_report_fetcher import get_espn_injury_report_from_json
from data.ttfl_data import save_injuries, scan_injuries

def update_injury_report():
    import pandas as pd
    df = pd.DataFrame()
    for fetch in (get_espn_injury_report_from_json,
                  get_nbacom_injury_report):
        try:
            result = fetch()
            df = result if result is not None else pd.DataFrame()
        except Exception as e:
            print(f"injury fetch failed ({fetch.__name__}): {e}")
            df = pd.DataFrame()
        if not df.empty and 'dt_fetch' in df.columns:
            break
        df = pd.DataFrame()

    if df.empty:
        print("injury report: all sources failed, keeping previous data")
        try:
            time, source = scan_injuries().select(['dt_fetch', 'source']).collect().row(0)
            return time, source
        except FileNotFoundError:
            return None, "indisponible"

    save_injuries(df)
    return df.loc[0, ['dt_fetch', 'source']].values

if __name__ == '__main__':
    update_injury_report()