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
    
    col_spacer1, col_progress, col_spacer2 = st.columns([2, 3, 1])
    with col_progress:
        progress_bar = st.progress(value=0, width=300)
        progress_text = st.empty()

    games_per_row = 3
    infoholders = [None] * len(games_info)
    buttonholders = [None] * len(games_info)
    for i in range(0, len(games_info), games_per_row):
        cols = st.columns(games_per_row)
        for j in range(games_per_row):
            idx = i + j
            if idx >= len(games_info):
                continue

            with cols[j]:
                infoholders[idx] = st.empty()
                buttonholders[idx] = st.empty()

    tableholders = [st.empty() for _ in games_info]
    for idx, game in enumerate(games_info):
        st.session_state.setdefault(f"boxscore_{idx}", False)

        home = game["homeTeam"]
        away = game["awayTeam"]
        scores = [game["awayScore"], game["homeScore"]]
        logos = [
            st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, f"{team}.png"), width=40)
            for team in [away, home]
        ]

        infoholders[idx].markdown(
            f"""
            <div style='display:flex;justify-content:center;align-items:center;gap:1rem;margin:1rem 0;'>
                <div>{logos[0]}</div>
                <div style='font-size:16px;font-weight:bold;'>
                    {away} {scores[0]} - {scores[1]} {home}
                </div>
                <div>{logos[1]}</div>
                <div>{game["time"]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        btn_text = (
            f"Montrer boxscore de {away} - {home}"
            if not st.session_state[f"boxscore_{idx}"]
            else f"Cacher boxscore de {away} - {home}"
        )

        buttonholders[idx].button(
            btn_text,
            key=f"btn_{idx}",
            on_click=lambda k=idx: st.session_state.update(
                {f"boxscore_{k}": not st.session_state[f"boxscore_{k}"]})
        )

    for idx in range(len(games_info)):
        if st.session_state[f"boxscore_{idx}"]:
            html_df = df_to_html(live_games[idx], show_cols=['Joueur', 'Equipe', 'Min', 'TTFL', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb', 'Blk', 'Stl', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'PF'],
                                            show_index=False,
                                            tooltips={},
                                            col_header_labels={'Equipe' : 'Équipe'}, 
                                            col_header_tooltips=[],
                                            image_tooltips=[],
                                            color_tooltip_pct=False)
            tableholders[idx].markdown(html_df, unsafe_allow_html=True)
        else:
            tableholders[idx].empty()
    
    refresh_rate = 30
    total_steps = int(remaining * refresh_rate)
    for i in range(total_steps, -1, -1):
        pct = (total_steps - i) / total_steps
        progress_bar.progress(value=pct, width=300)
        seconds_remaining = i / refresh_rate
        progress_text.text(f"MàJ dans {seconds_remaining:.0f}s")
        time.sleep(1 / refresh_rate)
        
    st.rerun()