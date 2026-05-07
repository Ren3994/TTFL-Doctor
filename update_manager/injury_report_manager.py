import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.espn_injury_report_fetcher import get_espn_injury_report
from fetchers.cbs_injury_report_fetcher import get_cbs_injury_report
from data.sql_functions import save_to_db

def update_injury_report(conn):
    import pandas as pd

    injury_report_df = get_cbs_injury_report()
    if injury_report_df.empty:
        injury_report_df = pd.DataFrame(columns=['player_name', 'simplified_status', 'injury_status', 'details'])
    if injury_report_df is not None:
        save_to_db(conn, injury_report_df, 'injury_report', if_exists = 'replace')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_injury_report_player ON injury_report(player_name);")