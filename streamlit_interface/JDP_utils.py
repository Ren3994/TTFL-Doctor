from rapidfuzz import fuzz, process
from datetime import timedelta
import streamlit as st
import pandas as pd
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_utils import conn_db, conn_supabase, fetch_supabase_users
from data.sql_functions import run_sql_query
from misc.misc import NICKNAMES

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
        game_dates_completed = run_sql_query(conn=self.conn,
                                             table='schedule', 
                                             select='DISTINCT gameDate',
                                             filters=['gameStatus = 3', 
                                                      "gameId LIKE '002%'"])
        
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
                        self.existing_users = fetch_supabase_users(self.supabase)

        df = self.display_cols(df)
        return df
    
    def completeCols(self, df:pd.DataFrame):
        scoresTTFL = run_sql_query(
                    conn=self.conn,
                    table="boxscores",
                    select=['playerName', 'gameDate', 'TTFL'],
                    filters='seconds > 0'
        )
        avg_TTFL = run_sql_query(conn=self.conn,
                                 table='player_avg_TTFL', 
                                 select=['playerName', 'avg_TTFL'])
        
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
        conn=conn_db()
        names_list=run_sql_query(conn, table='boxscores', select='DISTINCT playerName')['playerName'].tolist()

    clean_names = []
    for name in df[colname] :
        if name == '':
            clean_names.append('')
        else:
            clean_names.append(match_player(name, names_list))
    
    df[colname] = clean_names
    return df

def match_player(input_name, names_list=None):

    if names_list is None:
        conn=conn_db()
        names_list=run_sql_query(conn, table='boxscores', select='DISTINCT playerName')['playerName'].tolist()

    if input_name in names_list:
        return input_name
    
    input_upper = input_name.upper().replace('.', '')
    abbv_map, splits = generate_dicts(names_list)

    if input_upper in NICKNAMES:
        return NICKNAMES[input_upper]
    if input_upper in abbv_map and len(abbv_map[input_upper]) == 1:
        return abbv_map[input_upper][0]
    if input_upper in splits and len(splits[input_upper]) == 1:
        return splits[input_upper][0]
    if input_upper in abbv_map:
        conn = conn_db()
        pat = run_sql_query(conn=conn, table='player_avg_TTFL')
        filtered_df = pat[pat['playerName'].isin(abbv_map[input_upper])]
        return filtered_df.loc[filtered_df['avg_TTFL'].idxmax(), 'playerName']
    if input_upper in splits:
        conn = conn_db()
        pat = run_sql_query(conn=conn, table='player_avg_TTFL')
        filtered_df = pat[pat['playerName'].isin(splits[input_upper])]
        return filtered_df.loc[filtered_df['avg_TTFL'].idxmax(), 'playerName']
    
    match, _, _ = process.extractOne(input_name, names_list, scorer=fuzz.token_set_ratio)
    return match

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