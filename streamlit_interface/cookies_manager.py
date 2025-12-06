from st_cookies_manager import CookieManager
from datetime import datetime, timedelta
import streamlit as st
import secrets
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_supabase

cookies = CookieManager()
if not cookies.ready():
    st.stop()

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
    if st.session_state.get('username', '') == '':
        supabase = conn_supabase()
        cookies = get_manager()
        if 'ttfl-doctor.auth_token' in cookies.keys():
            auth_token = cookies['ttfl-doctor.auth_token']
            username = (supabase.table("user_auth")
                                .select("username")
                                .eq("auth_token", auth_token)
                                .execute()).data[0]['username']
        
            st.session_state.username = username










# @st.cache_resource(show_spinner=False)
# def get_cookies():
#     cookies = EncryptedCookieManager(
#         prefix="ttfl-doctor/st-cookies-manager/",
#         password=st.secrets.get("COOKIES_PWD", ""),
#     )
#     if not cookies.ready():
#         st.stop()
#     return cookies

# st.write("Current cookies:", cookies)
# value = st.text_input("New value for a cookie")
# if st.button("Change the cookie"):
#     cookies['a-cookie'] = value  # This will get saved on next rerun
#     if st.button("No really, change it now"):
#         cookies.save()  # Force saving the cookies now, without a rerun