from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from tqdm import tqdm
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.connection_manager import check_internet_connection
from update_manager.injury_report_manager import update_injury_report
from update_manager.nba_api_manager import update_nba_data
from update_manager.topTTFL_manager import get_top_TTFL
from update_manager.file_manager import manage_files
from streamlit_interface.streamlit_utils import launch_GUI
from data.sql_functions import update_tables

def run_TTFL_Doctor():

    if not check_internet_connection():
        tqdm.write('Pas de connection internet')
        return

    # --- Téléchargement des nouveaux matchs, mise à jour des rosters, et téléchargement du injury report
    tqdm.write('Mise à jour des données...')
    with ThreadPoolExecutor(max_workers=2) as executor:
        nba_api_future = executor.submit(update_nba_data)
        espn_future = executor.submit(update_injury_report)
        new_games_found = nba_api_future.result()
        espn_future.result()
    
    # --- Mise à jour des tables SQL
    update_tables()

    # # --- Nettoyage des vieux fichiers cache et mise à jour des backups
    manage_files()
            
    # --- Construction du df pour un ou plusieurs jours
    date_dt = datetime.now()
    days2calc = 1
    for _ in tqdm(range(days2calc), desc=f'Création des classements pour {days2calc} jours...'):
        date = datetime.strftime(date_dt, '%d/%m/%Y')
        get_top_TTFL(date, preload=True)
        date_dt += timedelta(days=1)

    # --- Lance le GUI Streamlit
    launch_GUI()
    
if __name__ == "__main__":
    run_TTFL_Doctor()