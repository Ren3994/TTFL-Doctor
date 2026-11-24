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
    try:
        admin_picks = pd.DataFrame(list((conn.table('ttfl_doctor_user_picks').select("picks")
                                                .eq("username", username)
                                                .execute()).data[0]['picks'].items()), columns=['datePick', 'joueur'])
        
        pick_ajd = admin_picks.loc[admin_picks['datePick'] == ajd_str, 'joueur']

        if pick_ajd.empty:
            return None
        
        pick = pick_ajd.iloc[0]
        return pick
    
    except:
        return 'SB error'

def send_telegram_message(message):
    TOKEN, CHAT_ID = os.environ.get('TELEGRAM_TOKEN', None), os.environ.get('TELEGRAM_CHAT_ID', None)

    if TOKEN is None or CHAT_ID is None:
        raise ValueError('Could not load values')

    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message},
        timeout=10,
    )
    r.raise_for_status()

def send_update(msg_if_ok=False):
    df_inj = update_injury_report(return_df=True)
    pick = get_user_pick_today()

    if pick is None:
        message = f'Aucun joueur n\'a été pick aujourd\'hui.'
    elif pick == 'SB error':
        message = 'Impossible de charger le pick de supabase'
    elif df_inj.empty:
        message = 'Impossible de télécharger les joueurs blessés '
    else:
        df_pick = df_inj.loc[df_inj['player_name'] == pick]

        if df_pick.empty:
            if not msg_if_ok:
                return
            first = df_inj.iloc[0]
            message = (f"{pick} n'est pas blessé (MàJ le {first['dt_fetch'].strftime('%d %b. à %Hh%M')} "
                        f"chez {first['source']}).")
        else:
            message = (df_pick['player_name'] + ' est ' + df_pick['simplified_status'].str.lower() + 
                        ' (MàJ le ' + df_pick['dt_fetch'].dt.strftime('%d %b. à %Hh%M') + ' chez ' + 
                        df_pick['source'] + ').\n\nDétails : ' + df_pick['details']).iloc[0]
    
    send_telegram_message(message)

if __name__ == '__main__':
    send_update(msg_if_ok=True)