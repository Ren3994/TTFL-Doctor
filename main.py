from streamlit_interface.streamlit_utils import launch_GUI
from data.ttfl_stats import latest_season
from tqdm import tqdm

if __name__ == "__main__":

    tqdm.write(f"Saison {latest_season()}")
    launch_GUI()
    tqdm.write("Done.")