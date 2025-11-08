from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.dates as mdates
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from datetime import datetime
import concurrent.futures
import streamlit as st
from io import BytesIO
import pandas as pd
import subprocess
import tempfile
import base64
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import RESIZED_LOGOS_PATH, MAX_WORKERS, PLOT_GEN_WORKER_PATH

def generate_all_plots(df, date, parallelize=False, max_workers=MAX_WORKERS):

    if not parallelize:
        for i, row in df.iterrows():
            df.loc[i, 'plots'] = generate_plot_row(row, date)
        return df

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
        results = list(
            pool.map(
                generate_plot_row,
                [row for _, row in df.iterrows()],
                [date] * len(df)
            )
        )

    df['plots'] = results
    return df

def add_plots_to_head(df, date, cutoff):

    head = df.iloc[:cutoff]
    head_with_plots = generate_all_plots(head, 
                                         date,
                                         parallelize=False)
        
    df.iloc[:cutoff] = head_with_plots

    return df

def add_plots_to_rest(df, date, cutoff):

    rest = df.iloc[cutoff:]

    with tempfile.NamedTemporaryFile(delete=False) as tmp_in, \
         tempfile.NamedTemporaryFile(delete=False) as tmp_out:
            
        input_path = tmp_in.name
        output_path = tmp_out.name
        rest.to_pickle(input_path)
        
        try :
            result = subprocess.run(
                [
                    "python", 
                    PLOT_GEN_WORKER_PATH, 
                    input_path, 
                    output_path, 
                    date
                ],
                capture_output=True, 
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print("Worker failed!")
            print("stdout:", e.stdout)
            print("stderr:", e.stderr)
                    
        rest_with_plots = pd.read_pickle(output_path)

        df.iloc[cutoff:] = rest_with_plots

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
    ax.plot(alldates, [avgTTFL for _ in alldates], linestyle = '--', color = 'r', linewidth=linew, alpha=alpha)

    for date, opp, TTFL in zip(dates, opps, TTFLs):
        opp_sprite_path = os.path.join(RESIZED_LOGOS_PATH, f'{opp}.png')
        if os.path.exists(opp_sprite_path):
            img = mpimg.imread(opp_sprite_path)
            imagebox = OffsetImage(img, zoom=0.2)
            ab = AnnotationBbox(imagebox, (date, TTFL), frameon = False)
            ax.add_artist(ab)

    # ax.vlines(requested_date, ymin, ymax, linestyles='--', color='k', linewidth=linew)
    
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