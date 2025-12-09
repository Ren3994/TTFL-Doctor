from datetime import datetime, timedelta
import streamlit as st
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from streamlit_interface.resource_manager import conn_deepl, deepl_api_limit_reached
from streamlit_interface.JDP_utils import get_cached_rosters
from streamlit_interface.color_palette import get_palette
from update_manager.topTTFL_manager import get_top_TTFL
from data.sql_functions import run_sql_query
from misc.misc import FRENCHIES

def accentuate_pct(text: str) -> str:
    palette = get_palette('pct')
    threshold = 10

    def color_for_value(value: float) -> str:
        if value >= threshold:
            return palette['gold']
        if value <= -threshold:
            return palette['blue']
        if value == 0:
            return palette['text']

        magnitude = min(abs(value), threshold) / threshold

        if value > 0:
            r1, g1, b1 = palette['light_green']
            r2, g2, b2 = palette['bright_green']
        else:
            r1, g1, b1 = palette['light_red']
            r2, g2, b2 = palette['bright_red']

        r = int(r1 + (r2 - r1) * magnitude)
        g = int(g1 + (g2 - g1) * magnitude)
        b = int(b1 + (b2 - b1) * magnitude)

        return f"rgb({r},{g},{b})"

    def replacer(match):
        value = float(match.group(1))
        color = color_for_value(value)
        return f'<span style="color:{color}">{match.group(0)}</span>'

    return re.sub(r'([+-]?\d+(?:\.\d+)?)%', replacer, text)

@st.cache_data(show_spinner=False)
def get_joueurs_pas_dispo(_conn, date) :
    import pandas as pd
    
    try:
        date_dt = datetime.strptime(date, '%d/%m/%Y')
    except:
        return []
    
    limite = date_dt - timedelta(days=30)
    jdp, joueurs_pas_dispo = [], []

    if st.session_state.local_instance:
        jdp = (run_sql_query(_conn, table="joueurs_deja_pick")
               .rename(columns={'datePick' : 'Date du pick', 'joueur' : 'Joueur'}))
    else:
        if 'jdp_df' in st.session_state and not (st.session_state.jdp_df['Joueur'] == '').all():
            jdp = st.session_state.jdp_df[['Joueur', 'Date du pick']]

    if len(jdp) > 0:
        jdp = jdp[jdp['Date du pick'] != date].copy()
        jdp['Date du pick'] = pd.to_datetime(jdp['Date du pick'], errors='coerce', dayfirst=True)
        joueurs_pas_dispo = jdp[jdp['Date du pick'] > limite]['Joueur'].tolist()
            
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
    import pandas as pd
    
    try:
        date_dt = datetime.strptime(date, '%d/%m/%Y')
    except:
        return ''
    limite = date_dt + timedelta(days=30)
    n_games = 2

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
            result_str += '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp;' + p
    else:
        result_str = ''.join(['&nbsp;'] * 15) + f'Pas de jours avec moins de {n_games} matchs'
   
    return result_str

@st.cache_data(show_spinner=False)
def get_deadline(_conn, date):
    import pandas as pd

    try:
        date_dt = datetime.strptime(date, '%d/%m/%Y')
    except:
        return ''
    df = run_sql_query(_conn, table='schedule', select=['gameDate', 'gameDateTime'], filters=f"gameDate = '{date}'")
    df['gameDateTime'] = pd.to_datetime(df['gameDateTime']).dt.tz_localize(None)
    df_before_midnight = df[df['gameDateTime'] - date_dt < timedelta(days=1)]
    if len(df_before_midnight) > 0:
        deadline = df_before_midnight.loc[df_before_midnight['gameDateTime'].dt.hour.idxmin(), 'gameDateTime'].strftime('%Hh%M')
        result_str = '<b>' + ''.join(['&nbsp;'] * 33)  + f'Deadline : {deadline}</b>'
    else:
        result_str = ''
    
    return result_str

# @st.cache_data(show_spinner=False)
# def translate_df_column(col_to_translate):
#     deepl_client = conn_deepl()
#     try:
#         translated_col_obj = deepl_client.translate_text(col_to_translate, target_lang='FR')
#         translated_col = [t.text for t in translated_col_obj]
#     except:
#         translated_col = [f'Impossible de traduire : {t}' for t in col_to_translate]
#     return translated_col

def get_pick(date, team=False):
    pick = None
    picks = st.session_state.get('jdp_df', None)
    if picks is not None:
        picks = picks[picks['Joueur'] != '']
        if not picks.empty:
            series = picks.loc[picks['Date du pick'] == date, 'Joueur']
            pick = series.iloc[0] if not series.empty else None
    if not team:
        return pick
    pick_team = None
    if pick is not None:
        rosters = get_cached_rosters()
        pick_team = rosters[rosters['playerName'] == pick]['teamTricode'].iloc[0]
    return pick, pick_team

def get_idx_pick(df, date, colname):
    idx_pick = None
    pick = get_pick(date)
    if (pick is not None and pick != '' and 
        pick in df[colname].tolist()):
        idx_pick = df.index[df[colname] == pick] + 1

    return idx_pick

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
                          'Adversaire' : 'Score TTFL relatif des joueurs adverses de ce poste contre cette équipe quand tel joueur est blessé',
                          'Équipe' : 'Score TTFL relatif du joueur quand ce coéquipier est blessé',
                          'Statut' : 'Survoler pour voir les détails de la blessure'},
    image_tooltips={'Joueur' : 'plots'},
    show_index=True,
    zebra_stripes=True,
    hover_highlight=True,
    bold_headers=True,
    padding=10,
    center_table=True,
    color_tooltip_pct=True,
    highlight_index=None,
    col_header_labels={'TTFL' : '<span style="text-decoration:overline">TTFL</span>'},
    highlight_frenchies=True,
    # translate_cols = [],
    best_pick_allowed=False
):
    """Render a dark-mode HTML table with centered, custom tooltips."""

    palette = get_palette('table')

    hover_color = palette['hover']
    text_color = palette['text']
    header_text_color = palette['header_text']
    header_bkg_color = palette['header_bkg']
    zebra_even_color, zebra_odd_color = palette['even'], palette['odd']
    highlight_color = palette['pick']
    hover_highlight_color = palette['pick_hover']
    best_pick_color = palette['best_pick'] if best_pick_allowed else highlight_color
    hover_best_pick_color = palette['best_pick_hover'] if best_pick_allowed else hover_highlight_color
    tooltip_bkg_color = palette['tooltip_bkg']
    tooltip_text_color = palette['tooltip_text']
    injured_warning_color = palette['injured']
    injured_warning_color_hover = palette['injured_hover']

    css = f"""
    <style>
    .custom-table-dark {{
        border-collapse: collapse;
        text-align: center;
        width: 100%;
        margin: {'0 auto' if center_table else '0'};
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
        background-color: {tooltip_bkg_color};
        color: {tooltip_text_color};
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
    .custom-table-dark tr.best-pick-row {{
        background-color: {best_pick_color} !important;
    }}
    .custom-table-dark tr.best-pick-row:hover {{
        background-color: {hover_best_pick_color} !important;
    }}
    .custom-table-dark tr.highlight-row {{
        background-color: {highlight_color} !important;
    }}
    .custom-table-dark tr.highlight-row:hover {{
        background-color: {hover_highlight_color} !important;
    }}
    .custom-table-dark tr.injured-pick-row {{
        background-color: {injured_warning_color} !important;
    }}
    .custom-table-dark tr.injured-pick-row:hover {{
        background-color: {injured_warning_color_hover} !important;
    }}
    </style>
    """

    # Translate columns
    # limit_reached, _ = deepl_api_limit_reached()
    # if len(translate_cols) > 0 and not limit_reached:
    #     for col in translate_cols:
    #         empty_string_mask = df[col] == ''
    #         to_translate = df.loc[~empty_string_mask, col].tolist()
    #         translated_text = translate_df_column(to_translate)
    #         df.loc[~empty_string_mask, col] = translated_text

    # Build HTML table
    html = css + '<table class="custom-table-dark">'
    html += "<thead><tr>"
    if show_index:
        html += "<th>Rang</th>"

    for col in show_cols:
        col_label = col
        if col in col_header_labels:
            col_label = col_header_labels[col]
        if col in col_header_tooltips:
            html += (
                '<th>'
                f'<div class="tooltip"><span class="header-text">{col_label}<sup>?</sup></span>'
                f'<span class="tooltiptext">{col_header_tooltips[col]}</span></div>'
                '</th>'
            )
        else:
            html += f'<th><span class="header-text">{col_label}</span></th>'

    html += "</tr></thead><tbody>"

    for i, row in enumerate(df.itertuples(index=False), start=1):
        if highlight_index is not None and i == highlight_index:
            if 'Statut' in show_cols and getattr(row, 'Statut') != '':
                row_class = "injured-pick-row"
            else:
                row_class = "best-pick-row" if i == 1 else "highlight-row"
            html += f'<tr class="{row_class}">'
        else:
            html += "<tr>"
        if show_index:
            html += f"<td>{i}</td>"
        for col in show_cols:
            cell_value = getattr(row, col)

            if highlight_frenchies and (
                cell_value in FRENCHIES or str(cell_value)[:-1] in FRENCHIES):
                cell_value = f"{cell_value} &nbsp;🇫🇷"

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
                    f'<span class="tooltiptext">{accentuate_pct(tooltip_value) if color_tooltip_pct else tooltip_value}</span>'
                    "</div></td>"
                )
            else:
                html += f"<td>{cell_value}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

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
        update_session_state_df(st.session_state.date_text)
    except ValueError:
        st.session_state.text_parse_error = True

def prev_date():
    st.session_state.selected_date -= timedelta(days=1)
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
    update_session_state_df(st.session_state.date_text)

def next_date():
    st.session_state.selected_date += timedelta(days=1)
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
    update_session_state_df(st.session_state.date_text)

def update_session_state_df(date):
    topTTFL_df = cached_get_top_TTFL(date)
    st.session_state.topTTFL_df = topTTFL_df
    st.session_state.plot_calc_incr = 20
    st.session_state.plot_calc_start = 0
    st.session_state.plot_calc_stop = 30
    st.session_state.games_TBD = False
    st.session_state.text_parse_error = False
    clear_classement_vars()

@st.cache_data(show_spinner=False)
def apply_df_filters(_conn, date, plot_calc_start, plot_calc_stop, filter_JDP, filter_inj, selected_games):
    joueurs_pas_dispo = get_joueurs_pas_dispo(_conn, date)
    joueurs_blesses = get_joueurs_blesses(_conn)

    filtered_topTTFL_df = st.session_state.topTTFL_df.copy()
    if filter_JDP:
        filtered_topTTFL_df = filtered_topTTFL_df[~filtered_topTTFL_df['Joueur'].isin(joueurs_pas_dispo)]
    if filter_inj:
        filtered_topTTFL_df = filtered_topTTFL_df[~filtered_topTTFL_df['Joueur'].isin(joueurs_blesses)]
    
    if len(selected_games) > 0:
        selected_teams = []
        for matchup in selected_games:
            selected_teams.append(matchup.split('-')[0])
            selected_teams.append(matchup.split('-')[1])

        filtered_topTTFL_df = filtered_topTTFL_df[filtered_topTTFL_df['Lieu'].isin(selected_teams)]
    
    filtered_topTTFL_df = filtered_topTTFL_df.reset_index(drop=True)
    return filtered_topTTFL_df

def clear_classement_vars():
    for key in list(st.session_state.keys()):
        if key.startswith('classement_'):
            st.session_state.pop(key, None)