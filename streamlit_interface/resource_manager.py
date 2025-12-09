from supabase import create_client
import streamlit as st
import pandas as pd
import sqlite3
import deepl
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import DB_PATH

@st.cache_resource(show_spinner=False, ttl=300)
def _create_supabase_client():
    url = st.secrets.get("SUPABASE_URL", "unknown")
    key = st.secrets.get("SUPABASE_KEY", "unknown")
    return create_client(url, key)

class SafeSupabase:
    def __init__(self):
        self.client = _create_supabase_client()

    def _reset(self):
        st.cache_resource.clear()
        self.client = _create_supabase_client()

    def __getattr__(self, name):
        attr = getattr(self.client, name)

        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            try:
                return attr(*args, **kwargs)
            except Exception:
                self._reset()
                attr2 = getattr(self.client, name)
                return attr2(*args, **kwargs)

        return wrapper
    
@st.cache_data(ttl=300, show_spinner=False)
def fetch_supabase_users(_supabase):
    data = _supabase.table("ttfl_doctor_user_picks").select("username").execute().data
    return pd.DataFrame(data)['username'].tolist()

def conn_supabase():
    return SafeSupabase()

@st.cache_resource(show_spinner=False)
def conn_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False) 
    return conn

@st.cache_resource(show_spinner=False)
def conn_deepl():
    api_key = st.secrets.get("DEEPL_API_KEY", "unknown")
    return deepl.DeepLClient(api_key)

@st.cache_data(show_spinner=False, ttl=60)
def deepl_api_limit_reached():
    deepl_client = conn_deepl()
    usage = deepl_client.get_usage()

    limit_reached = usage.any_limit_reached
    used_count = usage.character.count
    limit = usage.character.limit

    remaining = f'{used_count}/{limit}'

    return limit_reached, remaining