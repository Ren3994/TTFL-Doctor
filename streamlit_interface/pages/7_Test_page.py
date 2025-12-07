import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.cookies_manager import *
from streamlit_interface.sidebar import sidebar

sidebar(page='test')

cookies = get_manager()
cont = st.container(horizontal=True)
cont2 = st.container(horizontal=True)

st.write(cookies)
st.write(st.context.cookies)

cont.text_input('key', key='cookie_key', width=100)
cont.text_input('value', key='cookie_value', width=100)

if cont.button('rerun'):
    st.rerun()

if cont.button('Set'):
    set_cookie(st.session_state.cookie_key, st.session_state.cookie_value)

if cont.button('Del'):
    delete_cookie(st.session_state.cookie_key)

# if cont.button('save2supa + set token'):
    # token = generate_auth_token()
    # set_cookie('auth_token', token)
    # save_user_to_supabase(token)

if cont.button('check cookies for auth'):
    check_user_cookies_to_login()