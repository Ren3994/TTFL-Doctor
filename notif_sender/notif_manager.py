import streamlit as st
import polars as pl
import requests
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.streamlit_update_manager import cached_update_injury_report
from streamlit_interface.resource_manager import conn_supabase
from data.ttfl_data import scan_injuries

def get_user_pick_today(username='admin'):
    import pandas as pd
    from datetime import datetime
    from zoneinfo import ZoneInfo

    ajd = datetime.now(ZoneInfo("Europe/Paris"))
    ajd_str = ajd.strftime('%d/%m/%Y')

    conn = conn_supabase()
    admin_picks = pd.DataFrame(list((conn.table('ttfl_doctor_user_picks').select("picks")
                                            .eq("username", username)
                                            .execute()).data[0]['picks'].items()), columns=['datePick', 'joueur'])
    
    pick_ajd = admin_picks.loc[admin_picks['datePick'] == ajd_str, 'joueur']
    if pick_ajd.empty:
        return None
    return pick_ajd.iloc[0]

def check_pick_injured(pick, msg_if_ok=False):
    inj = (scan_injuries()
           .filter(pl.col('player_name') == pick)
           .with_columns(pl.format(
               '{} is {} (MàJ {} chez {}). Détails : {}',
               pl.col('player_name'),
               pl.col('simplified_status').str.to_lowercase(),
               pl.col('dt_fetch').dt.strftime('%d %b. à %Hh%M'),
               pl.col('source'),
               pl.col('details')
           ).alias('response'))
           .select('response')
           .collect()
           )
    
    if inj.is_empty():
        if msg_if_ok:
            return f'{pick} is fine.'
        return None
    
    return inj.item()

def send_update():
    cached_update_injury_report()
    pick = get_user_pick_today()
    response = check_pick_injured(pick, msg_if_ok=True)

    if response is None:
        return

    TOKEN = st.secrets.get('TELEGRAM_TOKEN')
    CHAT_ID = st.secrets.get('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={response}"

    requests.get(url).json()

if __name__ == '__main__':
    # pick = get_user_pick_today()
    # pick = 'Giannis Antetokounmpo'
    # print(check_pick_injured(pick))

    send_update()