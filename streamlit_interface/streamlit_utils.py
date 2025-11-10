import subprocess
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import STREAMLIT_MAIN_PY_PATH

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

def launch_GUI():
    subprocess.run([sys.executable, "-m", "streamlit", "run", STREAMLIT_MAIN_PY_PATH])

if __name__ == '__main__':
    launch_GUI()