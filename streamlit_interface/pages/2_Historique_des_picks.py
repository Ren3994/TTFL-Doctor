import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.clear_cache_functions import clear_after_JDP_update
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.streamlit_utils import SEO, config, custom_CSS
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'JDP'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)

# ---------- UI ------------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Historique des picks</div>', unsafe_allow_html=True)

st.markdown("""
1. Choisissez un nom d'utilisateur et appuyez sur **login** (ou entrée). Si vous avez déjà sauvegardé vos picks, ils s'afficheront dans le tableau
2. Rentrez vos picks dans la colonne **Joueur** (initiales, surnom, prénom, nom, ou nom entier). Pas besoin de capitaliser
3. Cliquez sur **💾 Sauvegarder**
4. Les scores vont s'afficher, vos picks seront sauvegardés et ne s'afficheront dans le tableau **"Classement TTFL"** que s'ils sont disponibles
""")

edited_df = st.data_editor(st.session_state.jdp_df,
                            key="jdp_editor",
                            num_rows="fixed",
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
save_col, error_col, spacer_col1, spacer_col2 = st.columns([2.5, 5.2, 2, 2])
with save_col:
    if st.button("💾 Sauvegarder"):
        if (st.session_state.local_instance or
            st.session_state.get('username', '') != ''):
                st.session_state.jdp_df = st.session_state.JDP.saveJDP(edited_df)
        else:
             st.session_state.jdp_df = st.session_state.JDP.saveJDP(edited_df, save=False)
             st.session_state.JDP_save_error = True
             st.session_state.temp_jdp_df = True
             
        clear_after_JDP_update()
        st.rerun()
        
with error_col:
    if st.session_state.JDP_save_error:
         st.error("Rentrez un nom d'utilisateur avant de sauvegarder pour que vos picks soit enregistrés pour la prochaine fois")
    
SEO('footer')