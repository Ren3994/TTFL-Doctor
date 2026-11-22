from supabase import create_client
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import requests
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.injury_report_manager import update_injury_report

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

def send_update(msg_if_ok=False):
    df_inj = update_injury_report(return_df=True)
    pick = get_user_pick_today()

    df_pick = df_inj.loc[df_inj['player_name'] == pick]

    if df_pick.empty:
        if not msg_if_ok:
            return
        response = f"{pick} n\'est pas blessé (MàJ le {df_inj.loc[0, 'dt_fetch'].strftime('%d %b. à %Hh%M')} chez {df_inj.loc[0, 'source']})."
    else:
        response = (df_pick['player_name'] + ' est ' + df_pick['simplified_status'].str.lower() + 
                    ' (MàJ le ' + df_pick['dt_fetch'].dt.strftime('%d %b. à %Hh%M') + ' chez ' + 
                    df_pick['source'] + ').\n\nDétails : ' + df_pick['details']).iloc[0]
    
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
    send_update(msg_if_ok=True)