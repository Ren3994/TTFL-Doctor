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

@st.cache_data(ttl=15, show_spinner=False)
def get_live_games():
    from nba_api.live.nba.endpoints import boxscore, scoreboard
    from nba_api.stats.endpoints import scoreboardv2
    import pandas as pd
    import numpy as np
    
    pat = get_cached_avg_TTFL()
    date_la = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    date_la_str = date_la.strftime('%d/%m/%Y')
    pending_games, finished_games = False, False
    all_live_data = {}

    for attempt in range(5):
        try:
            games = scoreboard.ScoreBoard().games.get_dict()
            all_boxscores_df = pd.DataFrame()
            upcoming_games = []
            live_games = []
            games_info = []

            for game in games:
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

                boxscores = boxscore.BoxScore(game_id=game['gameId']).get_dict()['game']
                games_info.append({'time' : boxscores['gameStatusText'],
                                'homeTeam' : boxscores['homeTeam']['teamTricode'],
                                'homeScore' : boxscores['homeTeam']['score'],
                                'awayTeam' : boxscores['awayTeam']['teamTricode'],
                                'awayScore' : boxscores['awayTeam']['score']})
                boxscore_data = {
                    'Joueur' : [],
                    'OGJoueur' : [],
                    'Equipe' : [],
                    'Pts' : [],
                    'Ast' : [],
                    'Reb' : [],
                    'OReb' : [],
                    'DReb' : [],
                    'Blk' : [],
                    'Stl' : [],
                    'Tov' : [],
                    'Min' : [],
                    'FG' : [],
                    'FGm' : [],
                    'FGa' : [],
                    'FG3' : [],
                    'FG3m' : [],
                    'FG3a' : [],
                    'FT' : [],
                    'FTm' : [],
                    'FTa' : [],
                    'Pm' : [],
                    'PF' : [],
                    'TTFL' : []
                }
                
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
                live_games.append(boxscore_df)
                all_boxscores_df = pd.concat([all_boxscores_df, boxscore_df], ignore_index=True)
            break

        except Exception as e:
            if attempt == 4:
                raise e
            time.sleep(5 * attempt)
    
    if len(upcoming_games) == 0 and not pending_games:
        date_paris = datetime.now(ZoneInfo("Europe/Paris")).date()
        pending_games, finished_games = False, False
    
        for attempt in range(5):
            try:
                games = scoreboardv2.ScoreboardV2(game_date=date_paris).game_header.get_dict()['data']
                upcoming_games = []
                live_games = []
                games_info = []

                for game in games:
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
            except Exception as e:
                if attempt == 4:
                    raise e
                time.sleep(5 * attempt)
    
    try:
        sorted_games_info = sort_games_info(games_info)
    except:
        sorted_games_info = games_info
        print('Error while sorting games info')
    
    all_live_data = {'global' : all_boxscores_df,
                     'upcoming_games' : upcoming_games,
                     'games_info' : sorted_games_info,
                     'live_games' : live_games,
                     'pending_games' : pending_games,
                     'finished_games' : finished_games,
                     'gameDate' : date_la_str,
                     'timestamp' : time.time()}

    return all_live_data

def sort_games_info(games_info):
    def game_sort_key(game):
        t = game['time']
        if t.startswith('Q'):
            quarter, clock = t.split(' ')
            q = int(quarter[1:])
            m, s = map(int, clock.split(':'))
            remaining = m * 60 + s
            return (0, q, -remaining)
        
        elif t == 'Half':
            return (0, 2.5, 0)
        
        elif t.startswith('OT'):
            overtime, clock = t.split(' ')
            ot = int(overtime[2:])
            m, s = map(int, clock.split(':'))
            remaining = m * 60 + s
            return (0, 4 + ot, -remaining)
        
        elif t == 'Final':
            return (1, 0, 0)
        
        return (2, 0, 0)
        
    games_info_sorted = sorted(games_info, key=game_sort_key)
    return games_info_sorted

if __name__ == "__main__":
    live_data = get_live_games()
    print(live_data)
    # for game in b:
    #     print(game['homeTeam'], game['awayTeam'], game['gameTimeParis'])