import streamlit as st
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from misc.misc import RESIZED_LOGOS_PATH, IMG_CHARGEMENT, IMG_PLUS_DE_GRAPHES
from streamlit_interface.streamlit_utils import config, conn_db
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.live_scores_utils import get_live_games
from streamlit_interface.classement_TTFL_utils import *
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'live_scores'
games_info, live_games, timestamp = get_live_games()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)
conn = conn_db()

if 'live_scores_update_timestamp' not in st.session_state:
    st.session_state.live_scores_update_timestamp = timestamp
else:
    if st.session_state.live_scores_update_timestamp != timestamp:
        st.session_state.live_scores_update_timestamp = timestamp

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Scores TTFL en direct</div>', unsafe_allow_html=True)

if len(live_games) == 0:
    st.subheader('Aucun match en cours.')
else:
    elapsed = time.time() - st.session_state.live_scores_update_timestamp
    remaining = max(0, 15 - int(elapsed))

    progress_bar = st.progress(value=0, width=300)
    progress_text = st.empty()
    for game_info, live_game in zip(games_info, live_games):
        homeTeam = game_info['homeTeam']
        awayTeam = game_info['awayTeam']
        teams = [awayTeam, homeTeam]
        logos = [st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, f"{team}.png"), width=50) for team in teams]
        scores = [game_info['awayScore'], game_info['homeScore']]
        st.markdown(f"<div style='display:flex;justify-content:center;align-items:center;gap:1rem;margin-bottom:2rem;margin-top:2rem;'><div>{logos[0]}</div><div style='font-size:20px;text-align:center;font-weight:bold;'>{teams[0]} {scores[0]} - {scores[1]} {teams[1]} </div><div>{logos[1]} </div>{game_info['time']}</div>", unsafe_allow_html=True)
        html_df = df_to_html(live_game, show_cols=['Joueur', 'Equipe', 'Min', 'TTFL', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb', 'Blk', 'Stl', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'PF'],
                            show_index=False,
                            tooltips={},
                            col_header_labels={'Equipe' : 'Équipe'}, 
                            col_header_tooltips=[],
                            image_tooltips=[],
                            color_tooltip_pct=False)
        st.markdown(html_df, unsafe_allow_html=True)

for i in range(int(remaining), -1, -1):
    pct = (15 - i) / 15
    progress_bar.progress(value=pct, width=300)
    progress_text.text(f"MàJ dans {i} secondes")
    time.sleep(1)

st.rerun()