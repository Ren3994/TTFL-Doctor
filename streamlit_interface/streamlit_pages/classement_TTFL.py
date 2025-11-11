from datetime import date
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import st_image_crisp, next_date, prev_date, on_text_change, df_to_html, get_joueurs_pas_dispo, get_joueurs_blesses, get_low_game_count, update_session_state_df, custom_CSS
from streamlit_interface.plotting_utils import generate_all_plots
from misc.misc import RESIZED_LOGOS_PATH, IMG_CHARGEMENT
from data.sql_functions import get_games_for_date

TITLE = "Classement TTFL"
ORDER = 2

def run():

    # ---------- Initialize session state ----------

    if "selected_date" not in st.session_state:
        today = date.today()
        st.session_state.selected_date = today
        st.session_state.text_parse_error = False
    
    if "date_text" not in st.session_state or st.session_state.date_text == "":
        st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")

    if "topTTFL_df" not in st.session_state:
        update_session_state_df(st.session_state.selected_date.strftime('%d/%m/%Y'))
        
    # ---------- UI ----------
    st.markdown(custom_CSS, unsafe_allow_html=True)
    st.write(st.session_state.username)
    # Title
    st.markdown('<div class="date-title">Classement TTFL du jour</div>', unsafe_allow_html=True)

    # Text field with buttons on the sides
    col_checkboxes, col_prev, col_input, col_next, col_low_games_count = st.columns([4, 0.7, 1.5, 0.7, 5], gap="small")

    with col_prev:
        st.button("◀️", on_click=prev_date)

    with col_input:
        st.text_input(
            label="date du jour",
            key="date_text",
            on_change=on_text_change,
            label_visibility="collapsed",
            width=120,
        )

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

    # Error handler if invalid date format in text field
    if st.session_state.text_parse_error:
        st.error("Format de date invalide — utilisez JJ/MM/AAAA (ex: 20/12/2025).")

    st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

    # Display for games with team logos
    games_for_date = get_games_for_date(st.session_state.selected_date.strftime("%d/%m/%Y")).to_dict(orient="records")

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
    st.write("")

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
        
        # db_hash = get_db_hash()
        # save_to_cache(st.session_state.topTTFL_df, st.session_state.selected_date.strftime('%d/%m/%Y'), db_hash)