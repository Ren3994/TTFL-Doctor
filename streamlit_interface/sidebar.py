from datetime import datetime
import streamlit as st
import keyboard
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.clear_cache_functions import clear_after_JDP_update, clear_after_db_update, clear_after_injury_update
from streamlit_interface.streamlit_utils import requests_form, deepl_api_limit_reached
from streamlit_interface.streamlit_update_manager import update_all_data
from update_manager.file_manager import cleanup_db, manage_backups
from streamlit_interface.JDP_utils import JoueursDejaPick

def on_username_change():

    st.session_state.JDP = JoueursDejaPick()
    st.session_state.jdp_df = st.session_state.JDP.initJDP()
    st.session_state.JDP_save_error = False
    st.session_state.temp_jdp_df = False

    clear_after_JDP_update()

def sidebar(page):

    if page != 'main':

        if st.sidebar.button('Recharger la page'):
            clear_after_JDP_update()
            clear_after_db_update()
            clear_after_injury_update()
            st.rerun()

        if "last_update" in st.session_state:
            st.sidebar.write(f"MàJ blessures : {datetime.strftime(st.session_state.last_update, '%d %b. à %Hh%M')}")

        if not st.session_state.local_instance:

            if st.session_state.get('username', '') != '':
                st.sidebar.write(f'Utilisateur : {st.session_state.username}')
            else:
                st.sidebar.write('Pas d\'utilisateur connecté')

            col_username_input, col_accept_username = st.sidebar.columns([2, 1], gap='small')
            with col_username_input:
                st.text_input(
                    label="Nom d'utilisateur",
                    placeholder="Nom d'utilisateur",
                    key="username",
                    on_change=on_username_change,
                    label_visibility='collapsed',
                    width=200)

            with col_accept_username:
                st.button('Login')

            if st.sidebar.button('Se déconnecter'):
                st.session_state.pop("username", None)
                on_username_change()
                st.rerun()

    st.sidebar.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)
    
    st.sidebar.header('Navigation')

    st.sidebar.page_link('pages/1_Classement_TTFL.py', label='1 - Classement TTFL')
    st.sidebar.page_link('pages/2_Historique_des_picks.py', label='2 - Historique des picks')
    st.sidebar.page_link('pages/3_Top_de_la_nuit.py', label='3 - Top de la nuit')
    st.sidebar.page_link('pages/4_Scores_TTFL_en_direct.py', label='4 - Scores TTFL en direct')
    st.sidebar.page_link('pages/5_Stats_par_equipes.py', label='5 - Stats par équipes (WIP)')
    st.sidebar.page_link('pages/6_Stats_par_joueurs.py', label='6 - Stats par joueurs (WIP)')
                
    if st.secrets.environment == 'local':
        if page != 'main':
            st.sidebar.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)
        
        st.sidebar.header('Dev tools')

        limit_reached, usage = deepl_api_limit_reached()
        st.sidebar.write(f'Deepl : {usage} ({limit_reached})')

        if 'local_instance' in st.session_state:
            st.sidebar.write(f"Instance : {'local' if st.session_state.local_instance else 'cloud'}")
            if st.sidebar.button('Switch instance'):
                st.session_state.local_instance = not st.session_state.local_instance
                st.session_state.pop('jdp_df', None)
                st.session_state.pop('JDP', None)
                st.rerun()
            
            if st.sidebar.button('Force update'):
                update_all_data(force_update=True)
                
            if st.sidebar.button("🛑 Quitter"):
                cleanup_db()
                manage_backups()

                keyboard.press_and_release('ctrl+w')
                os.kill(os.getpid(), signal.SIGTERM)
    else:
        st.sidebar.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)
        cols = st.sidebar.columns([1, 5, 1])
        if cols[1].button('Requêtes/Bugs'):
            requests_form()