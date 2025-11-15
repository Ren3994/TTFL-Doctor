from datetime import datetime
import streamlit as st
import subprocess
import keyboard
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.file_manager import cleanup_db, manage_backups
from streamlit_interface.classement_TTFL_utils import cached_get_top_TTFL
from streamlit_interface.plotting_utils import cached_generate_plot_row
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

    st.sidebar.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

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
                cached_get_top_TTFL.clear()
                cached_generate_plot_row.clear()
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

def custom_error(error_text, fontsize, center_text=True):
    st.markdown(f"""
            <div style="
                background-color: #3e2428; 
                color: #f06666; 
                padding: 10px; 
                border-radius: 5px; 
                font-size: {fontsize}px;
                text-align: {'center' if center_text else 'left'};
            ">
                {error_text}
            </div>
            """, unsafe_allow_html=True)

# if __name__ == '__main__':
#     launch_GUI()