import streamlit as st
import sqlite3
import httpx
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@st.cache_resource(show_spinner=False, ttl=300)
def _create_supabase_client():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "unknown")
    key = st.secrets.get("SUPABASE_KEY", "unknown")
    return create_client(url, key)

class SafeSupabase:
    def __init__(self):
        self.client = _create_supabase_client()

    def _reset(self):
        _create_supabase_client.clear()
        self.client = _create_supabase_client()

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            max_retries = 3
            backoff = 0.5
            for attempt in range(max_retries):
                try:
                    attr = getattr(self.client, name)
                    if not callable(attr):
                        return attr
                    
                    return attr(*args, **kwargs)

                except httpx.HTTPError:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(backoff)
                    backoff *= 2
                    self._reset()

        return wrapper
    
def conn_supabase():
    return SafeSupabase()
    
@st.cache_data(ttl=300, show_spinner=False)
def fetch_supabase_users(_supabase):
    import pandas as pd
    data = _supabase.table("ttfl_doctor_user_picks").select("username").execute().data
    return pd.DataFrame(data)['username'].tolist()