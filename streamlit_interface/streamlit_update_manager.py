from datetime import datetime, timedelta, UTC
from filelock import FileLock, Timeout
from zoneinfo import ZoneInfo
import streamlit as st
import polars as pl
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.clear_cache_functions import clear_after_db_update, clear_after_injury_update
from update_manager.injury_report_manager import update_injury_report
from update_manager.nba_api_manager import update_nba_data
from data.ttfl_data import scan_table, get_missing_gameids, latest_season
from misc.misc import DATA_DIR

@st.cache_data(show_spinner=False)
def get_cached_upcoming_games():
    upcoming_games = (scan_table('schedule')
     .filter([
         pl.col('season') == latest_season(),
         pl.col('gameStatus') != 3,
         (pl.col('gameId').str.starts_with('002')) | (pl.col('gameId').str.starts_with('004')) | (pl.col('gameId').str.starts_with('006')),
         pl.col('postponed') == 0
         ])
     .with_columns(gdt_utc_dt=pl.col('gameDateTimeUTC').str.to_datetime(time_zone="UTC"))
     .sort('gdt_utc_dt')
     .select('gdt_utc_dt')
     .limit(1)
     .collect())
    return upcoming_games

@st.cache_data(ttl=30, show_spinner=False)
def need_to_fetch_new_boxscores():
    df_missing_games = get_missing_gameids()
    if not df_missing_games.is_empty():
        return True
    
    df_upcoming_games = get_cached_upcoming_games()
    if df_upcoming_games.is_empty():
        return False
    
    next_game_time = df_upcoming_games.item()
    next_game_end = next_game_time + timedelta(hours=3)
    now_utc = datetime.now(UTC)
    return now_utc >= next_game_end

@st.cache_data(ttl=300, show_spinner=False)
def cached_update_injury_report():
    ij_last_update, source = update_injury_report()
    return ij_last_update, source

def update_all_data(force_update=False):
    try:
        with FileLock(os.path.join(DATA_DIR, ".update.lock"), timeout=1):

            default_ts = datetime(2000, 1, 1, tzinfo=ZoneInfo("Europe/Paris"))
            ij_prev_update = st.session_state.get('last_update', default_ts)
            st.session_state.last_update, st.session_state.last_source = cached_update_injury_report()

            ij_updated = ij_prev_update != st.session_state.last_update
            need_to_update = need_to_fetch_new_boxscores()

            if need_to_update or force_update:
                update_status = st.empty()
                with update_status.container():
                    with st.spinner('Téléchargement des matchs...'):

                        update_nba_data(proxy=st.session_state.nba_api_proxy)

                        get_cached_upcoming_games.clear()
                        clear_after_db_update()

                update_status.empty()

            if ij_updated or need_to_update or force_update:
                clear_after_injury_update()
                
    except Timeout:
        pass

# if __name__ == '__main__':
    # a = run_sql_query(conn=conn_db(), 
    #                    table='schedule', 
    #                    select='gameDateTimeUTC', 
    #                    filters=['gameStatus != 3', 
    #                             "(gameId LIKE '002%' OR gameId LIKE '004%')",
    #                             "postponed = 0"])
    
    # print(a)
    # a = need_to_fetch_new_boxscores()
