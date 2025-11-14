from datetime import datetime
import streamlit as st
import subprocess
import keyboard
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.file_manager import cleanup_db, manage_backups
from streamlit_interface.JDP_utils import JoueursDejaPick
from misc.misc import STREAMLIT_MAIN_PY_PATH

def launch_GUI():
    subprocess.run([sys.executable, "-m", "streamlit", "run", STREAMLIT_MAIN_PY_PATH])

def config(page):
    st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")

def sidebar(page):

    st.sidebar.header('Navigation')

    st.sidebar.page_link('pages/1_Classement_TTFL.py', label='1 - Classement TTFL')
    st.sidebar.page_link('pages/2_Historique_des_picks.py', label='2 - Historique des picks')

    if page != 'main':
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

    if st.secrets.environment == 'local':
        if st.sidebar.button("🛑 Quitter"):
            cleanup_db()
            if 'data_ready' in st.session_state:
                if st.session_state.data_ready:
                    manage_backups()

            keyboard.press_and_release('ctrl+w')
            os.kill(os.getpid(), signal.SIGTERM)
        
        st.sidebar.write(f"Instance : {'local' if st.session_state.local_instance else 'cloud'}")
        if st.sidebar.button('Switch instance'):
            st.session_state.local_instance = not st.session_state.local_instance
            st.session_state.pop('jdp_df', None)
            st.rerun()

# if __name__ == '__main__':
#     launch_GUI()