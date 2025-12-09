from datetime import datetime, timedelta
from rapidfuzz import fuzz, process
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_db, conn_supabase, fetch_supabase_users
from data.sql_functions import run_sql_query
from misc.misc import NICKNAMES

@st.cache_data(show_spinner=False)
def get_cached_game_dates_completed():
    gdc = run_sql_query(conn=conn_db(),
                        table='schedule', 
                        select='DISTINCT gameDate',
                        filters=['gameStatus = 3', 
                                "gameId LIKE '002%'"])
    return gdc

@st.cache_data(show_spinner=False)
def get_cached_scoresTTFL():
    scores = run_sql_query(
                    conn=conn_db(),
                    table="boxscores",
                    select=['playerName', 'gameDate', 'TTFL'],
                    filters='seconds > 0'
        )
    return scores

@st.cache_data(show_spinner=False)
def get_cached_avg_TTFL():
    avg_TTFL = run_sql_query(conn=conn_db(),
                                table='player_avg_TTFL', 
                                select=['playerName', 'avg_TTFL'])
    return avg_TTFL

@st.cache_data(show_spinner=False)
def get_cached_player_list():
    player_list = run_sql_query(conn=conn_db(), 
                                table='boxscores', 
                                select='DISTINCT playerName')
    return player_list['playerName'].tolist()

@st.cache_data(show_spinner=False)
def get_cached_pat():
    pat = run_sql_query(conn=conn_db(), table='player_avg_TTFL')
    return pat

@st.cache_data(show_spinner=False)
def get_cached_rosters():
    rosters = run_sql_query(conn=conn_db(), table='rosters')
    return rosters

class JoueursDejaPick():
    def __init__(self):
        self.conn = conn_db()
        self.supabase = conn_supabase()
        self.existing_users = []
        self._init_db()
            
    def _init_db(self):
        if st.session_state.local_instance:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS joueurs_deja_pick (
                    joueur TEXT,
                    datePick TEXT
                )
            """)
            self.conn.commit()
        else:
            self.existing_users = fetch_supabase_users(self.supabase)
            
    def loadJDP(self) -> pd.DataFrame:
        if st.session_state.local_instance:
            df = pd.read_sql_query("SELECT joueur, datePick FROM joueurs_deja_pick", self.conn)
        else:
            df = pd.DataFrame(columns=['joueur', 'datePick'])
            username_clean = re.sub(r'\W+', '', st.session_state.get('username', ''))
            if username_clean in self.existing_users:
                df = pd.DataFrame(list((self.supabase.table("ttfl_doctor_user_picks")
                                                .select("picks")
                                                .eq("username", username_clean)
                                                .execute()
                                        ).data[0]['picks'].items()), columns=['datePick', 'joueur'])
        return df
            
    def initJDP(self) -> pd.DataFrame:
        good_df = self.loadJDP()
        game_dates_completed = get_cached_game_dates_completed()

        new_dates = (datetime.now(ZoneInfo("Europe/Paris")).strftime('%d/%m/%Y'), 
            (datetime.now(ZoneInfo("Europe/Paris")) - timedelta(days=1)).strftime('%d/%m/%Y'))
        
        for new_date in new_dates:
            if new_date not in game_dates_completed['gameDate'].tolist():
                game_dates_completed.loc[len(game_dates_completed)] = new_date

        good_df = (game_dates_completed
                   .merge(good_df, 
                          left_on='gameDate', 
                          right_on='datePick', 
                          how='left')
                    [['joueur', 'gameDate']]
                    .rename(columns={'gameDate': 'datePick'})
                    .copy()
                )
        
        good_df['datePick'] = pd.to_datetime(good_df['datePick'], errors='coerce', dayfirst=True)
        good_df['dateRetour'] = good_df['datePick'] + timedelta(days=30)
        good_df['joueur'] = good_df['joueur'].fillna('')
        good_df = good_df.sort_values(by='datePick', ascending=False)
        
        good_df = self.dt_cols2str(good_df)
        good_df = self.completeCols(good_df)
        good_df = self.display_cols(good_df)
        
        return good_df
    
    def saveJDP(self, df:pd.DataFrame, save=True):

        df = self.db_cols(df)
        df = self.completeCols(df)

        df_db = df.copy()
        df_db = df_db[['joueur', 'datePick']]
        
        if save:
            if st.session_state.local_instance:
                df_db.to_sql("joueurs_deja_pick", self.conn, if_exists="replace", index=False)
            else:
                df_db = df_db[df_db['joueur'] != '']
                picks = dict(zip(df_db['datePick'], df_db['joueur']))
                if st.session_state.get('username', '') != '':
                    username_clean = re.sub(r'\W+', '', st.session_state.username)
                    if username_clean in self.existing_users:
                        update = (self.supabase.table("ttfl_doctor_user_picks")
                                                .update({"picks" : picks})
                                                .eq("username", username_clean)
                                                .execute())
                    else:
                        insert = (self.supabase.table("ttfl_doctor_user_picks")
                                                .insert({"username" : username_clean, 
                                                        "picks" : picks})
                                                .execute())
                        fetch_supabase_users.clear()
                        self.existing_users = fetch_supabase_users(self.supabase)

        df = self.display_cols(df)
        return df
    
    def completeCols(self, df:pd.DataFrame):
        scoresTTFL = get_cached_scoresTTFL()
        avg_TTFL = get_cached_avg_TTFL()
        
        for col in ['TTFL', 'avg_TTFL', 'gameDate']:
            if col in df.columns:
                df = df.drop(columns=col)

        df = clean_player_names(df, 'joueur', scoresTTFL['playerName'].unique().tolist())

        df_completed = df.copy()
        df_completed = df_completed.merge(
            scoresTTFL[['playerName', 'gameDate', 'TTFL']],
            left_on=['joueur', 'datePick'],
            right_on=['playerName', 'gameDate'],
            how='left'
        ).drop(columns=['playerName', 'gameDate'])

        df_completed = df_completed.merge(
            avg_TTFL[['playerName', 'avg_TTFL']],
            left_on=['joueur'],
            right_on=['playerName'],
            how='left'
        ).drop(columns=['playerName'])
        
        df_completed.loc[(df_completed['joueur'] != '') & 
                         (df_completed['TTFL'].isna()) & 
                         (df_completed['avg_TTFL'].notna()), ['TTFL']] = 0
        df_completed['TTFL'] = df_completed['TTFL'].apply(lambda x: int(x) if pd.notna(x) else '')

        df_completed[['TTFL', 'avg_TTFL']] = df_completed[['TTFL', 'avg_TTFL']].astype('string')
        df_completed.loc[df_completed['joueur'] == '', ['TTFL', 'avg_TTFL']] = ''

        return df_completed
    
    def display_cols(self, df:pd.DataFrame):
        df = df.rename(columns={
            'joueur': 'Joueur',
            'datePick': 'Date du pick',
            'TTFL': 'TTFL',
            'avg_TTFL': 'Moyenne TTFL',
            'dateRetour': 'Date de retour'
        })
        return df
    
    def db_cols(self, df:pd.DataFrame):
        df = df.rename(columns={
            'Joueur': 'joueur',
            'Date du pick': 'datePick',
            'TTFL': 'TTFL',
            'Moyenne TTFL': 'avg_TTFL',
            'Date de retour': 'dateRetour'
        })
        return df
    
    def dt_cols2str(self, df:pd.DataFrame):
        try:
            df['datePick'] = df['datePick'].dt.strftime('%d/%m/%Y')
        except:
            pass
        try:
            df['dateRetour'] = df['dateRetour'].dt.strftime('%d/%m/%Y')
        except:
            pass
        return df
    
    def str_cols2dt(self, df:pd.DataFrame):
        try:
            df['datePick'] = pd.to_datetime(df['datePick'], errors='coerce', dayfirst=True)
        except:
            pass
        try:
            df['dateRetour'] = pd.to_datetime(df['dateRetour'], errors='coerce', dayfirst=True)
        except:
            pass
        return df

def clean_player_names(df, colname, names_list=None):
    
    if names_list is None:
        names_list = get_cached_player_list()

    clean_names = []
    for name in df[colname] :
        if name == '':
            clean_names.append('')
        else:
            if name[-1] == '*':
                clean_names.append(f'{match_player(name, names_list)}*')
            else:
                clean_names.append(match_player(name, names_list))
    
    df[colname] = clean_names
    return df

def match_player(input_name, names_list=None, multi=False):

    matched_name = None

    if names_list is None:
        names_list = get_cached_player_list()

    if input_name in names_list:
        return [input_name] if multi else input_name
    
    input_upper = input_name.upper().replace('.', '')
    abbv_map, splits = generate_dicts(names_list)
    
    # Single match -> return it
    if input_upper in NICKNAMES:
        matched_name = NICKNAMES[input_upper]
    elif input_upper in abbv_map and len(abbv_map[input_upper]) == 1:
        matched_name = abbv_map[input_upper][0]
    elif input_upper in splits and len(splits[input_upper]) == 1:
        matched_name = splits[input_upper][0]
    
    # Multi match
    elif input_upper in abbv_map:
        if multi:
            matched_name = abbv_map[input_upper]
        else:
            pat = get_cached_pat()
            filtered_df = pat[pat['playerName'].isin(abbv_map[input_upper])]
            matched_name = filtered_df.loc[filtered_df['avg_TTFL'].idxmax(), 'playerName']
    
    elif input_upper in splits:
        if multi:
            matched_name = splits[input_upper]
        else:
            pat = get_cached_pat()
            filtered_df = pat[pat['playerName'].isin(splits[input_upper])]
            matched_name = filtered_df.loc[filtered_df['avg_TTFL'].idxmax(), 'playerName']

    elif matched_name is None:
        if multi:
            match_list = process.extract(input_name, names_list, scorer=fuzz.token_set_ratio, limit=10)
            matched_name = [name for name, _, _ in match_list]
        else:
            matched_name, _, _ = process.extractOne(input_name, names_list, scorer=fuzz.token_set_ratio)
    
    elif multi and isinstance(matched_name, str):
        matched_name = [matched_name]

    return matched_name

@st.cache_data(show_spinner=False)
def generate_dicts(names_list):
    abbreviations = {}
    splits = {}
    
    for name in names_list:
        parts = []
        for word in name.replace('.', '').split():
            parts.extend(word.split('-'))
        initials = ''.join(part[0] for part in parts).upper()

        for part in parts:
            if part.upper() in splits:
                splits[part.upper()].append(name)
            else:
                splits[part.upper()] = [name]
        
        if initials in abbreviations:
            abbreviations[initials].append(name)
        else :
            abbreviations[initials] = [name]

    return abbreviations, splits