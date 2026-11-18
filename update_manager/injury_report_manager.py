# import os
# import sys

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from fetchers.espn_injury_report_fetcher import get_espn_injury_report
# from fetchers.cbs_injury_report_fetcher import get_cbs_injury_report
from fetchers.nbacom_injury_report_fetcher import get_nbacom_injury_report
from fetchers.espn_json_injury_report_fetcher import get_espn_injury_report_from_json
# # from data.sql_functions import save_to_db
from data.ttfl_data import save_injuries, scan_injuries

def update_injury_report():
    import pandas as pd
    df = pd.DataFrame()
    for fetch in (get_espn_injury_report_from_json,          # primary
                  get_nbacom_injury_report):                  # secondary (fixed, see item C)
        try:
            df = fetch() or pd.DataFrame()
        except Exception as e:
            print(f"injury fetch failed ({fetch.__name__}): {e}")
            df = pd.DataFrame()
        if not df.empty and 'dt_fetch' in df.columns:
            break
        df = pd.DataFrame()

    if df.empty:                                             # total failure: keep the previous file, never crash
        print("injury report: all sources failed, keeping previous data")
        return scan_injuries().select(['dt_fetch', 'source']).collect().row(0)   # last saved fetch time

    save_injuries(df)
    return df.loc[0, ['dt_fetch', 'source']].values

if __name__ == '__main__':
    update_injury_report()