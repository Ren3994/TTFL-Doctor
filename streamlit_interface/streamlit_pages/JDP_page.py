import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import DB_PATH
from streamlit_interface.JDP_utils import JoueursDejaPick

TITLE = "Joueurs déjà pick"

def run():

    if "jdp_df" not in st.session_state:
        st.session_state.JDP = JoueursDejaPick(DB_PATH)
        st.session_state.jdp_df = st.session_state.JDP.initJDP()

    st.set_page_config(page_title="Joueurs déjà pick", layout="wide")
    
    st.write("### Historique des picks")
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
        st.success("Changes processed and saved!")
        st.rerun()