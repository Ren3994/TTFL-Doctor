from streamlit_extras.add_vertical_space  import add_vertical_space as vspace
from streamlit_extras.stylable_container import stylable_container as sc
import streamlit as st
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import config, st_image_crisp, custom_CSS, custom_mobile_CSS
from streamlit_interface.classement_TTFL_utils import df_to_html
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.live_scores_utils import get_live_games
from streamlit_interface.sidebar import sidebar
from misc.misc import RESIZED_LOGOS_PATH

# ---------- Initialize session state ----------
PAGENAME = 'live_scores'
REFRESH_RATE, TTL = 30, 15
games_info, live_games, timestamp = get_live_games()
init_session_state(page=PAGENAME, arg=timestamp)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Scores TTFL en direct</div>', unsafe_allow_html=True)

if len(live_games) == 0:
    st.subheader('Aucun match en cours.')
else:
    elapsed = time.time() - st.session_state.live_scores_update_timestamp
    real_start_pct = min(1, elapsed / TTL)
    start_pct = max(real_start_pct, st.session_state.progress_pct)

    mobile = st.session_state.get("mobile_layout", False)
    if mobile != st.session_state.get("mobile_layout", False):
        st.session_state.mobile_layout = mobile
        st.rerun()
    if mobile:
        st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
        col_progress = st.columns([1])[0]
        games_per_row = 1
    else:
        col_spacer1, col_progress, col_spacer2 = st.columns([2, 3, 1])
        games_per_row = 3
    with col_progress:
        progress_bar = st.progress(value=start_pct, width=300)
        progress_text = st.empty()

    buttonholders = [None] * len(games_info)
    for i in range(0, len(games_info), games_per_row):
        cols = st.columns(games_per_row)
        vspace()
        for j in range(games_per_row):
            idx = i + j
            if idx >= len(games_info):
                break

            with cols[j]:
                buttonholders[idx] = st.empty()

    tableholders = [st.empty() for _ in games_info]
    for idx, game in enumerate(games_info):
        st.session_state.setdefault(f"boxscore_{idx}", False)

        home = game["homeTeam"]
        away = game["awayTeam"]
        scores = [game["awayScore"], game["homeScore"]]
        logos = [
            st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, f"{team}.png"), raw=True)
            for team in [away, home]
        ]

        btn_text = (
            f'![icon](data:image/png;base64,{logos[0]})'
            f'&nbsp;&nbsp;&nbsp;{away} {scores[0]} - {scores[1]} {home}&nbsp;&nbsp;&nbsp;'
            f'![icon](data:image/png;base64,{logos[1]})'
            f'&nbsp;&nbsp;&nbsp;({game["time"]})'
        )

        with buttonholders[idx].container():
            selected_color = "#202A4E"
            hover_color = "#2E385C"
            default_hover_color = '#262831'
            button_css = f"""
                    div.stButton button:hover {{
                        background-color: {default_hover_color};
                    }}
                """
            if st.session_state[f"boxscore_{idx}"]:
                button_css = f"""
                    div.stButton button {{
                        background-color: {selected_color};
                    }}
                    div.stButton button:hover {{
                        background-color: {hover_color};
                    }}
                """
            with sc(f"custom_button_css_{idx}",  css_styles=button_css):
                st.button(btn_text,
                    key=f"btn_{idx}",
                    on_click=lambda k=idx: st.session_state.update(
                        {f"boxscore_{k}": not st.session_state[f"boxscore_{k}"]})
                )

    for idx in range(len(games_info)):
        if st.session_state[f"boxscore_{idx}"]:
            html_df = df_to_html(live_games[idx], show_cols=['Joueur', 'Equipe', 'Min', 'TTFL', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb', 'Blk', 'Stl', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'PF'],
                                            show_index=False,
                                            tooltips={},
                                            col_header_labels={'Equipe' : 'Équipe', 'Pm' : '±'}, 
                                            col_header_tooltips=[],
                                            image_tooltips=[],
                                            color_tooltip_pct=False)
            tableholders[idx].markdown(html_df, unsafe_allow_html=True)
        else:
            tableholders[idx].empty()
    
    total_steps = int(TTL * REFRESH_RATE)
    for step in range(int(start_pct * total_steps), total_steps + 1):
        pct = step / total_steps
        progress_bar.progress(value=pct, width=300)
        seconds_remaining = max(0, TTL - (pct * TTL))
        progress_text.text(f"MàJ dans {seconds_remaining:.0f}s")
        time.sleep(1 / REFRESH_RATE)
        
    st.rerun()