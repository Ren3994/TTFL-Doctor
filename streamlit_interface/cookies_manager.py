from datetime import datetime, timedelta
import streamlit as st
import secrets
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_supabase

def forget_user():
    cookie_manager = st.session_state.cookie_manager
    auth_token = st.session_state.auth_token
    
    try:
        cookie_manager.delete('ttfl-doctor.auth_token')
    except:
        pass

    try:
        supabase = conn_supabase()
        delete = (supabase.table("user_auth")
                          .delete()    
                          .eq("auth_token", auth_token)    
                          .execute())
    except:
        pass

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
        
def get_auth_token():
    if st.session_state.get('auth_token', None) is not None:
        return st.session_state.auth_token
    
    random_key = secrets.token_hex(10)
    all_cookies = st.session_state.cookie_manager.get_all(key=random_key)

    if len(all_cookies) > 0:
        st.session_state.cookies_retrieved = True

    if 'ttfl-doctor.auth_token' in all_cookies:
        return all_cookies['ttfl-doctor.auth_token']
    
    return None

def check_user_cookies_to_login():
    auto_login = False
    supabase = conn_supabase()
    try:
        username = (supabase.table("user_auth")
                            .select("username")
                            .eq("auth_token", st.session_state.auth_token)
                            .execute()).data[0]['username']
        
        st.session_state.username = username
        auto_login = True
    except:
        pass

    return auto_login