import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.player_stats_utils import get_all_player_stats
from streamlit_interface.streamlit_utils import config, custom_CSS
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'stats_joueurs'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Statistiques des joueurs</div>', unsafe_allow_html=True)

st.subheader('Work in progress...')

# --- Example: your avg_player_stats DataFrame ---
df = get_all_player_stats().copy()

# --- Checkbox to switch between raw stats and per36 ---
use_per36 = st.checkbox("Show per-36 stats", value=False)

# --- Define columns for raw vs per36 stats ---
raw_stats = [
    'TTFL', 'ttfl_per_min', 'points', 'assists', 'reboundsTotal', 'turnovers', 'steals', 'blocks', 'stocks',
    'fieldGoalsMade', 'fieldGoalsAttempted', 'threePointersMade', 'threePointersAttempted',
    'freeThrowsMade', 'freeThrowsAttempted', 'fg_pct', 'three_pct', 'ft_pct',
    'plusMinusPoints', 'EFG', 'TS', 'ast_to_tov', 'reboundsOffensive', 'reboundsDefensive'
]

per36_stats = [
    'pts_per36', 'ast_per36', 'reb_per36', 'tov_per36', 'stl_per36', 'stocks_per36', 'ttfl_per_36'
]

default_stats = raw_stats if not use_per36 else per36_stats

# --- Multiselect for columns to display ---
selected_stats = st.multiselect(
    "Select stats to display",
    options=default_stats,
    default=default_stats[:10]  # show first 8 by default
)

# Always include identifying columns
columns_to_show = ['playerName', 'teamTricode', 'n_games'] + selected_stats
df_filtered = df[columns_to_show]

# --- Optional search box for player name ---
search_name = st.text_input("Search player", placeholder='Rechercher joueur', label_visibility='collapsed')
if search_name:
    df_filtered = df_filtered[df_filtered['playerName'].str.contains(search_name, case=False)]

# --- Data editor configuration ---
column_config = {col: st.column_config.NumberColumn(col, format="%.2f") 
                 for col in df_filtered.select_dtypes(include='number').columns}

# Keep text columns as default
for col in df_filtered.select_dtypes(include='object').columns:
    column_config[col] = st.column_config.TextColumn(col)

# --- Display interactive table ---
st.data_editor(
    df_filtered,
    column_config=column_config,
    hide_index=True,
)