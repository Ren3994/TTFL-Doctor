from datetime import datetime
from io import BytesIO
import streamlit as st
import base64
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import RESIZED_LOGOS_PATH

@st.cache_data(show_spinner=False)
def load_logo(path):
    import matplotlib.image as mpimg
    return mpimg.imread(path)

def generate_all_plots(row_nographs, date):
    row = row_nographs.copy()
    joueur = row['Joueur']
    graph_dates = row['graph_dates']
    graph_opps = row['graph_opps']
    graph_TTFLs = row['graph_TTFLs']
    graph_wins = row['graph_wins']
    avgTTFL = row['TTFL']
    row['plots'] = cached_generate_plot_row(date, 
                                            joueur, 
                                            graph_dates, 
                                            graph_opps, 
                                            graph_TTFLs, 
                                            graph_wins, 
                                            avgTTFL)
    return row
    
@st.cache_data(show_spinner=False)
def cached_generate_plot_row(requested_date,
                             joueur, 
                             graph_dates, 
                             graph_opps, 
                             graph_TTFLs, 
                             graph_wins, 
                             avgTTFL):
    
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    # import seaborn as sns

    joueur = joueur.split(' (')[0]
    dates = [datetime.strptime(date, '%d/%m/%Y') for date in graph_dates.split(',')]
    requested_date = datetime.strptime(requested_date, '%d/%m/%Y')
    alldates = dates.copy()
    alldates.append(requested_date)
    njours = (alldates[-1] - alldates[0]).days
    opps = graph_opps.split(',')
    avgTTFL = float(avgTTFL[:4])
    TTFLs = [int(stat) for stat in graph_TTFLs.split(',')]
    wins = [int(win) for win in graph_wins.split(',')]

    linew = 1.5
    alpha = 0.7
    ymin = min(0, min(TTFLs) * 1.2)
    ymax = max(TTFLs) * 1.1

    plt.rcParams['figure.autolayout'] = False
    plt.style.use("seaborn-v0_8-dark")
    # palette = sns.color_palette("deep")
    fig, ax = plt.subplots(figsize=(6, 4))
    # bkg_color = fig.get_facecolor()

    ax.plot(dates, TTFLs, linestyle='--', linewidth=linew, alpha=alpha, color='grey')
    ax.hlines(avgTTFL, alldates[0], alldates[-1], linestyle = '--', color = 'r', linewidth=linew, alpha=alpha)

    # ypos_list = []
    # colors_list = []
    
    # n = 0
    for date, opp, TTFL, win in zip(dates, opps, TTFLs, wins):
        opp_sprite_path = os.path.join(RESIZED_LOGOS_PATH, f'{opp}.png')
        img = load_logo(opp_sprite_path)

        imagebox = OffsetImage(img, zoom = 0.23 - (njours * 0.08 / 173))
        ab = AnnotationBbox(imagebox, (date, TTFL), frameon = False)
        ax.add_artist(ab)
        # ypos = 0.9 + (-1)**n * 0.04
        # ypos_list.append(ypos)
        # colors_list.append(palette[2] if win else palette[3])

        # ax.text(date, ypos, 'W' if win else 'L', color = bkg_color, ha='center', va='center', fontweight='bold', zorder=3, transform=ax.get_xaxis_transform())
        # n += 1
        # x_size = timedelta(days=0.7)   imshow instead of AnnotationBbox could be faster with many images ? No diff for ~20 images
        # y_size = (ymax - ymin) * 0.05
        # ax.imshow(img,extent=(date - x_size,date + x_size,TTFL - y_size,TTFL + y_size),aspect='auto',zorder=5)

    # ax.scatter(dates, ypos_list, s=350, c=colors_list, edgecolor='k', linewidth=1, zorder=2, transform=ax.get_xaxis_transform())
    
    if ymin == 0:
        ymin = -2
    if ymax == 0:
        ymax = 2
    if ymin != ymax:
        ax.set_ylim((ymin, ymax))

    if njours < 40:
        ax.set_xticks(alldates)
        rotation = 30 + njours * 3 / 4
    else:
        ax.vlines(alldates[-1], ymin, ymax, color = 'grey', linewidth=linew, alpha=alpha)
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        rotation = 30

    formatter = mdates.DateFormatter('%d %b.')
    ax.xaxis.set_major_formatter(formatter)

    for t in ax.get_xticklabels():
        t.set_rotation(rotation)

    secax = ax.secondary_yaxis('right')
    secax.tick_params(axis='both', labelsize=8)
    
    ax.set_title(joueur, fontsize=10)
    ax.set_ylabel("TTFL", fontsize=8, rotation=0, labelpad=15)
    ax.tick_params(axis='both', labelsize=8)
    ax.grid(axis='both', which='major', linewidth=linew, alpha=alpha-0.5, color='grey')

    # plt.show()
    # fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="jpg", dpi=120)
    plt.close(fig)
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    return f"data:image/png;base64,{img_base64}"

def interactive_plot(player, dates, data, show_lines, show_scatter, avgs, trends, player_teams, hover_info, hide_legend):
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
                                    [stat] * len(hover_info['date'])
                                )),
                                 hovertemplate = ( "          %{customdata[6]} : %{y}<br>"
                                                   "%{customdata[0]} vs. %{customdata[1]}<br>"
                                                   "  %{customdata[2]}-%{customdata[3]}-%{customdata[4]}" 
                                                   " en %{customdata[5]} min"
                                                   "<extra></extra>"
                                 )
                                )
                        )

        if stat in avgs:
            fig.add_trace(go.Scatter(x=dates, y=avgs[stat], name=f'Moyenne de {stat}', mode='lines'))

        if stat in trends:
            fig.add_trace(go.Scatter(x=dates, y=trends[stat], name=f'Courbe de tendance de {stat}', mode='lines'))

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
