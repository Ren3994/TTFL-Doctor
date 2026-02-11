from update_manager.manager import run_TTFL_Doctor
from misc.misc import SEASON
from tqdm import tqdm

if __name__ == "__main__":

    tqdm.write(f"Saison {SEASON}")
    run_TTFL_Doctor()
    tqdm.write("Done.")