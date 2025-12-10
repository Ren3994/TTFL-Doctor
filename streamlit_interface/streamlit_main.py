import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import config, SEO, vspace, custom_CSS
from streamlit_interface.session_state_manager import init_session_state

# ---------- Initialize session state ----------
PAGENAME = 'main'
init_session_state(PAGENAME)
config(page=PAGENAME)

st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">TTFL Doctor</div>', unsafe_allow_html=True)

col_spacer1, col_text, col_spacer2 = st.columns([2, 5, 2])
with col_text:
    SEO('header')
    vspace(5)

# st.markdown('<div class="date-title">Pages disponibles</div>', unsafe_allow_html=True)

# col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])

# button_css = """.stButton button {{
#             font-size: 30px !important;
#             font-weight: bold !important;
#         }}"""

# with col1:
#     l, center, r = st.columns([1, 10, 1])
#     st.markdown('<div class="big-button">', unsafe_allow_html=True)
#     with center:
#         st.button('Classement TTFL')
#     st.markdown('</div>', unsafe_allow_html=True)

#     st.markdown('<div class="centered-text">Découvrez le classement TTFL de tous les joueurs qui vont jouer ce soir avec des informations sur les blessures toujours mises à jour.<br><br>' \
#              'Survoler les colonnes fera apparaître tous types de statistiques : évolution des perfs TTFL, impact des blessures des coéquipiers et des adversaires, scores à la maison/à l\'extérieur, contre cette adversaire, des joueurs de ce poste, et bien d\'autres'
#              '</div>', unsafe_allow_html=True)
# with col2:
#     st.markdown('<div class="big-text">Historique des picks</div>', unsafe_allow_html=True)
# with col3:
#     st.markdown('<div class="big-text">Top de la nuit</div>', unsafe_allow_html=True)
# with col4:
#     st.markdown('<div class="big-text">Scores TTFL en direct</div>', unsafe_allow_html=True)
# with col5:
#     st.markdown('<div class="big-text">Stats par équipes</div>', unsafe_allow_html=True)
# with col6:
#     st.markdown('<div class="big-text">Stats par joueurs</div>', unsafe_allow_html=True)
vspace(50)
SEO('footer')

st.switch_page('pages/1_Classement_TTFL.py')