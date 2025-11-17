from supabase import create_client
from datetime import datetime
import streamlit as st
import keyboard
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.file_manager import cleanup_db, manage_backups
from streamlit_interface.classement_TTFL_utils import cached_get_top_TTFL
from streamlit_interface.plotting_utils import cached_generate_plot_row
from streamlit_interface.JDP_utils import JoueursDejaPick

def sidebar(page):

    st.sidebar.header('Navigation')

    st.sidebar.page_link('pages/1_Classement_TTFL.py', label='1 - Classement TTFL')
    st.sidebar.page_link('pages/2_Historique_des_picks.py', label='2 - Historique des picks')

    st.sidebar.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

    if page != 'main':
        if "last_update" in st.session_state:
            st.sidebar.write(f"MàJ : {datetime.strftime(st.session_state.last_update, '%d %b. à %Hh%M')}")

        if not st.session_state.local_instance:
            col_username_input, col_accept_username = st.sidebar.columns([2, 1], gap='small')
            with col_username_input:
                if st.session_state.get('username_str', 'None') in ['', 'None']:
                    st.text_input(
                        label="Nom d'utilisateur",
                        placeholder="Nom d'utilisateur",
                        key="username",
                        label_visibility='collapsed',
                        width=200)
                else:
                    st.text_input(
                        label="Nom d'utilisateur",
                        value=st.session_state.username_str,
                        key="username",
                        label_visibility='collapsed',
                        width=200)
                    
            with col_accept_username:
                if st.button('Login'):
                    st.session_state.JDP = JoueursDejaPick()
                    st.session_state.jdp_df = st.session_state.JDP.initJDP()
                    st.session_state.username_str = st.session_state.username
                    st.session_state.JDP_save_error = False
                    st.session_state.temp_jdp_df = False
            
            if 'username' in st.session_state and st.session_state.username != '':
                st.session_state.JDP = JoueursDejaPick()
                st.session_state.jdp_df = st.session_state.JDP.initJDP()
                st.session_state.username_str = st.session_state.username
                st.session_state.JDP_save_error = False
                st.session_state.temp_jdp_df = False

        if st.session_state.data_ready:
            if st.sidebar.button("Mettre à jour les données"):
                cached_get_top_TTFL.clear()
                cached_generate_plot_row.clear()
                st.session_state.pop('topTTFL_df', None)
                st.session_state.pop('display_df', None)
                st.session_state.data_ready = False
                st.switch_page('streamlit_main.py')

    if st.secrets.environment == 'local':
        if page != 'main':
            st.sidebar.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)
        
        st.sidebar.header('Dev tools')

        st.sidebar.write(f"Instance : {'local' if st.session_state.local_instance else 'cloud'}")
        if st.sidebar.button('Switch instance'):
            st.session_state.local_instance = not st.session_state.local_instance
            st.session_state.pop('jdp_df', None)
            st.rerun()
            
        if st.sidebar.button("🛑 Quitter"):
            cleanup_db()
            if 'data_ready' in st.session_state:
                if st.session_state.data_ready:
                    manage_backups()

            keyboard.press_and_release('ctrl+w')
            os.kill(os.getpid(), signal.SIGTERM)