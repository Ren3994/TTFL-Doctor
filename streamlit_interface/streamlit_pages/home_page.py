from datetime import date
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

TITLE = 'Menu principal'
ORDER = 1

def run():
    st.title('Menu principal')

    if st.button(label=""):
        st.session_state.data_ready = True