import os

LEAGUE_ID = "00"
SEASON = "2025-26"
LAST_SEASON = "2024-25"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", f"data_{SEASON}.db")
DB_PATH_LAST_SEASON = os.path.join(BASE_DIR, "..", "data", f"data_{LAST_SEASON}.db")

CACHE_DIR_PATH = os.path.join(BASE_DIR, "..", "data", "cache")
BACKUP_DIR_PATH = os.path.join(BASE_DIR, "..", "data", "backups")
PLOT_GEN_WORKER_PATH = os.path.join(BASE_DIR, "..", "streamlit_interface", "plotting_worker.py")

FAILED_LOG_PATH = os.path.join(BASE_DIR, "..", "data", "failed_games.log")
OG_TEAM_LOGOS_PATH = os.path.join(BASE_DIR, "..", "data", "team_logos")
RESIZED_LOGOS_PATH = os.path.join(BASE_DIR, "..", "data", "team_logos_150")
ICON_PATH = os.path.join(BASE_DIR, "..", "data", "icon.png")

STREAMLIT_MAIN_PY_PATH = os.path.join(BASE_DIR, "..", "streamlit_interface", "streamlit_main.py")
STREAMLIT_PAGES_PATH = os.path.join(BASE_DIR, "..", "streamlit_interface", "streamlit_pages")

MAX_WORKERS = max(1, os.cpu_count() // 2)
MAX_BKG_WORKERS = max(1, os.cpu_count() // 3)

TRICODE2NAME = {'ATL': 'Hawks', 'BOS': 'Celtics', 'BKN': 'Nets', 'CHA': 'Hornets', 'CHI': 'Bulls', 'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors', 'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies', 'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks', 'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHX': 'Suns', 'POR': 'Trail Blazers', 'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards'}
NAME2TRICODE = {v: k for k, v in TRICODE2NAME.items()}

IMG_CHARGEMENT = 'data:image/png;base64,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'

TEAM_IDS = {
    'ATL': 1610612737,
    'BOS': 1610612738,
    'BKN': 1610612751,
    'CHA': 1610612766,
    'CHI': 1610612741,
    'CLE': 1610612739,
    'DAL': 1610612742,
    'DEN': 1610612743,
    'DET': 1610612765,
    'GSW': 1610612744,
    'HOU': 1610612745,
    'IND': 1610612754,
    'LAC': 1610612746,
    'LAL': 1610612747,
    'MEM': 1610612763,
    'MIA': 1610612748,
    'MIL': 1610612749,
    'MIN': 1610612750,
    'NOP': 1610612740,
    'NYK': 1610612752,
    'OKC': 1610612760,
    'ORL': 1610612753,
    'PHI': 1610612755,
    'PHX': 1610612756,
    'POR': 1610612757,
    'SAC': 1610612758,
    'SAS': 1610612759,
    'TOR': 1610612761,
    'UTA': 1610612762,
    'WAS': 1610612764
}

CHAR_MAP = {
    "ć": "c",
    "č": "c",
    "Č": "C",
    "é": "e",
    "í": "i",
    "Š": "S",
    "ö": "o",
    "ū": "u",
    "ņ": "n",
    "ģ": "g",
    "ô": "o",
    "ü": "u",
    "Đ": "D"
}

NICKNAMES = {'KD' : 'Kevin Durant',
             'KING' : 'LeBron James',
             'LBJ' : 'LeBron James',
             'BEARD' : 'James Harden',
             'BRODIE' : 'Russell Westbrook',
             'RUSS' : 'Russell Westbrook',
             'CHEF' : 'Stephen Curry',
             'STEPH' : 'Stephen Curry',
             'CP3' : 'Chris Paul',
             'AD' : 'Anthony Davis',
             'DAME' : 'Damian Lillard',
             'JOKER' : 'Nikola Jokic',
             'PROCESS' : 'Joel Embiid',
             'BOOK' : 'Devin Booker',
             'SPIDA' : 'Donovan Mitchell',
             'ANTMAN' : 'Anthony Edwards',
             'ANT' : 'Anthony Edwards',
             'WEMBY' : 'Victor Wembanyama',
             'ALIEN' : 'Victor Wembanyama',
             'HALI' : 'Tyrese Haliburton',
             'AR15' : 'Austin Reaves',
             'AR-15' : 'Austin Reaves',
             'FVV' : 'Fred VanVleet',
             'LUKA' : 'Luka Doncic'
             }