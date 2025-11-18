from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.plotting_utils import cached_generate_plot_row
from update_manager.injury_report_manager import update_injury_report
from data.sql_functions import run_sql_query, update_tables
from update_manager.nba_api_manager import update_nba_data
from streamlit_interface.streamlit_utils import conn_db
from streamlit_interface.classement_TTFL_utils import *

def need_to_fetch_new_boxscores():
    conn = conn_db()
    df = run_sql_query(conn, 
                       table='schedule', 
                       select='gameDateTimeUTC', 
                       filters=['gameStatus != 3', 
                                "gameId LIKE '002%'"])
    if df.empty:
        return False
    df['gameDateTimeUTC'] = pd.to_datetime(df['gameDateTimeUTC'], utc=True)
    df = df.sort_values('gameDateTimeUTC')
    next_game_time = df.at[0, 'gameDateTimeUTC']
    next_game_end = next_game_time + timedelta(hours=3)
    now_utc = datetime.now(UTC)
    return now_utc >= next_game_end

@st.cache_data(ttl=60, show_spinner=False)
def cached_update_injury_report():
    conn=conn_db()
    update_injury_report(conn)
    ij_last_update = datetime.now(ZoneInfo("Europe/Paris"))
    return ij_last_update

def update_all_data():
    conn = conn_db()
    
    default_ts = datetime(2000, 1, 1, tzinfo=ZoneInfo("Europe/Paris"))
    ij_prev_update = st.session_state.get('last_update', default_ts)
    st.session_state.last_update = cached_update_injury_report()

    ij_updated = ij_prev_update != st.session_state.last_update
    need_to_update = need_to_fetch_new_boxscores()

    if need_to_update:
        update_status = st.empty()
        with update_status.container():
            with st.spinner('Téléchargement des matchs...'):
                update_nba_data(conn=conn)
                get_low_game_count.clear()
                get_deadline.clear()
                cached_generate_plot_row.clear()
        update_status.empty()
    
    if ij_updated or need_to_update:
        update_tables(conn)
        get_joueurs_blesses.clear()
        cached_get_top_TTFL.clear()
        apply_df_filters.clear()