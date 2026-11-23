from datetime import datetime, date
from math import floor, ceil, log10
from html import escape
import streamlit as st
from pathlib import Path
import base64
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import RESIZED_LOGOS_PATH, JS_SVG_PLOTS_PATH

@st.cache_data(show_spinner=False)
def load_logo(path):
    import matplotlib.image as mpimg
    return mpimg.imread(path)

# def prep_svg_plots(df, date):
W, H = 500, 350                # canvas size of every plot (SVG viewBox)
MARGIN = dict(left=60, right=30, top=50, bottom=40)   # space around the plotting area
X_PAD = 22                     # horizontal padding inside the area so edge logos aren't cut
SHORT_RANGE_DAYS = 40          # below this many days: one x tick per game
LONG_RANGE_TICKS = 6           # otherwise: this many evenly spaced x ticks
N_Y_TICKS = 6                  # approximate number of horizontal grid lines

MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc."]

def _fmt_req(requested_date):
    """Anything date-like -> 'dd/mm/YYYY' (None = today)."""
    if requested_date is None:
        requested_date = datetime.now()
    if isinstance(requested_date, (datetime, date)):
        return requested_date.strftime("%d/%m/%Y")
    return str(requested_date)

def _s(v):
    """Cell -> clean string: '' for None/NaN, comma-join lists."""
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ",".join(map(str, v))
    try:
        if v != v:  # NaN
            return ""
    except Exception:
        pass
    return str(v)

def _label(d):
    """datetime -> '05 nov.'"""
    return f"{d.day:02d} {MONTHS[d.month - 1]}"
 
def _nice_y_ticks(lo, hi, n=N_Y_TICKS):
    """'Nice' tick values (1, 2, 5 x 10^k) between lo and hi."""
    raw = (hi - lo) / n
    mag = 10 ** floor(log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    ticks, v = [], ceil(lo / step) * step
    while v <= hi + 1e-9:
        ticks.append(round(v, 6))
        v += step
    return ticks
 
def _avg_from_cell(value):
    """'34.2 ...' -> 34.2 (first 4 chars, like the old matplotlib code). None if not a number."""
    try:
        return float(_s(value)[:4])
    except ValueError:
        return None

@st.cache_data(show_spinner=False)
def _compute_spec(joueur, req_str, graph_dates, graph_opps, graph_TTFLs,
                  graph_wins, graph_ishome, avg_ttfl):
    """Turn the raw comma-separated strings into a pixel-space spec."""
    title = joueur.split(" (")[0]
    dates_str = _s(graph_dates)
    if not dates_str:
        return {"w": W, "h": H, "title": title, "empty": True}
 
    # --- parse -----------------------------------------------------------------
    dates = [datetime.strptime(d, "%d/%m/%Y") for d in dates_str.split(",")]
    req = datetime.strptime(req_str, "%d/%m/%Y")
    opps = _s(graph_opps).split(",")
    ttfls = [int(float(x)) for x in _s(graph_TTFLs).split(",")]
    wins = [int(float(x)) for x in _s(graph_wins).split(",")]
    homes = [int(float(x)) for x in _s(graph_ishome).split(",")]
 
    start = dates[0]
    njours = (req - start).days          # width of the time axis in days
    span = max(njours, 1)                # avoid dividing by zero
 
    # --- y range (same rules as the old matplotlib version) ------------------------
    ymin = min(0, min(ttfls) * 1.2)
    ymax = max(ttfls) * 1.1
    if ymin == 0:
        ymin = -2
    if ymax == 0:
        ymax = 2
    if ymin == ymax:
        ymin, ymax = ymin - 1, ymax + 1
 
    # --- data -> pixels --------------------------------------------------------
    left, right = MARGIN["left"], W - MARGIN["right"]
    top, bottom = MARGIN["top"], H - MARGIN["bottom"]
 
    def x_of(d):
        days = (d - start).total_seconds() / 86400
        return left + X_PAD + days / span * ((right - left) - 2 * X_PAD)
 
    def y_of(v):
        return top + (ymax - v) / (ymax - ymin) * (bottom - top)
 
    r = lambda v: round(v, 1)  # 0.1 px is plenty and keeps the JSON small
 
    if njours < SHORT_RANGE_DAYS:
        tick_dates = dates + [req]
    else:
        tick_dates = [start + (req - start) * (i / (LONG_RANGE_TICKS - 1))
                      for i in range(LONG_RANGE_TICKS)]
 
    return {
        "w": W, "h": H,
        "title": title,
        "area": [left, top, right, bottom],
        "yTicks": [[r(y_of(t)), f"{t:g}"] for t in _nice_y_ticks(ymin, ymax)],
        "xTicks": [[r(x_of(d)), _label(d)] for d in tick_dates],
        # one entry per game: [x, y, win(0/1), home(0/1), opponent code]
        "games": [[r(x_of(d)), r(y_of(v)), w, h, o]
                  for d, v, w, h, o in zip(dates, ttfls, wins, homes, opps)],
        "reqX": r(x_of(req)),
        "avgY": r(y_of(avg_ttfl)) if avg_ttfl is not None else None,
        "logo": round(max(24, 46 - njours * 0.16) if njours < 173 else 32),
    }

@st.cache_data(show_spinner=False)
def build_plot_spec(joueur, requested_date, graph_dates, graph_opps, graph_TTFLs,
                    graph_wins, graph_ishome, avg_ttfl=None):
    """Spec for ONE player, cached on (joueur string, requested date).
 
    The cache lives as long as the Python process (so it survives Streamlit reruns).
    Only the key is checked: if the data for an already-cached (player, date)
    changes, call clear_plot_cache() or pass use_cache=False.
    """
    req_str = _fmt_req(requested_date)
    try:
        spec = _compute_spec(joueur, req_str, graph_dates, graph_opps, graph_TTFLs,
                             graph_wins, graph_ishome, avg_ttfl)
    except Exception:
        raise ValueError('Not this row')
    return spec

def build_plots(df, requested_date):
    """Build the plots for every row of `df`.
 
    Returns (keys, specs):
        keys   list with one key per row  -> store it in a column, e.g. df.assign(plots=keys)
        specs  {key: spec}                -> pass it to tooltip_assets()
 
    Rows with the same player/date share one spec, so duplicates cost nothing.
    Needs columns: Joueur, graph_dates, graph_opps, graph_TTFLs, graph_wins,
    graph_ishome, and `avg_col` (its first 4 chars give the red average line).
    """
    req_str = _fmt_req(requested_date)
    keys, specs = [], {}
    for row in df.itertuples(index=False):
        joueur = _s(getattr(row, "Joueur"))
        key = f"{joueur}|{req_str}"
        if key not in specs:
            specs[key] = build_plot_spec(
                joueur, req_str,
                getattr(row, "graph_dates"), getattr(row, "graph_opps"),
                getattr(row, "graph_TTFLs"), getattr(row, "graph_wins"),
                getattr(row, "graph_ishome"),
                avg_ttfl=_avg_from_cell(getattr(row, 'TTFL')),
            )
        keys.append(key)

    assets = tooltip_assets(specs)
    return keys, assets

@st.cache_data(show_spinner=False, persist='disk')
def _logo_symbol(opp):
    path = os.path.join(RESIZED_LOGOS_PATH, f"{opp}.png")
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        inner = f'<image href="data:image/png;base64,{b64}" width="100" height="100"/>'
    except OSError:  # missing file: grey disc with the team code
        inner = ('<circle cx="50" cy="50" r="45" fill="#888"/>'
                 f'<text x="50" y="60" text-anchor="middle" font-size="30" fill="#fff">{escape(opp)}</text>')
    return f'<symbol id="logo-{escape(opp, quote=True)}" viewBox="0 0 100 100">{inner}</symbol>'

@st.cache_data(show_spinner=False)
def tooltip_assets(specs):
    """Logo sprite + specs + plots.js."""

    def build_logo_sprite(opps):
        return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
                + "".join(_logo_symbol(o) for o in sorted(opps)) + "</svg>")
    
    opps = {g[4] for s in specs.values() for g in s.get("games", [])}
 
    # "</" inside a <script> could end it early, so escape it.
    data = json.dumps(specs, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    js = Path(JS_SVG_PLOTS_PATH).read_text(encoding="utf-8")   # re-read each time: edit plots.js and just rerun
 
    return (f"{build_logo_sprite(opps)}"
            '<div id="tip"></div>'
            f"<script>const PLOTS = {data};</script>"
            f"<script>{js}</script>")

# def letter_vlines(ax, letter, x, ymin, ymax, **kwargs):
#     """Same visual (10 stacked letters) in ONE artist instead of ten:
#     'H'/'A' = home/away, colour = win/loss, exactly as before."""
#     kwargs.setdefault('linespacing', 1.97)   # 19.7pt gaps == the old 0.8*ylim/9 data-space spacing
#     ax.text(x, (ymin + ymax) / 2, "\n".join([letter] * 10),
#             ha='center', va='center', multialignment='center', **kwargs)

# def plot_for_row(row, date):
#     return cached_generate_plot_row(date,
#                                     row['Joueur'],
#                                     row['graph_dates'],
#                                     row['graph_opps'],
#                                     row['graph_TTFLs'],
#                                     row['graph_wins'],
#                                     row['graph_ishome'],
#                                     row['TTFL'])

    
# @st.cache_data(show_spinner=False, persist="disk", max_entries=2000)
# def cached_generate_plot_row(requested_date,
#                              joueur, 
#                              graph_dates, 
#                              graph_opps, 
#                              graph_TTFLs, 
#                              graph_wins, 
#                              graph_ishome,
#                              avgTTFL):
    
#     from matplotlib.offsetbox import OffsetImage, AnnotationBbox
#     import matplotlib.pyplot as plt
#     import matplotlib.dates as mdates
#     # import seaborn as sns

#     plt.rcParams['figure.autolayout'] = False
#     plt.style.use("seaborn-v0_8-dark")
#     # palette = sns.color_palette("deep")
#     fig, ax = plt.subplots(figsize=(6, 4))

#     joueur = joueur.split(' (')[0]
#     if graph_dates == [''] or graph_dates == '':
#         ax.text(0.5, 0.5, "Pas de données disponibles", ha='center', va='center', fontsize=20)
#         ax.axis('off')
#     else:
#         dates = [datetime.strptime(date, '%d/%m/%Y') for date in graph_dates.split(',')]
#         requested_date = datetime.strptime(requested_date, '%d/%m/%Y')
#         alldates = dates.copy()
#         alldates.append(requested_date)
#         njours = (alldates[-1] - alldates[0]).days
#         opps = graph_opps.split(',')
#         TTFLs = [int(stat) for stat in graph_TTFLs.split(',')]
#         wins = [int(float(win)) for win in graph_wins.split(',')]
#         ishome = [int(float(home)) for home in graph_ishome.split(',')]
#         try:
#             avgTTFL = float(avgTTFL[:4])
#         except:
#             avgTTFL = None

#         linew = 1.5
#         alpha = 0.7
#         ymin = min(0, min(TTFLs) * 1.2)
#         ymax = max(TTFLs) * 1.1

#         # bkg_color = fig.get_facecolor()

#         ax.plot(dates, TTFLs, linestyle='--', linewidth=linew, alpha=alpha, color='grey')
#         ax.vlines(requested_date, ymin, ymax, ls='--', color='grey', alpha=alpha)

#         if avgTTFL is not None:
#             ax.hlines(avgTTFL, alldates[0], alldates[-1], linestyle = '--', color = 'r', linewidth=linew, alpha=0.4)

#         # ypos_list = []
#         # colors_list = []
        
#         # n = 0
#         for date, opp, TTFL, win in zip(dates, opps, TTFLs, wins):
#             opp_sprite_path = os.path.join(RESIZED_LOGOS_PATH, f'{opp}.png')
#             img = load_logo(opp_sprite_path)

#             imagebox = OffsetImage(img, zoom = 0.23 - (njours * 0.08 / 173))
#             ab = AnnotationBbox(imagebox, (date, TTFL), frameon = False)
#             ax.add_artist(ab)
#             # ypos = 0.9 + (-1)**n * 0.04
#             # ypos_list.append(ypos)
#             # colors_list.append(palette[2] if win else palette[3])

#             # ax.text(date, ypos, 'W' if win else 'L', color = bkg_color, ha='center', va='center', fontweight='bold', zorder=3, transform=ax.get_xaxis_transform())
#             # n += 1
#             # x_size = timedelta(days=0.7)   imshow instead of AnnotationBbox could be faster with many images ? No diff for ~20 images
#             # y_size = (ymax - ymin) * 0.05
#             # ax.imshow(img,extent=(date - x_size,date + x_size,TTFL - y_size,TTFL + y_size),aspect='auto',zorder=5)

#         # ax.scatter(dates, ypos_list, s=350, c=colors_list, edgecolor='k', linewidth=1, zorder=2, transform=ax.get_xaxis_transform())
        
#         if ymin == 0:
#             ymin = -2
#         if ymax == 0:
#             ymax = 2
#         if ymin != ymax:
#             ax.set_ylim((ymin, ymax))

#         if njours < 40:
#             ax.set_xticks(alldates)
#             rotation = 30 + njours * 3 / 4
#         else:
#             ax.vlines(alldates[-1], ymin, ymax, color = 'grey', linewidth=linew, alpha=alpha)
#             locator = mdates.AutoDateLocator()
#             ax.xaxis.set_major_locator(locator)
#             rotation = 30

#         formatter = mdates.DateFormatter('%d %b.')
#         ax.xaxis.set_major_formatter(formatter)

#         for t in ax.get_xticklabels():
#             t.set_rotation(rotation)

#         secax = ax.secondary_yaxis('right')
#         secax.tick_params(axis='both', labelsize=8)
        
#         ax.set_title(joueur, fontsize=10)
#         ax.set_ylabel("TTFL", fontsize=8, rotation=0, labelpad=15)
#         ax.tick_params(axis='both', labelsize=8)
#         ax.grid(axis='y', which='major', linewidth=linew, alpha=alpha-0.5, color='grey')
#         # ax.vlines(dates, ymin, ymax, colors=['g' if w == 1 else 'r' for w in wins], ls='--', lw=linew, alpha=alpha)
#         [letter_vlines(ax, 'H' if h else 'A', x, ymin, ymax, alpha=alpha-0.3, c='g' if w == 1 else 'r', zorder=0) 
#          for (x, w, h) in zip(dates, wins, ishome)]

#     # plt.show()
#     # fig.tight_layout()
#     buf = BytesIO()
#     fig.savefig(buf, format="jpg", dpi=120, pil_kwargs={"quality": 60, "optimize": True})
#     plt.close(fig)
#     img_base64 = base64.b64encode(buf.getvalue()).decode()

#     return f"data:image/jpeg;base64,{img_base64}"

def interactive_plot(player, dates, data, show_lines, show_scatter, avgs, trends, 
                     player_teams, hover_info, hide_legend, show_ttfl_details, ttfl_details):
    import plotly.graph_objects as go
    import plotly.express as px
    import numpy as np

    fig = go.Figure()
    fig.update(layout_title_text=player)
    mode = 'lines+markers' if show_lines else 'markers'

    for stat in data:
        if show_scatter:
            fig.add_trace(go.Scatter(x=dates, y=data[stat], name=stat, mode=mode,
                                 customdata = np.column_stack((
                                    hover_info['date'], hover_info['opp'], hover_info['pts'],
                                    hover_info['reb'], hover_info['ast'], hover_info['min'],
                                    [stat] * len(hover_info['date']),
                                    hover_info['FGM'], hover_info['FGA'],
                                    hover_info['FG3M'], hover_info['FG3A'],
                                    hover_info['FTM'], hover_info['FTA'],
                                    hover_info['win']
                                )),
                                 hovertemplate = ( "%{customdata[6]} : %{y} (%{customdata[13]})<br>"
                                                   "%{customdata[0]} vs. %{customdata[1]}<br>"
                                                   "  %{customdata[2]}-%{customdata[3]}-%{customdata[4]}" 
                                                   " en %{customdata[5]} min<br>"
                                                   "   %{customdata[7]}/%{customdata[8]} - "
                                                   "%{customdata[9]}/%{customdata[10]} - "
                                                   "%{customdata[11]}/%{customdata[12]}"
                                                   "<extra></extra>"
                                 )
                                )
                        )

        if stat in avgs:
            fig.add_trace(go.Scatter(x=dates, y=avgs[stat], name=f'Moyenne de {stat}', mode='lines'))

        if stat in trends:
            fig.add_trace(go.Scatter(x=dates, y=trends[stat], name=f'Courbe de tendance de {stat}', mode='lines'))

    if show_ttfl_details:
        for stat in ttfl_details:
            fig.add_trace(go.Bar(x=dates, y=ttfl_details[stat], name=stat))

    if len(player_teams) > 0:

        for date in player_teams['trade_dates']:
            fig.add_vline(x=date, line_color="red", line_dash="dash")
        
        base = player_teams['mid_dates'][0]
        span = player_teams['mid_dates'][-1] - base
        date_ratios = [((y - base) / (span)) * 0.95 for y in player_teams['mid_dates'][1:-1]]
        
        for date, team in zip(date_ratios, player_teams['teams']):
            logo_path = os.path.join(RESIZED_LOGOS_PATH, f'{team}.png')
            plotly_logo = base64.b64encode(open(logo_path, 'rb').read())
            fig.add_layout_image(dict(
                source = 'data:image/png;base64,{}'.format(plotly_logo.decode()),
                x=date,
                y=1,
                xref="paper",
                yref="paper",
                sizex=0.125,
                sizey=0.125,
                xanchor="center",
                yanchor="middle",
                layer="above"
            ))

        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="Transferts",
                                 line=dict(color="red", dash="dash")))

    fig.update_layout(hoverlabel=dict(align="left"), 
                      showlegend=not hide_legend,
                      colorway=px.colors.qualitative.Dark24)
    if show_ttfl_details:
        fig.update_layout(barmode='relative')
    
    return fig

def team_standings(df):
    import plotly.graph_objects as go
    import plotly.express as px
    fig = go.Figure()
    colors = px.colors.qualitative.Alphabet

    mode = 'lines'
    for i, (team, g) in enumerate(df.groupby('teamTricode')):
        fig.add_trace(go.Scatter(x=g['gameDate_ymd'], y=g['cum_wins'], name=team, mode=mode,
                                 line=dict(color=colors[i % len(colors)])))

    return fig

if __name__ == '__main__':
    a = ['CAP', 'BLT', 'CHZ', 'CHP', 'CHP', 'CHZ', 'BLT', 'CAP', 'HUS', 'CHS', 'PRO', 'DEF', 'BOM', 'PIT', 'CLR', 'PHW', 'SFW', 'GOS', 'SFW', 'PHW', 'BAL', 'JET', 'FTW', 'FTW', 'MNL', 'MNL', 'ROC', 'CIN', 'KCK', 'ROC', 'CIN', 'KCK', 'TCB', 'MIH', 'STL', 'TCB', 'MIH', 'STL', 'DN', 'INO', 'SHE', 'WAT', 'AND', 'SYR', 'PHL', 'SYR', 'SEA', 'SEA', 'SDR', 'SDR', 'BUF', 'SDC', 'SDC', 'BUF', 'NOJ', 'UTH', 'NOJ', 'SAN', 'NYN', 'NJN', 'NYN', 'NJN', 'NOH', 'NOK', 'NOH', 'NOK', 'VAN', 'VAN', 'CHH']
    # from matplotlib import pyplot as plt
    # import matplotlib
    # matplotlib.use("TkAgg")

    # for team in a:

    #     fig, ax = plt.subplots(figsize=(4, 2))

    #     ax.text(0, 0, team, fontsize=75)
    #     ax.set_xlim((-0.01, 0.14))
    #     ax.set_ylim((-0.2, 0.5))
    #     plt.axis('off')

    #     # plt.show()
    #     fig.savefig(f'{team}.png')
    #     plt.close()


    # import pandas as pd
    # data = {
    # 'Joueur': ['Player A', 'Player B', 'Player C'],
    # 'graph_dates': [
    #     '10/10/2025,12/10/2025,14/10/2025',
    #     '10/10/2025,12/10/2025',
    #     '12/10/2025,14/10/2025,18/10/2025,22/10/2025,25/10/2025,27/10/2025,29/10/2025,30/10/2025,01/11/2025,04/11/2025,07/04/2026'
    # ],
    # 'graph_opps': [
    #     'LAL,BOS,DEN',
    #     'NYK,MIA',
    #     'SAS,OKC,UTA,POR,SAS,OKC,UTA,POR,SAS,OKC,UTA'
    # ],
    # 'graph_TTFLs': [
    #     '32,28,40',
    #     '15,22',
    #     '45,38,50,41,45,38,50,41,45,38,50'
    # ],
    # 'graph_wins' : [
    #     '1,1,0',
    #     '0,0',
    #     '0,1,1,1,0,1,1,0,1,1,1'
    # ],
    # 'TTFL': ['33±5', '19±3', '43±4']
    # }
    # df = pd.DataFrame(data)
    # # print(df)
    # df = generate_all_plots(df, '25/10/2025')
