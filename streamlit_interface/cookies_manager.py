from st_cookies_manager import CookieManager
from datetime import datetime, timedelta
import streamlit as st
import secrets
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_supabase

if 'cookies' not in st.session_state:
    st.session_state.cookies = CookieManager()

cookies = st.session_state.cookies

def get_manager():
    if not cookies.ready():
        st.stop()
    return cookies

def set_cookie(key, value, prefix='ttfl-doctor.'):
    m = get_manager()
    m[f'{prefix}{key}'] = value
    m.save()

def delete_cookie(key, prefix='ttfl-doctor.'):
    m = get_manager()
    full_key = f'{prefix}{key}'
    m._queue[full_key] = dict(
        value=None,
        expires_at=(datetime.now() - timedelta(days=1)).isoformat(),
        path="/"
    )
    m.save()

def remember_user():
    token = secrets.token_hex(32)
    set_cookie('auth_token', token)
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
        cookies = get_manager()
        if 'ttfl-doctor.auth_token' in cookies.keys():
            auth_token = cookies['ttfl-doctor.auth_token']
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