import streamlit as st
import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.sidebar import sidebar

sidebar(page='test')

manager = st.session_state.get('cookie_manager', None)
if manager is not None:
    cookies = manager.get_all()
    st.write(cookies)