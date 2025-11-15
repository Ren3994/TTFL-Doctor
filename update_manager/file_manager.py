from datetime import datetime, timedelta
from shutil import copy2
import sqlite3
import hashlib
import pickle
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import DB_PATH, CACHE_DIR_PATH, BACKUP_DIR_PATH, SEASON

def cleanup_db():
    with sqlite3.connect(DB_PATH) as conn:
        for table in ['team_games', 'played', 'teammate_played', 'rel_avg_opp_TTFL', 'home_away_rel_TTFL', 'avg_TTFL_per_pos', 'rel_patop', 'absent_teammate_rel_impact', 'games_missed_by_players', 'opp_pos_avg_per_game']:
            drop_table(conn, table)
        conn.execute("""VACUUM;""")

def manage_backups():
    current_date = datetime.today()
    delete_backup_date = current_date - timedelta(days=30)
    current_date_str = current_date.strftime('%d-%m-%Y')
    os.makedirs(BACKUP_DIR_PATH, exist_ok=True)

    existing_backup_dates = []
    for filename in os.listdir(BACKUP_DIR_PATH):
        backup_date = filename[:-3].split('_')[-1]
        backup_date_dt = datetime.strptime(backup_date, '%d-%m-%Y')
        existing_backup_dates.append(backup_date)

        if backup_date_dt < delete_backup_date:
            os.remove(os.path.join(BACKUP_DIR_PATH, filename))

    if current_date_str not in existing_backup_dates:
        new_backup_path = os.path.join(BACKUP_DIR_PATH, f'backup_db_{SEASON}_{current_date_str}.db')
        copy2(DB_PATH, new_backup_path)

def drop_table(conn, table_name: str):
    if not table_name:
        print("No table name provided.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.commit()
    except Exception as e:
        print(f"Error deleting table '{table_name}': {e}")

if __name__ == "__main__":
    # manage_files()
    # cleanup_db()
    manage_backups()