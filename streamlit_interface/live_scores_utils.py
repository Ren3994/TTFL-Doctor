from nba_api.live.nba.endpoints import scoreboard, boxscore
import streamlit as st
import isodate
import pandas as pd
import time

@st.cache_data(ttl=15, show_spinner=False)
def get_live_games():

    games = scoreboard.ScoreBoard().games.get_dict()
    live_games = []
    game_info = []

    for game in games:
        if game['gameStatus'] != 2:
            continue
        boxscores = boxscore.BoxScore(game_id=game['gameId']).get_dict()['game']
        game_info.append({'time' : boxscores['gameStatusText'],
                          'homeTeam' : boxscores['homeTeam']['teamTricode'],
                          'homeScore' : boxscores['homeTeam']['score'],
                          'awayTeam' : boxscores['awayTeam']['teamTricode'],
                          'awayScore' : boxscores['awayTeam']['score']})
        boxscore_data = {
            'Joueur' : [],
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
            'FG3' : [],
            'FT' : [],
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
                pm = hp['statistics']['plusMinusPoints']
                pf = hp['statistics']['foulsPersonal']
                ttfl = (pts + ast + reb + stl + blk + int(fgm) + int(fg3m) + int(ftm)
                            - tov - (int(fga)-int(fgm)) - (int(fg3a)-int(fg3m)) - (int(fta)-int(ftm)))
                
                boxscore_data['Joueur'].append(playerName)
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
                boxscore_data['FG3'].append(f'{fg3m}/{fg3a}')
                boxscore_data['FT'].append(f'{ftm}/{fta}')
                boxscore_data['Pm'].append(pm)
                boxscore_data['PF'].append(pf)
                boxscore_data['TTFL'].append(ttfl)

        boxscore_df = pd.DataFrame(boxscore_data)
        boxscore_df = boxscore_df.sort_values(by=['Equipe', 'TTFL'], ascending=[True, False]).reset_index(drop=True)
        live_games.append(boxscore_df)

    return game_info, live_games, time.time()

if __name__ == "__main__":
    get_live_games()