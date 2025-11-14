from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.dates as mdates
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from datetime import datetime
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
            imagebox = OffsetImage(img, zoom=0.2)
            ab = AnnotationBbox(imagebox, (date, TTFL), frameon = False)
            ax.add_artist(ab)
    
    if ymin == 0:
        ymin = -2
    if ymax == 0:
        ymax = 2
    if ymin != ymax:
        ax.set_ylim((ymin, ymax))

    ax.set_xticks(alldates)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate()
    
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