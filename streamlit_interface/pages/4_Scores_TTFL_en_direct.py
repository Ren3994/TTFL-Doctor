from streamlit_extras.add_vertical_space  import add_vertical_space as vspace
from streamlit_extras.stylable_container import stylable_container as sc
import streamlit as st
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, st_image_crisp, custom_button_css, custom_CSS, custom_mobile_CSS
from streamlit_interface.classement_TTFL_utils import df_to_html
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.live_scores_utils import get_live_games
from streamlit_interface.sidebar import sidebar
from misc.misc import RESIZED_LOGOS_PATH

# ---------- Initialize session state ----------
PAGENAME = 'live_scores'
REFRESH_RATE, TTL = 30, 15
upcoming_games, games_info, live_games, game_night_date, timestamp = get_live_games()
init_session_state(page=PAGENAME, arg=timestamp)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Scores TTFL en direct</div>', unsafe_allow_html=True)
mobile = st.session_state.get("mobile_layout", False)
if mobile != st.session_state.get("mobile_layout", False):
    st.session_state.mobile_layout = mobile
    st.rerun()
if mobile:
    upcoming_games_per_row = 1
else:
    upcoming_games_per_row = 3

if len(upcoming_games) > 0:
    st.subheader('Matchs à venir :')
    for i in range(0, len(upcoming_games), upcoming_games_per_row):
        cols = st.columns(upcoming_games_per_row)
        for j in range(upcoming_games_per_row):
            idx = i + j
            if idx >= len(upcoming_games):
                break
            upcoming_game = upcoming_games[idx]
            ha = [upcoming_game['homeTeam'], upcoming_game['awayTeam']]
            gameTime = upcoming_game['gameTimeParis']
            logos = [st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, f"{team}.png"), width=30)
                    for team in ha]

            with cols[j]:
                st.markdown(f"""
                    <div style='display:flex;justify-content:center;align-items:center;gap:1rem;margin:5px;margin-top:0'>
                        <div>{logos[0]}</div>
                        <div style='font-size:16px;'>
                            {ha[0]} - {ha[1]}
                        </div>
                        <div>{logos[1]}</div>
                        <div>{gameTime}</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    vspace(2)

if len(live_games) == 0:
    st.subheader('Aucun match en cours.')
    vspace(50)
else:
    elapsed = time.time() - st.session_state.live_scores_update_timestamp
    real_start_pct = min(1, elapsed / TTL)
    start_pct = max(real_start_pct, st.session_state.progress_pct)
    if mobile:
        st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
        col_subheader = st.columns([1])[0]
        col_progress, col_progress_text = st.columns([1, 1])
        col_toggle = st.columns([1])[0]
        prog_width=100
        games_per_row = 1
    else:
        col_subheader, col_progress_text, col_progress, col_toggle = st.columns([2.5, 1.5, 4, 1.5], gap='small')
        prog_width=300
        games_per_row = 3

    with col_subheader:
        st.subheader('Matchs en cours :')

    col_toggle.space('small')
    with col_toggle:
        new_toggle_value = st.toggle('Par équipe', key='live_scores_by_team')

    col_progress.space('small')
    with col_progress:
        progress_bar = st.progress(value=start_pct, width=prog_width)
    col_progress_text.space('small')

    with col_progress_text:
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
            f'{away} {scores[0]} - {scores[1]} {home}'
            f'![icon](data:image/png;base64,{logos[1]})'
            f'({game["time"]})'
        )

        with buttonholders[idx].container():
            with sc(f"custom_button_css_{idx}",  css_styles=custom_button_css(
                st.session_state[f"boxscore_{idx}"])
            ):
                st.button(btn_text,
                    key=f"btn_{idx}",
                    on_click=lambda k=idx: st.session_state.update(
                        {f"boxscore_{k}": not st.session_state[f"boxscore_{k}"]}),
                    width=255
                )

    for idx in range(len(games_info)):
        if st.session_state[f"boxscore_{idx}"]:

            live_games[idx] = (live_games[idx].sort_values(
                by=['Equipe', 'TTFL'] if st.session_state.live_scores_by_team else 'TTFL', 
                ascending=[True, False] if st.session_state.live_scores_by_team else False)
                .reset_index(drop=True))
            
            idx_pick = None
            picks = st.session_state.get('jdp_df', None)
            if picks is not None and not (picks['Joueur'] == '').all():
                series = picks.loc[picks['Date du pick'] == game_night_date, 'Joueur']
                pick = series.iloc[0] if not series.empty else None
                if ((pick is not None and pick != '') and 
                    (pick in live_games[idx]['Joueur'].tolist() or
                     f'{pick}*' in live_games[idx]['Joueur'].tolist())):
                    idx_pick = live_games[idx].index[live_games[idx]['Joueur'] == pick] + 1

            html_df = df_to_html(live_games[idx], show_cols=['Joueur', 'Equipe', 'Min', 'TTFL', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb', 'Blk', 'Stl', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'PF'],
                                            show_index=False,
                                            tooltips={
                                                'TTFL' : 'perf_str',
                                                'FG' : 'FGpct',
                                                'FG3' : 'FG3pct',
                                                'FT' : 'FTpct'
                                            },
                                            col_header_labels={'Equipe' : 'Équipe', 'Pm' : '±'}, 
                                            col_header_tooltips=[],
                                            image_tooltips=[],
                                            color_tooltip_pct=False,
                                            highlight_index=idx_pick)
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

SEO('footer')