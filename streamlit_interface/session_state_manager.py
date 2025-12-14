from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.classement_TTFL_utils import update_session_state_df
from streamlit_interface.streamlit_utils import is_mobile_layout
from streamlit_interface.cookies_manager import get_auth_token
from streamlit_interface.JDP_utils import JoueursDejaPick

def init_session_state(page, arg=None):
    import extra_streamlit_components as stx

    if 'local_instance' not in st.session_state:
        env = st.secrets.get("environment", "unknown")
        if env == 'local':
            st.session_state.local_instance = True
        elif env == 'cloud':
            st.session_state.local_instance = False

    if 'mobile_layout' not in st.session_state:
        st.session_state.mobile_layout = is_mobile_layout()
    if 'cookie_manager' not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
        st.session_state.cookies_retrieved = False
    
    if not st.session_state.cookies_retrieved:
        st.session_state.auth_token = get_auth_token()

    st.session_state.dark_mode = True if st.context.theme.type == 'dark' else False
    st.session_state.byteam = st.session_state.get('byteam', False)
    st.session_state.username = st.session_state.get('username', '')

    if page == 'classement':
        st.session_state.selected_date = st.session_state.get("selected_date", 
                                                              datetime.now(ZoneInfo("Europe/Paris")))

        st.session_state.date_text = st.session_state.get("date_text",
            st.session_state.selected_date.strftime("%d/%m/%Y"))
        
        st.session_state.date_text_ymd = st.session_state.get("date_text_ymd",
            st.session_state.selected_date.strftime("%Y-%m-%d"))

        if st.session_state.date_text == "" or not st.session_state.date_text:
            st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")

        if st.session_state.date_text_ymd == "" or not st.session_state.date_text_ymd:
            st.session_state.date_text_ymd = st.session_state.selected_date.strftime("%Y-%m-%d")

        if "topTTFL_df" not in st.session_state:
            update_session_state_df(st.session_state.date_text_ymd)

        if 'games_TBD' not in st.session_state:
            st.session_state.games_TBD = False
        
        if 'calculated' not in st.session_state:
            st.session_state.calculated = []
        
        if 'bool_translate' not in st.session_state:
            st.session_state.bool_translate = False

    if page in ['classement', 'JDP', 'top_nuit', 'live_scores']:
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
                                                      (datetime.now(ZoneInfo("Europe/Paris")) - 
                                                       timedelta(days=1)))

        st.session_state.date_text_nuit = st.session_state.get("date_text_nuit",
                    st.session_state.selected_date_nuit.strftime("%d/%m/%Y"))

        if st.session_state.date_text_nuit == "" or not st.session_state.date_text_nuit:
            st.session_state.date_text_nuit = st.session_state.selected_date_nuit.strftime("%d/%m/%Y")
        
        if 'show_my_pick' not in st.session_state:
            st.session_state.show_my_pick = False
    
    if page == 'live_scores':
        if 'live_scores_update_timestamp' not in st.session_state:
            st.session_state.live_scores_update_timestamp = arg
        else:
            if st.session_state.live_scores_update_timestamp != arg:
                st.session_state.live_scores_update_timestamp = arg
        
        if 'progress_pct' not in st.session_state:
            st.session_state.progress_pct = 0

        if 'live_scores_by_team' not in st.session_state:
            st.session_state.live_scores_by_team = False

    if page == 'stats_joueurs':
        if 'player_stats_matched' not in st.session_state:
            st.session_state.player_stats_matched = ''
        if 'search_player_indiv_stats' not in st.session_state:
            st.session_state.search_player_indiv_stats = ''
        if 'compare_players' not in st.session_state:
            st.session_state.compare_players = []
        if 'player_stats' not in st.session_state:
            st.session_state.player_stats = None
        