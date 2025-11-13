from streamlit_js_eval import streamlit_js_eval
from datetime import datetime, date
import streamlit as st
import keyboard
import signal
import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.classement_TTFL_utils import st_image_crisp, next_date, prev_date, on_text_change, df_to_html, get_joueurs_pas_dispo, get_joueurs_blesses, get_low_game_count, update_session_state_df, custom_CSS, custom_mobile_CSS
from streamlit_interface.plotting_utils import generate_all_plots
from misc.misc import RESIZED_LOGOS_PATH, IMG_CHARGEMENT, ICON_PATH
from update_manager.file_manager import cleanup_db, get_db_hash, save_to_cache
from data.sql_functions import get_games_for_date
from streamlit_interface.JDP_utils import JoueursDejaPick

st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")

# ---------- Initialize session state ----------

if 'data_ready' not in st.session_state:
    st.switch_page('streamlit_main.py')

if "selected_date" not in st.session_state:
    today = date.today()
    st.session_state.selected_date = today
    st.session_state.text_parse_error = False

if "date_text" not in st.session_state or st.session_state.date_text == "":
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")

st.write(f'-{st.session_state.selected_date.strftime("%d/%m/%Y")}-{st.session_state.date_text}-')

if st.session_state.text_parse_error:
    st.error("Format de date invalide — utilisez JJ/MM/AAAA (ex: 20/12/2025).")

if "topTTFL_df" not in st.session_state:
    update_session_state_df(st.session_state.selected_date.strftime('%d/%m/%Y'))

if 'scr_key' not in st.session_state:
    st.session_state.scr_key = str(uuid.uuid4())

if "screen_width" not in st.session_state:
    width = streamlit_js_eval(js_expressions='screen.width', key=st.session_state.scr_key)
    if width:
        st.session_state.screen_width = width
    
# --- Sidebar ---
if "last_update" in st.session_state:
    st.sidebar.write(f"MàJ : {datetime.strftime(st.session_state.last_update, '%d %b. à %Hh%M')}")

if not st.session_state.local_instance:
    col_username_input, col_accept_username = st.sidebar.columns([2, 1], gap='small')
    with col_username_input:
        if 'username_str' not in st.session_state:
            st.text_input(
                label="Nom d'utilisateur",
                placeholder="Nom d'utilisateur",
                key="username",
                label_visibility='collapsed',
                width=200,
            )
        else:
            if st.session_state.username_str == '':
                st.text_input(
                    label="Nom d'utilisateur",
                    placeholder="Nom d'utilisateur",
                    key="username",
                    label_visibility='collapsed',
                    width=200,
                )
            else:
                st.text_input(
                    label="Nom d'utilisateur",
                    value=st.session_state.username_str,
                    key="username",
                    label_visibility='collapsed',
                    width=200,
                )
    with col_accept_username:
        if st.button('Login'):
            st.session_state.JDP = JoueursDejaPick()
            st.session_state.jdp_df = st.session_state.JDP.initJDP()
            st.session_state.username_str = st.session_state.username
    
    if 'username' in st.session_state:
        st.session_state.JDP = JoueursDejaPick()
        st.session_state.jdp_df = st.session_state.JDP.initJDP()
        st.session_state.username_str = st.session_state.username

if st.session_state.data_ready:
    if st.sidebar.button("Mettre à jour les données"):
        st.session_state.data_ready = False
        st.switch_page('streamlit_main.py')

if st.session_state.local_instance:
    if st.sidebar.button("🛑 Quitter"):
        keyboard.press_and_release('ctrl+w')
        cleanup_db()
        os.kill(os.getpid(), signal.SIGTERM)

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)

st.markdown('<div class="date-title">Classement TTFL du jour</div>', unsafe_allow_html=True)

mobile = st.session_state.get("screen_width", 1000) <= 500
if mobile:
    st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
    cols_top = st.columns([1, 5, 1], gap="small")
    col_prev, col_input, col_next = cols_top[0], cols_top[1], cols_top[2]
    col_checkboxes, col_low_games_count = st.columns([1])[0], st.columns([1])[0]
else:
    cols_top = st.columns([4, 0.7, 1.5, 0.7, 5], gap="small")
    col_prev, col_input, col_next = cols_top[1], cols_top[2], cols_top[3]
    col_checkboxes, col_low_games_count = cols_top[0], cols_top[4]

with col_prev:
    st.button("◀️", on_click=prev_date)

with col_input:
    st.write(f'-{st.session_state.selected_date.strftime("%d/%m/%Y")}-{st.session_state.date_text}-')
    st.text_input(
        label="date du jour",
        key="date_text",
        on_change=on_text_change,
        label_visibility="collapsed",
        width=120)

with col_next:
    st.button("▶️", on_click=next_date)

with col_checkboxes:
    filter_JDP = st.checkbox("Masquer les joueurs déjà pick", value=True)
    filter_inj = st.checkbox("Masquer les joueurs blessés", value=False)
    
    if st.button('Générer plus de graphes'):
        st.session_state.plot_calc_start += st.session_state.plot_calc_incr
        st.session_state.plot_calc_stop += st.session_state.plot_calc_incr
        st.session_state.with_plots = False

with col_low_games_count:
    st.markdown(get_low_game_count(st.session_state.selected_date.strftime("%d/%m/%Y")), unsafe_allow_html=True)

st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

# Display for games with team logos
games_for_date = get_games_for_date(st.session_state.selected_date.strftime("%d/%m/%Y")).to_dict(orient="records")
if mobile:
    games_per_row = 1
else:
    games_per_row = 3
cols_per_game = 3
total_cols = games_per_row * cols_per_game

for i in range(0, len(games_for_date), games_per_row):
    chunk = games_for_date[i : i + games_per_row]
    cols = st.columns(total_cols)

    for j, game in enumerate(chunk):
        home = game["homeTeam"]
        away = game["awayTeam"]

        home_logo = os.path.join(RESIZED_LOGOS_PATH, f"{home}.png")
        away_logo = os.path.join(RESIZED_LOGOS_PATH, f"{away}.png")

        base = j * cols_per_game
        with cols[base]:
            st_image_crisp(home_logo, width=30)
        with cols[base + 1]:
            st.markdown(f"{home} - {away}")
        with cols[base + 2]:
            st_image_crisp(away_logo, width=30)

st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

# Display the TTFL table

if st.session_state.topTTFL_df.empty:
    st.subheader(f"Pas de matchs NBA le {st.session_state.selected_date.strftime('%d/%m/%Y')}")

else:
    table_placeholder = st.empty()
    if not st.session_state.with_plots:
        
        if st.session_state.plot_calc_start == 0:
            st.session_state.topTTFL_df['plots'] = IMG_CHARGEMENT                

        topTTFL_html = df_to_html(st.session_state.topTTFL_df)
        table_placeholder.markdown(topTTFL_html, unsafe_allow_html=True)
        
        chunk_size = 5
        for i in range(st.session_state.plot_calc_start, 
                        min(len(st.session_state.topTTFL_df), st.session_state.plot_calc_stop), 
                        chunk_size):
            chunk = st.session_state.topTTFL_df.iloc[i:i+chunk_size]
            chunk_with_plots = generate_all_plots(chunk, 
                                                    st.session_state.selected_date.strftime('%d/%m/%Y'),
                                                    parallelize = False)
            st.session_state.topTTFL_df.iloc[i:i+chunk_size] = chunk_with_plots
            topTTFL_html = df_to_html(st.session_state.topTTFL_df)
            table_placeholder.markdown(topTTFL_html, unsafe_allow_html=True)

    joueurs_pas_dispo = get_joueurs_pas_dispo(st.session_state.selected_date.strftime('%d/%m/%Y'))
    joueurs_blesses = get_joueurs_blesses()

    filtered_topTTFL_df = st.session_state.topTTFL_df.copy()
    if filter_JDP:
        filtered_topTTFL_df = filtered_topTTFL_df[~filtered_topTTFL_df['Joueur'].isin(joueurs_pas_dispo)]
    if filter_inj:
        filtered_topTTFL_df = filtered_topTTFL_df[~filtered_topTTFL_df['Joueur'].isin(joueurs_blesses)]

    filtered_topTTFL_html = df_to_html(filtered_topTTFL_df)
    table_placeholder.markdown(filtered_topTTFL_html, unsafe_allow_html=True)
    
    db_hash = get_db_hash()
    save_to_cache(st.session_state.topTTFL_df, st.session_state.selected_date.strftime('%d/%m/%Y'), db_hash)