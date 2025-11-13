from datetime import datetime
import streamlit as st
import keyboard
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from update_manager.file_manager import cleanup_db
from streamlit_interface.JDP_utils import JoueursDejaPick
from misc.misc import ICON_PATH

st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")

# ---------- Initialize session state ----------

if 'data_ready' not in st.session_state:
    st.switch_page('streamlit_main.py')

if "jdp_df" not in st.session_state:
    st.session_state.JDP = JoueursDejaPick()
    st.session_state.jdp_df = st.session_state.JDP.initJDP()

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

if st.session_state.local_instance:
    if st.sidebar.button("🛑 Quitter"):
        keyboard.press_and_release('ctrl+w')
        cleanup_db()
        os.kill(os.getpid(), signal.SIGTERM)

st.write("### Historique des picks")
st.markdown("""
1. Choisissez un nom d'utilisateur et appuyez sur **login** (ou entrée). Si vous avez déjà rentré vos picks, ils s'afficheront dans le tableau
2. Rentrez vos picks (initiales, surnom, juste prénom, juste nom, ou nom entier)
3. Cliquez sur **sauvegarder**
4. Les scores vont s'afficher, vos picks seront sauvegardés et ne s'afficheront dans le tableau **"Classement TTFL"** que s'ils sont disponibles
""")
edited_df = st.data_editor(st.session_state.jdp_df,
                            key="jdp_editor",
                            num_rows="dynamic",
                            width='stretch',
                            column_config={
                                "Joueur": st.column_config.TextColumn("Joueur", disabled=False),
                                "Date du pick": st.column_config.TextColumn("Date du pick", disabled=True),
                                "TTFL": st.column_config.TextColumn("TTFL", disabled=True),
                                "Moyenne TTFL": st.column_config.TextColumn("Moyenne TTFL", disabled=True),
                                "Date de retour": st.column_config.TextColumn("Date de retour", disabled=True)
                            },
                            hide_index=True,
                            column_order=("Joueur", "Date du pick", "TTFL", "Moyenne TTFL", "Date de retour")
                            )

if st.button("💾 Sauvegarder"):
    st.session_state.jdp_df = st.session_state.JDP.saveJDP(edited_df)
    st.rerun()
