import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.JDP_utils import get_cached_rosters, get_cached_game_dates_completed, get_cached_scoresTTFL, get_cached_avg_TTFL, get_cached_player_list, get_cached_all_game_dates, get_cached_alltime_player_list, get_cached_future_dates
from streamlit_interface.classement_TTFL_utils import get_low_game_count, get_deadline, get_joueurs_blesses, cached_get_top_TTFL, apply_df_filters, update_session_state_df
from streamlit_interface.player_stats_utils import cached_player_stats, cached_player_v_team, cached_historique_des_perfs, cached_player_stats_by_season, cached_maximums
from streamlit_interface.team_stats_utils import cached_query_team_stats, get_cached_opp_team_stats, standings_progress_plot
from streamlit_interface.plotting_utils import _compute_spec, tooltip_assets
from streamlit_interface.top_nuit_utils import get_top_de_la_nuit

def clear_after_db_update():
    cached_get_top_TTFL.clear()
    get_low_game_count.clear()
    get_deadline.clear()
    get_top_de_la_nuit.clear()
    cached_query_team_stats.clear()
    get_cached_opp_team_stats.clear()
    cached_player_stats.clear()
    get_cached_game_dates_completed.clear()
    get_cached_scoresTTFL.clear()
    get_cached_avg_TTFL.clear()
    get_cached_player_list.clear()
    get_cached_rosters.clear()
    cached_player_v_team.clear()
    cached_historique_des_perfs.clear()
    cached_player_stats_by_season.clear()
    st.session_state.calculated = set()
    from streamlit_interface.streamlit_update_manager import need_to_fetch_new_boxscores
    need_to_fetch_new_boxscores.clear()
    cached_maximums.clear()
    get_cached_all_game_dates.clear()
    get_cached_alltime_player_list.clear()
    standings_progress_plot.clear()
    tooltip_assets.clear()
    _compute_spec.clear()
    get_cached_future_dates.clear()

def clear_after_injury_update():
    get_joueurs_blesses.clear()
    cached_get_top_TTFL.clear()
    if st.session_state.get('date_text_ymd'):
        update_session_state_df(st.session_state.date_text_ymd)

def clear_after_JDP_update():
    get_top_de_la_nuit.clear()
    cached_get_top_TTFL.clear()
