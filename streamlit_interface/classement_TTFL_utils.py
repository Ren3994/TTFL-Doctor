from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import base64
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.topTTFL_manager import get_top_TTFL
from data.sql_functions import run_sql_query
from misc.misc import TBD_LOGO_PATH

def accentuate_pct(text: str) -> str:
    def color_for_value(value: float) -> str:
        if value >= 10:
            return "#FFD700"  # gold
        if value <= -10:
            return "#1E90FF"  # blue
        if value == 0:
            return "gray"

        magnitude = min(abs(value), 10) / 10.0

        if value > 0:
            r1, g1, b1 = (182, 242, 182)  # #b6f2b6
            r2, g2, b2 = (0, 204, 102)    # #00cc66
        else:
            r1, g1, b1 = (246, 176, 176)  # #f6b0b0
            r2, g2, b2 = (255, 77, 77)    # #ff4d4d

        r = int(r1 + (r2 - r1) * magnitude)
        g = int(g1 + (g2 - g1) * magnitude)
        b = int(b1 + (b2 - b1) * magnitude)

        return f"rgb({r},{g},{b})"

    def replacer(match):
        value = float(match.group(1))
        color = color_for_value(value)
        return f'<span style="color:{color}">{match.group(0)}</span>'

    return re.sub(r'([+-]?\d+(?:\.\d+)?)%', replacer, text)

def get_joueurs_pas_dispo(conn, date) :

    date_dt = datetime.strptime(date, '%d/%m/%Y')
    limite = date_dt - timedelta(days=30)

    if st.session_state.local_instance:
        JDP = run_sql_query(conn, table="joueurs_deja_pick")
        JDP['datePick'] = pd.to_datetime(JDP['datePick'], errors='coerce', dayfirst=True)
        joueurs_pas_dispo = JDP[JDP['datePick'] > limite]['joueur'].tolist()
    else:
        if 'jdp_df' in st.session_state:
            JDP = st.session_state.jdp_df[['Joueur', 'Date du pick']].copy()
            JDP['Date du pick'] = pd.to_datetime(JDP['Date du pick'], errors='coerce', dayfirst=True)
            joueurs_pas_dispo = JDP[JDP['Date du pick'] > limite]['Joueur'].tolist()
        else:
            joueurs_pas_dispo=[]

    return joueurs_pas_dispo

@st.cache_data(show_spinner=False)
def get_joueurs_blesses(_conn):
    injury_report = run_sql_query(_conn,
                                  table="injury_report", 
                                  select='player_name', 
                                  filters="""simplified_status != 'Probable'""")
    
    return injury_report['player_name'].tolist()

@st.cache_data(show_spinner=False)
def get_low_game_count(_conn, date) :

    date_dt = datetime.strptime(date, '%d/%m/%Y')
    limite = date_dt + timedelta(days=30)
    n_games = 3

    games_per_day = run_sql_query(_conn, 
                                  table="schedule", 
                                  select=['gameDate', 
                                          'GROUP_CONCAT(homeTeam) AS homes', 
                                          'GROUP_CONCAT(awayTeam) AS aways', 
                                          'COUNT(*) AS n_games'], 
                                  filters='homeTeam IS NOT NULL', 
                                  group_by='gameDate')
    
    games_per_day['gameDate'] = pd.to_datetime(games_per_day['gameDate'], errors='coerce', dayfirst=True)
    games_per_day = games_per_day.sort_values(by='gameDate')
    
    mask_date = (games_per_day['gameDate'] >= date_dt) & (games_per_day['gameDate'] <= limite)
    games_in_mask = games_per_day[mask_date]
    
    low_games_count = games_in_mask[games_in_mask['n_games'] <= n_games].reset_index(drop=True)
    low_games_count['homes'] = low_games_count['homes'].str.split(',')
    low_games_count['aways'] = low_games_count['aways'].str.split(',')

    if len(low_games_count) > 0:
        parts = []
        for _, row in low_games_count.iterrows():
            date_str = pd.to_datetime(row['gameDate']).strftime('%d/%m')
            games = [f"{h}-{a}" for h, a in zip(row['homes'], row['aways'])]
            games_str = ", ".join(games)
            part = f"{date_str} : {row['n_games']} matchs ({games_str})"
            parts.append(part)
        result_str = ''.join(['&nbsp;'] * 20) + f'<b>Jours avec moins de {n_games} matchs :</b>'
        for p in parts:
            result_str += '<br>'
            result_str += '•&nbsp;&nbsp;&nbsp;&nbsp;' + p
    else:
        result_str = ''.join(['&nbsp;'] * 15) + f'Pas de jours avec moins de {n_games} matchs'

    return result_str

def df_to_html(
    df,
    show_cols=['Joueur', 'Lieu', 'Équipe', 'Adversaire', 'TTFL', 'Statut'],
    tooltips={
            'Statut' : 'details',
            'Équipe' : 'team_injury_status',
            'Adversaire' : 'opp_inj_status',
            'TTFL' : 'allrel'
            },
    col_header_tooltips = {'Joueur' : 'Survoler pour voir le graphe d\'évolution des scores TTFL',
                          'TTFL' : 'Toutes les équipes contre : scores TTFL relatifs des équipes adverses contre cette équipe' + \
                          '<br>Postes contre : scores TTFL relatifs des joueurs de ce poste contre cette équipe',
                          'Adversaire' : 'Score TTFL relatif des joueurs adverses de ce poste quand ils sont blessés',
                          'Équipe' : 'Score TTFL relatif du joueur quand ce coéquipier est blessé',
                          'Statut' : 'Survoler pour voir les détails de la blessure'},
    image_tooltips={'Joueur' : 'plots'},
    show_index=True,
    zebra_stripes=True,
    hover_highlight=True,
    hover_color="#1e2a3b",
    bold_headers=True,
    shadow_table=False,
    padding=10,
    text_color="#C5C5C5",
    header_text_color="#CAC8C8",
    center_table=True,
):
    """Render a dark-mode HTML table with centered, custom tooltips."""
    
    header_bkg_color = "#252b32"
    zebra_even_color, zebra_odd_color = "#222222", "#111111"
    shadow_color = "rgba(28,41,54,0.6)"

    css = f"""
    <style>
    .custom-table-dark {{
        border-collapse: collapse;
        text-align: center;
        width: 100%;
        margin: {'0 auto' if center_table else '0'};
        {'box-shadow: 2px 2px 8px ' + shadow_color + ';' if shadow_table else ''}
    }}
    .custom-table-dark th {{
        
        {'background-color: ' + header_bkg_color + ';' if bold_headers else ''}
        color: {header_text_color} !important;
        padding: {padding}px;
        text-align: center;
        border: none;
    }}
    .custom-table-dark th .header-text {{
        font-weight: bold;
    }}
    .custom-table-dark td {{
        padding: {padding}px;
        text-align: center;
        color: {text_color} !important;
        border: none;
        position: relative;
    }}
    {" .custom-table-dark tr:nth-child(even) { background-color: " + zebra_even_color + "; }" if zebra_stripes else ""}
    {" .custom-table-dark tr:nth-child(odd)  { background-color: " + zebra_odd_color + "; }" if zebra_stripes else ""}
    {(".custom-table-dark tr:hover { background-color: " + hover_color + " !important; }") if hover_highlight else ""}

    /* Custom tooltip styling */
    .tooltip {{
        position: relative;
        display: inline-block;
        cursor: help;
    }}
    .tooltip .tooltiptext {{
        visibility: hidden;
        width: max-content;
        max-width: 500px;
        background-color: #2b2b2b;
        color: #e0e0e0;
        text-align: center;
        font-weight: normal !important;
        border-radius: 6px;
        padding: 6px 10px;
        position: absolute;
        z-index: 1;
        bottom: 120%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.2s ease;
        font-size: 13px;
        box-shadow: 0 0 5px rgba(0,0,0,0.4);
        white-space: normal;
    }}
    .tooltip:hover .tooltiptext {{
        visibility: visible;
        opacity: 1;
    }}
    .tooltip .tooltiptext img {{
        max-width: 700;
        max-height: 466px;
        border-radius: 4px;
        z-index: 0;
    }}
    </style>
    """

    # Build HTML table
    html = css + '<table class="custom-table-dark">'
    html += "<thead><tr>"
    if show_index:
        html += "<th>Classement</th>"


    for col in show_cols:
        if col in col_header_tooltips:
            html += (
                '<th>'
                f'<div class="tooltip"><span class="header-text">{col}<sup>?</sup></span>'
                f'<span class="tooltiptext">{col_header_tooltips[col]}</span></div>'
                '</th>'
            )
        else:
            html += f'<th><span class="header-text">{col}</span></th>'

    html += "</tr></thead><tbody>"

    for i, row in enumerate(df.itertuples(index=False), start=1):
        html += "<tr>"
        if show_index:
            html += f"<td>{i}</td>"
        for col in show_cols:
            cell_value = getattr(row, col)

            if image_tooltips and col in image_tooltips:
                img_col = image_tooltips[col]
                img_src = getattr(row, img_col)
                html += (
                    f'<td><div class="tooltip">{cell_value}'
                    f'<span class="tooltiptext"><img src="{img_src}"></span>'
                    "</div></td>"
                )

            elif tooltips and col in tooltips:
                tooltip_value = getattr(row, tooltips[col])
                html += (
                    '<td><div class="tooltip">'
                    f"{cell_value}"
                    f'<span class="tooltiptext">{accentuate_pct(tooltip_value)}</span>'
                    "</div></td>"
                )
            else:
                html += f"<td>{cell_value}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

@st.cache_data(show_spinner=False)
def st_image_crisp(path, width=40):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except:
        with open(TBD_LOGO_PATH, "rb") as f:
            data=f.read()
    encoded = base64.b64encode(data).decode()
    return f"""<img src="data:image/png;base64,{encoded}" style="width:{width}px;height:auto;object-fit:contain;"/>"""

@st.cache_data(show_spinner=False)
def cached_get_top_TTFL(date):
    topTTFL_df = get_top_TTFL(date)
    return topTTFL_df

def on_text_change():
    """Parse text input into a date object."""
    text_value = st.session_state.date_text.strip()
    try:
        new_date = datetime.strptime(text_value, "%d/%m/%Y").date()
        st.session_state.selected_date = new_date
        st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
        st.session_state.text_parse_error = False
        update_session_state_df(st.session_state.selected_date.strftime("%d/%m/%Y"))
    except ValueError:
        st.session_state.text_parse_error = True

def prev_date():
    st.session_state.selected_date -= timedelta(days=1)
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
    update_session_state_df(st.session_state.selected_date.strftime("%d/%m/%Y"))

def next_date():
    st.session_state.selected_date += timedelta(days=1)
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
    update_session_state_df(st.session_state.selected_date.strftime("%d/%m/%Y"))

def update_session_state_df(date):
    topTTFL_df = cached_get_top_TTFL(date)
    st.session_state.topTTFL_df = topTTFL_df
    st.session_state.plot_calc_incr = 20
    st.session_state.plot_calc_start = 0
    st.session_state.plot_calc_stop = 30
    st.session_state.games_TBD = False
    st.session_state.gen_more_plots = False

@st.cache_data(show_spinner=False)
def apply_df_filters(_conn, date, plot_calc_start, plot_calc_stop, filter_JDP, filter_inj):
    joueurs_pas_dispo = get_joueurs_pas_dispo(_conn, date)
    joueurs_blesses = get_joueurs_blesses(_conn)

    filtered_topTTFL_df = st.session_state.topTTFL_df.copy()
    if filter_JDP:
        filtered_topTTFL_df = filtered_topTTFL_df[~filtered_topTTFL_df['Joueur'].isin(joueurs_pas_dispo)]
    if filter_inj:
        filtered_topTTFL_df = filtered_topTTFL_df[~filtered_topTTFL_df['Joueur'].isin(joueurs_blesses)]
    
    return filtered_topTTFL_df

custom_CSS = """
    <style>
    /* --- Title styling --- */
    .date-title {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: -3rem;
        margin-top: -3.8rem;
        margin-left: -2.5rem
    }
    </style>
    """

custom_mobile_CSS = """
        <style>
        /* Allow columns to shrink on small screens */
        @media (max-width: 600px) {
            .stColumn {
                flex: 1 !important;
                min-width: 0 !important;
            }
        }
        </style>
        """