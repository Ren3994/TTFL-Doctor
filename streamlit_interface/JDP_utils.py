from supabase import create_client, Client
from datetime import datetime, timedelta
from rapidfuzz import fuzz, process
import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.sql_functions import run_sql_query
from misc.misc import NICKNAMES

class JoueursDejaPick():
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
            
    def _init_db(self):
        if st.session_state.local_instance:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS joueurs_deja_pick (
                        joueur TEXT,
                        datePick TEXT
                    )
                """)
                conn.commit()
        else:
            url = st.secrets.get("SUPABASE_URL", "unknown")
            key = st.secrets.get("SUPABASE_KEY", "unknown")
            self.supabase: Client = create_client(url, key)
            self.existing_users = pd.DataFrame(self.supabase.table("ttfl_doctor_user_picks")
                                                            .select("username")
                                                            .execute().data
                                                )['username'].tolist()
        
    def loadJDP(self) -> pd.DataFrame:
        if st.session_state.local_instance:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("SELECT joueur, datePick FROM joueurs_deja_pick", conn)
        else:
            df = pd.DataFrame(columns=['joueur', 'datePick'])
            if 'username' in st.session_state and st.session_state.username is not None:
                username_clean = re.sub(r'\W+', '', st.session_state.username)
                if username_clean in self.existing_users:
                    df = pd.DataFrame(list((self.supabase.table("ttfl_doctor_user_picks")
                                                    .select("picks")
                                                    .eq("username", username_clean)
                                                    .execute()
                                            ).data[0]['picks'].items()), columns=['joueur', 'datePick'])
                    st.write('data')
                    st.write((self.supabase.table("ttfl_doctor_user_picks")
                                                    .select("picks")
                                                    .eq("username", username_clean)
                                                    .execute()
                                            ).data)
                    st.write('data[0]')
                    st.write((self.supabase.table("ttfl_doctor_user_picks")
                                                    .select("picks")
                                                    .eq("username", username_clean)
                                                    .execute()
                                            ).data[0])
                    st.write('data[0]["picks"]')
                    st.write((self.supabase.table("ttfl_doctor_user_picks")
                                                    .select("picks")
                                                    .eq("username", username_clean)
                                                    .execute()
                                            ).data[0]['picks'])
                    st.write('data[0]["picks"].items()')
                    st.write((self.supabase.table("ttfl_doctor_user_picks")
                                                    .select("picks")
                                                    .eq("username", username_clean)
                                                    .execute()
                                            ).data[0]['picks'].items())
                    st.write('list')
                    st.write(list((self.supabase.table("ttfl_doctor_user_picks")
                                                    .select("picks")
                                                    .eq("username", username_clean)
                                                    .execute()
                                            ).data[0]['picks'].items()))
        return df
            
    def initJDP(self) -> pd.DataFrame:
        df = self.loadJDP()

        with sqlite3.connect(self.db_path) as conn:
            game_dates_completed = run_sql_query(conn, 
                                                    table='schedule', 
                                                    select='DISTINCT gameDate',
                                                    filters='gameStatus = 3',
                                                    order_by='gameDate DESC')
                
        completed_game_dates = pd.to_datetime(game_dates_completed['gameDate'], errors='coerce', dayfirst=True).sort_values(ascending=False)

        if df.empty:
            st.write('Empty')
            df['datePick'] = completed_game_dates.reset_index(drop=True)
            df['joueur'] = df['joueur'].fillna('')
            
        else:
            st.write('not empty')
            if len(df) < len(completed_game_dates):
                st.write('in')
                extra_rows = len(completed_game_dates) - len(df)
                df = pd.concat([pd.DataFrame(index=range(extra_rows), columns=df.columns), df], ignore_index=True)
        
        # st.write(df)
        df['datePick'] = completed_game_dates.reset_index(drop=True)
        df['dateRetour'] = df['datePick'] + timedelta(days=30)
        df['joueur'] = df['joueur'].fillna('')
        
        df = self.dt_cols2str(df)
        df = self.completeCols(df)
        df = self.display_cols(df)
        # st.write(df)
        
        return df
    
    def saveJDP(self, df:pd.DataFrame):

        df = self.db_cols(df)
        df = self.completeCols(df)

        df_db = df.copy()
        df_db = df_db[['joueur', 'datePick']]
        
        if st.session_state.local_instance:
            with sqlite3.connect(self.db_path) as conn:
                df_db.to_sql("joueurs_deja_pick", conn, if_exists="replace", index=False)
        else:
            df_db = df_db[df_db['joueur'] != '']
            picks = dict(zip(df_db['joueur'], df_db['datePick']))
            if 'username' in st.session_state and st.session_state.username is not None:
                username_clean = re.sub(r'\W+', '', st.session_state.username)
                if username_clean in self.existing_users:
                    update = (self.supabase.table("ttfl_doctor_user_picks")
                                            .update({"picks" : picks})
                                            .eq("username", username_clean)
                                            .execute()
                            )
                else:
                    insert = (self.supabase.table("ttfl_doctor_user_picks")
                                             .insert({"username" : username_clean, 
                                                     "picks" : picks})
                                             .execute()
                                )

        df = self.display_cols(df)
        return df
    
    def completeCols(self, df:pd.DataFrame):
        scoresTTFL = run_sql_query(
                    table="boxscores b",
                    select=['b.playerName', 'b.gameDate', 'b.TTFL, pat.avg_TTFL'],
                    filters='b.seconds > 0',
                    joins=[{
                        'table' : 'player_avg_TTFL pat',
                        'on' : 'b.playerName = pat.playerName',
                        'type' : 'LEFT'
                    }]
        )

        if 'TTFL' in df.columns:
            df = df.drop(columns=['TTFL', 'avg_TTFL'])

        df = clean_player_names(df, 'joueur', scoresTTFL['playerName'].unique().tolist())

        df_completed = df.copy()
        df_completed = df_completed.merge(
        scoresTTFL[['playerName', 'gameDate', 'TTFL', 'avg_TTFL']],
        left_on=['joueur', 'datePick'],
        right_on=['playerName', 'gameDate'],
        how='left'
        )
        
        df_completed['TTFL'] = df_completed['TTFL'].apply(lambda x: int(x) if pd.notna(x) else '')
        df_completed['avg_TTFL'] = df_completed['avg_TTFL'].fillna('')

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

def clean_player_names(df, colname, names_list):
    clean_names = []
    for name in df[colname] :
        if name == '':
            clean_names.append('')
        else:
            clean_names.append(match_player(name, names_list))
    
    df[colname] = clean_names
    return df

def match_player(input_name, names_list):

    if input_name in names_list:
        return input_name
    
    input_upper = input_name.upper().replace('.', '')
    abbv_map, splits = generate_dicts(names_list)

    if input_upper in NICKNAMES:
        return NICKNAMES[input_upper]
    if input_upper in abbv_map and len(abbv_map[input_upper]) == 1: ### Ajouter : si il y en a plusieurs, prendre celui avec la meilleure moyenne TTFL
        return abbv_map[input_upper][0]
    if input_upper in splits and len(splits[input_upper]) == 1:
        return splits[input_upper][0]
    
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