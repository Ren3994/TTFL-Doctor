import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from misc.misc import DB_PATH
from streamlit_interface.JDP_utils import JoueursDejaPick

TITLE = "Joueurs déjà pick"
ORDER = 3

# def run():

if "jdp_df" not in st.session_state:
    st.session_state.JDP = JoueursDejaPick(DB_PATH)
    st.session_state.jdp_df = st.session_state.JDP.initJDP()

st.set_page_config(page_title="Joueurs déjà pick", layout="wide")

st.write("### Historique des picks")

if not st.session_state.local_instance:
    col_username_input, col_accept_username = st.columns([5, 5])
    with col_username_input:
        st.text_input(
            label="Nom d'utilisateur",
            key="username",
            label_visibility="collapsed",
            width=120,
        )
    with col_accept_username:
        if st.button('OK'):
            st.session_state.JDP = JoueursDejaPick(DB_PATH)
            st.session_state.jdp_df = st.session_state.JDP.initJDP()

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
    st.success("Modifications sauvegardées")
    st.rerun()