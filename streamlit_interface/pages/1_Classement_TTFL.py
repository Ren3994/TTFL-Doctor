import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import config, custom_error, conn_db, custom_CSS, custom_mobile_CSS
from misc.misc import RESIZED_LOGOS_PATH, IMG_CHARGEMENT, IMG_PLUS_DE_GRAPHES
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.plotting_utils import generate_all_plots
from streamlit_interface.classement_TTFL_utils import *
from data.sql_functions import get_games_for_date
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'classement'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)
conn = conn_db()

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Classement TTFL du jour</div>', unsafe_allow_html=True)

mobile = st.session_state.get("screen_width", 1000) <= 500
if mobile:
    st.markdown(custom_mobile_CSS, unsafe_allow_html=True)
    cols_top = st.columns([1, 5, 1], gap="small")
    col_prev, col_input, col_next = cols_top[0], cols_top[1], cols_top[2]
    col_checkboxes, col_low_games_count = st.columns([1])[0], st.columns([1])[0]
    games_per_row = 2
else:
    cols_top = st.columns([4, 0.7, 1.5, 0.7, 5], gap="small")
    col_prev, col_input, col_next = cols_top[1], cols_top[2], cols_top[3]
    col_checkboxes, col_low_games_count = cols_top[0], cols_top[4]
    games_per_row = 4

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
    if ((st.session_state.local_instance) or
        (st.session_state.get('username', '') != '') or
        (st.session_state.get('temp_jdp_df', False))):
            filter_JDP = st.checkbox("Masquer les joueurs déjà pick", value=True)
    else:
        filter_JDP = st.checkbox("Masquer les joueurs déjà pick", 
                                 value=False, 
                                 disabled=True, 
                                 help=("Rentrez des picks dans la page "
                                 "\"Historique des picks\" pour pouvoir les filtrer")
                                )

    filter_inj = st.checkbox("Masquer les joueurs blessés", value=False)
    
    if st.button('Générer plus de graphes'):
        st.session_state.plot_calc_start += st.session_state.plot_calc_incr
        st.session_state.plot_calc_stop += st.session_state.plot_calc_incr

with col_low_games_count:
    st.markdown(get_low_game_count(conn, st.session_state.selected_date.strftime("%d/%m/%Y")), unsafe_allow_html=True)
    deadline = get_deadline(conn, st.session_state.selected_date.strftime("%d/%m/%Y"))
    st.markdown(deadline, unsafe_allow_html=True)

st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

# Display tonight's games
games_for_date = get_games_for_date(conn, st.session_state.selected_date.strftime("%d/%m/%Y")).to_dict(orient="records")
games_tonight = st.empty()

for i in range(0, len(games_for_date), games_per_row):
    games_tonight_row = st.empty()
    row_games = games_for_date[i:i + games_per_row]
    cols = games_tonight_row.columns(games_per_row)

    for col, game in zip(cols, row_games):
        ha = [game["homeTeam"], game["awayTeam"]]
        logos = [st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, f"{team}.png"), width=30) for team in ha]

        if ha[0] == 'TBD' or ha[1] == 'TBD':
            st.session_state.games_TBD = True
        
        with col:
            st.markdown(
            f"""
            <div style='display:flex;justify-content:center;align-items:center;gap:1rem;margin:5px;margin-top:0'>
                <div>{logos[0]}</div>
                <div style='font-size:16px;'>
                    {ha[0]} - {ha[1]}
                </div>
                <div>{logos[1]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

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
        or (st.session_state.topTTFL_df.loc[
            st.session_state.plot_calc_start:
            st.session_state.plot_calc_stop - 1, 
            'plots'] == IMG_PLUS_DE_GRAPHES).any()):
        
        if st.session_state.plot_calc_start == 0: # Si aucun graphe n'existe
            st.session_state.topTTFL_df['plots'] = IMG_PLUS_DE_GRAPHES
        
        if 'display_df' not in st.session_state:
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
            plots_to_update = plots_to_update.groupby(level=0).first()
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