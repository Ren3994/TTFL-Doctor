from supabase import create_client
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import polars as pl
import requests
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from update_manager.injury_report_manager import update_injury_report
# from data.ttfl_data import scan_injuries

def get_client():
    url, key = os.environ.get('SUPABASE_URL', None), os.environ.get('SUPABASE_KEY', None)

    if url is None or key is None:
        raise ValueError('Could not load .env file')
    
    return create_client(url, key)

def get_user_pick_today(username='admin'):

    ajd = datetime.now(ZoneInfo("Europe/Paris"))
    ajd_str = ajd.strftime('%d/%m/%Y')

    conn = get_client()
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
    # update_injury_report()
    pick = get_user_pick_today()
    response = check_pick_injured(pick, msg_if_ok=True)

    if response is None:
        return
    
    TOKEN, CHAT_ID = os.environ.get('TELEGRAM_TOKEN', None), os.environ.get('TELEGRAM_CHAT_ID', None)

    if TOKEN is None or CHAT_ID is None:
        raise ValueError('Could not load values')

    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": response},
        timeout=10,
    )
    r.raise_for_status()

if __name__ == '__main__':
    # send_update()
    # print('hi')
    # get_user_pick_today()
    get_client()