from collections import Counter
from tqdm import tqdm
import pandas as pd
import unicodedata
import sqlite3
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import DB_PATH, CHAR_MAP

def load_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def reformat_boxscores_dates(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    
    # Read the boxscores table
    df = pd.read_sql_query("SELECT * FROM boxscores", conn)
    
    # Convert gameDate to datetime, then to desired format
    df['gameDate'] = pd.to_datetime(df['gameDate']).dt.strftime('%d/%m/%Y')
    
    # Overwrite the table with reformatted dates
    df.to_sql('boxscores', conn, if_exists='replace', index=False)
    
    print("gameDate column reformatted to %d/%m/%Y.")
    conn.close()

def drop_table(table_name: str, db_path=DB_PATH, verbose=True):
    """
    Deletes the specified table from the database.
    """
    if not table_name:
        print("No table name provided.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.commit()
        if verbose:
            print(f"Table '{table_name}' has been deleted.")
    except Exception as e:
        print(f"Error deleting table '{table_name}': {e}")
    finally:
        conn.close()

def list_unique_characters_from_table(table):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT DISTINCT playerName FROM {table}")
    names = [row[0] for row in cursor.fetchall() if row[0]]

    conn.close()

    # Combine all characters
    all_chars = "".join(names)
    unique_chars = sorted(set(all_chars))

    # Count frequency (optional but helpful)
    char_counts = Counter(all_chars)

    print("=== Unique Characters in playerName ===")
    print("".join(unique_chars))
    print("\n=== Detailed counts ===")
    for ch, count in sorted(char_counts.items(), key=lambda x: -x[1]):
        codepoint = f"U+{ord(ch):04X}"
        print(f"{repr(ch):6} {count:5} {codepoint}")

def normalize_name(name: str) -> str:
    """
    Normalize player names:
    - Replace special characters via CHAR_MAP
    - Remove accents using Unicode normalization
    - Strip double spaces, trim, etc.
    """
    if not name:
        return name

    # Step 1: Apply manual mapping
    for src, target in CHAR_MAP.items():
        name = name.replace(src, target)

    # Step 2: Remove diacritics (accents)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(ch for ch in name if unicodedata.category(ch) != 'Mn')

    # Step 3: Cleanup
    name = " ".join(name.split())  # collapse multiple spaces
    return name.strip()

def normalize_boxscores_playernames(tablename):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT DISTINCT playerName FROM {tablename}")
    names = [row[0] for row in cursor.fetchall() if row[0]]

    # tqdm.write(f"Found {len(names)} unique player names")

    weird_names = []
    updates = []
    for name in names:
        clean = normalize_name(name)
        if clean != name:
            updates.append((clean, name))
            weird_names.append((clean, name))

    # tqdm.write(f"{len(updates)} names will be updated")

    for new_name, old_name in tqdm(updates, desc="Updating names"):
        cursor.execute(f"UPDATE {tablename} SET playerName = ? WHERE playerName = ?", (new_name, old_name))

    conn.commit()
    conn.close()
    tqdm.write("Player names normalized successfully.")

def show_db_structure(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Tables in database ({len(tables)}): {tables}\n")

    for table in tables:
        print(f"Table: {table}")

        # Get column info
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        
        for col in columns:
            # Show one example value from the column
            cursor.execute(f"SELECT {col[1]} FROM {table} LIMIT 1")
            value = cursor.fetchone()
            value_display = value[0] if value else None
            print(f"  - {col[1]} ({col[2]}) | {value_display}")

        # Count rows
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total_rows = cursor.fetchone()[0]
        print(f"  Total rows: {total_rows}")

        # Special case for boxscores: unique gameId count
        if table == 'boxscores':
            cursor.execute("SELECT COUNT(DISTINCT gameId) FROM boxscores")
            unique_gameIds = cursor.fetchone()[0]
            print(f"  Unique gameIds: {unique_gameIds}")

        print("")

    conn.close()

if __name__ == "__main__":

    # normalize_boxscores_playernames('rosters')

    # list_unique_characters_from_table("rosters")

    # reformat_boxscores_dates()

    # drop_table('cross_ir_ati')
    # drop_table('joueurs_deja_pick')
    # drop_table('player_positions')
    # drop_table('avgTTFL_by_playerName')

    show_db_structure()


    df = load_table('joueurs_deja_pick')
    # print(df[df['playing_teammate'] == 'Chet Holmgren'])#[df['playing_teammate'] == 'Shai Gilgeous-Alexander'])
    # print(df[df['injured_player'] == 'Giannis Antetokounmpo'].iloc[0])#.sort_values(by="injured_player_avg_TTFL", ascending=False))
    # .sort_values(by="isHome"))
    print(df)
    # print(df[df['teamTricode'] == 'HOU'])
