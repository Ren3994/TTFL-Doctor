from datetime import datetime, timedelta
from html import escape
import streamlit as st
import polars as pl
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.ttfl_data import scan_injuries, scan_schedule, scan_table, latest_season
from streamlit_interface.JDP_utils import get_cached_rosters
from streamlit_interface.streamlit_utils import french_flag
from streamlit_interface.plotting_utils import build_plots
from streamlit_interface.color_palette import get_palette
from data.new_topTTFL_manager import get_top_TTFL as top2

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
    
    def wl_sequence_replacer(match):
        prefix = match.group(1)
        sequence = match.group(2)

        green = palette["bright_green"]
        red = palette["bright_red"]

        colored = ''.join(
            f'<span style="color:rgb({green[0]},{green[1]},{green[2]})">W</span>'
            if c == 'W'
            else f'<span style="color:rgb({red[0]},{red[1]},{red[2]})">L</span>'
            for c in sequence
        )

        return prefix + colored
    
    text = re.sub(r'([+-]?\d+(?:\.\d+)?)%', replacer, text)
    
    text = re.sub(
        r'(10 derniers matchs\s*:\s*)([WL]+)',
        wl_sequence_replacer,
        text
    )

    return text

def get_joueurs_pas_dispo(date) :
    import pandas as pd
    
    try:
        date_dt = datetime.strptime(date, '%d/%m/%Y')
    except:
        return []
    
    limite = date_dt - timedelta(days=30)
    jdp, joueurs_pas_dispo = [], []

    # if st.session_state.local_instance:
    #     jdp = (run_sql_query(_conn, table="joueurs_deja_pick")
    #            .rename(columns={'datePick' : 'Date du pick', 'joueur' : 'Joueur'}))
    # else:
    if 'jdp_df' in st.session_state and not (st.session_state.jdp_df['Joueur'] == '').all():
        jdp = st.session_state.jdp_df[['Joueur', 'Date du pick']]

    if len(jdp) > 0:
        jdp = jdp[jdp['Date du pick'] != date].copy()
        jdp['Date du pick'] = pd.to_datetime(jdp['Date du pick'], errors='coerce', dayfirst=True)
        joueurs_pas_dispo = jdp[jdp['Date du pick'] > limite]['Joueur'].tolist()
            
    return joueurs_pas_dispo

@st.cache_data(show_spinner=False)
def get_joueurs_blesses():
    injured = (scan_injuries()
                .filter(pl.col('simplified_status') != 'Probable')
                .select('player_name')
                .collect()
                .to_series()
                .to_list())
    return injured

@st.cache_data(show_spinner=False)
def get_low_game_count(date, delta=30, min_games=2) :
    import polars as pl

    date_dt = datetime.strptime(date, '%d/%m/%Y')
    low_game_count = (scan_schedule()
                      .filter([~pl.col('gameId').str.starts_with('003'),
                               pl.col('season') == latest_season(),
                               pl.col('homeTeam').is_not_null(),
                               pl.col('gameDate_ymd').is_between(date_dt, date_dt + timedelta(days=delta))])
                      .group_by('gameDate_ymd')
                      .agg(n_games=pl.len(), 
                           games=pl.concat_str([
                           pl.col('homeTeam'), pl.lit('-'), pl.col('awayTeam')
                          ])
                        )
                      .filter(pl.col('n_games') <= min_games)
                      .with_columns(
                          result=pl.format(
                              '{} : {} matchs ({})',
                              pl.col('gameDate_ymd').dt.strftime('%d/%m'),
                              pl.col('n_games'),
                              pl.col('games').list.join(', ')
                          )
                      )
                      .select('result')
                      .collect()
                )

    if not low_game_count.is_empty():
        result_str = (
            '&nbsp;' * 20
            + f'<b>Jours avec moins de {min_games} matchs :</b><br>'
            + ('<br>' + '&nbsp;' * 10 + '•&nbsp;&nbsp;&nbsp;&nbsp;').join(
                low_game_count['result'].to_list()
            )
        )
    else:
        result_str = ''.join(['&nbsp;'] * 15) + f'Pas de jours avec moins de {min_games} matchs'
   
    return result_str

@st.cache_data(show_spinner=False)
def get_deadline(date):
    import polars as pl
    from zoneinfo import ZoneInfo

    date_dt = datetime.strptime(date, '%d/%m/%Y').replace(tzinfo=ZoneInfo('Europe/Paris'), hour=12)

    b = (scan_table('schedule')
        .filter(pl.col('season') == latest_season())
        .with_columns(
            paris_time=pl.col('gameDateTimeUTC').str.to_datetime(time_zone="UTC")
            .dt.convert_time_zone('Europe/Paris')
        )
        .filter([
            pl.col('paris_time') >= date_dt, 
            pl.col('paris_time') < date_dt + timedelta(hours=12),
            ])
        .limit(1)
        .with_columns(hour=pl.col('paris_time').dt.strftime('%Hh%M'))
        
                    
        .select(['hour'])
        .collect()
        )

    if not b.is_empty():
        deadline = '<b>' + ''.join(['&nbsp;'] * 33)  + f'Deadline : {b.item()}</b>'
    else:
        deadline = ''

    return deadline

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
        match = rosters.loc[rosters['playerName'] == pick, 'teamTricode']
        pick_team = match.iloc[0] if not match.empty else None
    return pick, pick_team

def get_idx_pick(df, date, colname):
    idx_pick = None
    pick = get_pick(date)
    dfcopy = df.copy()
    dfcopy[colname] = dfcopy[colname].str.split(r' \((?:IST|B2B)\)').str[0]
    if (pick is not None and pick != '' and 
        pick in dfcopy[colname].tolist()):
        idx_pick = dfcopy.index[dfcopy[colname] == pick] + 1

    return idx_pick

def get_idx_from_pick(df, pick, colname):
    idx_pick = None
    dfcopy = df.copy()
    dfcopy[colname] = dfcopy[colname].str.split(r' \((?:IST|B2B)\)').str[0]
    if (pick is not None and pick != '' and 
        pick in dfcopy[colname].tolist()):
        idx_pick = dfcopy.index[dfcopy[colname] == pick] + 1
    
    return idx_pick

def df_to_html(
    df,
    show_cols=['Joueur', 'Lieu', 'Équipe', 'Adversaire', 'TTFL', 'Statut'],
    tooltips={
            'Statut' : 'details',
            'Équipe' : 'team_info',
            'Adversaire' : 'opp_info',
            'TTFL' : 'allrel'
            },
    col_header_tooltips = {'Joueur' : 'Survoler pour voir le graphe d\'évolution des scores TTFL',
                          'TTFL' : 'Toutes les équipes contre : scores TTFL relatifs des équipes adverses contre cette équipe' + \
                          '<br>Postes contre : scores TTFL relatifs des joueurs de ce poste contre cette équipe',
                          'Adversaire' : 'Score TTFL relatif des joueurs de ce poste contre l\'équipe du joueur blessé, pendant ses absences.',
                          'Équipe' : 'Score TTFL relatif du joueur quand ce coéquipier est blessé (N : nombre de matchs où le joueur a joué avec ce coéquipier blessé)',
                          'Statut' : 'Survoler pour voir les détails de la blessure'},
    plot_tooltips={'Joueur' : 'plots'},   # {column showing the plot : column holding its key}
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
    best_pick_allowed=False,
    js_assets=None
):
    """Render a dark-mode HTML table. Returns <style> + <table> + optional JS assets."""
 
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
    tooltip_bkg = palette['tooltip_bkg']
    tooltip_text = palette['tooltip_text']
    svg_plot_bkg = palette['svg_plot_bkg']
    svg_plot_text_color = palette['svg_plot_text_color']
    injured_warning_color = palette['injured']
    injured_warning_color_hover = palette['injured_hover']

    css = f"""
    <style>
    body {{
        margin: 10px;
        font-family: Source Sans, sans-serif;
        font-size: 15px;
    }}
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
 
    /* Tooltip triggers. The popup itself is the floating #tip (see plots.tooltip_assets);
       .tooltiptext spans only hold the text that plots.js copies into it. */
    .tooltip {{ position: relative; display: inline-block; cursor: help; }}
    .tooltip .tooltiptext {{ display: none; }}

    #tip {{
        display: none; position: fixed; z-index: 1000; pointer-events: none;
        width: max-content; max-width: 500px;
        background-color: {tooltip_bkg}; color: {tooltip_text};
        text-align: center; font-weight: normal; font-size: 13px; white-space: normal;
        border-radius: 6px; padding: 6px 10px; box-shadow: 0 0 5px rgba(0,0,0,0.4);
    }}
    #tip.plot {{
        max-width: none; padding: 4px;
        background-color: {svg_plot_bkg}; color: {svg_plot_text_color};
    }}
    #tip svg {{ display: block; width: 500px; height: auto; fill: currentColor; }}
 
    .custom-table-dark tr.best-pick-row {{ background-color: {best_pick_color} !important; }}
    .custom-table-dark tr.best-pick-row:hover {{ background-color: {hover_best_pick_color} !important; }}
    .custom-table-dark tr.highlight-row {{ background-color: {highlight_color} !important; }}
    .custom-table-dark tr.highlight-row:hover {{ background-color: {hover_highlight_color} !important; }}
    .custom-table-dark tr.injured-pick-row {{ background-color: {injured_warning_color} !important; }}
    .custom-table-dark tr.injured-pick-row:hover {{ background-color: {injured_warning_color_hover} !important; }}
    </style>
    """

    # Get indices of rows with max TTFL value
    if best_pick_allowed and 'TTFL' in df.columns:
        best_pick_indices = df.index[df['TTFL'] == df['TTFL'].max()].tolist()

    # Build HTML table
    html = css + '<table class="custom-table-dark">'
    html += "<thead><tr>"
    if show_index:
        html += "<th>Rang</th>"

    for col in show_cols:
        col_label = col_header_labels.get(col, col)
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
            elif best_pick_allowed and (i - 1) in best_pick_indices:
                row_class = "best-pick-row"
            else:
                row_class = "highlight-row"
            html += f'<tr class="{row_class}">'
        else:
            html += "<tr>"
        if show_index:
            html += f"<td>{i}</td>"
        for col in show_cols:
            cell_value = getattr(row, col)

            if highlight_frenchies:
                cell_value = french_flag(cell_value, html=True)

            if plot_tooltips and col in plot_tooltips:
                plot_key = escape(str(getattr(row, plot_tooltips[col])), quote=True)
                html += f'<td><div class="tooltip" data-plot="{plot_key}">{cell_value}</div></td>'

            elif tooltips and col in tooltips:
                tooltip_value = getattr(row, tooltips[col])
                if 'all time' in tooltip_value:
                    cell_value = str(cell_value[:4]) + '*' + str(cell_value[4:])
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
    html = html.replace("\n", "").replace("\r", "")

    if js_assets is not None:
        html += js_assets

    return html

def build_display_df_html(df, date, highlight_index):
    keys, assets = build_plots(df, date)
    df_with_plots = df.assign(plots=keys)
    html_df = df_to_html(df_with_plots, highlight_index=highlight_index, js_assets=assets)
    return html_df

@st.cache_data(show_spinner=False)
def cached_get_top_TTFL(date_ymd):
    # topTTFL_df = get_top_TTFL(date_ymd)
    topTTFL_df = top2(date_ymd)
    return topTTFL_df

def on_text_change():
    """Parse text input into a date object."""
    text_value = st.session_state.date_text.strip()
    try:
        new_date = datetime.strptime(text_value, "%d/%m/%Y").date()
        st.session_state.selected_date = new_date
        st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
        st.session_state.date_text_ymd = st.session_state.selected_date.strftime("%Y-%m-%d")
        update_session_state_df(st.session_state.date_text_ymd)
    except ValueError:
        st.session_state.text_parse_error = True

def prev_date():
    st.session_state.selected_date -= timedelta(days=1)
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
    st.session_state.date_text_ymd = st.session_state.selected_date.strftime("%Y-%m-%d")
    update_session_state_df(st.session_state.date_text_ymd)

def next_date():
    st.session_state.selected_date += timedelta(days=1)
    st.session_state.date_text = st.session_state.selected_date.strftime("%d/%m/%Y")
    st.session_state.date_text_ymd = st.session_state.selected_date.strftime("%Y-%m-%d")
    update_session_state_df(st.session_state.date_text_ymd)

def update_session_state_df(date_ymd):
    topTTFL_df = cached_get_top_TTFL(date_ymd)
    st.session_state.topTTFL_df = topTTFL_df
    st.session_state.plot_calc_incr = 20
    st.session_state.plot_calc_start = 0
    st.session_state.plot_calc_stop = 30
    st.session_state.games_TBD = False
    st.session_state.text_parse_error = False
    clear_classement_vars()

def apply_df_filters(df, date, plot_calc_start, plot_calc_stop, filter_JDP, filter_inj, 
                     selected_games, joueurs_pas_dispo):
    joueurs_blesses = get_joueurs_blesses()

    if filter_JDP:
        df = df[~df['Joueur'].str.split(r' \((?:IST|B2B)\)').str[0].isin(joueurs_pas_dispo)]
    if filter_inj:
        df = df[~df['Joueur'].str.split(r' \((?:IST|B2B)\)').str[0].isin(joueurs_blesses)]
    
    if len(selected_games) > 0:
        df['team'] = df['Équipe'].str.split(' ').str[0]
        selected_teams = []
        for matchup in selected_games:
            selected_teams.append(matchup.split('-')[0])
            selected_teams.append(matchup.split('-')[1])

        df = df[df['team'].isin(selected_teams)]
        df = df.drop(columns='team')
    
    df = df.reset_index(drop=True)
    return df

def clear_classement_vars():
    for key in list(st.session_state.keys()):
        if key.startswith('classement_'):
            st.session_state.pop(key, None)