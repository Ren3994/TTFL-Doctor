from datetime import datetime, timedelta
import streamlit as st
import secrets
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_supabase

def delete_auth_cookie():
    cookie_manager = st.session_state.cookie_manager
    auth_token = cookie_manager.get(cookie='ttfl-doctor.auth_token')
    if auth_token is not None:
        cookie_manager.delete('ttfl-doctor.auth_token')

def remember_user():
    cookie_manager = st.session_state.cookie_manager
    token = secrets.token_hex(32)
    if st.session_state.get('username', '') == 'admin':
        expiration_date = datetime.now() + timedelta(days = 365)
    else:
        expiration_date = datetime.now() + timedelta(days = 30)
    cookie_manager.set(cookie='ttfl-doctor.auth_token', val=token, expires_at=expiration_date)
    save_user_to_supabase(token)

def save_user_to_supabase(token):
    supabase = conn_supabase()
    username = st.session_state.get('username', '')
    if username != '':
        insert = (supabase.table("user_auth")
                            .insert({"username" : username,
                                    "auth_token" : token})
                            .execute())

def check_user_cookies_to_login():
    auto_login = False
    if st.session_state.get('username', '') == '':
        supabase = conn_supabase()
        cookie_manager = st.session_state.get('cookie_manager', None)
        if cookie_manager is not None:
            auth_token = cookie_manager.get(cookie='ttfl-doctor.auth_token')
            if auth_token is not None:
                try:
                    username = (supabase.table("user_auth")
                                        .select("username")
                                        .eq("auth_token", auth_token)
                                        .execute()).data[0]['username']
                    
                    st.session_state.username = username
                    auto_login = True
                except:
                    pass

    return auto_login