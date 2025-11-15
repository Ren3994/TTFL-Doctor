from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.dates as mdates
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from io import BytesIO
import base64
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import RESIZED_LOGOS_PATH, MAX_WORKERS, PLOT_GEN_WORKER_PATH

def generate_all_plots(df, date, parallelize=False, max_workers=MAX_WORKERS):

    if not parallelize:
        for i, row in df.iterrows():
            df.loc[i, 'plots'] = generate_plot_row(row, date)
        return df

def generate_plot_row(row, requested_date):

    joueur = row['Joueur']
    graph_dates = row['graph_dates']
    graph_opps = row['graph_opps']
    graph_TTFLs = row['graph_TTFLs']
    avgTTFL = float(row['TTFL'].split('±')[0])

    dates = [datetime.strptime(date, '%d/%m/%Y') for date in graph_dates.split(',')]
    requested_date = datetime.strptime(requested_date, '%d/%m/%Y')
    alldates = dates.copy()
    alldates.append(requested_date)
    njours = (alldates[-1] - alldates[0]).days
    opps = graph_opps.split(',')
    TTFLs = [int(stat) for stat in graph_TTFLs.split(',')]

    plt.style.use("seaborn-v0_8-dark")

    linew = 1.5
    alpha=0.7
    ymin = min(0, min(TTFLs) * 1.2)
    ymax = max(TTFLs) * 1.2

    fig, ax = plt.subplots(figsize=(6, 4))

    ax.plot(dates, TTFLs, linestyle='--', linewidth=linew, alpha=alpha, color='grey')
    ax.hlines(avgTTFL, alldates[0], alldates[-1], linestyle = '--', color = 'r', linewidth=linew, alpha=alpha)

    for date, opp, TTFL in zip(dates, opps, TTFLs):
        opp_sprite_path = os.path.join(RESIZED_LOGOS_PATH, f'{opp}.png')
        if os.path.exists(opp_sprite_path):
            img = mpimg.imread(opp_sprite_path)
            imagebox = OffsetImage(img, zoom = 0.23 - (njours * 0.08 / 173))
            ab = AnnotationBbox(imagebox, (date, TTFL), frameon = False)
            ax.add_artist(ab)
    
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
        rotation = None

    formatter = mdates.DateFormatter('%d %b.')
    ax.xaxis.set_major_formatter(formatter)

    if rotation:
        plt.xticks(rotation=rotation)
    else:
        fig.autofmt_xdate()

    secax = ax.secondary_yaxis('right')
    secax.tick_params(axis='both', labelsize=8)
    
    ax.set_title(joueur, fontsize=10)
    ax.set_ylabel("TTFL", fontsize=8, rotation=0, labelpad=15)
    ax.tick_params(axis='both', labelsize=8)
    ax.grid(axis='both', which='major', linewidth=linew, alpha=alpha-0.5, color='grey')

    # plt.show()

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=150)
    plt.close(fig)
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    return f"data:image/png;base64,{img_base64}"

if __name__ == '__main__':
    import pandas as pd
    data = {
    'Joueur': ['Player A', 'Player B', 'Player C'],
    'graph_dates': [
        '10/10/2025,12/10/2025,14/10/2025',
        '10/10/2025,12/10/2025',
        '12/10/2025,14/10/2025,18/10/2025,22/10/2025,25/10/2025,27/10/2025,29/10/2025,30/10/2025,01/11/2025,04/11/2025,07/04/2026'
    ],
    'graph_opps': [
        'LAL,BOS,DEN',
        'NYK,MIA',
        'SAS,OKC,UTA,POR,SAS,OKC,UTA,POR,SAS,OKC,UTA'
    ],
    'graph_TTFLs': [
        '32,28,40',
        '15,22',
        '45,38,50,41,45,38,50,41,45,38,50'
    ],
    'TTFL': ['33±5', '19±3', '43±4']
    }
    df = pd.DataFrame(data)
    # print(df)
    df = generate_all_plots(df, '25/10/2025')