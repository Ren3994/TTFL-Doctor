
from datetime import datetime, date
import streamlit as st
from tqdm import tqdm
import requests

@st.cache_data(ttl=60, show_spinner=False)
def get_proxy_stats(api_key, price_per_gb=4, breakline='\n'):

    if api_key is None:
        return 'No API key'
    
    HEADERS = {"Authorization": api_key}

    try:
        r = requests.get('https://api.decodo.com/v2/subscriptions', headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()[0]
    except (requests.RequestException, ValueError) as e:
        tqdm.write(f'Error while fetching proxy usage stats : {e}')
        return 'Proxy stats unavailable'
    
    limit_gb = float(data['traffic_limit'])
    used_gb = float(data['traffic'])
    pct = 100 * used_gb / limit_gb if limit_gb else 0
    valid_until = datetime.strptime(data['valid_until'], '%Y-%m-%d')    
    days_left = (valid_until.date() - date.today()).days

    return (f'{used_gb:.1f}/{limit_gb:.1f} GB ({pct:.0f}%)' + breakline +
            f'{used_gb * price_per_gb:.1f}/{limit_gb * price_per_gb:.0f} $' + breakline +
            f'Limite : {valid_until.strftime('%b. %d')} ({days_left} days left)')