from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.clear_cache_functions import clear_after_db_update, clear_after_injury_update
from data.sql_functions import run_sql_query, update_tables, get_missing_gameids, check_table_exists
from update_manager.injury_report_manager import update_injury_report
from update_manager.nba_api_manager import update_nba_data
from streamlit_interface.streamlit_utils import conn_db

@st.cache_data(show_spinner=False)
def get_cached_upcoming_games():
    upcoming_games = run_sql_query(conn=conn_db(), 
                       table='schedule', 
                       select='gameDateTimeUTC', 
                       filters=['gameStatus != 3', 
                                "gameId LIKE '002%'"])
    return upcoming_games

def need_to_fetch_new_boxscores():
    conn = conn_db()
    df_missing_games = get_missing_gameids(conn)
    if not df_missing_games.empty:
        return True
    
    df_upcoming_games = get_cached_upcoming_games()
    if df_upcoming_games.empty:
        return False
    
    df_upcoming_games['gameDateTimeUTC'] = pd.to_datetime(df_upcoming_games['gameDateTimeUTC'], utc=True)
    df_upcoming_games = df_upcoming_games.sort_values('gameDateTimeUTC')
    next_game_time = df_upcoming_games.at[0, 'gameDateTimeUTC']
    next_game_end = next_game_time + timedelta(hours=3)
    now_utc = datetime.now(UTC)
    return now_utc >= next_game_end

@st.cache_data(ttl=60, show_spinner=False)
def cached_update_injury_report():
    conn=conn_db()
    update_injury_report(conn)
    ij_last_update = datetime.now(ZoneInfo("Europe/Paris"))
    return ij_last_update

def update_all_data(force_update=False):
    conn = conn_db()
    
    default_ts = datetime(2000, 1, 1, tzinfo=ZoneInfo("Europe/Paris"))
    ij_prev_update = st.session_state.get('last_update', default_ts)
    st.session_state.last_update = cached_update_injury_report()

    ij_updated = ij_prev_update != st.session_state.last_update
    need_to_update = need_to_fetch_new_boxscores()
    tables_exist = check_table_exists()

    if need_to_update or force_update:
        update_status = st.empty()
        with update_status.container():
            with st.spinner('Téléchargement des matchs...'):

                update_nba_data(conn=conn)

                get_cached_upcoming_games.clear()
                clear_after_db_update()

        update_status.empty()
    
    if ij_updated or need_to_update or force_update or not tables_exist:

        update_tables(conn)
        clear_after_injury_update()