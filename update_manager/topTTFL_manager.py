import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.resource_manager import conn_db
from data.sql_functions import topTTFL_query

def get_top_TTFL(game_date_ymd: str):

    conn = conn_db()

    df = topTTFL_query(conn, game_date_ymd)
    prettydf = format_to_table(df)

    return prettydf

def format_to_table(df) :
    import pandas as pd
    import numpy as np

    if df.empty :
        return df

    prettydf = pd.DataFrame()

    # ----------------------------------------- Regular player info -------------------------------------------------

    prettydf['Joueur'] = df['playerName']
    prettydf['Poste'] = df['pos']
    prettydf['Lieu'] = df['team'].where(df['isHome'] == 1, df['opponent'])
    prettydf['Équipe'] = df['team'] + ' (' + df['teamWins'].astype(str) + 'W-' + df['teamLosses'].astype(str) + 'L)'
    prettydf['Adversaire'] = df['opponent'] + ' (' + df['oppWins'].astype(str) + 'W-' + df['oppLosses'].astype(str) + 'L)'
    prettydf['TTFL'] = df['avg_TTFL'].round(1).fillna('N/A')
    prettydf['stdTTFL'] = df['stddev_TTFL'].round(1).fillna('N/A')
    prettydf['median_TTFL'] = df['median_TTFL'].astype(int).fillna('N/A')
    prettydf['Statut'] = df['injury_status'].fillna('')
    prettydf['details'] = df['details'].fillna('')
    prettydf['opp'] = df['opponent']
    prettydf['is_b2b'] = df['is_b2b']
    prettydf['n_btb'] = df['n_btb']
    prettydf['Joueur'] = prettydf['Joueur'].where(prettydf['is_b2b'] == 0, prettydf['Joueur'] + ' (B2B)')

    # -------------------------------------------- Nemesis stuff -------------------------------------------------
    
    df['rel_TTFL_v_team_nemesis'] = pd.to_numeric(df['rel_TTFL_v_team_nemesis'], errors='coerce')
    df['games_v_team_nemesis'] = pd.to_numeric(df['games_v_team_nemesis'], errors='coerce')
    prettydf['team_nemesis'] = np.select([df['team_nemesis'].isna(), df['rel_TTFL_v_team_nemesis'] >= 0], 
                            [       '', '<br> - ' + df['team_nemesis'] + ' : +' + df['rel_TTFL_v_team_nemesis'].round(1).astype(str) + '%' + ' (' + df['games_v_team_nemesis'].astype('Int64').astype(str) + ' matchs)'],
                            '<br> - ' + df['team_nemesis'] + ' : ' + df['rel_TTFL_v_team_nemesis'].round(1).astype(str) + '%' + ' (' + df['games_v_team_nemesis'].astype('Int64').astype(str) + ' matchs)')
    
    df['player_nem_split'] = df['player_nemesis'].str.split(",")
    df['player_rel_nem_split'] = df['rel_TTFL_v_player_nemesis'].str.split(",")
    df['player_gc_split'] = df['games_v_player_nemesis'].str.split(",")

    df_player_nem = df.explode(['player_nem_split', 'player_rel_nem_split', 'player_gc_split'])

    df_player_nem = df_player_nem.drop_duplicates(
            subset=[
                "playerName",
                "pos",
                "player_nem_split",
                "player_rel_nem_split",
                "player_gc_split"
            ]
        )

    df_player_nem["player_rel_nem_split"] = pd.to_numeric(
            df_player_nem["player_rel_nem_split"], errors="coerce"
        )
    df_player_nem["player_gc_split"] = pd.to_numeric(
        df_player_nem["player_gc_split"], errors="coerce"
    )

    df_player_nem = df_player_nem.sort_values(
            by="player_rel_nem_split", ascending=False
        )
    
    df_player_nem["player_rel_nem_split"] = np.select([
                df_player_nem["player_rel_nem_split"].isna(),
                df_player_nem["player_rel_nem_split"] >= 0,
            ],
            [
                "",
                "+" + df_player_nem["player_rel_nem_split"].round(1).astype(str),
            ],
            default=df_player_nem["player_rel_nem_split"].round(1).astype(str),
        )
    
    df_player_nem["player_nemesis"] = np.select(
            [
                df_player_nem["player_nem_split"].isna()
            ],
            [
                ''
            ],
            default = ' - ' + df_player_nem['player_nem_split'] + ' : ' + \
                      df_player_nem['player_rel_nem_split'] + \
                      '% (' + df_player_nem['player_gc_split'].astype('Int64').astype(str) + ' matchs)'
        )

    prettydf['player_nemesis'] = df_player_nem.groupby(level=0)['player_nemesis'].agg(lambda x: '<br>'.join(v for v in x if v != ''))
    
    prettydf['nemesis'] = np.select([
        (prettydf['team_nemesis'] == '') & (prettydf['player_nemesis'] == '')], [''],
        default = '<br><br>' + prettydf['Joueur'] + ' all time vs. :<hr style="margin:0px 0;">' + \
            prettydf['player_nemesis'] + prettydf['team_nemesis']
        )
        
    # -------------------------------------------- Graph stuff -------------------------------------------------

    prettydf['graph_dates'] = df['graph_dates']
    prettydf['graph_opps'] = df['graph_opps']
    prettydf['graph_TTFLs'] = df['graph_TTFLs']
    prettydf['graph_wins'] = df['graph_wins']

    # ------------------------------------------ Relative stuff ------------------------------------------------

    df['pos_rel_TTFL_v_team'] = pd.to_numeric(df['pos_rel_TTFL_v_team'], errors='coerce')
    df['rel_TTFL_v_opp'] = pd.to_numeric(df['rel_TTFL_v_opp'], errors='coerce')
    df['ha_rel_TTFL'] = pd.to_numeric(df['ha_rel_TTFL'], errors='coerce')
    df['rel_btb_TTFL'] = pd.to_numeric(df['rel_btb_TTFL'], errors='coerce')
    df['n_btb'] = pd.to_numeric(df['n_btb'], errors='coerce').fillna(0)

    prettydf['pos_rel_TTFL_v_team'] = np.select([df['pos_rel_TTFL_v_team'].isna(), df['pos_rel_TTFL_v_team'] >= 0], 
                            [       'N/A',                        '+' + df['pos_rel_TTFL_v_team'].round(1).astype(str) + '%'],
                            df['pos_rel_TTFL_v_team'].round(1).astype(str) + '%')

    prettydf['ha_rel_TTFL'] = df['playerName'] + np.where(df['isHome'] == 1, ' à la maison : ', ' à l\'extérieur : ') + \
                            np.select([df['ha_rel_TTFL'].isna(), df['ha_rel_TTFL'] >= 0], 
                            [       'N/A',                        '+' + df['ha_rel_TTFL'].round(1).astype(str) + '%'],
                            df['ha_rel_TTFL'].round(1).astype(str) + '%')

    prettydf['rel_TTFL_v_opp'] = df['playerName'] + ' contre ' + df['opponent'] + ' : ' + \
                            np.select([df['rel_TTFL_v_opp'].isna(), df['rel_TTFL_v_opp'] >= 0], 
                            [       'N/A',                        '+' + df['rel_TTFL_v_opp'].round(1).astype(str) + '%'],
                            df['rel_TTFL_v_opp'].round(1).astype(str) + '%')
    
    prettydf['rel_opp_avg_TTFL'] = 'Toutes les équipes contre ' + df['opponent'] + ' : ' + \
                                np.select([df['rel_opp_avg_TTFL'].isna(), df['rel_opp_avg_TTFL'] >= 0],
                                [           'N/A',           '+' + df['rel_opp_avg_TTFL'].round(1).astype(str) + '%'],
                                df['rel_opp_avg_TTFL'].round(1).astype(str) + '%')
    
    prettydf['rel_btb_TTFL'] = df['playerName'] + ' en back to back : ' + \
                                np.select([df['rel_btb_TTFL'].isna(), df['rel_btb_TTFL'] >= 0],
                                [           'N/A<br>',           '+' + df['rel_btb_TTFL'].round(1).astype(str) + '% (' + df['n_btb'].astype(int).astype(str) + ' matchs)<br>'],
                                df['rel_btb_TTFL'].round(1).astype(str) + '% (' + df['n_btb'].astype(int).astype(str) + ' matchs)<br>')
    
    prettydf['rel_btb_TTFL_with_br'] = prettydf['rel_btb_TTFL'].where(prettydf['is_b2b'] == 1, '')
    
    # -------------------------------------------- Team injury status ------------------------------------------------

    df['inj_team_split'] = df['injured_teammates'].str.split(",")
    df['inj_team_simp_split'] = df['simp_statuses'].str.split(",")
    df['inj_team_TTFL_split'] = df['inj_teammates_TTFLs'].str.split(",")
    df['inj_team_rel_abs'] = df['rel_TTFL_inj_teammate_abs'].str.split(",")
    df['inj_team_n_abs_split'] = df['inj_teammates_abs_count'].str.split(",")

    df_inj_teammates = df.explode(['inj_team_split', 'inj_team_simp_split', 
                                'inj_team_TTFL_split', 'inj_team_rel_abs',
                                'inj_team_n_abs_split'])

    df_inj_teammates = df_inj_teammates.drop_duplicates(
            subset=[
                "playerName",
                "pos",
                "inj_team_split",
                "inj_team_simp_split",
                "inj_team_TTFL_split",
                "inj_team_rel_abs",
                "inj_team_n_abs_split",
            ]
        )

    df_inj_teammates["inj_team_TTFL_split"] = pd.to_numeric(
            df_inj_teammates["inj_team_TTFL_split"], errors="coerce"
        )
    df_inj_teammates["inj_team_rel_abs"] = pd.to_numeric(
        df_inj_teammates["inj_team_rel_abs"], errors="coerce"
    )

    df_inj_teammates = df_inj_teammates.sort_values(
            by="inj_team_TTFL_split", ascending=False
        )

    df_inj_teammates["inj_team_rel_abs"] = np.select([
                df_inj_teammates["inj_team_rel_abs"].isna(),
                df_inj_teammates["inj_team_rel_abs"] >= 0,
            ],
            [
                "N/A",
                "+" + df_inj_teammates["inj_team_rel_abs"].round(1).astype(str),
            ],
            default=df_inj_teammates["inj_team_rel_abs"].round(1).astype(str),
        )

    df_inj_teammates["team_injury_status"] = np.select(
            [
                df_inj_teammates["inj_team_TTFL_split"].isna()
            ],
            [
                ''
            ],
            default=  '- ' + df_inj_teammates['inj_team_split'] + ' (' + \
                    df_inj_teammates['inj_team_simp_split'] + ')' + \
                    ' - TTFL : ' + df_inj_teammates['inj_team_TTFL_split'].fillna('N/A').astype(str) + \
                    ' - Absent : ' + df_inj_teammates['inj_team_rel_abs'].astype(str) + \
                    '% (' + df_inj_teammates['inj_team_n_abs_split'] + ' matchs)'
        )

    prettydf['team_injury_status'] = df_inj_teammates.groupby(level=0)['team_injury_status'].agg(lambda x: '<br>'.join(v for v in x if v != ''))

    prettydf["team_injury_status"] = np.select(
        [
            prettydf["team_injury_status"] == ''
        ],
        [
            'Pas de joueurs blessés chez ' + df['team']
        ],
        default='Joueurs blessés chez ' + df['team'] + ' :<hr style="margin:3px 0;">' + prettydf["team_injury_status"]
    )

    # -------------------------------------------- Opponent team injury status ------------------------------------------------

    df['opp_inj_split'] = df['inj_opponents'].str.split(",")
    df['opp_simp_split'] = df['inj_opponents_simp_statuses'].str.split(",")
    df['opp_TTFL_split'] = df['inj_opponents_TTFLs'].str.split(",")
    df['rel_opp_pos_split'] = df['pos_rel_TTFL_when_inj_opp'].str.split(",")

    df_inj_opp = df.explode(['opp_inj_split', 'opp_simp_split', 
                            'opp_TTFL_split', 'rel_opp_pos_split'])

    df_inj_opp = df_inj_opp.drop_duplicates(
        subset=[
            "playerName",
            "pos",
            "opp_inj_split",
            "opp_simp_split",
            "opp_TTFL_split",
            "rel_opp_pos_split",
        ]
    )

    df_inj_opp["opp_TTFL_split"] = pd.to_numeric(
            df_inj_opp["opp_TTFL_split"], errors="coerce"
        )

    df_inj_opp["rel_opp_pos_split"] = pd.to_numeric(
            df_inj_opp["rel_opp_pos_split"], errors="coerce"
        )

    df_inj_opp = df_inj_opp.sort_values(
            by="opp_TTFL_split", ascending=False
        )

    df_inj_opp["opp_team_injury_status_no_rel"] = np.select(
            [
                df_inj_opp["opp_TTFL_split"].isna()
            ],
            [
                ''
            ],
            default=  '- ' + df_inj_opp['opp_inj_split'] + ' (' + \
                    df_inj_opp['opp_simp_split'] + ')' + \
                    ' - TTFL : ' + df_inj_opp['opp_TTFL_split'].fillna('N/A').astype(str)# + \
        )

    df_inj_opp["opp_team_rel_opp_pos"] = np.select(
            [
                df_inj_opp["opp_TTFL_split"].isna()
            ],
            [
                ''
            ],
            default = df_inj_opp['rel_opp_pos_split']
        )

    prettydf['opp_team_injury_status_no_rel'] = df_inj_opp.groupby(level=0)['opp_team_injury_status_no_rel'].agg(lambda x: ','.join(v for v in x if v != ''))
    prettydf['opp_team_rel_opp_pos'] = df_inj_opp.groupby(level=0)['opp_team_rel_opp_pos'].agg(lambda x: ','.join(v for v in x if v != ''))

    grouped = prettydf.groupby(['Joueur', 'opp_team_injury_status_no_rel'])
    result = []
    for (name, opp), group in grouped:
        positions = group['Poste'].tolist()
        rels = group['opp_team_rel_opp_pos'].tolist()

        opps = opp.split(',')
        if opps == [''] :
            result.append({
                'Joueur': name,
                'pos': '-'.join(sorted(set(positions))),
                'opp_inj_status': ''
            })
            continue
        rels_split = [r.split(',') for r in rels]
        
        opp_strings = []
        for i, o in enumerate(opps):
            pos_rel_pairs = []
            for j, pos in enumerate(positions):
                rel = rels_split[j][i] if len(rels_split[j]) > i else ''
                pos_rel_pairs.append(f"{pos} : {float(rel):+.1f}%")

            opp_string = f"{o} : {' - '.join(pos_rel_pairs)}"
            opp_strings.append(opp_string)

        inj_summary = '<br>'.join(opp_strings)
        unique_pos = '-'.join(sorted(set(positions)))

        result.append({
            'Joueur': name,
            'pos': unique_pos,
            'opp_inj_status': inj_summary
        })

    result_df = pd.DataFrame(result)

    prettydf = prettydf.groupby('Joueur', as_index=False).agg({
        col: (lambda x: list(set(x))) if col in ['Poste', 'pos_rel_TTFL_v_team'] else 'first'
                for col in prettydf.columns if col not in ['Joueur', 'opp_team_injury_status_no_rel', 'opp_team_rel_opp_pos']})
        
    prettydf = prettydf.merge(result_df, on='Joueur', how='left')

    prettydf["opp_inj_status"] = np.select(
        [
            prettydf["opp_inj_status"] == ''
        ],
        [
            'Pas de joueurs blessés chez ' + prettydf['opp']
        ],
        default='Joueurs blessés chez ' + prettydf['opp'] + ' :<hr style="margin:3px 0;">' + prettydf["opp_inj_status"]
    )

    # -------------------------------------------- Clean graph data stuff ----------------------------------

    prettydf['graph_dates_split'] = prettydf['graph_dates'].str.split(',')
    prettydf['graph_opps_split'] = prettydf['graph_opps'].str.split(',')
    prettydf['graph_TTFLs_split'] = prettydf['graph_TTFLs'].str.split(',')

    exploded_graph_df = prettydf[['graph_dates_split', 'graph_opps_split', 'graph_TTFLs_split']].explode(
        ['graph_dates_split', 'graph_opps_split', 'graph_TTFLs_split'])

    exploded_graph_df['graph_dates_split'] = pd.to_datetime(exploded_graph_df['graph_dates_split'],
                                                            dayfirst=True)
    exploded_graph_df['orig_index'] = exploded_graph_df.index
    exploded_graph_df = exploded_graph_df.sort_values(['orig_index', 'graph_dates_split'])

    graph_df_sorted = (
    exploded_graph_df
    .groupby(level=0, sort=False)
    .agg({
        'graph_dates_split': lambda x: ','.join(x.dt.strftime('%d/%m/%Y')),
        'graph_opps_split': lambda x: ','.join(x),
        'graph_TTFLs_split': lambda x: ','.join(x)
    })
    )
    prettydf[['graph_dates', 'graph_opps', 'graph_TTFLs']] = graph_df_sorted

    # ------------------------------------------------- Final cleanup ---------------------------------------

    prettydf['pos_v_team'] = prettydf.apply(lambda r:"Postes contre " + r['opp'] + ' : ' + " - ".join([f"{a} : {b}" for a, b in zip(r['Poste'], r['pos_rel_TTFL_v_team'])]), axis=1)
    prettydf['allrel'] = (prettydf['rel_opp_avg_TTFL'] + '<br>' + 
                          prettydf['rel_TTFL_v_opp'] + '<br>' + 
                          prettydf['ha_rel_TTFL'] + '<br>' + 
                          prettydf['pos_v_team'] + '<br>' + 
                          prettydf['rel_btb_TTFL_with_br'] +
                          'Médiane/Ecart-type : ' + 
                          prettydf['median_TTFL'].astype(str) + '/' +
                          prettydf['stdTTFL'].astype(str) + 
                          prettydf['nemesis'].astype(str))
    
    prettydf = prettydf.sort_values(by='TTFL', ascending=False)
    prettydf = prettydf.drop(['Poste', 'pos_rel_TTFL_v_team', 'opp', 'pos_v_team', 'rel_TTFL_v_opp', 'ha_rel_TTFL'], axis = 1)
    prettydf = prettydf.rename({'pos' : 'Poste'}, axis = 1)
    prettydf['TTFL'] = prettydf['TTFL'].round(1).fillna('N/A')
    prettydf = prettydf.reset_index(drop=True)

    return prettydf