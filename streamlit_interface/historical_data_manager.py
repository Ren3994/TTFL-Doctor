import sys
import os
import requests
import time
import zstandard as zstd
import hashlib
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.resource_manager import conn_hist_db, conn_db
from data.sql_functions import update_tables, run_sql_query, save_to_db
from misc.misc import DB_PATH_HISTORICAL, DB_PATH_HISTORICAL_ZST, HIST_DB_URL, CHECKSUM

def checksum():
    h = hashlib.sha256()
    with open(DB_PATH_HISTORICAL_ZST, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download_hist_db(status, progress):
    with st.spinner('Téléchargement des boxscores historiques...'):
        with requests.get(HIST_DB_URL, stream=True, timeout=(10, 300)) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            with open(DB_PATH_HISTORICAL_ZST, "wb") as f:
                for chunk in r.iter_content(1024*1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        progress.progress(min((downloaded / total) / 10, 0.1))
                        status.text(f"Téléchargement... {downloaded / total:.0%}")

def init_hist_db():
    
    os.makedirs(os.path.dirname(DB_PATH_HISTORICAL_ZST), exist_ok=True)
    
    if not os.path.exists(DB_PATH_HISTORICAL_ZST): # Télécharger si manquant
        status = st.empty()
        progress = st.progress(0)
        download_hist_db(status, progress)

    new_file_hash = checksum() # Vérifier la validité du fichier
    if new_file_hash != CHECKSUM:
        os.remove(DB_PATH_HISTORICAL_ZST)
        print('Wrong hash')
        return False

    if not os.path.exists(DB_PATH_HISTORICAL): # Décompression de l'archive
        with open(DB_PATH_HISTORICAL_ZST, "rb") as f:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(f) as reader:
                with open(f'{DB_PATH_HISTORICAL_ZST}.tmp', "wb") as out:
                    while True:
                        chunk = reader.read(16384)
                        if not chunk:
                            break
                        out.write(chunk)

        os.replace(f'{DB_PATH_HISTORICAL_ZST}.tmp', DB_PATH_HISTORICAL)
    
    update_total_boxscores(status, progress)
    if status:
        status.empty()
        progress.empty()
    return True

def update_total_boxscores(status, progress):
    
    conn = conn_db()
    hist_conn = conn_hist_db()

    boxscore_cols = '''
        season, gameId, teamTricode, isHome, opponent, playerName, minutes, points, assists, TTFL, win, 
        reboundsTotal, steals, blocks, turnovers, fieldGoalsMade, fieldGoalsAttempted, threePointersMade, 
        threePointersAttempted, freeThrowsMade, freeThrowsAttempted, plusMinusPoints, homeTeam, visitorTeam, 
        seconds, reboundsOffensive, position_boxscores, reboundsDefensive, gameDate, gameDate_ymd, prev_gameDate_ymd, 
        teamPoints, opponentPoints, teamTTFL, opponentTTFL
        '''

    table_exists = hist_conn.execute("""SELECT 1
                                        FROM sqlite_master
                                        WHERE type='table'
                                        AND name='boxscores'
                                     """).fetchone()

    if not table_exists:
        hist_conn.execute(f'''CREATE TABLE boxscores AS
                              SELECT {boxscore_cols}
                              FROM historical_boxscores''')
        
        progress.progress(0.5)
        hist_conn.execute("CREATE UNIQUE INDEX idx_unique ON boxscores(playerName, gameId)")
        progress.progress(0.6)
        hist_conn.execute("CREATE INDEX idx_seconds ON boxscores(seconds)")
        progress.progress(0.65)
        hist_conn.execute("CREATE INDEX idx_gameDate_ymd ON boxscores(gameDate_ymd)")
        progress.progress(0.7)
    
    query_last_gameDate = """SELECT gameDate_ymd FROM boxscores ORDER BY gameDate_ymd DESC LIMIT 1"""
    last_gameDate_current_boxscores = conn.execute(query_last_gameDate).fetchone()[0]
    last_gameDate_total_boxscores = hist_conn.execute(query_last_gameDate).fetchone()[0]

    up_to_date = last_gameDate_current_boxscores == last_gameDate_total_boxscores
    if not up_to_date:

        current_boxscores = run_sql_query(conn, 'boxscores')
        save_to_db(hist_conn, current_boxscores, 'current_boxscores', if_exists='replace')
        progress.progress(0.8)
        hist_conn.execute(f'''INSERT OR IGNORE INTO boxscores ({boxscore_cols})
                            SELECT {boxscore_cols}
                            FROM current_boxscores''')
        progress.progress(0.9)

        hist_conn.commit()
        progress.progress(1)
    
if __name__ == '__main__':
    # init_historical_stats()
    # t0 = time.time()
    update_total_boxscores(0, 0)
    # print(time.time() - t0)
    # hist_conn = conn_hist_db()
    # update_tables(hist_conn, historical=True)
    # print(time.time() - t0)

    # hist_conn.execute("""VACUUM;""")
    # hist_conn.execute("""ANALYZE;""")

    # hist_conn.execute("""
    # CREATE UNIQUE INDEX idx_unique_player_date_season ON boxscores(playerName, gameDate_ymd, season)
    # """)
    # hist_conn.commit()

    # a = hist_conn.execute("""
    # SELECT name, sql
    # FROM sqlite_master
    # WHERE type='index' AND tbl_name='boxscores'
    # """).fetchall()

    # print(os.path.dirname(DB_PATH_HISTORICAL_ZST))

    # init_hist_db()

    # import zstandard as zstd
    # with open(DB_PATH_HISTORICAL_ZST, 'rb') as f:
    #     dctx = zstd.ZstdDecompressor()
    #     with open(DB_PATH_HISTORICAL, 'wb') as out:
    #         dctx.copy_stream(f, out)

    # checksum()

    