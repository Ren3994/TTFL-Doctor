from datetime import datetime
from shutil import copy2
from tqdm import tqdm
import sqlite3
import hashlib
import pickle
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import DB_PATH, CACHE_DIR_PATH, BACKUP_DIR_PATH, SEASON

def manage_files():
    current_hash = get_db_hash()
    current_date = datetime.today().date()
    manage_cache(current_hash, current_date)
    manage_backups(current_hash)

def cleanup_db():
    for table in ['team_games', 'played', 'teammate_played', 'player_avg_TTFL', 'rel_avg_opp_TTFL', 'home_away_rel_TTFL', 'avg_TTFL_per_pos', 'rel_patop', 'absent_teammate_rel_impact', 'games_missed_by_players', 'opp_pos_avg_per_game', 'injury_report']:
            drop_table(table)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""VACUUM;""")

def manage_backups(db_hash):
    os.makedirs(BACKUP_DIR_PATH, exist_ok=True)
    for filename in os.listdir(BACKUP_DIR_PATH):
        if SEASON in filename and db_hash not in filename:
            old_backup_path = os.path.join(BACKUP_DIR_PATH, filename)
            os.remove(old_backup_path)
            new_db_path = os.path.join(BACKUP_DIR_PATH, f'backup_db_{SEASON}_{db_hash}.db')
            copy2(DB_PATH, new_db_path)

def manage_cache(db_hash, date):
    os.makedirs(CACHE_DIR_PATH, exist_ok=True)
    for filename in os.listdir(CACHE_DIR_PATH):
        if db_hash not in filename:
            os.remove(os.path.join(CACHE_DIR_PATH, filename))
            continue
        
        file_date = filename.split('_')[0]
        file_date_dt = datetime.strptime(file_date, '%d-%m-%Y').date()
        if file_date_dt < date:
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
    cleanup_db()