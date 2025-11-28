import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.JDP_utils import get_cached_pat, get_cached_game_dates_completed, get_cached_scoresTTFL, get_cached_avg_TTFL, get_cached_player_list
from streamlit_interface.classement_TTFL_utils import get_low_game_count, get_deadline, get_joueurs_blesses, cached_get_top_TTFL, apply_df_filters, get_joueurs_pas_dispo
from streamlit_interface.plotting_utils import cached_generate_plot_row
from streamlit_interface.player_stats_utils import get_all_player_stats
from streamlit_interface.top_nuit_utils import get_top_de_la_nuit
from streamlit_interface.team_stats_utils import get_team_stats

def clear_after_db_update():
    get_low_game_count.clear()
    get_deadline.clear()
    cached_generate_plot_row.clear()
    get_top_de_la_nuit.clear()
    get_team_stats.clear()
    get_all_player_stats.clear()
    get_cached_pat.clear()
    get_cached_game_dates_completed.clear()
    get_cached_scoresTTFL.clear()
    get_cached_avg_TTFL.clear()
    get_cached_player_list.clear()

def clear_after_injury_update():
    get_joueurs_blesses.clear()
    cached_get_top_TTFL.clear()
    apply_df_filters.clear()

def clear_after_JDP_update():
    apply_df_filters.clear()
    get_joueurs_pas_dispo.clear()
    get_top_de_la_nuit.clear()
