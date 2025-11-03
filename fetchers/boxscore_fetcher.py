from nba_api.stats.endpoints import BoxScoreTraditionalV3
import pandas as pd

def fetch_boxscores(game_date, game_id, visitor_team, home_team):

    if not game_id:
        return pd.DataFrame()

    boxscore = BoxScoreTraditionalV3(
        game_id=game_id,
        start_period=1,
        end_period=10,
        start_range=0,
        end_range=0,
        range_type=0
        )
    
    boxscore_df = boxscore.get_data_frames()[0]

    boxscore_df['homeTeam'] = home_team
    boxscore_df['visitorTeam'] = visitor_team
    boxscore_df['gameDate'] = game_date.strftime('%d/%m/%Y')

    return boxscore_df