import os
import sys
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.injury_report_fetcher import get_injury_report
from data.sql_functions import save_to_db
from misc.misc import DB_PATH

def update_injury_report():

    conn = sqlite3.connect(DB_PATH)

    injury_report_df = get_injury_report()

    if injury_report_df is not None:
        save_to_db(conn, injury_report_df, 'injury_report', if_exists = 'replace')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_injury_report_player ON injury_report(player_name);")