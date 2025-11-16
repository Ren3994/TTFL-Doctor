from streamlit_js_eval import streamlit_js_eval
from datetime import date
import streamlit as st
import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from misc.misc import RESIZED_LOGOS_PATH, IMG_CHARGEMENT, IMG_PLUS_DE_GRAPHES
from streamlit_interface.streamlit_utils import config, custom_error, conn_db
from streamlit_interface.plotting_utils import generate_all_plots
from streamlit_interface.classement_TTFL_utils import *
# from streamlit_interface.update import update_all_data
from data.sql_functions import get_games_for_date
from streamlit_interface.sidebar import sidebar

# ---------- Run updates if needed ----------
# last_update = update_all_data()

if 'data_ready' not in st.session_state:
    st.switch_page('streamlit_main.py')

# --- Sidebar ---
sidebar(page='classement')

# ---------- Initialize session state ----------
conn = conn_db()
config(page='classement')

# st.session_state.last_update = last_update


st.session_state.selected_date = st.session_state.get("selected_date", date.today())

st.session_state.date_text = st.session_state.get(
    "date_text",
    st.session_state.selected_date.strftime("%d/%m/%Y"))

if st.session_state.date_text == "" or not st.session_state.date_text:
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")

if "topTTFL_df" not in st.session_state:
    update_session_state_df(st.session_state.selected_date.strftime('%d/%m/%Y'))

if 'games_TBD' not in st.session_state:
    st.session_state.games_TBD = False

if 'scr_key' not in st.session_state:
    st.session_state.scr_key = str(uuid.uuid4())

if "screen_width" not in st.session_state:
    width = streamlit_js_eval(js_expressions='screen.width', key=st.session_state.scr_key)
    if width:
        st.session_state.screen_width = width

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Classement TTFL du jour</div>', unsafe_allow_html=True)

mobile = st.session_state.get("screen_width", 1000) <= 500
if mobile:
    st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
    cols_top = st.columns([1, 5, 1], gap="small")
    col_prev, col_input, col_next = cols_top[0], cols_top[1], cols_top[2]
    col_checkboxes, col_low_games_count = st.columns([1])[0], st.columns([1])[0]
    games_per_row = 1
else:
    cols_top = st.columns([4, 0.7, 1.5, 0.7, 5], gap="small")
    col_prev, col_input, col_next = cols_top[1], cols_top[2], cols_top[3]
    col_checkboxes, col_low_games_count = cols_top[0], cols_top[4]
    games_per_row = 3

with col_prev:
    st.button("◀️", on_click=prev_date)

with col_input:
    st.text_input(
        label="date du jour",
        key="date_text",
        on_change=on_text_change,
        label_visibility="collapsed",
        width=120)
    if st.session_state.get("text_parse_error", False):
        custom_error('Format invalide<br>JJ/MM/AAAA', fontsize=13)
        
with col_next:
    st.button("▶️", on_click=next_date)

with col_checkboxes:
    if (st.session_state.local_instance) or ('username_str' in st.session_state and st.session_state.username_str != ''):
        filter_JDP = st.checkbox("Masquer les joueurs déjà pick", value=True)
    else:
        filter_JDP = False

    filter_inj = st.checkbox("Masquer les joueurs blessés", value=False)
    
    if st.button('Générer plus de graphes'):
        st.session_state.plot_calc_start += st.session_state.plot_calc_incr
        st.session_state.plot_calc_stop += st.session_state.plot_calc_incr
        st.session_state.gen_more_plots = True

with col_low_games_count:
    st.markdown(get_low_game_count(conn, st.session_state.selected_date.strftime("%d/%m/%Y")), unsafe_allow_html=True)

st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

# Display tonight's games
games_for_date = get_games_for_date(conn, st.session_state.selected_date.strftime("%d/%m/%Y")).to_dict(orient="records")
cols_per_game = 3
total_cols = games_per_row * cols_per_game

for i in range(0, len(games_for_date), games_per_row):
    chunk = games_for_date[i : i + games_per_row]
    cols = st.columns(total_cols)

    for j, game in enumerate(chunk):
        home = game["homeTeam"]
        away = game["awayTeam"]

        if home == 'TBD' or away == 'TBD':
            st.session_state.games_TBD = True

        home_logo_path = os.path.join(RESIZED_LOGOS_PATH, f"{home}.png")
        away_logo_path = os.path.join(RESIZED_LOGOS_PATH, f"{away}.png")

        base = j * cols_per_game
        with cols[base]:
            home_logo = st_image_crisp(home_logo_path, width=30)
            st.markdown(home_logo, unsafe_allow_html=True)
        with cols[base + 1]:
            st.markdown(f"{home} - {away}")
        with cols[base + 2]:
            away_logo = st_image_crisp(away_logo_path, width=30)
            st.markdown(away_logo, unsafe_allow_html=True)

if len(games_for_date) > 0:
    st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

# Display the TTFL table
if st.session_state.topTTFL_df.empty:
    if not st.session_state.games_TBD:
        st.subheader(f"Pas de matchs NBA le {st.session_state.selected_date.strftime('%d/%m/%Y')}")
    else:
        st.subheader(f"Les équipes de des matchs du {st.session_state.selected_date.strftime('%d/%m/%Y')} n'ont pas encore été déterminées")

else:
    table_placeholder = st.empty()
    if ('plots' not in st.session_state.topTTFL_df.columns 
        or st.session_state.gen_more_plots):
        # or (st.session_state.topTTFL_df['plots'] == IMG_PLUS_DE_GRAPHES).all()):
        
        if st.session_state.plot_calc_start == 0: # Si aucun graphe n'existe
            st.session_state.topTTFL_df['plots'] = IMG_PLUS_DE_GRAPHES
            st.session_state.display_df = st.session_state.topTTFL_df.copy()
        
        st.session_state.display_df.loc[
            st.session_state.plot_calc_start:
            st.session_state.plot_calc_stop - 1, 'plots'] = IMG_CHARGEMENT

        topTTFL_html = df_to_html(st.session_state.display_df)
        table_placeholder.markdown(topTTFL_html, unsafe_allow_html=True)

        chunk_size = 5 # On calcule et on ajoute les graphes dans le df complet
        for i in range(st.session_state.plot_calc_start, 
                        min(len(st.session_state.topTTFL_df), st.session_state.plot_calc_stop), 
                        chunk_size):
            chunk = st.session_state.topTTFL_df.iloc[i:i+chunk_size]
            chunk_with_plots = generate_all_plots(chunk, 
                                                    st.session_state.selected_date.strftime('%d/%m/%Y'),
                                                    parallelize = False)
            st.session_state.topTTFL_df.iloc[i:i+chunk_size] = chunk_with_plots
            
            # On met à jour les graphes dans le df display
            plots_to_update = st.session_state.topTTFL_df.set_index('Joueur')['plots']
            st.session_state.display_df['plots'] = st.session_state.display_df['Joueur'].map(plots_to_update)

            topTTFL_html = df_to_html(st.session_state.display_df)
            table_placeholder.markdown(topTTFL_html, unsafe_allow_html=True)

    st.session_state.display_df = apply_df_filters(conn,
                                           st.session_state.selected_date.strftime('%d/%m/%Y'),
                                           st.session_state.plot_calc_start,
                                           st.session_state.plot_calc_stop,
                                           filter_JDP,
                                           filter_inj)
    
    display_df_html = df_to_html(st.session_state.display_df)
    table_placeholder.markdown(display_df_html, unsafe_allow_html=True)