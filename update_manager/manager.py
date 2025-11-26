from tqdm import tqdm
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_manager.connection_manager import check_internet_connection
from streamlit_interface.streamlit_utils import launch_GUI

def run_TTFL_Doctor():

    # if not check_internet_connection():
    #     tqdm.write('Pas de connection internet')
    #     return

    # --- Lance le GUI Streamlit
    launch_GUI()
    
# if __name__ == "__main__":
#     run_TTFL_Doctor()