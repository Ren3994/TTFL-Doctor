import multiprocessing
multiprocessing.set_start_method("spawn", force=True)

import pandas as pd
import traceback
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.plotting_utils import generate_all_plots

def run_worker():
    try:
        input_pickle = sys.argv[1]
        output_pickle = sys.argv[2]

        df = pd.read_pickle(input_pickle)
        date = sys.argv[3]

        generate_all_plots(df, date, parallelize=True)

        df.to_pickle(output_pickle, protocol=4)

    except Exception as e:
        print("ERROR: An exception occurred in worker.py", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    else :
        sys.exit(0)

if __name__ == "__main__":
    run_worker()
    