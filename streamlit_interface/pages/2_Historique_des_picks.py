import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.classement_TTFL_utils import custom_CSS
from streamlit_interface.streamlit_utils import config, sidebar
from streamlit_interface.JDP_utils import JoueursDejaPick

# ---------- Initialize session state ----------
config(page='JDP')

if 'data_ready' not in st.session_state:
    st.switch_page('streamlit_main.py')

if "JDP" not in st.session_state:
    st.session_state.JDP = JoueursDejaPick()

if "jdp_df" not in st.session_state:
    st.session_state.jdp_df = st.session_state.JDP.initJDP()

# --- Sidebar ---
sidebar(page='JDP')

# ---------- UI ------------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Historique des picks</div>', unsafe_allow_html=True)

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