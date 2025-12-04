from nba_api.live.nba.endpoints import boxscore, scoreboard
from nba_api.stats.endpoints import scoreboardv2
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import numpy as np
import isodate
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.JDP_utils import clean_player_names, get_cached_avg_TTFL
from misc.misc import TEAM_IDS2TRICODE

@st.cache_data(ttl=15, show_spinner=False)
def get_live_games():
    pat = get_cached_avg_TTFL()
        
    for attempt in range(5):
        try:
            games = scoreboard.ScoreBoard().games.get_dict()
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

                if game['gameStatus'] == 2:
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
                            playerName = hp['name'] + ('*' if hp['oncourt'] == '1' else '')
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
                    ).drop(columns=['OGJoueur', 'playerName'])

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
            break

        except Exception as e:
            if attempt == 4:
                raise e
            time.sleep(5 * attempt)
    
    if len(upcoming_games) == 0 and len(live_games) == 0:
        date_new_york = datetime.now(ZoneInfo("America/New_York")).date()
        date_paris = datetime.now(ZoneInfo("Europe/Paris")).date()
            
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
                    awayTEAMID = game[7]
                    
                    if gameStatus != 1:
                        continue
                    upcoming_games.append({'homeTeam' : TEAM_IDS2TRICODE[homeTeamID],
                                           'awayTeam' : TEAM_IDS2TRICODE[awayTEAMID],
                                           'gameTimeParis' : (
                                                datetime.strptime(gameTimeStringET.replace(" ET", ""), 
                                                                   "%I:%M %p")
                                                         .replace(year=date_new_york.year, 
                                                                  month=date_new_york.month, 
                                                                  day=date_new_york.day, 
                                                                  tzinfo=ZoneInfo("America/New_York"))
                                                         .astimezone(ZoneInfo("Europe/Paris"))
                                                         .strftime('%d %b. à %Hh%M'))
                                           })
            except Exception as e:
                if attempt == 4:
                    raise e
                time.sleep(5 * attempt)

    return upcoming_games, games_info, live_games, time.time()

if __name__ == "__main__":
    a, b, c, d = get_live_games()
    for game in a:
        print(game['homeTeam'], game['awayTeam'], game['gameTimeParis'])