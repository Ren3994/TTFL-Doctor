from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
import isodate
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.JDP_utils import clean_player_names, get_cached_avg_TTFL
from misc.misc import TEAM_IDS2TRICODE
from fetchers.net_utils import NBA_API, NBA_CDN, retry_call

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


def _fetch_next_day_games(date_paris, date_la):
    """Upcoming games from ScoreboardV2 (used when today's slate is over)."""
    from nba_api.stats.endpoints import scoreboardv2

    ## v2 is deprecated -> switch to v3 in the future if problems arise
    rows = retry_call(
        lambda: scoreboardv2.ScoreboardV2(game_date=date_paris, timeout=10)
                            .game_header.get_dict()['data'],
        label="scoreboardv2", policy=STATS_POLICY,
        validate=lambda r: isinstance(r, list),
        raise_on_failure=True)

    upcoming_games = []
    for game in rows:
        gameStatus = game[3]
        gameTimeStringET = game[4]
        homeTeamID = game[6]
        awayTeamID = game[7]

        if gameStatus != 1 or gameTimeStringET == 'TBD' or homeTeamID is None:
            continue
        upcoming_games.append({'homeTeam' : TEAM_IDS2TRICODE[homeTeamID],
                               'awayTeam' : TEAM_IDS2TRICODE[awayTeamID],
                               'gameTimeParis' : (
                                    datetime.strptime(gameTimeStringET.replace(" ET", ""),
                                                       "%I:%M %p")
                                             .replace(year=date_la.year,
                                                      month=date_la.month,
                                                      day=date_la.day,
                                                      tzinfo=ZoneInfo("America/New_York"))
                                             .astimezone(ZoneInfo("Europe/Paris"))
                                             .strftime('%d %b. à %Hh%M'))
                               })
    return upcoming_games


# --------------------------------------------------------------------------- #
# Parsing: your code, unchanged, just moved out of the retry loop             #
# --------------------------------------------------------------------------- #
def _build_game(game, boxscores, pat):
    """(game_info dict, boxscore DataFrame) for one live/finished game."""
    import pandas as pd
    import numpy as np

    game_info = {'time' : boxscores['gameStatusText'],
                 'homeTeam' : boxscores['homeTeam']['teamTricode'],
                 'homeScore' : boxscores['homeTeam']['score'],
                 'awayTeam' : boxscores['awayTeam']['teamTricode'],
                 'awayScore' : boxscores['awayTeam']['score']}

    boxscore_data = {k: [] for k in (
        'Joueur', 'OGJoueur', 'Equipe', 'Pts', 'Ast', 'Reb', 'OReb', 'DReb', 'Blk', 'Stl',
        'Tov', 'Min', 'FG', 'FGm', 'FGa', 'FG3', 'FG3m', 'FG3a', 'FT', 'FTm', 'FTa',
        'Pm', 'PF', 'TTFL')}

    for team in ['homeTeam', 'awayTeam']:
        players = boxscores[team]['players']
        teamTricode = boxscores[team]['teamTricode']
        for hp in players:
            if hp['status'] == 'INACTIVE':
                continue
            playerName = hp['name'] + ('*' if (hp['oncourt'] == '1' and game['gameStatus'] == 2) else '')
            OGplayerName = hp['name']
            pts = hp['statistics']['points']
            ast = hp['statistics']['assists']
            reb = hp['statistics']['reboundsTotal']
            oreb = hp['statistics']['reboundsOffensive']
            dreb = hp['statistics']['reboundsDefensive']
            blk = hp['statistics']['blocks']
            stl = hp['statistics']['steals']
            tov = hp['statistics']['turnovers']
            min_iso = int(isodate.parse_duration(hp['statistics']['minutes']).total_seconds())
            min_str = f"{min_iso // 60:02d}:{min_iso % 60:02d}"
            fgm = str(hp['statistics']['fieldGoalsMade'])
            fga = str(hp['statistics']['fieldGoalsAttempted'])
            fg3m = str(hp['statistics']['threePointersMade'])
            fg3a = str(hp['statistics']['threePointersAttempted'])
            ftm = str(hp['statistics']['freeThrowsMade'])
            fta = str(hp['statistics']['freeThrowsAttempted'])
            pm = np.select([hp['statistics']['plusMinusPoints'] < 0],
                           [str(int(hp['statistics']['plusMinusPoints']))],
                           '+' + str(int(hp['statistics']['plusMinusPoints'])))
            pf = hp['statistics']['foulsPersonal']
            ttfl = (pts + ast + reb + stl + blk + int(fgm) + int(fg3m) + int(ftm)
                        - tov - (int(fga)-int(fgm)) - (int(fg3a)-int(fg3m)) - (int(fta)-int(ftm)))

            boxscore_data['Joueur'].append(playerName)
            boxscore_data['OGJoueur'].append(OGplayerName)
            boxscore_data['Equipe'].append(teamTricode)
            boxscore_data['Pts'].append(pts)
            boxscore_data['Ast'].append(ast)
            boxscore_data['Reb'].append(reb)
            boxscore_data['OReb'].append(oreb)
            boxscore_data['DReb'].append(dreb)
            boxscore_data['Blk'].append(blk)
            boxscore_data['Stl'].append(stl)
            boxscore_data['Tov'].append(tov)
            boxscore_data['Min'].append(min_str)
            boxscore_data['FG'].append(f'{fgm}/{fga}')
            boxscore_data['FGm'].append(int(fgm))
            boxscore_data['FGa'].append(int(fga))
            boxscore_data['FG3'].append(f'{fg3m}/{fg3a}')
            boxscore_data['FG3m'].append(int(fg3m))
            boxscore_data['FG3a'].append(int(fg3a))
            boxscore_data['FT'].append(f'{ftm}/{fta}')
            boxscore_data['FTm'].append(int(ftm))
            boxscore_data['FTa'].append(int(fta))
            boxscore_data['Pm'].append(pm)
            boxscore_data['PF'].append(pf)
            boxscore_data['TTFL'].append(ttfl)

    boxscore_df = pd.DataFrame(boxscore_data)
    boxscore_df = clean_player_names(boxscore_df, 'OGJoueur')
    boxscore_df = boxscore_df.merge(
        pat[['playerName', 'avg_TTFL']],
        left_on=['OGJoueur'],
        right_on=['playerName'],
        how='left'
    ).drop(columns=['OGJoueur'])

    boxscore_df['perf'] = np.select([boxscore_df['avg_TTFL'] == 0, boxscore_df['TTFL'] < boxscore_df['avg_TTFL']],
            ['0', (100 * (boxscore_df['TTFL'] - boxscore_df['avg_TTFL']) / boxscore_df['avg_TTFL']).round(1).astype(str) + '%'],
            '+' + (100 * (boxscore_df['TTFL'] - boxscore_df['avg_TTFL']) / boxscore_df['avg_TTFL']).round(1).astype(str) + '%')

    boxscore_df['perf_str'] = np.select([boxscore_df['perf'] == '0'],
                ['<span style="text-decoration:overline">TTFL</span> : 0'],
                '<span style="text-decoration:overline">TTFL</span> : ' +
                boxscore_df['avg_TTFL'].astype(str) + ' (' + boxscore_df['perf'] + ')')

    boxscore_df['FGpct'] = np.select([boxscore_df['FGa'] == 0, boxscore_df['FGa'] == boxscore_df['FGm']],
                            ['', '100%'],
                (100 * boxscore_df['FGm'] / boxscore_df['FGa']).round(1).astype(str) + '%')
    boxscore_df['FG3pct'] = np.select([boxscore_df['FG3a'] == 0, boxscore_df['FG3a'] == boxscore_df['FG3m']],
                            ['', '100%'],
                (100 * boxscore_df['FG3m'] / boxscore_df['FG3a']).round(1).astype(str) + '%')
    boxscore_df['FTpct'] = np.select([boxscore_df['FTa'] == 0, boxscore_df['FTa'] == boxscore_df['FTm']],
                            ['', '100%'],
                (100 * boxscore_df['FTm'] / boxscore_df['FTa']).round(1).astype(str) + '%')

    boxscore_df = clean_player_names(boxscore_df, 'Joueur')
    return game_info, boxscore_df


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
        if boxscores is None:          # net_utils already logged why; show the other games
            continue

        game_info, boxscore_df = _build_game(game, boxscores, pat)
        games_info.append(game_info)
        live_games.append(boxscore_df)
        frames.append(boxscore_df)

    all_boxscores_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if len(upcoming_games) == 0 and not pending_games:
        date_paris = datetime.now(ZoneInfo("Europe/Paris")).date()
        pending_games, finished_games = False, False
        upcoming_games = _fetch_next_day_games(date_paris, date_la)
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

# from json import JSONDecodeError
# from datetime import datetime
# from zoneinfo import ZoneInfo
# import streamlit as st
# import isodate
# import time
# import sys
# import os

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from streamlit_interface.JDP_utils import clean_player_names, get_cached_avg_TTFL
# from misc.misc import TEAM_IDS2TRICODE

# @st.cache_data(ttl=15, show_spinner=False)
# def get_live_games():
#     from nba_api.live.nba.endpoints import boxscore, scoreboard
#     from nba_api.stats.endpoints import scoreboardv2
#     import pandas as pd
#     import numpy as np
    
#     pat = get_cached_avg_TTFL()
#     date_la = datetime.now(ZoneInfo("America/Los_Angeles")).date()
#     date_la_str = date_la.strftime('%d/%m/%Y')
#     pending_games, finished_games = False, False
#     all_live_data = {}

#     for attempt in range(3):
#         try:
#             upcoming_games = []
#             live_games = []
#             games_info = []
#             all_boxscores_df = pd.DataFrame()
#             games = scoreboard.ScoreBoard().games.get_dict()
            
#             for game in games:
#                 if game['gameStatus'] == 1:
#                     upcoming_games.append({'homeTeam' : game['homeTeam']['teamTricode'],
#                                            'awayTeam' : game['awayTeam']['teamTricode'],
#                                            'gameTimeParis' : (datetime.fromisoformat(
#                                                game['gameTimeUTC'].replace("Z", "+00:00"))
#                                                .astimezone(ZoneInfo("Europe/Paris"))
#                                                .strftime('%d %b. à %Hh%M'))
#                                           })
#                     continue
                
#                 elif game['gameStatus'] == 2:
#                     pending_games = True
#                 elif game['gameStatus'] == 3:
#                     finished_games = True   

#                 boxscores = boxscore.BoxScore(game_id=game['gameId']).get_dict()['game']
#                 games_info.append({'time' : boxscores['gameStatusText'],
#                                 'homeTeam' : boxscores['homeTeam']['teamTricode'],
#                                 'homeScore' : boxscores['homeTeam']['score'],
#                                 'awayTeam' : boxscores['awayTeam']['teamTricode'],
#                                 'awayScore' : boxscores['awayTeam']['score']})
#                 boxscore_data = {
#                     'Joueur' : [],
#                     'OGJoueur' : [],
#                     'Equipe' : [],
#                     'Pts' : [],
#                     'Ast' : [],
#                     'Reb' : [],
#                     'OReb' : [],
#                     'DReb' : [],
#                     'Blk' : [],
#                     'Stl' : [],
#                     'Tov' : [],
#                     'Min' : [],
#                     'FG' : [],
#                     'FGm' : [],
#                     'FGa' : [],
#                     'FG3' : [],
#                     'FG3m' : [],
#                     'FG3a' : [],
#                     'FT' : [],
#                     'FTm' : [],
#                     'FTa' : [],
#                     'Pm' : [],
#                     'PF' : [],
#                     'TTFL' : []
#                 }
                
#                 for team in ['homeTeam', 'awayTeam']:
#                     players = boxscores[team]['players']
#                     teamTricode = boxscores[team]['teamTricode']
#                     for hp in players:
#                         if hp['status'] == 'INACTIVE':
#                             continue
#                         playerName = hp['name'] + ('*' if (hp['oncourt'] == '1' and game['gameStatus'] == 2) else '')
#                         OGplayerName = hp['name']
#                         pts = hp['statistics']['points']
#                         ast = hp['statistics']['assists']
#                         reb = hp['statistics']['reboundsTotal']
#                         oreb = hp['statistics']['reboundsOffensive']
#                         dreb = hp['statistics']['reboundsDefensive']
#                         blk = hp['statistics']['blocks']
#                         stl = hp['statistics']['steals']
#                         tov = hp['statistics']['turnovers']
#                         min_iso = int(isodate.parse_duration(hp['statistics']['minutes']).total_seconds())
#                         min_str = f"{min_iso // 60:02d}:{min_iso % 60:02d}"
#                         fgm = str(hp['statistics']['fieldGoalsMade'])
#                         fga = str(hp['statistics']['fieldGoalsAttempted'])
#                         fg3m = str(hp['statistics']['threePointersMade'])
#                         fg3a = str(hp['statistics']['threePointersAttempted'])
#                         ftm = str(hp['statistics']['freeThrowsMade'])
#                         fta = str(hp['statistics']['freeThrowsAttempted'])
#                         pm = np.select([hp['statistics']['plusMinusPoints'] < 0], 
#                                     [str(int(hp['statistics']['plusMinusPoints']))],
#                                     '+' + str(int(hp['statistics']['plusMinusPoints'])))
#                         pf = hp['statistics']['foulsPersonal']
#                         ttfl = (pts + ast + reb + stl + blk + int(fgm) + int(fg3m) + int(ftm)
#                                     - tov - (int(fga)-int(fgm)) - (int(fg3a)-int(fg3m)) - (int(fta)-int(ftm)))
                        
#                         boxscore_data['Joueur'].append(playerName)
#                         boxscore_data['OGJoueur'].append(OGplayerName)
#                         boxscore_data['Equipe'].append(teamTricode)
#                         boxscore_data['Pts'].append(pts)
#                         boxscore_data['Ast'].append(ast)
#                         boxscore_data['Reb'].append(reb)
#                         boxscore_data['OReb'].append(oreb)
#                         boxscore_data['DReb'].append(dreb)
#                         boxscore_data['Blk'].append(blk)
#                         boxscore_data['Stl'].append(stl)
#                         boxscore_data['Tov'].append(tov)
#                         boxscore_data['Min'].append(min_str)
#                         boxscore_data['FG'].append(f'{fgm}/{fga}')
#                         boxscore_data['FGm'].append(int(fgm))
#                         boxscore_data['FGa'].append(int(fga))
#                         boxscore_data['FG3'].append(f'{fg3m}/{fg3a}')
#                         boxscore_data['FG3m'].append(int(fg3m))
#                         boxscore_data['FG3a'].append(int(fg3a))
#                         boxscore_data['FT'].append(f'{ftm}/{fta}')
#                         boxscore_data['FTm'].append(int(ftm))
#                         boxscore_data['FTa'].append(int(fta))
#                         boxscore_data['Pm'].append(pm)
#                         boxscore_data['PF'].append(pf)
#                         boxscore_data['TTFL'].append(ttfl)

#                 boxscore_df = pd.DataFrame(boxscore_data)
#                 boxscore_df = clean_player_names(boxscore_df, 'OGJoueur')
#                 boxscore_df = boxscore_df.merge(
#                     pat[['playerName', 'avg_TTFL']],
#                     left_on=['OGJoueur'],
#                     right_on=['playerName'],
#                     how='left'
#                 ).drop(columns=['OGJoueur'])

#                 boxscore_df['perf'] = np.select([boxscore_df['avg_TTFL'] == 0, boxscore_df['TTFL'] < boxscore_df['avg_TTFL']],
#                         ['0', (100 * (boxscore_df['TTFL'] - boxscore_df['avg_TTFL']) / boxscore_df['avg_TTFL']).round(1).astype(str) + '%'], 
#                         '+' + (100 * (boxscore_df['TTFL'] - boxscore_df['avg_TTFL']) / boxscore_df['avg_TTFL']).round(1).astype(str) + '%')
                
#                 boxscore_df['perf_str'] = np.select([boxscore_df['perf'] == '0'], 
#                             ['<span style="text-decoration:overline">TTFL</span> : 0'],
#                             '<span style="text-decoration:overline">TTFL</span> : ' + 
#                             boxscore_df['avg_TTFL'].astype(str) + ' (' + boxscore_df['perf'] + ')')
                
#                 boxscore_df['FGpct'] = np.select([boxscore_df['FGa'] == 0, boxscore_df['FGa'] == boxscore_df['FGm']], 
#                                         ['', '100%'], 
#                             (100 * boxscore_df['FGm'] / boxscore_df['FGa']).round(1).astype(str) + '%')
#                 boxscore_df['FG3pct'] = np.select([boxscore_df['FG3a'] == 0, boxscore_df['FG3a'] == boxscore_df['FG3m']], 
#                                         ['', '100%'], 
#                             (100 * boxscore_df['FG3m'] / boxscore_df['FG3a']).round(1).astype(str) + '%')
#                 boxscore_df['FTpct'] = np.select([boxscore_df['FTa'] == 0, boxscore_df['FTa'] == boxscore_df['FTm']], 
#                                         ['', '100%'], 
#                             (100 * boxscore_df['FTm'] / boxscore_df['FTa']).round(1).astype(str) + '%')

#                 boxscore_df = clean_player_names(boxscore_df, 'Joueur')
#                 live_games.append(boxscore_df)
#                 all_boxscores_df = pd.concat([all_boxscores_df, boxscore_df], ignore_index=True)
#             break
        
#         except JSONDecodeError as e:
#             print('JSONDecodeError, retrying...')
#             pass

#         except Exception as e:
#             print('Something else', e)
#             if attempt == 2:
#                 raise e
#             time.sleep(5 * attempt)
    
#     if len(upcoming_games) == 0 and not pending_games:
#         date_paris = datetime.now(ZoneInfo("Europe/Paris")).date()
#         pending_games, finished_games = False, False
    
#         for attempt in range(3):
#             try:
#                 ## v2 is deprecated -> switch to v3 in the future if problems arise
#                 games = scoreboardv2.ScoreboardV2(game_date=date_paris).game_header.get_dict()['data']
#                 upcoming_games = []
#                 live_games = []
#                 games_info = []

#                 for game in games:
#                     gameStatus = game[3]
#                     gameTimeStringET = game[4]
#                     homeTeamID = game[6]
#                     awayTeamID = game[7]
                    
#                     if gameStatus != 1 or gameTimeStringET == 'TBD' or homeTeamID is None:
#                         continue
#                     upcoming_games.append({'homeTeam' : TEAM_IDS2TRICODE[homeTeamID],
#                                            'awayTeam' : TEAM_IDS2TRICODE[awayTeamID],
#                                            'gameTimeParis' : (
#                                                 datetime.strptime(gameTimeStringET.replace(" ET", ""), 
#                                                                    "%I:%M %p")
#                                                          .replace(year=date_la.year, 
#                                                                   month=date_la.month, 
#                                                                   day=date_la.day, 
#                                                                   tzinfo=ZoneInfo("America/New_York"))
#                                                          .astimezone(ZoneInfo("Europe/Paris"))
#                                                          .strftime('%d %b. à %Hh%M'))
#                                            })
#             except Exception as e:
#                 print('???', e)
#                 if attempt == 2:
#                     raise e
#                 time.sleep(5 * attempt)
    
#     sorted_games_info, sorted_live_games = sort_games_info(games_info, live_games)
    
#     all_live_data = {'global' : all_boxscores_df,
#                      'upcoming_games' : upcoming_games,
#                      'games_info' : sorted_games_info,
#                      'live_games' : sorted_live_games,
#                      'pending_games' : pending_games,
#                      'finished_games' : finished_games,
#                      'gameDate' : date_la_str,
#                      'timestamp' : time.time()}

#     return all_live_data

# def sort_games_info(games_info, live_games):
#     def game_sort_key(game):
#         t = game['time']
#         try:
#             if t.startswith('Q'):
#                 quarter, clock = t.split(' ')
#                 q = int(quarter[1:])
#                 m, s = clock.split(':')
#                 minutes = int(m) if m else 0
#                 seconds = float(s) if s else 0
#                 remaining = minutes * 60 + seconds
#                 return (0, q, -remaining)
            
#             elif t.startswith('END Q'):
#                 quarter = int(t[5:])
#                 return (0, quarter, 0)
            
#             elif t == 'Half':
#                 return (0, 2.5, 0)
            
#             elif t.startswith('OT'):
#                 overtime, clock = t.split(' ')
#                 ot = int(overtime[2:])
#                 m, s = clock.split(':')
#                 minutes = int(m) if m else 0
#                 seconds = float(s) if s else 0
#                 remaining = minutes * 60 + seconds
#                 return (0, 4 + ot, -remaining)
            
#             elif t == 'Final':
#                 return (1, 0, 0)
#         except:
#             print(f'Error parsing game with time : {t}')
#             return (2, 0, 0)
    
#     try:
#         sorted_indices = sorted(range(len(games_info)), key=lambda i: game_sort_key(games_info[i]))

#         games_info_sorted = [games_info[i] for i in sorted_indices]
#         live_games_sorted = [live_games[i] for i in sorted_indices]
#     except:
#         print('error sorting games')
#         games_info_sorted = games_info
#         live_games_sorted = live_games
        
#     return games_info_sorted, live_games_sorted

# if __name__ == "__main__":
#     live_data = get_live_games()
#     print(live_data)
#     # for game in b:
#     #     print(game['homeTeam'], game['awayTeam'], game['gameTimeParis'])