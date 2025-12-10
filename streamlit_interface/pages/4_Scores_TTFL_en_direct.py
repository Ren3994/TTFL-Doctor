import streamlit as st
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, vspace, get_sc, st_image_crisp, custom_button_css, custom_CSS, custom_mobile_CSS
from streamlit_interface.classement_TTFL_utils import df_to_html, get_idx_pick, get_pick
from streamlit_interface.streamlit_update_manager import need_to_fetch_new_boxscores
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.live_scores_utils import get_live_games
from streamlit_interface.sidebar import sidebar
from misc.misc import RESIZED_LOGOS_PATH

# ---------- Initialize session state ----------
PAGENAME = 'live_scores'
REFRESH_RATE, TTL = 30, 15

live_data = get_live_games()

init_session_state(page=PAGENAME, arg=live_data['timestamp'])
sidebar(page=PAGENAME)
config(page=PAGENAME)
sc = get_sc()

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Scores TTFL en direct</div>', unsafe_allow_html=True)

if st.session_state.mobile_layout:
    upcoming_games_per_row = 1
else:
    upcoming_games_per_row = 3

if len(live_data['upcoming_games']) > 0:
    st.subheader('Matchs à venir :')
    for i in range(0, len(live_data['upcoming_games']), upcoming_games_per_row):
        cols = st.columns(upcoming_games_per_row)
        for j in range(upcoming_games_per_row):
            idx = i + j
            if idx >= len(live_data['upcoming_games']):
                break
            upcoming_game = live_data['upcoming_games'][idx]
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
    
    vspace()

if len(live_data['live_games']) == 0 and not need_to_fetch_new_boxscores():
    st.subheader('Aucun match en cours.')
    vspace(50)
else:
    elapsed = time.time() - st.session_state.live_scores_update_timestamp
    real_start_pct = min(1, elapsed / TTL)
    start_pct = max(real_start_pct, st.session_state.progress_pct)
    
    subheader_width = 280
    prog_width = 180
    pick, pick_team = get_pick(date=live_data['gameDate'], team=True)
    if live_data['pending_games']:
        if live_data['finished_games']:
            games_header_str = 'Matchs en cours/matchs finis :'
            subheader_width = 360
            prog_width = 120
        else:
            games_header_str = 'Matchs en cours :'
    else:
        games_header_str = 'Matchs finis :'
        if len(live_data['global']) > 0:
            st.session_state.global_boxscores = True

    if st.session_state.mobile_layout:
        st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
        cont = st.container()
        cont.empty()
        cont_subheader = cont.container()
        cont_progress = cont.container(horizontal=True, horizontal_alignment='center')
        cont_prog_text = cont_progress.container(horizontal_alignment='center')
        cont_progress = cont_progress.container(horizontal_alignment='center')
        cont_toggles = cont.container(horizontal=True, horizontal_alignment='center')
        cont_toggle_byteam = cont_toggles.container(horizontal_alignment='center')
        cont_toggle_global = cont_toggles.container(horizontal_alignment='center')
        games_per_row = 1
    else:
        cont = st.container(horizontal=True)
        cont.empty()
        cont_subheader = cont.container(width = subheader_width)
        cont_prog_text = cont.container(horizontal_alignment='center')
        cont_progress = cont.container(horizontal_alignment='center', width=prog_width)
        cont_toggle_byteam = cont.container(horizontal_alignment='center')
        cont_toggle_global = cont.container(horizontal_alignment='center')
        cont_toggle_byteam.space('small')
        cont_toggle_global.space('small')
        cont_progress.space('small')
        cont_prog_text.space('small')
        games_per_row = 3

    cont_subheader.subheader(games_header_str)

    if live_data['pending_games']:
        progress_bar = cont_progress.progress(value=start_pct)
        progress_text = cont_prog_text.empty()
    
    cont_toggle_byteam.toggle('Par équipe', key='live_scores_by_team')
    cont_toggle_global.toggle('Global', key='global_boxscores')

    vspace()

    cont_buttons = st.container(horizontal_alignment='center')
    cont_buttons.empty()
    for i in range(0, len(live_data['games_info']), games_per_row):
        row_buttons = live_data['games_info'][i:i + games_per_row]
        cont_row_button = cont_buttons.container(horizontal=True, horizontal_alignment='center')
        cont_row_button.empty()
        cont_buttons.write('')
        if st.session_state.mobile_layout:
            cont_row_button.write('')
        for j, game in enumerate(row_buttons):
            idx = i + j
            st.session_state.setdefault(f"boxscore_{idx}", False)
            cont_button = cont_row_button.container(width=280)

            home = game["homeTeam"]
            away = game["awayTeam"]
            matchup = f'{home}-{away}'
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
            
            with cont_button.container():
                with sc(f"custom_button_css_{idx}",  css_styles=custom_button_css(
                    st.session_state[f"boxscore_{idx}"], button_team=matchup, pick_team=pick_team)
                ):
                    st.button(btn_text,
                        key=f"btn_{idx}",
                        on_click=lambda k=idx: st.session_state.update(
                            {f"boxscore_{k}": not st.session_state[f"boxscore_{k}"]}),
                        width=280
                    )
        if st.session_state.mobile_layout:
            cont_row_button.write('')

    vspace()
    tableholders = [st.empty() for _ in live_data['games_info']]

    if st.session_state.global_boxscores:
        all_boxscores_df = (live_data['global'].sort_values(
                    by=['Equipe', 'TTFL'] if st.session_state.live_scores_by_team else 'TTFL', 
                    ascending=[True, False] if st.session_state.live_scores_by_team else False)
                    .reset_index(drop=True))
                
        idx_pick = get_idx_pick(all_boxscores_df, live_data['gameDate'], 'playerName')
        html_df = df_to_html(all_boxscores_df, show_cols=['Joueur', 'Equipe', 'Min', 'TTFL', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb', 'Blk', 'Stl', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'PF'],
                                        show_index = not st.session_state.live_scores_by_team,
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
                                        highlight_index=idx_pick,
                                        best_pick_allowed=True)
        if len(tableholders) == 0:
            tableholders = [st.empty()]
        tableholders[0].markdown(html_df, unsafe_allow_html=True)
        
    else:
        for idx in range(len(live_data['games_info'])):
            if st.session_state[f"boxscore_{idx}"]:

                live_data['live_games'][idx] = (live_data['live_games'][idx].sort_values(
                    by=['Equipe', 'TTFL'] if st.session_state.live_scores_by_team else 'TTFL', 
                    ascending=[True, False] if st.session_state.live_scores_by_team else False)
                    .reset_index(drop=True))
                
                idx_pick = get_idx_pick(live_data['live_games'][idx], live_data['gameDate'], 'playerName')
                html_df = df_to_html(live_data['live_games'][idx], show_cols=['Joueur', 'Equipe', 'Min', 'TTFL', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb', 'Blk', 'Stl', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'PF'],
                                                show_index = not st.session_state.live_scores_by_team,
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
    
    if live_data['pending_games'] :
        total_steps = int(TTL * REFRESH_RATE)
        for step in range(int(start_pct * total_steps), total_steps + 1):
            pct = step / total_steps
            progress_bar.progress(value=pct, width=300)
            seconds_remaining = max(0, TTL - (pct * TTL))
            progress_text.text(f"MàJ dans {seconds_remaining:.0f}s")
            time.sleep(1 / REFRESH_RATE)
        
        st.rerun()
    else:
        vspace(50)
SEO('footer')