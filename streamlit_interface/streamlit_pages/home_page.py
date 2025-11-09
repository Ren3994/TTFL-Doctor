from datetime import datetime, timedelta
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.injury_report_manager import update_injury_report
from streamlit_interface.plotting_utils import add_plots_to_rest
from update_manager.nba_api_manager import update_nba_data
from update_manager.topTTFL_manager import get_top_TTFL, get_db_hash, save_to_cache
from data.sql_functions import update_tables

TITLE = 'Menu principal'
ORDER = 1

def run():
    st.title('Menu principal')
    if not st.session_state.data_ready:
        with st.status("Mise à jour des données en cours...", expanded=True) as status:
            
            st.write('Mise à jour du injury report...')
            update_injury_report()
            st.write("Injury report à jour ✅")
            
            st.write('Mise à jour des données NBA...')
            update_nba_data()
            st.write("Données NBA à jour ✅")

            update_tables()

            #### FIX THE BUG WHERE DATA CAN BE WRITTEN MULTIPLE TIMES IN BOXSCORES

            # status.update(label="Mise à jour des données réussie ✅", state="complete")
            st.session_state.data_ready = True
            st.rerun()
    
    if st.session_state.data_ready:
        st.success("Toutes les données sont à jour ✅")

        if st.button('Mettre à jour les données'):
            st.session_state.data_ready = False
            st.rerun()
        
        if st.button('Calculer les classements pour 7 jours'):
            st.session_state.data_ready = False
            status_classement = st.empty()
            progress_bar_classement = st.progress(0)
            date_dt = datetime.now()
            days2calc = 7
            for i in range(days2calc):
                date = datetime.strftime(date_dt, '%d/%m/%Y')
                status_classement.text(f"{i+1}/7 : {date}")
                topTTFL_df, _ = get_top_TTFL(date)
                topTTFL_df_with_plots = add_plots_to_rest(topTTFL_df, date, 0)
                db_hash = get_db_hash()
                save_to_cache(topTTFL_df_with_plots, date, db_hash)
                progress_bar_classement.progress((i + 1) / 7)
                date_dt += timedelta(days=1)
            st.success("Classements calculés ✅")
            st.session_state.data_ready = True
            st.rerun()