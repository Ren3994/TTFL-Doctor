from datetime import datetime
import unicodedata
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import FAILED_LOG_PATH, CHAR_MAP

def log_failure(game_date, game_id, error):
    """Append a failed game ID and reason to a log file."""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(FAILED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] GameDate: {game_date} - GameID: {game_id} - Error: {error}\n")

def normalize_name(name: str) -> str:
    """
    Normalize player names:
    - Replace special characters via CHAR_MAP
    - Remove accents using Unicode normalization
    - Strip double spaces, trim, etc.
    """
    if not name:
        return name

    # Step 1: Apply manual mapping
    for src, target in CHAR_MAP.items():
        name = name.replace(src, target)

    # Step 2: Remove diacritics (accents)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(ch for ch in name if unicodedata.category(ch) != 'Mn')

    # Step 3: Cleanup
    name = " ".join(name.split())  # collapse multiple spaces
    return name.strip()

def normalize_position(pos: str) -> str:
    """
    Normalize NBA position strings into abbreviated forms.
    
    Examples:
        'Forward' -> 'F'
        'Center' -> 'C'
        'Guard' -> 'G'
        'Center-Forward' -> 'C-F'
        'Forward-Center' -> 'F-C'
    """
    pos = pos.strip()  # Remove leading/trailing whitespace
    mapping = {
        'Guard': 'G',
        'Forward': 'F',
        'Center': 'C',
    }
    
    if '-' in pos:
        parts = pos.split('-')
        parts = [mapping.get(p, p) for p in parts]  # map to abbreviations
        return '-'.join(parts)
    else:
        return mapping.get(pos, pos)
    
def height2cm(height_ft):
    try:
        height_cm = int(height_ft.split("-")[0]) * 30.48 + int(height_ft.split("-")[1]) * 2.54
    except:
        height_cm = None
    return height_cm