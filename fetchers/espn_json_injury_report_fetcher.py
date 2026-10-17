from tqdm import tqdm
import requests
import time

def get_espn_injury_report_from_json():
    import pandas as pd

    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
    response = requests.get(url)
    
    df_injury_reports = None
    for attempt in range(3):
        try :
            data = response.json()
            if data['status'] != 'success':
                return pd.DataFrame()  # Return an empty DataFrame if the status is not 'success'

            injury_reports = []
            for team in data['injuries']:
                teamName = team.get('displayName')
                for player in team.get('injuries'):
                    playerName = player.get('athlete', {}).get('displayName')
                    short_comment = player.get('shortComment', '')
                    short_comment_lower = short_comment.lower()
                    # long_comment = player.get('longComment', '')
                    simplified = player.get('status', '')
                    update_date = player.get('date', '')
                    est_return = player.get('details', {}).get('returnDate', '')

                    update_date_fmt = pd.to_datetime(update_date).strftime('%d/%m') if update_date else '??'
                    est_return_fmt = pd.to_datetime(est_return).strftime('%d/%m') if est_return else '??'
                
                    if simplified.lower() == "day-to-day":
                        if any(x in short_comment_lower for x in [
                                "will not suit up", 
                                "won't suit up", 
                                "isn't warming up", 
                                "is not warming up", 
                                "not participating", 
                                "will be rested", 
                                "ruled out", 
                                "won't play", 
                                "will not play",
                                "will not return",
                                "won't return",
                                "is out", 
                                "personal", 
                                "is not starting", 
                                "is not in the starting",
                                "won't start",
                                "won't be starting",
                                "won't be in the starting",
                                "no timetable", 
                                "will not be available", 
                                "won't be available"]):
                            simplified = "Out"

                    elif "questionable" in short_comment_lower:
                        simplified = "Questionable"

                    elif "probable" in short_comment_lower:
                        simplified = "Probable"

                    injury_reports.append({
                                "player_name": playerName,
                                "simplified_status": simplified,
                                "injury_status": f'{update_date_fmt}: {simplified} (retour est. : {est_return_fmt})',
                                "details": short_comment
                            })

            df_injury_reports = pd.DataFrame(injury_reports)
    
        except Exception as e:
            tqdm.write(f'Erreur lors du téléchargement du injury report (ESPN JSON) : {e}. Nouvel essai dans {3 * (attempt + 1)}s')
            time.sleep(3 * (attempt + 1))
            
        if df_injury_reports is None:
            df_injury_reports = pd.DataFrame(columns=['player_name', 'simplified_status', 'injury_status', 'details'])
        
        return df_injury_reports
    
if __name__ == "__main__":
    print(get_espn_injury_report_from_json())