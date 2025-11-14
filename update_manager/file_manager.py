from datetime import datetime, timedelta
from shutil import copy2
import sqlite3
import hashlib
import pickle
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import DB_PATH, CACHE_DIR_PATH, BACKUP_DIR_PATH, SEASON

def manage_files():
    current_hash = get_db_hash()
    manage_cache(current_hash)
    # manage_backups(current_hash)

def cleanup_db():
    for table in ['team_games', 'played', 'teammate_played', 'rel_avg_opp_TTFL', 'home_away_rel_TTFL', 'avg_TTFL_per_pos', 'rel_patop', 'absent_teammate_rel_impact', 'games_missed_by_players', 'opp_pos_avg_per_game']:
        drop_table(table)
    with sqlite3.connect(DB_PATH) as conn:
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

def manage_cache():
    os.makedirs(CACHE_DIR_PATH, exist_ok=True)
    db_hash = get_db_hash()
    for filename in os.listdir(CACHE_DIR_PATH):
        if db_hash not in filename:
            os.remove(os.path.join(CACHE_DIR_PATH, filename))
    
def get_db_hash() -> str:
    """Compute a hash representing the current state of the tables."""
    m = hashlib.md5()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for table in ["boxscores", "rosters", "injury_report"]: 
            cursor.execute(f"SELECT * FROM {table}")
            for row in cursor.fetchall():
                m.update(str(row).encode())
    return m.hexdigest()

def save_to_cache(df, game_date: str, db_hash: str):
    os.makedirs(CACHE_DIR_PATH, exist_ok=True)
    game_date = game_date.replace("/", "-")
    path = os.path.join(CACHE_DIR_PATH, f"{game_date}_{db_hash}.pkl")
    with open(path, "wb") as f:
        pickle.dump(df, f)

def load_from_cache(game_date: str, db_hash: str):
    game_date = game_date.replace("/", "-")
    path = os.path.join(CACHE_DIR_PATH, f"{game_date}_{db_hash}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

def drop_table(table_name: str, db_path=DB_PATH):
    if not table_name:
        print("No table name provided.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.commit()
    except Exception as e:
        print(f"Error deleting table '{table_name}': {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # manage_files()
    # cleanup_db()
    manage_backups()