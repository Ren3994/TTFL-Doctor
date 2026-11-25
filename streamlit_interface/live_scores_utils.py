from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import polars as pl
import time
import sys
import re
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.JDP_utils import clean_player_names, get_cached_avg_TTFL
from fetchers.net_utils import NBA_API, NBA_CDN, retry_call
from data.ttfl_stats import scan_schedule, latest_season

# --------------------------------------------------------------------------- #
# Retry policies                                                              #
# --------------------------------------------------------------------------- #
# This function is cached for 15s and a user is waiting on it, so the budget is small:
# worst case ~15-20s instead of 3 x 30s (nba_api's default timeout is 30s per request).
LIVE_TIMEOUT = 5
LIVE_POLICY = NBA_CDN.replace(max_attempts=3, wait_base=1, wait_max=4, max_total_time=15)
# ScoreboardV2 lives on stats.nba.com, which is slower and throttles harder.
STATS_POLICY = NBA_API.replace(max_attempts=3, wait_base=3, wait_max=10, max_total_time=40)


# --------------------------------------------------------------------------- #
# Fetching: the only place that talks to the network                          #
# --------------------------------------------------------------------------- #
def _fetch_scoreboard():
    """Today's live scoreboard (list of game dicts). Raises RetryFailed if it can't be
    had: without it there is nothing to show (and st.cache_data does not cache
    exceptions, so the next rerun simply tries again)."""
    from nba_api.live.nba.endpoints import scoreboard
    return retry_call(
        lambda: scoreboard.ScoreBoard(timeout=LIVE_TIMEOUT).games.get_dict(),
        label="scoreboard live", policy=LIVE_POLICY,
        validate=lambda games: isinstance(games, list),      # [] is fine (no games today)
        raise_on_failure=True)


def _fetch_boxscore(game_id):
    """One game's live boxscore dict, or None if it still fails after the retries
    (the caller skips that game; the rest of the page is unaffected)."""
    from nba_api.live.nba.endpoints import boxscore
    return retry_call(
        lambda: boxscore.BoxScore(game_id=game_id, timeout=LIVE_TIMEOUT).get_dict().get('game'),
        label=f"boxscore live {game_id}", policy=LIVE_POLICY,
        validate=lambda g: isinstance(g, dict) and 'homeTeam' in g and 'awayTeam' in g)


def _fetch_next_day_games():
    date = datetime.now(ZoneInfo("America/Los_Angeles")) + timedelta(hours=2)

    games = (scan_schedule()
            .filter(
                pl.col('season') == latest_season(),
                pl.col('gameDate') == date.strftime('%d/%m/%Y')
                )
            .with_columns(
                gameTimeParis=pl.col('gameDateTimeUTC').str.to_datetime(time_zone="UTC")
                .dt.convert_time_zone('Europe/Paris').dt.strftime('%d %b. à %Hh%M')
            )
            .sort('gameDate_ymd')
            .select(['homeTeam', 'awayTeam', 'gameTimeParis'])
            .collect()
            .to_dicts()
            )
    return games

# --------------------------------------------------------------------------- #
# Game parsing for live games                                                 #
# --------------------------------------------------------------------------- #
COLUMNS = ('Joueur', 'OGJoueur', 'Equipe', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb',
           'Blk', 'Stl', 'Tov', 'Min', 'FG', 'FGm', 'FGa', 'FG3', 'FG3m', 'FG3a',
           'FT', 'FTm', 'FTa', 'Pm', 'PF', 'TTFL')

_MINUTES_RE = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)(?:\.\d+)?S)?')
_TTFL_LABEL = '<span style="text-decoration:overline">TTFL</span> : '


def _iso_minutes(iso):
    """'PT34M12.00S' -> '34:12' (fractional seconds truncated, like int(total_seconds()))."""
    m = _MINUTES_RE.fullmatch(iso)
    if m is None:
        raise ValueError(f'Unexpected minutes format: {iso!r}')
    h, mn, s = (int(g or 0) for g in m.groups())
    return '{:02d}:{:02d}'.format(*divmod(3600 * h + 60 * mn + s, 60))


def _pct(made, att):
    """Shooting percentage string: '' if no attempts, '100%' if perfect."""
    if att == 0:
        return ''
    if made == att:
        return '100%'
    return f'{round(100 * made / att, 1)}%'


def _perf(ttfl, avg):
    """'+12.5%' / '-3.0%' vs. the season average; '0' when the average is 0."""
    if avg == 0:
        return '0'
    return f'{100 * (ttfl - avg) / avg:+.1f}%'


def _player_row(player, team, live):
    """One boxscore row (dict keyed by COLUMNS) for a single player."""
    s = player['statistics']
    pts, ast, reb = s['points'], s['assists'], s['reboundsTotal']
    blk, stl, tov = s['blocks'], s['steals'], s['turnovers']
    fgm, fga = int(s['fieldGoalsMade']), int(s['fieldGoalsAttempted'])
    fg3m, fg3a = int(s['threePointersMade']), int(s['threePointersAttempted'])
    ftm, fta = int(s['freeThrowsMade']), int(s['freeThrowsAttempted'])
    on_court = live and player['oncourt'] == '1'

    return {
        'Joueur': player['name'] + ('*' if on_court else ''),
        'OGJoueur': player['name'],
        'Equipe': team,
        'Pts': pts, 'Ast': ast, 'Reb': reb,
        'OReb': s['reboundsOffensive'], 'DReb': s['reboundsDefensive'],
        'Blk': blk, 'Stl': stl, 'Tov': tov,
        'Min': _iso_minutes(s['minutes']),
        'FG': f'{fgm}/{fga}', 'FGm': fgm, 'FGa': fga,
        'FG3': f'{fg3m}/{fg3a}', 'FG3m': fg3m, 'FG3a': fg3a,
        'FT': f'{ftm}/{fta}', 'FTm': ftm, 'FTa': fta,
        'Pm': f"{int(s['plusMinusPoints']):+d}",
        'PF': s['foulsPersonal'],
        # pts+ast+reb+stl+blk+made - tov - missed, with missed = att - made
        'TTFL': pts + ast + reb + stl + blk - tov
                + 2 * (fgm + fg3m + ftm) - (fga + fg3a + fta),
    }


def _build_game(game, boxscores, pat):
    """(game_info dict, boxscore DataFrame) for one live/finished game."""
    home, away = boxscores['homeTeam'], boxscores['awayTeam']
    game_info = {'time': boxscores['gameStatusText'],
                 'homeTeam': home['teamTricode'], 'homeScore': home['score'],
                 'awayTeam': away['teamTricode'], 'awayScore': away['score']}

    live = game['gameStatus'] == 2
    rows = [_player_row(p, t['teamTricode'], live)
            for t in (home, away)
            for p in t['players'] if p['status'] != 'INACTIVE']

    df = clean_player_names(pd.DataFrame(rows, columns=COLUMNS), 'OGJoueur')

    # Lookup instead of merge (assumes playerName is unique in `pat`).
    avg = df['OGJoueur'].map(pat.set_index('playerName')['avg_TTFL'])
    df = df.rename(columns={'OGJoueur' : 'playerName'}).assign(avg_TTFL=avg)

    # Performance vs. season average
    perf = [_perf(t, a) for t, a in zip(df['TTFL'], avg)]
    df['perf'] = perf
    df['perf_str'] = [_TTFL_LABEL + ('0' if p == '0' else f'{a} ({p})')
                      for p, a in zip(perf, avg)]

    for key in ('FG', 'FG3', 'FT'):
        df[f'{key}pct'] = [_pct(m, a) for m, a in zip(df[f'{key}m'], df[f'{key}a'])]

    return game_info, clean_player_names(df, 'Joueur')

# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=15, show_spinner=False)
def get_live_games():
    import pandas as pd

    pat = get_cached_avg_TTFL()
    date_la = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    date_la_str = date_la.strftime('%d/%m/%Y')
    pending_games, finished_games = False, False
    upcoming_games, live_games, games_info, frames = [], [], [], []

    # 1 scoreboard request, then 1 request per started game, each retried on its own.
    # (Before: any hiccup restarted the whole scoreboard + every boxscore.)
    for game in _fetch_scoreboard():
        if game['gameStatus'] == 1:
            upcoming_games.append({'homeTeam' : game['homeTeam']['teamTricode'],
                                   'awayTeam' : game['awayTeam']['teamTricode'],
                                   'gameTimeParis' : (datetime.fromisoformat(
                                       game['gameTimeUTC'].replace("Z", "+00:00"))
                                       .astimezone(ZoneInfo("Europe/Paris"))
                                       .strftime('%d %b. à %Hh%M'))
                                  })
            continue

        elif game['gameStatus'] == 2:
            pending_games = True
        elif game['gameStatus'] == 3:
            finished_games = True

        boxscores = _fetch_boxscore(game['gameId'])
        if boxscores is None:
            continue

        game_info, boxscore_df = _build_game(game, boxscores, pat)
        games_info.append(game_info)
        live_games.append(boxscore_df)
        frames.append(boxscore_df)

    all_boxscores_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if len(upcoming_games) == 0 and not pending_games:
        pending_games, finished_games = False, False
        upcoming_games = _fetch_next_day_games()
        live_games = []
        games_info = []

    sorted_games_info, sorted_live_games = sort_games_info(games_info, live_games)

    return {'global' : all_boxscores_df,
            'upcoming_games' : upcoming_games,
            'games_info' : sorted_games_info,
            'live_games' : sorted_live_games,
            'pending_games' : pending_games,
            'finished_games' : finished_games,
            'gameDate' : date_la_str,
            'timestamp' : time.time()}


def sort_games_info(games_info, live_games):
    def game_sort_key(game):
        t = game['time']
        try:
            if t.startswith('Q'):
                quarter, clock = t.split(' ')
                q = int(quarter[1:])
                m, s = clock.split(':')
                minutes = int(m) if m else 0
                seconds = float(s) if s else 0
                remaining = minutes * 60 + seconds
                return (0, q, -remaining)

            elif t.startswith('END Q'):
                quarter = int(t[5:])
                return (0, quarter, 0)

            elif t == 'Half':
                return (0, 2.5, 0)

            elif t.startswith('OT'):
                overtime, clock = t.split(' ')
                ot = int(overtime[2:])
                m, s = clock.split(':')
                minutes = int(m) if m else 0
                seconds = float(s) if s else 0
                remaining = minutes * 60 + seconds
                return (0, 4 + ot, -remaining)

            elif t == 'Final':
                return (1, 0, 0)
        except:
            print(f'Error parsing game with time : {t}')
            return (2, 0, 0)

    try:
        sorted_indices = sorted(range(len(games_info)), key=lambda i: game_sort_key(games_info[i]))

        games_info_sorted = [games_info[i] for i in sorted_indices]
        live_games_sorted = [live_games[i] for i in sorted_indices]
    except:
        print('error sorting games')
        games_info_sorted = games_info
        live_games_sorted = live_games

    return games_info_sorted, live_games_sorted


if __name__ == "__main__":
    live_data = get_live_games()
    print(live_data)