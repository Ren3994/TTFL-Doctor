from datetime import datetime
import streamlit as st
from tqdm import tqdm
import pandas as pd
import sqlite3
import random
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.sql_functions import init_db, save_to_db, get_missing_gameids
from update_manager.boxscores_manager import get_boxscores, log_failure
from misc.misc import DB_PATH

def update_nba_data(update_attempt=1, max_update_attempts=3, init_database=True, progress=None, status=None):

    conn = sqlite3.connect(DB_PATH)
    new_games_found = True

    if init_database:
        progress = init_db(conn, progress)

    missing_gameIds_df = get_missing_gameids(conn)
    if missing_gameIds_df.empty :
        tqdm.write('Aucun nouveau match.')
        new_games_found = False
        progress.progress(80/100)
        return new_games_found
    
    # tqdm.write(f"{len(missing_gameIds_df)} matchs manquants.")
    missing_gameIds_list = missing_gameIds_df.to_dict(orient="records")
    if len(missing_gameIds_df) < 5:
        lower_bound, upper_bound = 0.2, 0.5
    if len(missing_gameIds_df) < 15:
        lower_bound, upper_bound = 0.6, 1
    elif len(missing_gameIds_df) > 100:
        lower_bound, upper_bound = 3, 5
    else:
        lower_bound, upper_bound = 1.5, 2.5
    new_boxscores = []
    
    total = len(missing_gameIds_list)
    # progress_bar = st.progress(0)
    # status = st.empty()

    # for game_info in tqdm(missing_gameIds_list, desc = 'Téléchargement des matchs manquants...', ncols = 100) :
    for i, game_info in enumerate(missing_gameIds_list):
        game_id = game_info['gameId']
        game_date = datetime.strptime(game_info['gameDate'], '%d/%m/%Y')
        visitor_team = game_info['awayTeam']
        home_team = game_info['homeTeam']
        status.text(f"Injury report : ✅\nDonnées NBA : match {i+1}/{total} ({home_team} - {visitor_team})\nTables de calculs :")

        for attempt in range(5):  # Retry up to 5 times
            try:
                boxscore = get_boxscores(game_date, game_id, visitor_team, home_team)
                if not boxscore.empty and game_id in boxscore['gameId'].values:
                    new_boxscores.extend(boxscore.to_dict(orient="records"))
                    time.sleep(random.uniform(lower_bound, upper_bound))
                    progress.progress((30 + 50*((i + 1) / total))/100)
                break  # Exit the retry loop if successful

            except Exception as e:
                tqdm.write(f"Erreur lors du téléchargement du match avec id {game_id}: {e}")
                time.sleep(30 * (attempt + 1))
                if attempt == 4:  # 5th failure
                    log_failure(game_date, game_id, str(e))
                    continue

        if new_boxscores:
            save_to_db(conn, pd.DataFrame(new_boxscores), "boxscores", if_exists="append", index=False)
            new_boxscores.clear()
    
    final_missing_gameIds_df = get_missing_gameids(conn)

    if not final_missing_gameIds_df.empty and update_attempt < max_update_attempts:
        tqdm.write(f'Retry {update_attempt + 1}/{max_update_attempts} for {len(final_missing_gameIds_df)} missing games...')
        time.sleep(10)
        conn.close()
        update_nba_data(update_attempt + 1, init_database=False)
        return new_games_found
        
    elif not final_missing_gameIds_df.empty:
        tqdm.write(f'Still missing {len(final_missing_gameIds_df)} but they could not be fetched.')

    conn.execute("CREATE INDEX IF NOT EXISTS idx_boxscores_game_player ON boxscores(gameId, playerName);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_boxscores_opponent_player ON boxscores(opponent, playerName);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_boxscores_team_game ON boxscores(teamTricode, gameId);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_boxscores_team_game ON boxscores(teamTricode, opponentTTFL);")
    conn.close()

    return new_games_found