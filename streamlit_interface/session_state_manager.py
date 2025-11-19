from streamlit_js_eval import streamlit_js_eval
from datetime import date, timedelta
import streamlit as st
import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import update_session_state_df
from streamlit_interface.JDP_utils import JoueursDejaPick

def init_session_state(page):
    if 'local_instance' not in st.session_state:
        env = st.secrets.get("environment", "unknown")
        if env == 'local':
            st.session_state.local_instance = True
        elif env == 'cloud':
            st.session_state.local_instance = False
    
    st.session_state.username = st.session_state.get('username', '')
    
    if page == 'classement':
    
        st.session_state.selected_date = st.session_state.get("selected_date", date.today())

        st.session_state.date_text = st.session_state.get("date_text",
            st.session_state.selected_date.strftime("%d/%m/%Y"))

        if st.session_state.date_text == "" or not st.session_state.date_text:
            st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")

        if "topTTFL_df" not in st.session_state:
            update_session_state_df(st.session_state.selected_date.strftime('%d/%m/%Y'))

        if 'games_TBD' not in st.session_state:
            st.session_state.games_TBD = False

    if page in ['classement', 'top_nuit']:
        if 'scr_key' not in st.session_state:
            st.session_state.scr_key = str(uuid.uuid4())

        if "screen_width" not in st.session_state:
            width = streamlit_js_eval(js_expressions='screen.width', key=st.session_state.scr_key)
            if width:
                st.session_state.screen_width = width
    
    if page in ['JDP', 'top_nuit']:
        if "JDP" not in st.session_state:
            st.session_state.JDP = JoueursDejaPick()

        if "jdp_df" not in st.session_state:
            st.session_state.jdp_df = st.session_state.JDP.initJDP()

        if "JDP_save_error" not in st.session_state:
            st.session_state.JDP_save_error = False
            
        if 'temp_jdp_df' not in st.session_state:
            st.session_state.temp_jdp_df = False
    
    if page == 'top_nuit':
        st.session_state.selected_date_nuit = st.session_state.get("selected_date_nuit", 
                                                      date.today() - timedelta(days=1))

        st.session_state.date_text_nuit = st.session_state.get("date_text_nuit",
                    st.session_state.selected_date_nuit.strftime("%d/%m/%Y"))

        if st.session_state.date_text_nuit == "" or not st.session_state.date_text_nuit:
            st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")