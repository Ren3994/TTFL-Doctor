from typing import List, Optional, Union, Dict, Any
from tqdm import tqdm
import sqlite3
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import SEASON, DB_PATH_HISTORICAL, FRANCHISE_FILTERS
from fetchers.player_position_fetcher import fetch_player_positions
from streamlit_interface.resource_manager import conn_hist_db
from fetchers.team_stats_fetcher import get_team_stats
from fetchers.schedule_fetcher import get_schedule
from fetchers.rosters_fetcher import get_rosters

def init_db(conn):
    try :
        schedule = get_schedule()
        if schedule is not None:
            save_to_db(conn, schedule, "schedule", if_exists="replace")
        else :
            tqdm.write("Schedule is None. Table could not be saved.")
    except:
        tqdm.write('Error fetching schedule. Check internet connection')
    
    rosters = get_rosters()
    if rosters is not None:
        save_to_db(conn, rosters, 'rosters', if_exists = 'replace')
    else:
        tqdm.write("Rosters is None. Table could not be saved.")

    check_table_exists(conn, 'player_positions')
    rosters_with_pos = add_pos_to_rosters(conn)
    if rosters_with_pos is not None:
        save_to_db(conn, rosters_with_pos, 'rosters', if_exists='replace')
    else:
        tqdm.write("Rosters with positions is None. Table could not be saved.")
    
    team_stats = get_team_stats()
    if team_stats is not None:
        save_to_db(conn, team_stats, 'team_stats', if_exists='replace')
    else:
        tqdm.write('Team stats table is None. Table could not be saved')

    conn.execute("CREATE INDEX IF NOT EXISTS idx_rosters_team_player ON rosters(teamTricode, playerName);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rosters_team ON rosters(teamTricode);")

def check_table_exists(conn, table):
    cursor = conn.cursor()
    table_exists = cursor.execute(f"""SELECT 1
                                        FROM sqlite_master
                                        WHERE type='table'
                                        AND name='{table}'
                                     """).fetchone()
    if not table_exists:
        if table == 'player_positions':
            tqdm.write(f"La table {table} est manquante. Téléchargement...")
            player_pos = fetch_player_positions()
            save_to_db(conn, player_pos, table, if_exists="replace")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_player_positions_player ON player_positions(playerName);")
        return False
    return True

def add_pos_to_rosters(conn):
    df = run_sql_query(
        conn,
        select=["rosters.playerName", "rosters.teamTricode", "player_positions.position"],
        table='rosters',
        joins=[
            {"type" : "LEFT", "table" : "player_positions", "on" : "rosters.playerName = player_positions.playerName"}
        ]
    )
    return df

def update_helper_tables(conn):

    run_sql_query(
        conn,
        table="boxscores",
        select=["teamTricode", "gameId"],
        distinct=True,
        output_table="team_games"
    )

    run_sql_query(
        conn,
        table="boxscores",
        select=["playerName AS playerA", "teamTricode", "gameId", "TTFL AS player_TTFL"],
        filters=["seconds > 0"],
        output_table="played"
    )

    run_sql_query(
        conn,
        table="played",
        select=["playerA AS teammate", "gameId"],
        distinct=True,
        output_table="teammate_played"
    )

    run_sql_query(conn, 
                  table="boxscores", 
                  select=[
                      'teamTricode',
                      'AVG(teamTTFL) AS avg_team_TTFL',
                      'AVG(opponentTTFL) AS avg_opp_TTFL',
                      'AVG(AVG(teamTTFL)) OVER () AS overall_avg_team_TTFL',
                      'AVG(AVG(opponentTTFL)) OVER () AS overall_avg_opp_TTFL',
                      '100 * (AVG(teamTTFL) - AVG(AVG(teamTTFL)) OVER ()) / AVG(AVG(teamTTFL)) OVER () AS rel_team_avg_TTFL',
                      '100 * (AVG(opponentTTFL) - AVG(AVG(opponentTTFL)) OVER ()) / AVG(AVG(opponentTTFL)) OVER () AS rel_opp_avg_TTFL'
                      ],
                  group_by='teamTricode', 
                  order_by='avg_opp_TTFL', 
                  output_table='rel_avg_opp_TTFL')
    
    run_sql_query(conn, 
                  table='rosters r1', 
                  select=['r1.playerName AS playerA', 
                               'r2.playerName AS teammate',
                               'r1.teamTricode'],
                  joins=[{'table' : 'rosters r2',
                        'on' : 'r1.teamTricode = r2.teamTricode'}],
                  filters='r1.playerName <> r2.playerName',
                  output_table='roster_pairs')

    cur = conn.cursor()
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_team_games_team ON team_games(teamTricode);""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_played_player_game ON played(playerA, gameId);""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_teammate_played_game ON teammate_played(teammate, gameId);""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_rp_team ON roster_pairs(teamTricode);""")
    conn.commit()

def remove_duplicates_from_boxscores(conn):
    try:
        conn.execute("""
        WITH dupes AS (
            SELECT b1.rowid
            FROM boxscores b1
            JOIN boxscores b2
              ON b1.gameId = b2.gameId
              AND b1.playerName = b2.playerName
              AND b1.rowid > b2.rowid
        )
        DELETE FROM boxscores
        WHERE rowid IN (SELECT rowid FROM dupes);
        """)
        conn.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            tqdm.write('No boxscore table')

def check_boxscores_null_games(conn):
    try:
        conn.execute("""DELETE FROM boxscores WHERE teamTTFL = 0""")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            tqdm.write('No boxscore table')

def check_boxscores_integrity(conn):
    check_boxscores_null_games(conn)
    remove_duplicates_from_boxscores(conn)

def add_missing_pos_to_rosters(conn):
    conn.execute("""
    UPDATE rosters
    SET position = (
        SELECT new_position FROM (
            SELECT 
                b.playerName,
                CASE 
                    WHEN COUNT(DISTINCT NULLIF(b.position_boxscores, '')) = 0 THEN '?'
                    WHEN COUNT(DISTINCT NULLIF(b.position_boxscores, '')) = 1 THEN MAX(NULLIF(b.position_boxscores, ''))
                    ELSE REPLACE(
                        GROUP_CONCAT(DISTINCT NULLIF(b.position_boxscores, '')),
                        ',', '-'
                    )
                END AS new_position
            FROM boxscores b
            GROUP BY b.playerName
        ) AS bps
        WHERE bps.playerName = rosters.playerName
    )
    WHERE position IS NULL
    AND EXISTS (
        SELECT 1 FROM (
            SELECT 
                b.playerName,
                CASE 
                    WHEN COUNT(DISTINCT NULLIF(b.position_boxscores, '')) = 0 THEN '?'
                    WHEN COUNT(DISTINCT NULLIF(b.position_boxscores, '')) = 1 THEN MAX(NULLIF(b.position_boxscores, ''))
                    ELSE REPLACE(
                        GROUP_CONCAT(DISTINCT NULLIF(b.position_boxscores, '')),
                        ',', '-'
                    )
                END AS new_position
            FROM boxscores b
            GROUP BY b.playerName
        ) AS bps
        WHERE bps.playerName = rosters.playerName
            AND bps.new_position IS NOT NULL
    )
    """)
    conn.commit()

def update_tables(conn, historical=False):

    calc_TTFL_stats(conn)

    if not historical:
        update_helper_tables(conn)
        add_missing_pos_to_rosters(conn)
        update_avg_TTFL_per_pos(conn)
        update_avg_TTFL_per_pos_per_opp(conn)
        update_rel_player_avg_ttfl_v_opp(conn)
        update_absent_teammate_rel_impact(conn)
        updates_games_missed_by_players(conn)
        update_opp_pos_avg_per_game(conn)
        calc_nemesis(conn)
        calc_min_resriction(conn)
        calc_streak(conn)
        calc_team_recent_wins(conn)

def calc_TTFL_stats(conn):
    import pandas as pd
    query = """
    SELECT playerName, TTFL, season, isHome, gameDate_ymd, prev_gameDate_ymd
    FROM boxscores
    WHERE seconds > 0
      AND gameId LIKE '002%'
    """
    df = pd.read_sql_query(query, conn, dtype_backend='pyarrow')

    df['playerName'] = df['playerName'].astype('category')
    df['season'] = df['season'].astype('category')

    dfavg = df[['playerName', 'TTFL', 'season']]
    overall_avg = (dfavg.groupby(['playerName'], observed=True)['TTFL']
               .agg(['median', 'mean', 'std'])
               .rename(columns={'median' : 'median_TTFL', 
                                'mean' : 'avg_TTFL',
                                'std' : 'stddev_TTFL'}))
    
    per_season_avg = (dfavg.groupby(['playerName', 'season'], observed=True)['TTFL']
                  .agg(['median', 'mean', 'std'])
                  .rename(columns={'median' : 'median_TTFL_season', 
                                   'mean' : 'avg_TTFL_season',
                                   'std' : 'stddev_TTFL_season'}))
    
    avgs = (per_season_avg.reset_index().merge(
                 overall_avg.reset_index(), on='playerName', how='left')).round(2)
    
    avgs.to_sql('player_avg_TTFL', conn, if_exists='replace', index=False)

    # Home away stats

    df_ha = df[['playerName', 'TTFL', 'isHome', 'season']]
    home = df_ha[df_ha['isHome'] == 1].groupby('playerName', observed=True)['TTFL'].agg(['mean', 'size']).rename(columns={'mean': 'home_avg_TTFL', 'size': 'n_home_games'})
    away = df_ha[df_ha['isHome'] == 0].groupby('playerName', observed=True)['TTFL'].agg(['mean', 'size']).rename(columns={'mean': 'away_avg_TTFL', 'size': 'n_away_games'})
    overall_ha = pd.concat([home, away], axis=1)

    overall_ha['overall_avg_TTFL'] = df_ha.groupby('playerName', observed=True)['TTFL'].mean()

    overall_ha['home_rel_TTFL'] = ((overall_ha['home_avg_TTFL'] - overall_ha['overall_avg_TTFL']) * 100.0 /
                                overall_ha['overall_avg_TTFL']).where(overall_ha['overall_avg_TTFL'] != 0, None)
    overall_ha['away_rel_TTFL'] = ((overall_ha['away_avg_TTFL'] - overall_ha['overall_avg_TTFL']) * 100.0 /
                                overall_ha['overall_avg_TTFL']).where(overall_ha['overall_avg_TTFL'] != 0, None)

    # Seasonal stats
    home_season = df_ha[df_ha['isHome'] == 1].groupby(['playerName', 'season'], observed=True)['TTFL'].agg(['mean', 'size']).rename(columns={'mean': 'home_avg_TTFL_season', 'size': 'n_home_games_season'})
    away_season = df_ha[df_ha['isHome'] == 0].groupby(['playerName', 'season'], observed=True)['TTFL'].agg(['mean', 'size']).rename(columns={'mean': 'away_avg_TTFL_season', 'size': 'n_away_games_season'})
    per_season_ha = pd.concat([home_season, away_season], axis=1)

    per_season_ha['overall_avg_TTFL_season'] = df_ha.groupby(['playerName', 'season'], observed=True)['TTFL'].mean()
    per_season_ha['home_rel_TTFL_season'] = ((per_season_ha['home_avg_TTFL_season'] - per_season_ha['overall_avg_TTFL_season']) * 100.0 /
                                        per_season_ha['overall_avg_TTFL_season']).where(per_season_ha['overall_avg_TTFL_season'] != 0, None)
    per_season_ha['away_rel_TTFL_season'] = ((per_season_ha['away_avg_TTFL_season'] - per_season_ha['overall_avg_TTFL_season']) * 100.0 /
                                        per_season_ha['overall_avg_TTFL_season']).where(per_season_ha['overall_avg_TTFL_season'] != 0, None)

    # Merge results
    ha = per_season_ha.reset_index().merge(overall_ha.reset_index(), on='playerName', how='left').round(2)

    ha = ha[
        [
            'playerName', 'season',
            'home_avg_TTFL', 'away_avg_TTFL', 'home_rel_TTFL', 'away_rel_TTFL',
            'n_home_games', 'n_away_games',
            'home_avg_TTFL_season', 'away_avg_TTFL_season',
            'home_rel_TTFL_season', 'away_rel_TTFL_season',
            'n_home_games_season', 'n_away_games_season'
        ]
    ]

    ha.to_sql('home_away_rel_TTFL', conn, if_exists='replace', index=False)

    df_btb = (df[['playerName', 'season', 'TTFL', 'gameDate_ymd', 'prev_gameDate_ymd']]
              .sort_values(['playerName', 'gameDate_ymd']))

    # Identify back-to-back games
    btb = df_btb.merge(
        df_btb,
        left_on=['playerName', 'season', 'prev_gameDate_ymd'],
        right_on=['playerName', 'season', 'gameDate_ymd'],
        how='inner',
        suffixes=('', '_prev'),
        sort=True
    )[['playerName', 'season', 'TTFL']].rename(columns={'TTFL': 'btb_TTFL'})

    # Calculate aggregates
    btb_overall = btb.groupby('playerName', observed=True)['btb_TTFL'].agg(['mean', 'size']).rename(columns={'mean': 'btbTTFL', 'size': 'n_btb'})
    btb_season = btb.groupby(['playerName', 'season'], observed=True)['btb_TTFL'].agg(['mean', 'size']).rename(columns={'mean': 'btbTTFL_season', 'size': 'n_btb_season'}).reset_index()

    # Merge with player averages
    btb_result = (
        btb_season
        .merge(btb_overall.reset_index(), on='playerName', how='left')
        .merge(avgs, on=['playerName', 'season'], how='left')
    )

    # Calculate relative differences
    btb_result['rel_btb_TTFL'] = (100 * (btb_result['btbTTFL'] - btb_result['avg_TTFL']) / btb_result['avg_TTFL']).where(btb_result['avg_TTFL'] != 0, None)
    btb_result['rel_btb_TTFL_season'] = (100 * (btb_result['btbTTFL_season'] - btb_result['avg_TTFL_season']) / btb_result['avg_TTFL_season']).where(btb_result['avg_TTFL_season'] != 0, None)

    # Select columns
    btb_result = btb_result[
        [
            'playerName', 'season',
            'btbTTFL', 'n_btb',
            'rel_btb_TTFL',
            'btbTTFL_season', 'n_btb_season',
            'rel_btb_TTFL_season'
        ]
    ].round(2)

    btb_result.to_sql('rel_btb_TTFL', conn, if_exists='replace', index=False)

    conn.execute("""CREATE INDEX IF NOT EXISTS idx_player_avg_TTFL_player ON player_avg_TTFL(playerName);""")
    conn.commit()

def calc_nemesis(conn):
    import pandas as pd
    import sqlite3
    import time
    from streamlit_interface.historical_data_manager import init_hist_db

    for _ in range(3):
        try:
            if not os.path.exists(DB_PATH_HISTORICAL):
                init_hist_db()
        except sqlite3.OperationalError as e:
            if "locked" not in str(e): raise
            time.sleep(0.5)

    hist_conn = conn_hist_db()

    query = """
    WITH selector AS (
        SELECT gameId, teamTricode, opponent, playerName, TTFL
        FROM boxscores
        WHERE seconds > 600
            AND gameId LIKE '002%'
    ),
    current_players AS (
        SELECT DISTINCT playerName
        FROM current_boxscores
    )
    SELECT s.playerName, teamTricode, opponent, gameId, TTFL
    FROM selector s
    JOIN current_players cp
        ON cp.playerName = s.playerName
    """

    query_avg = """SELECT DISTINCT playerName, avg_TTFL
                FROM player_avg_TTFL"""

    query_curr_team = """SELECT DISTINCT playerName, teamTricode
                        FROM rosters"""

    df = pd.read_sql_query(query, hist_conn, dtype_backend='pyarrow')
    avg = pd.read_sql_query(query_avg, hist_conn, dtype_backend='pyarrow')
    curr_team = pd.read_sql_query(query_curr_team, conn, dtype_backend='pyarrow')

    ### Player nemesis calculations

    gid = df.merge(df, on='gameId', suffixes=('_player', '_opponent'))
    gid = gid[gid['playerName_player'] != gid['playerName_opponent']]
    gid = gid[gid['teamTricode_player'] != gid['teamTricode_opponent']]

    pairs = (gid.groupby(["playerName_player", "playerName_opponent"],as_index=False)
                .agg(
                    avg_ttfl_against=("TTFL_player", "mean"),
                    games_played=("gameId", "nunique")
                    )
                .rename(columns={'playerName_player' : 'player',
                                'playerName_opponent' : 'opp'})
            )

    pairs["z"] = (pairs.groupby("player")["avg_ttfl_against"]
                    .transform(lambda x: (x - x.mean()) / x.std(ddof=0)))

    player_nemesis = pairs[(pairs["games_played"] >= 5) & (pairs["z"].abs() >= 1.5)]

    player_nemesis = (player_nemesis.merge(avg, left_on='player', right_on='playerName')
                                    .drop(columns='playerName'))

    player_nemesis = player_nemesis[player_nemesis['avg_TTFL'] > 20]

    player_nemesis['rel'] = (
        ((player_nemesis['avg_ttfl_against'] - player_nemesis['avg_TTFL']) * 100.0 / player_nemesis['avg_TTFL'])
        .where(player_nemesis['avg_TTFL'] != 0, None))

    player_nemesis = player_nemesis.merge(curr_team, left_on='opp', right_on='playerName')

    player_nemesis = (player_nemesis[['player', 'opp', 'teamTricode', 'rel', 'games_played']]
                    .rename(columns={'opp' : 'opp_player',
                                    'teamTricode' : 'opp_curr_team',
                                    'games_played' : 'games_v_player',
                                    'rel' : 'rel_v_player'})
                    .reset_index(drop=True)
                    .round(2))
    
    player_nemesis.to_sql('player_nemesis', conn, if_exists='replace', index=False)

    ### Team nemesis calculation

    team_nemesis = (df[['playerName', 'opponent', 'TTFL']]
                    .groupby(['playerName', 'opponent'], as_index=False)
                    .agg(
                        avg_ttfl_v_team=("TTFL", "mean"),
                        games_played=("TTFL", "size"))
                    .merge(avg, on='playerName', how='left')
                )

    team_nemesis["z"] = (team_nemesis.groupby("playerName")["avg_ttfl_v_team"]
                                    .transform(lambda x: (x - x.mean()) / x.std(ddof=0)))

    team_nemesis = team_nemesis[(team_nemesis["games_played"] >= 5) & (team_nemesis["z"].abs() >= 1.5)]

    team_nemesis['rel'] = (
        ((team_nemesis['avg_ttfl_v_team'] - team_nemesis['avg_TTFL']) * 100.0 / team_nemesis['avg_TTFL'])
        .where(team_nemesis['avg_TTFL'] != 0, None))

    team_nemesis = (team_nemesis[['playerName', 'opponent', 'rel', 'games_played']]
                    .rename(columns={'playerName' : 'player',
                                    'opponent' : 'opp_team',
                                    'games_played' : 'games_v_team',
                                    'rel' : 'rel_v_team'})
                    .reset_index(drop=True)
                    .round(2))
    
    team_nemesis.to_sql('team_nemesis', conn, if_exists='replace', index=False)

def calc_min_resriction(conn):
    import pandas as pd
    query = """
    WITH ranked AS (
        SELECT
            playerName,
            seconds,
            ROW_NUMBER() OVER (
                PARTITION BY playerName
                ORDER BY gameDate_ymd DESC
            ) AS rn
        FROM boxscores
        WHERE seconds > 0
    )
    SELECT
        r.playerName,
        a.avg_sec / 60 AS avg_min,
        CASE
            WHEN a.avg_sec = 0 THEN 0
            ELSE (100.0 * (r.seconds - a.avg_sec)) / a.avg_sec
        END AS rel_last,
        l5.last_5
    FROM ranked r
    JOIN (
        SELECT
            playerName,
            AVG(seconds) AS avg_sec
        FROM boxscores
        WHERE seconds > 0
        GROUP BY playerName
    ) a
        ON a.playerName = r.playerName
    LEFT JOIN (
    SELECT
        playerName,
        GROUP_CONCAT(minutes, ' - ') AS last_5
        FROM (
            SELECT
                playerName,
                seconds / 60 AS minutes
            FROM ranked
            WHERE rn IN (1, 2, 3, 4, 5)
            ORDER BY playerName, rn DESC
        )
        GROUP BY playerName
    ) l5
        ON r.playerName = l5.playerName
    WHERE r.rn = 1
    AND a.avg_sec > 60 * 15
    """

    df = pd.read_sql_query(query, conn)
    df = df[df['rel_last'] < -15].reset_index(drop=True)
    df['min_restr'] = 'Moyenne : ' + df['avg_min'].astype(int).astype(str) + ' min, récents : ' + df['last_5']
    df.to_sql('min_restrictions', conn, if_exists='replace', index=False)

def calc_team_recent_wins(conn):
    import pandas as pd

    query = """
    WITH 
    ranked AS (
        SELECT
            DISTINCT teamTricode, win, gameDate_ymd
        FROM boxscores
        ORDER BY teamTricode, gameDate_ymd DESC
    ),
    byteam AS (
       SELECT
           teamTricode, 
           CASE WHEN win = 1 THEN 'W' ELSE 'L' END AS win,
           ROW_NUMBER() OVER (PARTITION BY teamTricode) AS rn
        FROM ranked
    )
    SELECT
        teamTricode, GROUP_CONCAT(win, '') AS last_wins
    FROM byteam
    WHERE rn <= 10
    GROUP BY teamTricode
    """
    df = pd.read_sql_query(query, conn)
    df['last_wins'] = df['last_wins'].str[::-1]

    df.to_sql('team_recent_wins', conn, if_exists='replace', index=False)

def calc_streak(conn):
    import pandas as pd
    query = """
    WITH ranked AS (
        SELECT
            b.playerName,
            b.TTFL,
            pat.avg_TTFL,
            ROW_NUMBER() OVER (
                PARTITION BY b.playerName
                ORDER BY b.gameDate_ymd DESC
            ) AS rn
        FROM boxscores b
        JOIN player_avg_TTFL pat
            ON b.playerName = pat.playerName
        WHERE b.seconds > 0
    ),
    recent AS (
    SELECT 
        playerName,
        AVG(TTFL) AS recent_TTFL
    FROM ranked
    WHERE rn IN (1, 2, 3, 4, 5)
    GROUP BY playerName
    )
    SELECT
        DISTINCT r.playerName,
        r.avg_TTFL,
        re.recent_TTFL,
        CASE WHEN r.avg_TTFL = 0 THEN 0
            ELSE (100.0 * (re.recent_TTFL - r.avg_TTFL)) / r.avg_TTFL
        END AS rel_recent
    FROM ranked r
    JOIN recent re
        ON r.playerName = re.playerName
    WHERE avg_TTFL > 15
    ORDER BY rel_recent DESC
    """
    df = pd.read_sql_query(query, conn)
    df = df.round(1)

    df.to_sql('recent_streaks', conn, if_exists='replace', index=False)

def update_avg_TTFL_per_pos(conn):
    import pandas as pd

    query="""
    WITH
        -- Expand composite positions so each player can count for G, F and/or C
        position_expansion AS (
            SELECT playerName, 'G' AS pos FROM rosters WHERE position LIKE '%G%'
            UNION ALL
            SELECT playerName, 'F' AS pos FROM rosters WHERE position LIKE '%F%'
            UNION ALL
            SELECT playerName, 'C' AS pos FROM rosters WHERE position LIKE '%C%'
            UNION ALL
            SELECT playerName, '?' AS pos FROM rosters WHERE position = '?'
        ),
        boxscores_exp_pos AS (
        SELECT
                b.TTFL,
                pe.pos AS position
            FROM boxscores b
            JOIN position_expansion pe
                ON b.playerName = pe.playerName
        )
    SELECT
        position,
        AVG(TTFL) AS avg_TTFL
        FROM boxscores_exp_pos
        GROUP BY position
    """
    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, "avg_TTFL_per_pos", if_exists="replace")

def update_avg_TTFL_per_pos_per_opp(conn):
    import pandas as pd

    query="""
    WITH
        -- Expand composite positions so each player can count for G, F and/or C
        position_expansion AS (
            SELECT playerName, 'G' AS pos FROM rosters WHERE position LIKE '%G%'
            UNION ALL
            SELECT playerName, 'F' AS pos FROM rosters WHERE position LIKE '%F%'
            UNION ALL
            SELECT playerName, 'C' AS pos FROM rosters WHERE position LIKE '%C%'
            UNION ALL
            SELECT playerName, '?' AS pos FROM rosters WHERE position = '?'
        ),
        boxscores_exp_pos AS (
        SELECT
                b.TTFL,
                b.opponent,
                pe.pos AS position
            FROM boxscores b
            JOIN position_expansion pe
                ON b.playerName = pe.playerName
        )
    SELECT
        position,
        opponent,
        AVG(TTFL) AS avg_TTFL
        FROM boxscores_exp_pos
        GROUP BY opponent, position
    """
    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, "avg_TTFL_per_pos_per_opp", if_exists="replace")

def update_rel_player_avg_ttfl_v_opp(conn):
    import pandas as pd
    
    query = """
    WITH patop AS (
    SELECT 
        playerName,
        opponent,
        AVG(TTFL) AS avg_TTFL,
        COUNT(*) AS n_games_played
    FROM boxscores
    WHERE minutes > 0
    GROUP BY playerName, opponent
    )

    SELECT patop.playerName, patop.opponent, patop.n_games_played,

      CASE
        WHEN 
          patop.avg_TTFL IS NULL OR patop.avg_TTFL = 0
          OR
          pat.avg_TTFL is NULL OR pat.avg_TTFL = 0
          THEN NULL
        ELSE (patop.avg_TTFL - pat.avg_TTFL) * 100.0 / pat.avg_TTFL
      END AS rel_TTFL_v_opp

    FROM patop
    JOIN player_avg_TTFL pat
      ON patop.playerName = pat.playerName
    """

    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, "rel_patop", if_exists="replace")

def update_absent_teammate_rel_impact(conn):
    import pandas as pd

    query = """
    WITH

    -- pair_games = expand each pair across all team games
    pair_games AS (
      SELECT rp.playerA, rp.teammate, rp.teamTricode, tg.gameId
      FROM roster_pairs rp
      JOIN team_games tg
        ON rp.teamTricode = tg.teamTricode
    ),

    --aggregation (without relative TTFL)
    absent_teammate_impact AS (
      SELECT
        pg.playerA                    AS playerName,
        pg.teammate                   AS teammate,
        pg.teamTricode                AS teamTricode,
        COUNT(CASE WHEN tp.teammate IS NULL AND pp.player_TTFL IS NOT NULL
               THEN 1 END) AS games_absent_count,
        AVG(CASE WHEN tp.teammate IS NULL AND pp.player_TTFL IS NOT NULL
            THEN pp.player_TTFL END) AS avg_TTFL_when_teammate_absent

      FROM pair_games pg

      -- join teammate_played to detect when teammate was present
      LEFT JOIN teammate_played tp
        ON pg.gameId = tp.gameId
      AND pg.teammate = tp.teammate

      -- join player's TTFL for games they played
      LEFT JOIN played pp
        ON pg.gameId = pp.gameId
      AND pg.playerA = pp.playerA

      -- add average TTFL to compute the relative values
      LEFT JOIN player_avg_TTFL pat
          ON pg.playerA = pat.playerName

      GROUP BY pg.playerA, pg.teammate, pg.teamTricode
    )

    SELECT ati.playerName, ati.teammate, ati.teamTricode, ati.games_absent_count, 
      CASE
        WHEN avg_TTFL_when_teammate_absent IS NULL OR avg_TTFL_when_teammate_absent = 0
          OR pat.avg_TTFL IS NULL OR pat.avg_TTFL = 0
          THEN NULL
        ELSE (avg_TTFL_when_teammate_absent - pat.avg_TTFL) * 100.0 / pat.avg_TTFL
      END AS rel_TTFL_teammate_absent

      FROM absent_teammate_impact ati
      LEFT JOIN player_avg_TTFL pat
        ON ati.playerName = pat.playerName
    """

    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, "absent_teammate_rel_impact", if_exists="replace")

    cur = conn.cursor()
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_absent_teammate_player ON absent_teammate_rel_impact(playerName, teammate);""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_absent_teammate_team ON absent_teammate_rel_impact(teamTricode);""")
    conn.commit()
    
def updates_games_missed_by_players(conn):
    import pandas as pd

    query = """
    SELECT
        tg.gameId,
        tg.teamTricode AS team,
        r.playerName AS did_not_play
    FROM team_games tg
    JOIN rosters r
        ON tg.teamTricode = r.teamTricode
    LEFT JOIN (
        SELECT DISTINCT gameId, playerName
        FROM boxscores
        WHERE seconds > 0
    ) bs
        ON bs.gameId = tg.gameId
    AND bs.playerName = r.playerName
    JOIN player_avg_TTFL pat
        ON r.playerName = pat.playerName
    WHERE bs.playerName IS NULL AND pat.avg_TTFL IS NOT NULL
    ORDER BY tg.gameId, tg.teamTricode, r.playerName
    """

    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, 'games_missed_by_players', if_exists='replace')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_games_missed_team_game ON games_missed_by_players(gameId, team);")
    
def update_opp_pos_avg_per_game(conn):
    import pandas as pd

    query="""
    WITH
    -- Expand composite positions so each player can count for G, F and/or C
    position_expansion AS (
        SELECT playerName, 'G' AS pos FROM rosters WHERE position LIKE '%G%'
        UNION ALL
        SELECT playerName, 'F' AS pos FROM rosters WHERE position LIKE '%F%'
        UNION ALL
        SELECT playerName, 'C' AS pos FROM rosters WHERE position LIKE '%C%'
        UNION ALL
        SELECT playerName, '?' AS pos FROM rosters WHERE position = '?'
    ),
    boxscores_exp_pos AS (
    SELECT
            b.gameId, b.teamTricode, b.opponent, b.TTFL,
            pe.pos AS position

        FROM boxscores b
        JOIN position_expansion pe
            ON b.playerName = pe.playerName
    ),
    -- Compute average TTFL for each position for each game
    team_pos_avg_per_game AS (
    SELECT
        position,
        gameId,
        teamTricode,
        opponent,
        AVG(TTFL) AS avg_TTFL,
        COUNT(*) AS n_players
    FROM boxscores_exp_pos
    GROUP BY gameId, position, teamTricode, opponent
    )
    -- Join to get opponent position averages
    SELECT
        t1.gameId,
        t1.teamTricode,
        t1.opponent AS opp_team,
        t2.position AS opp_pos,
        t2.avg_TTFL  AS opp_pos_avg_TTFL,
        t2.n_players AS opp_pos_n_players

    FROM team_pos_avg_per_game t1
    JOIN team_pos_avg_per_game t2
        ON t1.gameId = t2.gameId
        AND t1.opponent = t2.teamTricode
        AND t1.teamTricode = t2.opponent
    """
    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, "opp_pos_avg_per_game", if_exists="replace")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_pos_avg_per_game_team_game ON opp_pos_avg_per_game(gameId, teamTricode);")

def topTTFL_query(conn, game_date_ymd, seasons_list=[SEASON]):
    import pandas as pd

    params_seasons = ", ".join([f":val{i}" for i in range(len(seasons_list))])
    params = {'date' : game_date_ymd}
    params.update({f"val{i}": v for i, v in enumerate(seasons_list)})

    query = f"""

    WITH

    schedule_ajd AS ( 
    ------------------------------------ Les matchups du soir ---------------------------------------------
    -- homeTeam  |  homeTeam_wins  |  homeTeam_losses  |  awayTeam   |  awayTeam_wins  |  awayTeam_losses
    --   IND     |        0        |         1         |     OKC     |        2        |         0
    --   GSW     |        2        |         0         |     DEN     |        0        |         1

    SELECT homeTeam, homeTeam_wins, homeTeam_losses, awayTeam, awayTeam_wins, awayTeam_losses
    FROM schedule
    WHERE gameDate_ymd = :date
    --AND season IN ({params_seasons})
    ),

    position_expansion AS (
    ----------- Tous les joueurs avec leurs multiples positions quand ils en ont plusieurs ----------------
    --    playerName  |  pos
    --   Luka Doncic  |   G
    --   Luka Doncic  |   F

    SELECT playerName, 'G' AS pos FROM rosters WHERE position LIKE '%G%'
    UNION ALL
    SELECT playerName, 'F' AS pos FROM rosters WHERE position LIKE '%F%'
    UNION ALL
    SELECT playerName, 'C' AS pos FROM rosters WHERE position LIKE '%C%'
    UNION ALL
    SELECT playerName, '?' AS pos FROM rosters WHERE position = '?'
    ),

    home_players AS (
    SELECT r.playerName, r.teamTricode AS team,
            sa.homeTeam_wins AS teamWins, sa.homeTeam_losses AS teamLosses,
            sa.awayTeam AS opponent, sa.awayTeam_wins AS oppWins, sa.awayTeam_losses AS oppLosses,
            1 AS isHome, pe.pos
    FROM rosters r
    JOIN schedule_ajd sa 
        ON r.teamTricode = sa.homeTeam
    JOIN position_expansion pe
        ON r.playerName = pe.playerName
    ),

    away_players AS (
    SELECT r.playerName, r.teamTricode AS team,
            sa.awayTeam_wins AS teamWins, sa.awayTeam_losses AS teamLosses,
            sa.homeTeam AS opponent, sa.homeTeam_wins AS oppWins, sa.homeTeam_losses AS oppLosses,
            0 AS isHome, pe.pos
    FROM rosters r
    JOIN schedule_ajd sa 
        ON r.teamTricode = sa.awayTeam
    JOIN position_expansion pe
        ON r.playerName = pe.playerName
    ),

    all_players AS (
    --------------------------------- Rosters for tonight's games -------------------------------------
    --    playerName  |  pos | team | teamWins | teamLosses | opponent | oppWins | oppLosses | isHome
    --  Aaron Gordon  |   F  |  DEN |     0    |      1     |    GSW   |    2    |     0     |   0
    --  Aaron Nesmith |   G  |  IND |     0    |      1     |    OKC   |    2    |     0     |   1
    --  Aaron Nesmith |   F  |  IND |     0    |      1     |    OKC   |    2    |     0     |   1

    SELECT playerName, pos, team, teamWins, teamLosses, opponent, oppWins, oppLosses, isHome
    FROM home_players
    UNION ALL
    SELECT playerName, pos, team, teamWins, teamLosses, opponent, oppWins, oppLosses, isHome
    FROM away_players
    ),
    
    is_back_to_back AS (
    SELECT
    ap.playerName,
    EXISTS (
        SELECT 1
        FROM schedule s
        WHERE (s.awayTeam = ap.team 
           OR s.homeTeam = ap.team)
          AND s.gameDate_ymd = date(:date, '-1 day')
    ) AS is_b2b
    FROM all_players ap
    ),

    inj_report AS (
    --------------------------- Le tableau (mis à jour) des joueurs blessés -----------------------------------
    -- player_name  |  simplified_status  |  injury_status  |  details
    -- Luka Garza   |          Out        |  25/10: Out ... |  Garza (concussion) has been ruled out...

    SELECT *
    FROM injury_report
    ),

    player_ha_rel_TTFL AS (
    ----------- Variation de la moyenne TTFL domicile/extérieur relative à moyenne TTFL globale -----------------
    -- playerName  |  home_rel_TTFL  |  away_rel_TTFL
    --  AJ Green   |       20.0      |      -20.0

    SELECT playerName, home_rel_TTFL, away_rel_TTFL
    FROM home_away_rel_TTFL
    ),

    rel_avg_opp_TTFL2 AS (
    ----- Variation de la moyenne des scores TTFL de l'équipe adverse (total tous les joueurs) relatif à la moyenne globale
    --  teamTricode    |    rel_opp_avg_TTFL
    --      HOU        |         -11.8
    --      OKC        |         -11.8
    --      SAS        |         -11.5

    SELECT teamTricode, rel_opp_avg_TTFL
    FROM rel_avg_opp_TTFL
    ),

    pos_avg_TTFL AS (
    ------------------------ Moyenne TTFL globale par poste (avec postes séparés) ---------------------------------
    -- position  |  avg_TTFL
    --     C     |    16.26
    --     F     |    15.32
    --     G     |    14.59

    SELECT * 
    FROM avg_TTFL_per_pos
    ),

    player_avgTTFL AS (
    ------------------------------------------- Moyennes TTFL par joueur --------------------------------------------
    --       playerName       |  avg_TTFL  |  stddev_TTFL
    --      Luka Doncic       |    62.4    |     12.6
    -- Giannis Antetokounmpo  |    59.7    |     11.6
    --     Nikola Jokic       |    54.7    |     14.6

    SELECT playerName, avg_TTFL, stddev_TTFL, median_TTFL
    FROM player_avg_TTFL 
    ),

    games_missed AS (
    ------------------------------------- Liste des matchs ratés par joueur ------------------------------------
    -- gameId  |  team  |  did_not_play
    --   001   |   OKC  | Branden Carlson
    --   001   |   OKC  |  Ousmane Dieng
    --   001   |   GSW  |  Moses Moody
    --   001   |   GSW  |  Pat Spencer

    SELECT *
    FROM games_missed_by_players
    ),

    rel_player_avg_TTFL_v_opp AS (
    ---------------------- Variation de la moyenne TTFL de chaque joueur contre chaque équipe -----------------------
    --   playerName  |  opponent  |  n_games_played  |  rel_TTFL_v_opp
    --  Luka Doncic  |     GSW    |         1        |        -8.0
    --  Luka Doncic  |     MIN    |         1        |         8.0

    SELECT * 
    FROM rel_patop
    ),

    rel_TTFL_abs_teammate AS (
    ------------------ Variation de la moyenne TTFL quand chaque coéquipier est absent ------------------------------
    --  playerName  |       teammate      |  teamTricode  |  games_absent_count  |  rel_TTFL_teammate_absent
    --   AJ Green   | Alex Antetokounmpo  |       MIL     |           2          |            0.0
    --   AJ Green   |  Andre Jackson Jr.  |       MIL     |           1          |           -20.0

    SELECT *
    FROM absent_teammate_rel_impact
    ),

    inj_teammate_rel_impact AS (
    -------------------------- Variation of TTFL score when a teammate doesn't play ------------------------------
    --    injured_player    |    playing_teammate    |    rel_TTFL_teammate_absent    |    injured_player_avg_TTFL   |   simp_status
    --  Kristaps Porzingis  |       Asa Newell       |              0.0               |             34.0             |       Out
    --  Kristaps Porzingis  |      Caleb Houstan     |              NaN               |             34.0             |       Out
    --  Kristaps Porzingis  |      Dyson Daniels     |             22.05              |             34.0             |       Out

    SELECT
    ir.player_name AS injured_player,
    ir.simplified_status AS simp_status,
    rtat.playerName AS playing_teammate,
    COALESCE(rtat.rel_TTFL_teammate_absent, '0.0') AS rel_TTFL_teammate_absent,
    COALESCE(rtat.games_absent_count, 0) AS games_absent_count,
    ROUND(pat.avg_TTFL, 1) AS injured_player_avg_TTFL

    FROM inj_report ir
    LEFT JOIN rel_TTFL_abs_teammate rtat
        ON ir.player_name = rtat.teammate
    JOIN player_avgTTFL pat
        ON ir.player_name = pat.playerName
    ),

    opp_pos_avg_per_gameId AS (
    ------------------------ Average TTFL score of opposing positions for every game ------------------------
    --   gameId    |    teamTricode    |    opp_team    |    opp_pos    |  opp_pos_avg_TTFL  
    --     001     |        HOU        |      OKC       |       C       |        31.0        
    --     001     |        HOU        |      OKC       |       F       |        14.8        
    --     001     |        HOU        |      OKC       |       G       |        19.2        
    --     001     |        OKC        |      HOU       |       C       |        30.3        
    --     001     |        OKC        |      HOU       |       F       |        10.1      

    SELECT gameId, teamTricode, opp_team, opp_pos, opp_pos_avg_TTFL
    FROM opp_pos_avg_per_game
    ),

    player_avg_rel_TTFL_per_opp_pos AS (
    --------------------- Variation of TTFL score per opponent position when player did not play --------------------
    --   did_not_play  |    opp_pos    |    avg_rel_TTFL_per_opp_pos
    --   AJ Johnson    |       C       |              31.2
    --   AJ Johnson    |       F       |              10.9
    --   AJ Johnson    |       G       |             -58.9
    --   Al Horford    |       C       |             -32.4
    --   Al Horford    |       F       |              39.7

    SELECT 
    gmbp.did_not_play, 
    opapg.opp_pos, 
    AVG(100 * (opapg.opp_pos_avg_TTFL - atpppo.avg_TTFL) / atpppo.avg_TTFL) AS avg_rel_TTFL_per_opp_pos
    FROM games_missed_by_players gmbp
    JOIN opp_pos_avg_per_gameId opapg
        ON gmbp.gameId = opapg.gameId
        AND gmbp.team = opapg.teamTricode
    JOIN avg_TTFL_per_pos_per_opp atpppo
        ON opapg.opp_pos = atpppo.position
        AND opapg.opp_team = atpppo.opponent
    GROUP BY gmbp.did_not_play, opapg.opp_pos
    ),

    pos_rel_TTFL_v_team AS (
    ----------------------- Variation of TTFL score for each position against each team -----------------------
    -- opponent    |    pos    |    pos_rel_TTFL_v_team
    --   ATL       |     C     |             35.3
    --   ATL       |     F     |             31.6
    --   ATL       |     G     |             31.0
    --   BKN       |     C     |            -17.0
    --   BKN       |     F     |            -12.8

    SELECT b.opponent, pe.pos,
    100 * (AVG(b.TTFL) - posat.avg_TTFL) / posat.avg_TTFL AS pos_rel_TTFL_v_team
    FROM boxscores b
    JOIN position_expansion pe
        ON b.playerName = pe.playerName
    JOIN pos_avg_TTFL posat
        ON pe.pos = posat.position
    GROUP BY b.opponent, pe.pos
    ),

    opp_roster_with_stats AS (
    ---------- Opponent roster with their simp status, avg TTFL, and the relative TTFL score of opposing players that match the position ------------
    --    playerName  |  pos  | inj_opp_player  | simplified_status | opp_player_TTFL | avg_rel_TTFL_per_opp_pos
    --  Aaron Holiday |   G   |  Alex Caruso    |        Out        |       11.0      |        -5.300364
    --   Al Horford   |   F   |  Jaxson Hayes   |        Out        |       11.0      |        -41.057935
    --   Al Horford   |   C   |  Jaxson Hayes   |        Out        |       11.0      |         19.375857

    SELECT 

    ap.playerName, ap.pos, 
    r.playerName AS inj_opp_player,
    ir.simplified_status,
    ROUND(pat.avg_TTFL, 1) AS opp_player_TTFL,
    COALESCE(partpop.avg_rel_TTFL_per_opp_pos, 0) AS avg_rel_TTFL_per_opp_pos

    FROM all_players ap
    JOIN rosters r
        ON r.teamTricode = ap.opponent
    JOIN inj_report ir
        ON ir.player_name = r.playerName
    JOIN player_avgTTFL pat
        ON r.playerName = pat.playerName
    LEFT JOIN player_avg_rel_TTFL_per_opp_pos partpop
        ON r.playerName = partpop.did_not_play
        AND ap.pos = partpop.opp_pos
    ),

    graph_data AS (
    ------------------------------------ Data to make the graphs in the streamlit page ----------------------------
    --    playerName    |        graph_dates        |       graph_opps       |        graph_TTFLs
    --    AJ Johnson    |   22/10/2025, 26/10/2025  |         MIL, CHA       |           2, -1
    SELECT
      playerName,
      GROUP_CONCAT(gameDate) AS graph_dates,
      GROUP_CONCAT(opponent) AS graph_opps, 
      GROUP_CONCAT(TTFL) AS graph_TTFLs,
      GROUP_CONCAT(win) AS graph_wins
    FROM boxscores
    WHERE seconds > 0
    GROUP BY playerName
    )
        --------------------------------------------- FINAL AGGREGATION ---------------------------------------------
    SELECT 
    
    -- Regular player info
    ap.playerName, ap.pos, ap.isHome, 
    ap.team, ap.teamWins, ap.teamLosses,
    ap.opponent, ap.oppWins, ap.oppLosses,
    pat.avg_TTFL, pat.stddev_TTFL, pat.median_TTFL,

    -- Player injury status
    ir.injury_status, ir.details, mr.min_restr,

    -- Relative info (player position vs opp team, player vs opp team, player home/away, all teams vs that opp)
    prtvt.pos_rel_TTFL_v_team,
    rpatop.rel_TTFL_v_opp,
    CASE 
        WHEN ap.isHome = 1 THEN hart.home_rel_TTFL
        ELSE hart.away_rel_TTFL
    END AS ha_rel_TTFL,
    raot.rel_opp_avg_TTFL,
    btb.rel_btb_TTFL, btb.n_btb, ibtb.is_b2b,
    rs.recent_TTFL, rs.rel_recent,

    -- Team and player nemesis
    tn.opp_team AS team_nemesis,
    tn.rel_v_team AS rel_TTFL_v_team_nemesis,
    tn.games_v_team AS games_v_team_nemesis,

    GROUP_CONCAT(pn.opp_player) AS player_nemesis,
    GROUP_CONCAT(pn.rel_v_player) AS rel_TTFL_v_player_nemesis,
    GROUP_CONCAT(pn.games_v_player) AS games_v_player_nemesis,
    
    -- Concatenated injured teammates info
    GROUP_CONCAT(itri.injured_player) AS injured_teammates,
    GROUP_CONCAT(itri.simp_status) AS simp_statuses,
    GROUP_CONCAT(itri.injured_player_avg_TTFL) AS inj_teammates_TTFLs,
    GROUP_CONCAT(itri.rel_TTFL_teammate_absent) AS rel_TTFL_inj_teammate_abs,
    GROUP_CONCAT(itri.games_absent_count) AS inj_teammates_abs_count,

    -- Concatenated opponents info
    GROUP_CONCAT(orws.inj_opp_player) AS inj_opponents,
    GROUP_CONCAT(orws.simplified_status) AS inj_opponents_simp_statuses,
    GROUP_CONCAT(orws.opp_player_TTFL) AS inj_opponents_TTFLs,
    GROUP_CONCAT(orws.avg_rel_TTFL_per_opp_pos) AS pos_rel_TTFL_when_inj_opp,

    -- Team and opp recent wins
    trw.last_wins AS team_last_wins,
    orw.last_wins AS opp_last_wins,

    -- Graph data
    gd.graph_dates,
    gd.graph_opps,
    gd.graph_TTFLs,
    gd.graph_wins

    FROM all_players ap
    JOIN player_avgTTFL pat
        ON ap.playerName = pat.playerName
    LEFT JOIN inj_report ir
        ON ap.playerName = ir.player_name
    LEFT JOIN inj_teammate_rel_impact itri
        ON ap.playerName = itri.playing_teammate
    LEFT JOIN opp_roster_with_stats orws
        ON ap.playerName = orws.playerName
        AND ap.pos = orws.pos
    LEFT JOIN home_away_rel_TTFL hart
        ON ap.playerName = hart.playerName
    LEFT JOIN rel_player_avg_TTFL_v_opp rpatop
        ON ap.playerName = rpatop.playerName
        AND ap.opponent = rpatop.opponent
    LEFT JOIN pos_rel_TTFL_v_team prtvt
        ON ap.opponent = prtvt.opponent
        AND ap.pos = prtvt.pos
    LEFT JOIN graph_data gd
      ON ap.playerName = gd.playerName
    JOIN rel_avg_opp_TTFL2 raot
        ON ap.opponent = raot.teamTricode
    LEFT JOIN rel_btb_TTFL btb
        ON btb.playerName = ap.playerName
    JOIN is_back_to_back ibtb
        ON ibtb.playerName = ap.playerName
    LEFT JOIN team_nemesis tn
        ON tn.player = ap.playerName
        AND tn.opp_team = ap.opponent
    LEFT JOIN player_nemesis pn
        ON pn.player = ap.playerName
        AND pn.opp_curr_team = ap.opponent
    LEFT JOIN min_restrictions mr
        ON mr.playerName = ap.playerName
    LEFT JOIN recent_streaks rs
        ON rs.playerName = ap.playerName
    LEFT JOIN team_recent_wins trw
        ON trw.teamTricode = ap.team
    LEFT JOIN team_recent_wins orw
        ON orw.teamTricode = ap.opponent
    GROUP BY ap.playerName, ap.team, ap.pos
    ORDER BY pat.avg_TTFL DESC
        """

    df = pd.read_sql_query(query, conn, params=params)

    return df

def run_sql_query(
    conn: sqlite3.Connection = None,
    table: str = '',
    select: Union[str, List[str]] = "*",
    joins: Optional[List[dict]] = None,
    filters: Optional[Union[str, List[str]]] = None,
    group_by: Optional[Union[str, List[str]]] = None,
    having: Optional[Union[str, List[str]]] = None,
    order_by: Optional[Union[str, List[str]]] = None,
    limit: Optional[int] = None,
    distinct: bool = False,
    output_table: Optional[str] = None,
    if_exists: str = "replace",
    return_df: bool = True,
    verbose: bool = False,
    group_agg: Optional[Dict[str, Union[str, Dict[str, Any], None]]] = None,
    dtypes: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    ctes: Optional[List[dict]] = None,
    ):

    """
    Parameters
    ----------
    conn : sqlite3.Connection
        Active SQLite database connection.

    table : str
        The primary table name to query from.

    select : str | list[str], default="*"
        Columns to select. Can be a single string (e.g. `"id, name"`) or a list of column names.

    joins : list[dict], optional
        List of JOIN specifications, each dict containing:
        - `"table"` (str): Table to join.
        - `"on"` (str): Join condition (e.g. `"a.id = b.user_id"`).
        - `"type"` (str): Join type ("INNER", "LEFT", etc., defaults to "INNER").

    filters : str | list[str], optional
        WHERE conditions. If multiple are provided, they are combined using `AND`.

    group_by : str | list[str], optional
        GROUP BY columns.

    having : str | list[str], optional
        HAVING clause conditions.

    order_by : str | list[str], optional
        ORDER BY columns or expressions.

    limit : int, optional
        Maximum number of rows to return.

    distinct : bool, default=False
        Whether to use SELECT DISTINCT.

    output_table : str, optional
        If provided, saves query results into this table name in the database.

    if_exists : {"replace", "append", "fail"}, default="replace"
        Behavior when output_table already exists.

    return_df : bool, default=True
        Whether to return a pandas DataFrame of the query results.
        If False, only writes to output_table (if provided).

    verbose : bool, default=False
        If True, prints the generated SQL and progress messages.

    group_agg : dict, optional
        Enables SQL aggregation and grouping. Each key is the output alias, and each value
        defines how to aggregate:
          - None → include column in GROUP BY
          - str → shorthand for GROUP_CONCAT(DISTINCT {value})
          - dict → detailed spec, e.g.:
              {"avg_score": {"agg": "AVG", "col": "score"}}
              {"ids": {"agg": "GROUP_CONCAT", "col": "id", "distinct": True}}

    dtypes : dict, optional
        Column data types to pass to `pandas.read_sql_query`.

    ctes : list[dict], optional
        List of CTE specifications, each dict containing:
        - "name" (str): Name of the CTE.
        - "table" (str): Table to query for this CTE.
        - All other keys are the same as the main function (select, joins, filters, etc.).

    Returns
    -------
    pandas.DataFrame | None
        Returns a DataFrame if `return_df=True` and `output_table` is not set.
        Returns None if data is written to a table or query fails.
    """
    import pandas as pd
    import re

    def ensure_list(x):
        if x is None:
            return []
        return [x] if isinstance(x, str) else x

    select_cols = ensure_list(select)
    filters = ensure_list(filters)
    group_by = ensure_list(group_by)
    having = ensure_list(having)
    order_by = ensure_list(order_by)
    ctes = ensure_list(ctes) if ctes else []
    params = ensure_list(params)

    sql_params = []
    final_filters = []
    empty_params = []

    for param in params:
        if params[param] == []:
            empty_params.append(param)

    for f in filters:
        named_params = re.findall(r":(\w+)", f)
        if any(np in empty_params for np in named_params):
            continue
        for p in named_params:
            if p not in params:
                raise ValueError(f"Filter uses :{p}, but params does not provide it.")
            value = params[p]
            if isinstance(value, (list, tuple, set)):
                placeholders = ','.join('?' for _ in value)
                f = f.replace(f":{p}", f"({placeholders})")
                sql_params.extend(value)  # flatten values into positional args
            else:
                f = f.replace(f":{p}", "?")
                sql_params.append(value)
        final_filters.append(f)

    # Build CTEs
    cte_sqls = []
    cte_params = []
    for cte in ctes:
        cte_name = cte["name"]
        cte_table = cte["table"]
        cte_select = ensure_list(cte.get("select", "*"))
        cte_joins = cte.get("joins", [])
        cte_filters = ensure_list(cte.get("filters", []))
        cte_group_by = ensure_list(cte.get("group_by", []))
        cte_having = ensure_list(cte.get("having", []))
        cte_order_by = ensure_list(cte.get("order_by", []))
        cte_limit = cte.get("limit")
        cte_distinct = cte.get("distinct", False)
        cte_group_agg = cte.get("group_agg")
        cte_params_local = []

        # Process CTE filters
        cte_final_filters = []
        for f in cte_filters:
            named_params = re.findall(r":(\w+)", f)
            for p in named_params:
                if p not in params:
                    raise ValueError(f"CTE filter uses :{p}, but params does not provide it.")
                value = params[p]
                if isinstance(value, (list, tuple)):
                    placeholders = ','.join('?' for _ in value)
                    f = f.replace(f":{p}", f"({placeholders})")
                    cte_params_local.extend(value)
                else:
                    f = f.replace(f":{p}", "?")
                    cte_params_local.append(value)
            cte_final_filters.append(f)

        # Build CTE SELECT clause
        group_concat_cols = []
        if cte_group_agg:
            agg_parts = []
            group_cols = []
            for alias, spec in cte_group_agg.items():
                if spec is None:
                    group_cols.append(alias)
                    agg_parts.append(alias)
                elif isinstance(spec, str):
                    out_alias = alias
                    agg_sql = f"GROUP_CONCAT(DISTINCT {spec}) AS {out_alias}"
                    agg_parts.append(agg_sql)
                    group_concat_cols.append(out_alias)
                elif isinstance(spec, dict):
                    agg_func = spec.get("agg", "").upper()
                    col = spec.get("col", alias)
                    distinct = "DISTINCT " if spec.get("distinct", False) else ""
                    out_alias = alias
                    if agg_func:
                        agg_parts.append(f"{agg_func}({distinct}{col}) AS {out_alias}")
                        if agg_func == "GROUP_CONCAT":
                            group_concat_cols.append(out_alias)
                    else:
                        group_cols.append(alias)
                        agg_parts.append(alias)
            cte_select_clause = "SELECT " + ", ".join(agg_parts)
            cte_query = f"{cte_select_clause} FROM {cte_table}"
        else:
            cte_select_clause = "SELECT DISTINCT " if cte_distinct else "SELECT "
            cte_select_clause += ", ".join(cte_select) if cte_select else "*"
            cte_query = f"{cte_select_clause} FROM {cte_table}"

        # Add CTE JOINs
        for j in cte_joins:
            join_type = j.get("type", "INNER").upper()
            join_table = j["table"]
            join_condition = j["on"]
            cte_query += f" {join_type} JOIN {join_table} ON {join_condition}"

        # CTE clauses
        if cte_final_filters:
            cte_query += " WHERE " + " AND ".join(cte_final_filters)
        if cte_group_agg and group_cols:
            cte_query += " GROUP BY " + ", ".join(group_cols)
        elif cte_group_by:
            cte_query += " GROUP BY " + ", ".join(cte_group_by)
        if cte_having:
            cte_query += " HAVING " + " AND ".join(cte_having)
        if cte_order_by:
            cte_query += " ORDER BY " + ", ".join(cte_order_by)
        if cte_limit is not None:
            cte_query += f" LIMIT {cte_limit}"

        cte_sqls.append(f"{cte_name} AS (\n{cte_query}\n)")
        cte_params.extend(cte_params_local)

    # Build SELECT clause
    group_concat_cols = []  # holds the *aliases* created by GROUP_CONCAT so we can clean them afterwards
    if group_agg:
        agg_parts = []
        group_cols = []
        for alias, spec in group_agg.items():
            # spec == None means "include this column in GROUP BY" (no aggregation)
            if spec is None:
                group_cols.append(alias)
                agg_parts.append(alias)
            elif isinstance(spec, str):
                # shorthand: group_agg={"gameIds": "gameId"} -> GROUP_CONCAT(DISTINCT gameId) AS gameIdS
                out_alias = alias
                agg_sql = f"GROUP_CONCAT(DISTINCT {spec}) AS {out_alias}"
                agg_parts.append(agg_sql)
                group_concat_cols.append(out_alias)
            elif isinstance(spec, dict):
                agg_func = spec.get("agg", "").upper()
                col = spec.get("col", alias)
                distinct = "DISTINCT " if spec.get("distinct", False) else ""
                out_alias = alias
                if agg_func:
                    # e.g. {"avg_TTFL": {"agg": "AVG", "col": "TTFL"}}
                    agg_parts.append(f"{agg_func}({distinct}{col}) AS {out_alias}")
                    if agg_func == "GROUP_CONCAT":
                        group_concat_cols.append(out_alias)
                else:
                    group_cols.append(alias)
                    agg_parts.append(alias)
        select_clause = "SELECT " + ", ".join(agg_parts)
        query = f"{select_clause} FROM {table}"
    else:
        select_clause = "SELECT DISTINCT " if distinct else "SELECT "
        select_clause += ", ".join(select_cols) if select_cols else "*"
        query = f"{select_clause} FROM {table}"

    # Add JOINs
    if joins:
        for j in joins:
            join_type = j.get("type", "INNER").upper()
            join_table = j["table"]
            join_condition = j["on"]
            query += f" {join_type} JOIN {join_table} ON {join_condition}"

    # Clauses
    if final_filters:
        query += " WHERE " + " AND ".join(final_filters)
    if group_agg and group_cols:
        query += " GROUP BY " + ", ".join(group_cols)
    elif group_by:
        query += " GROUP BY " + ", ".join(group_by)
    if having:
        query += " HAVING " + " AND ".join(having)
    if order_by:
        query += " ORDER BY " + ", ".join(order_by)
    if limit is not None:
        query += f" LIMIT {limit}"

    # Combine CTEs and main query
    if cte_sqls:
        cte_part = ",\n".join(cte_sqls)
        query = f"WITH {cte_part}\n{query}"

    all_params = cte_params + sql_params
    if verbose:
        tqdm.write(f"\n📘 Executing SQL:\n{query}\nWith params : {all_params}")

    try:
        df = pd.read_sql_query(query, conn, dtype=dtypes, params=all_params)

        # Clean up any GROUP_CONCAT columns produced by group_agg (using alias names collected)
        for col in group_concat_cols:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype("string")
                    .fillna("")
                    .str.split(",")
                    .apply(lambda lst: [v.strip() for v in lst if v])
                )

        if output_table:
            save_to_db(conn, df, output_table, if_exists=if_exists)
            if verbose:
                tqdm.write(f"✅ Wrote {len(df)} rows to '{output_table}'")
            return None

        if return_df:
            if verbose:
                tqdm.write(f"✅ Query returned {len(df)} rows ({len(df.columns)} columns)")
            return df

    except Exception as e:
        tqdm.write(f"❌ SQL query failed: {e}")
        tqdm.write(f"Query:\n{query}")
        return None

def save_to_db(conn, df, table_name, if_exists, index=False):
    try:
        df.to_sql(table_name, conn, if_exists=if_exists, index=index, chunksize=500)
    except Exception as e:
        tqdm.write(f"Error saving to DB: {e} {df.columns} {if_exists}")
        return

def get_missing_gameids(conn):
    import pandas as pd

    cursor = conn.cursor()
    query = """
        SELECT s.gameId, s.gameDate, s.homeTeam, s.awayTeam
        FROM schedule s
        LEFT JOIN (
            SELECT DISTINCT gameId FROM boxscores
        ) b ON s.gameId = b.gameId
        WHERE s.gameStatus = 3 
          AND s.gameId LIKE '002%'
          AND s.postponed = 0
          AND b.gameId IS NULL
        ORDER BY gameDate ASC
    """

    try:
        cursor.execute("""SELECT gameId, gameDate, hometeam, awayTeam FROM schedule;""")
    except:
        schedule = get_schedule()
        if schedule is not None:
            save_to_db(conn, schedule, "schedule", if_exists="replace")
        else :
            tqdm.write("Schedule is None. Table could not be saved.")

    try:
        cursor.execute("""SELECT * FROM boxscores;""")

    except sqlite3.OperationalError as e:
        if "no such table" in str(e): # boxscores table does not exist
            query = """
            SELECT gameId, gameDate, hometeam, awayTeam
            FROM schedule
            WHERE gameStatus = 3 AND gameId LIKE '002%' AND postponed = 0
            ORDER BY gameDate ASC
            """

    missing_games = pd.read_sql_query(query, conn)

    return missing_games

def get_games_for_date(conn, game_date_str):
    import pandas as pd

    df = pd.read_sql_query(f"SELECT * FROM schedule WHERE gameDate = '{game_date_str}'", conn)
    
    df['homeTeam'] = df['homeTeam'].fillna('TBD') # For games where teams have not yet been determined (IST final bracket, ...)
    df['awayTeam'] = df['awayTeam'].fillna('TBD')

    df["pair_key"] = df.apply(lambda x: tuple(sorted([x["homeTeam"], x["awayTeam"]])), axis=1)

    df_unique = df.drop_duplicates(subset="pair_key").copy()
    df_unique = df_unique.drop(columns=["pair_key"])

    return df_unique

def query_player_stats(conn, alltime=False, only_active_players=False, seasons=[], playoffs='Saison régulière', team=''):
    import pandas as pd
    
    if alltime:
        try:
            conn.execute('SELECT * FROM player_avg_TTFL')
        except:
            update_tables(conn, historical=True)

    boxscore_cols = """
        playerName, seconds, points, assists, steals, blocks, turnovers, plusMinusPoints, TTFL, 
        reboundsTotal, reboundsOffensive, reboundsDefensive, fieldGoalsMade, fieldGoalsAttempted, 
        threePointersMade, threePointersAttempted, freeThrowsMade, freeThrowsAttempted, season, 
        gameDate_ymd"""
    
    agg_cols = """
        playerName, COUNT(*) AS GP, ROUND(AVG(seconds), 1) AS SECONDS, SUM(seconds) AS TOT_SECONDS, 
        AVG(points) AS Pts, SUM(points) AS TOT_Pts, AVG(assists) AS Ast, SUM(assists) AS TOT_Ast, 
        AVG(steals) AS Stl, SUM(steals) AS TOT_Stl, AVG(blocks) AS Blk, SUM(blocks) AS TOT_Blk, 
        (AVG(steals) + AVG(blocks)) AS Stk, (SUM(steals) + SUM(blocks)) AS TOT_Stk, 
        AVG(reboundsTotal) AS Reb, SUM(reboundsTotal) AS TOT_Reb, 
        AVG(reboundsOffensive) AS Oreb, SUM(reboundsOffensive) AS TOT_Oreb, 
        AVG(reboundsDefensive) AS Dreb, SUM(reboundsDefensive) AS TOT_Dreb, 
        AVG(turnovers) AS Tov, SUM(turnovers) AS TOT_Tov, 
        AVG(fieldGoalsMade) AS FGM, SUM(fieldGoalsMade) AS TOT_FGM, 
        AVG(fieldGoalsAttempted) AS FGA, SUM(fieldGoalsAttempted) AS TOT_FGA, 
        AVG(threePointersMade) AS FG3M, SUM(threePointersMade) AS TOT_FG3M, 
        AVG(threePointersAttempted) AS FG3A, SUM(threePointersAttempted) AS TOT_FG3A, 
        AVG(freeThrowsMade) AS FTM, SUM(freeThrowsMade) AS TOT_FTM, 
        AVG(freeThrowsAttempted) AS FTA, SUM(freeThrowsAttempted) AS TOT_FTA, 
        AVG(plusMinusPoints) AS PM, SUM(plusMinusPoints) AS TOT_PM, 
        SUM(TTFL) AS TOT_TTFL, 
        (SUM(fieldGoalsMade) * 1.0 / SUM(fieldGoalsAttempted)) AS FG_PCT,
        (SUM(threePointersMade) * 1.0 / SUM(threePointersAttempted)) AS FG3_PCT, 
        (SUM(freeThrowsMade) * 1.0 / SUM(freeThrowsAttempted)) AS FT_PCT, 
        ((SUM(fieldGoalsMade) + 0.5 * SUM(threePointersMade)) / SUM(fieldGoalsAttempted)) AS EFG, 
        (SUM(points) / (2 * (SUM(fieldGoalsAttempted) + 0.44 * SUM(freeThrowsAttempted)))) AS TS, 
        (SUM(assists) * 1.0 / NULLIF(SUM(turnovers), 0)) AS ast_to_tov, 
        SUM(TTFL) * 1.0 / (SUM(seconds) / 60) AS ttfl_per_min, 
        MAX(TTFL) AS max_ttfl, MIN(TTFL) AS min_ttfl,
        MAX(gameDate_ymd) AS last_date
        """
    
    add_teamTricode = ', b.teamTricode' if not alltime else ''
    join_last_teamTricode = 'JOIN boxscores b ON b.playerName = agg.playerName AND b.gameDate_ymd = agg.last_date' if not alltime else ''
    active_players = ('active_players AS (SELECT DISTINCT playerName FROM current_boxscores),'
                      if only_active_players else '')
    join_active_players = ('JOIN active_players ap ON ap.playerName = se.playerName' 
                           if only_active_players else '')
    
    add_seasons = f"""AND season IN ({', '.join(['?'] * len(seasons))})""" if len(seasons) > 0 else ''
    if playoffs == 'Saison régulière':
        add_playoffs = "AND gameId LIKE '002%'"
    elif playoffs == 'Playoffs':
        add_playoffs = "AND gameId LIKE '004%'"
    elif playoffs == 'Les deux':
        add_playoffs = "AND (gameId LIKE '004%' OR gameId LIKE '002%')"

    add_team = f"AND ({FRANCHISE_FILTERS[team]})" if team != '' else ''
    
    query = f"""
    WITH selector AS (
        SELECT 
            {boxscore_cols} FROM boxscores
        WHERE seconds > 0
        {add_playoffs}
        {add_seasons}
        {add_team}
    ),

    {active_players}

    aggregator AS (
        SELECT se.{agg_cols}
        FROM selector se
        {join_active_players} 
        GROUP BY se.playerName
    ),
    
    avg AS (
        SELECT playerName, avg_TTFL AS TTFL, stddev_TTFL, median_TTFL
        FROM player_avg_TTFL 
        GROUP BY playerName
    ),

    home_away AS (
        SELECT playerName, home_rel_TTFL, away_rel_TTFL, home_avg_TTFL, away_avg_TTFL 
        FROM home_away_rel_TTFL 
        GROUP BY playerName
    ),

    back_to_back AS (
        SELECT playerName, btbTTFL, rel_btb_TTFL, n_btb 
        FROM rel_btb_TTFL 
        GROUP BY playerName
    )

    SELECT 
        agg.playerName, pat.TTFL, GP, agg.SECONDS, TOT_SECONDS, Pts, TOT_Pts, Ast, TOT_Ast, Stl, TOT_Stl, Blk, TOT_Blk, 
        Stk, TOT_Stk, Reb, TOT_Reb, Oreb, TOT_Oreb, Dreb, TOT_Dreb, Tov, TOT_Tov, FGM, TOT_FGM, FGA, TOT_FGA, 
        FG3M, TOT_FG3M, FG3A, TOT_FG3A, FTM, TOT_FTM, FTA, TOT_FTA, PM, TOT_PM, TOT_TTFL, FG_PCT, FG3_PCT, FT_PCT, 
        EFG, TS, ast_to_tov, ttfl_per_min, max_ttfl, min_ttfl, pat.median_TTFL, pat.stddev_TTFL, ha.home_rel_TTFL, 
        ha.away_rel_TTFL, ha.home_avg_TTFL, ha.away_avg_TTFL, btb.btbTTFL, btb.rel_btb_TTFL, btb.n_btb
        {add_teamTricode}

    FROM aggregator agg
    LEFT JOIN home_away ha 
        ON ha.playerName = agg.playerName 
    LEFT JOIN back_to_back btb 
        ON btb.playerName = agg.playerName 
    LEFT JOIN avg pat 
        ON pat.playerName = agg.playerName
    {join_last_teamTricode}
    """
    df = pd.read_sql_query(query, conn, params=seasons)
    return df

def query_player_stats_by_season(conn, player, seasons=[], playoffs='Saison régulière', team=''):
    import pandas as pd

    boxscore_cols = """
        playerName, seconds, points, assists, steals, blocks, turnovers, plusMinusPoints, TTFL, 
        reboundsTotal, reboundsOffensive, reboundsDefensive, fieldGoalsMade, fieldGoalsAttempted, 
        threePointersMade, threePointersAttempted, freeThrowsMade, freeThrowsAttempted, season"""
    
    agg_cols = """
        playerName, COUNT(*) AS GP, ROUND(AVG(seconds), 1) AS SECONDS, SUM(seconds) AS TOT_SECONDS, 
        AVG(points) AS Pts, SUM(points) AS TOT_Pts, AVG(assists) AS Ast, SUM(assists) AS TOT_Ast, 
        AVG(steals) AS Stl, SUM(steals) AS TOT_Stl, AVG(blocks) AS Blk, SUM(blocks) AS TOT_Blk, 
        (AVG(steals) + AVG(blocks)) AS Stk, (SUM(steals) + SUM(blocks)) AS TOT_Stk, 
        AVG(reboundsTotal) AS Reb, SUM(reboundsTotal) AS TOT_Reb, 
        AVG(reboundsOffensive) AS Oreb, SUM(reboundsOffensive) AS TOT_Oreb, 
        AVG(reboundsDefensive) AS Dreb, SUM(reboundsDefensive) AS TOT_Dreb, 
        AVG(turnovers) AS Tov, SUM(turnovers) AS TOT_Tov, 
        AVG(fieldGoalsMade) AS FGM, SUM(fieldGoalsMade) AS TOT_FGM, 
        AVG(fieldGoalsAttempted) AS FGA, SUM(fieldGoalsAttempted) AS TOT_FGA, 
        AVG(threePointersMade) AS FG3M, SUM(threePointersMade) AS TOT_FG3M, 
        AVG(threePointersAttempted) AS FG3A, SUM(threePointersAttempted) AS TOT_FG3A, 
        AVG(freeThrowsMade) AS FTM, SUM(freeThrowsMade) AS TOT_FTM, 
        AVG(freeThrowsAttempted) AS FTA, SUM(freeThrowsAttempted) AS TOT_FTA, 
        AVG(plusMinusPoints) AS PM, SUM(plusMinusPoints) AS TOT_PM, 
        SUM(TTFL) AS TOT_TTFL, 
        (SUM(fieldGoalsMade) * 1.0 / SUM(fieldGoalsAttempted)) AS FG_PCT,
        (SUM(threePointersMade) * 1.0 / SUM(threePointersAttempted)) AS FG3_PCT, 
        (SUM(freeThrowsMade) * 1.0 / SUM(freeThrowsAttempted)) AS FT_PCT, 
        ((SUM(fieldGoalsMade) + 0.5 * SUM(threePointersMade)) / SUM(fieldGoalsAttempted)) AS EFG, 
        (SUM(points) / (2 * (SUM(fieldGoalsAttempted) + 0.44 * SUM(freeThrowsAttempted)))) AS TS, 
        (SUM(assists) * 1.0 / NULLIF(SUM(turnovers), 0)) AS ast_to_tov, 
        SUM(TTFL) * 1.0 / (SUM(seconds) / 60) AS ttfl_per_min, 
        MAX(TTFL) AS max_ttfl, MIN(TTFL) AS min_ttfl
        """
    
    add_seasons = f"""AND season IN ({', '.join(['?'] * len(seasons))})""" if len(seasons) > 0 else ''
    if playoffs == 'Saison régulière':
        add_playoffs = "AND gameId LIKE '002%'"
    elif playoffs == 'Playoffs':
        add_playoffs = "AND gameId LIKE '004%'"
    elif playoffs == 'Les deux':
        add_playoffs = "AND (gameId LIKE '004%' OR gameId LIKE '002%')"

    add_team = f"AND {FRANCHISE_FILTERS[team]}" if team != '' else ''
    
    query = f"""
    WITH selector AS (
        SELECT 
            {boxscore_cols} FROM boxscores
        WHERE playerName = "{player}"
        AND seconds > 0
        {add_playoffs}
        {add_seasons}
        {add_team}
    ),

    avg_season AS (
        SELECT
            season,
            avg_TTFL_season,
            stddev_TTFL_season,
            median_TTFL_season
        FROM player_avg_TTFL 
        WHERE playerName = "{player}"
    ),

    home_away_season AS (
        SELECT 
            season,
            home_rel_TTFL_season, 
            away_rel_TTFL_season, 
            home_avg_TTFL_season, 
            away_avg_TTFL_season

        FROM home_away_rel_TTFL 
        WHERE playerName = "{player}"
    ),

    back_to_back_season AS (
        SELECT 
            season,
            btbTTFL_season, 
            rel_btb_TTFL_season, 
            n_btb_season

        FROM rel_btb_TTFL 
        WHERE playerName = "{player}"
    ),

    global AS (
        SELECT
            'Global' AS season,
            se.{agg_cols},
            a.avg_TTFL AS TTFL, 
            a.stddev_TTFL, 
            a.median_TTFL,
            ha.home_rel_TTFL, 
            ha.away_rel_TTFL, 
            ha.home_avg_TTFL, 
            ha.away_avg_TTFL,
            btb.btbTTFL, 
            btb.rel_btb_TTFL, 
            btb.n_btb

        FROM selector se
        CROSS JOIN (
            SELECT avg_TTFL, stddev_TTFL, median_TTFL
            FROM player_avg_TTFL
            WHERE playerName = "{player}"
            LIMIT 1
        ) a
        CROSS JOIN (
            SELECT home_rel_TTFL, away_rel_TTFL, home_avg_TTFL, away_avg_TTFL
            FROM home_away_rel_TTFL
            WHERE playerName = "{player}"
            LIMIT 1
        ) ha
        CROSS JOIN (
            SELECT btbTTFL, rel_btb_TTFL, n_btb
            FROM rel_btb_TTFL
            WHERE playerName = "{player}"
            LIMIT 1
        ) btb
        GROUP BY se.playerName
    ),

    by_season AS (
        SELECT 
            a.season,
            se.{agg_cols},
            a.avg_TTFL_season AS TTFL,
            a.stddev_TTFL_season AS stddev_TTFL,
            a.median_TTFL_season AS median_TTFL,
            ha.home_rel_TTFL_season AS home_rel_TTFL,
            ha.away_rel_TTFL_season AS away_rel_TTFL,
            ha.home_avg_TTFL_season AS home_avg_TTFL,
            ha.away_avg_TTFL_season AS away_avg_TTFL,
            btb.btbTTFL_season AS btbTTFL,
            btb.rel_btb_TTFL_season AS rel_btb_TTFL,
            btb.n_btb_season AS n_btb_season

        FROM selector se
        JOIN avg_season a 
            ON se.season = a.season
        JOIN home_away_season ha 
            ON se.season = ha.season
        JOIN back_to_back_season btb 
            ON se.season = btb.season
        GROUP BY se.season
        ORDER BY se.season DESC
    )

    SELECT * FROM global
    UNION ALL
    SELECT * FROM by_season
    """

    df = pd.read_sql_query(query, conn, params=seasons)
    return df

def query_player_v_team(conn, player, alltime, seasons, playoffs, team):
    import pandas as pd

    if alltime:
        try:
            conn.execute('SELECT * FROM player_avg_TTFL')
        except:
            update_tables(conn, historical=True)

    boxscore_cols = '''
        playerName, opponent, TTFL, points, assists, reboundsTotal, reboundsOffensive, reboundsDefensive, 
        steals, blocks, turnovers, fieldGoalsMade, fieldGoalsAttempted, threePointersMade, 
        threePointersAttempted, freeThrowsMade, freeThrowsAttempted, plusMinusPoints, seconds, season
    '''
    agg_cols = '''
        opponent, COUNT(*) AS GP, AVG(TTFL) AS TTFL, AVG(points) AS Pts, 
        AVG(assists) AS Ast, AVG(reboundsTotal) AS Reb, AVG(steals) AS Stl, 
        AVG(blocks) AS Blk, AVG(turnovers) AS Tov,
        AVG(fieldGoalsMade) AS FGM, AVG(fieldGoalsAttempted) AS FGA,
        AVG(threePointersMade) AS FG3M, AVG(threePointersAttempted) AS FG3A,
        AVG(freeThrowsMade) AS FTM, AVG(freeThrowsAttempted) AS FTA,
        AVG(plusMinusPoints) AS PM, AVG(seconds) AS seconds,
        AVG(reboundsOffensive) AS Oreb, AVG(reboundsDefensive) AS Dreb,
        (AVG(fieldGoalsMade) / AVG(fieldGoalsAttempted)) AS FG_PCT,
        (AVG(threePointersMade) / AVG(threePointersAttempted)) AS FG3_PCT,
        (AVG(freeThrowsMade) / AVG(freeThrowsAttempted)) AS FT_PCT,
        ROUND((100 * (AVG(fieldGoalsMade) + 0.5 * AVG(threePointersMade)) / AVG(fieldGoalsAttempted)), 1) AS EFG,
        ROUND(100 * (SUM(points) / (2 * (SUM(fieldGoalsAttempted) + 0.44 * SUM(freeThrowsAttempted)))), 1) AS TS,
        ROUND((AVG(assists) / NULLIF(AVG(turnovers), 0)), 1) AS ast_to_tov'''
    
    add_seasons = f"""AND season IN ({', '.join(['?'] * len(seasons))})""" if len(seasons) > 0 else ''
    if playoffs == 'Saison régulière':
        add_playoffs = "WHERE gameId LIKE '002%'"
    elif playoffs == 'Playoffs':
        add_playoffs = "WHERE gameId LIKE '004%'"
    elif playoffs == 'Les deux':
        add_playoffs = "WHERE (gameId LIKE '004%' OR gameId LIKE '002%')"
    
    add_team = f"AND {FRANCHISE_FILTERS[team]}" if team != '' else ''

    query = f"""
    WITH selector AS (
        SELECT 
            {boxscore_cols} FROM boxscores
            {add_playoffs}
            {add_team}
    )
    SELECT {agg_cols}
    FROM selector
    WHERE seconds > 0
        AND playerName = "{player}"
        {add_seasons}
    GROUP BY opponent
    """
    df = pd.read_sql_query(query, conn, params=seasons)
    return df

def query_historique_des_perfs(conn, player, alltime, seasons, playoffs, team):
    import pandas as pd

    if alltime:
        try:
            conn.execute('SELECT * FROM player_avg_TTFL')
        except:
            update_tables(conn, historical=True)

    add_seasons = f"""AND season IN ({', '.join(['?'] * len(seasons))})""" if len(seasons) > 0 else ''
    if playoffs == 'Saison régulière':
        add_playoffs = "AND gameId LIKE '002%'"
    elif playoffs == 'Playoffs':
        add_playoffs = "AND gameId LIKE '004%'"
    elif playoffs == 'Les deux':
        add_playoffs = "AND (gameId LIKE '004%' OR gameId LIKE '002%')"

    add_team = f"AND {FRANCHISE_FILTERS[team]}" if team != '' else ''
            
    query = f"""
    SELECT * 
    FROM boxscores
    WHERE seconds > 0
        AND playerName = "{player}"
        {add_seasons}
        {add_playoffs}
        {add_team}
    """
    df = pd.read_sql_query(query, conn, params=seasons)
    return df

def query_opp_team_avgs(conn):
    import pandas as pd
    query = """
    WITH
    per_gid AS (
        SELECT opponent, gameId, 
        SUM(points) AS pts, SUM(assists) AS ast,
        SUM(reboundsTotal) AS reb, SUM(reboundsOffensive) AS Oreb, SUM(reboundsDefensive) AS Dreb,
        SUM(turnovers) AS tov, SUM(steals) AS stl, SUM(blocks) AS blk,
        SUM(fieldGoalsMade) AS FGM, SUM(fieldGoalsAttempted) AS FGA,
        SUM(threePointersMade) AS FG3M, SUM(threePointersAttempted) AS FG3A,
        SUM(freeThrowsMade) AS FTM, SUM(freeThrowsAttempted) AS FTA,
        MIN(win) AS win
        FROM boxscores 
        WHERE seconds > 0
        GROUP BY gameId, opponent
    )
    SELECT opponent AS teamTricode, AVG(pts) as pts, AVG(ast) AS ast, AVG(reb) AS reb,
        AVG(Oreb) AS Oreb, AVG(Dreb) AS Dreb, AVG(tov) AS tov, AVG(stl) AS stl, AVG(blk) AS blk,
        AVG(FGM) AS opp_FGM, AVG(FGA) AS opp_FGA, 100.0 * AVG(FGM) / AVG(FGA) AS opp_FG_PCT,
        AVG(FG3M) AS opp_FG3M, AVG(FG3A) AS opp_FG3A, 100.0 * AVG(FG3M) / AVG(FG3A) AS opp_FG3_PCT,
        AVG(FTM) AS opp_FTM, AVG(FTA) AS opp_FTA, 100.0 * AVG(FTM) / AVG(FTA) AS opp_FT_PCT,
        (100.0 * (SUM(FGM) + 0.5 * SUM(FG3M)) / SUM(FGA)) AS opp_EFG,
        100.0 * (SUM(pts) / (2 * (SUM(FGA) + 0.44 * SUM(FTA)))) AS opp_TS,
        SUM(win) AS wins
        
    FROM per_gid
    GROUP BY opponent
    ORDER BY pts DESC
    """

    df = pd.read_sql_query(query, conn)
    return df

if __name__ == '__main__':
    from misc.misc import DB_PATH, DB_PATH_HISTORICAL
    with sqlite3.connect(DB_PATH_HISTORICAL) as conn:
        # print(query_player_stats(conn, alltime=True, only_active_players=True)['FG_PCT'])
        # print(query_player_v_team(conn, 'Larry Bird', alltime=True))
        # print(query_historique_des_perfs(conn, 'Larry Bird', True))
        # calc_nemesis(conn)
        print(query_player_stats_by_season(conn, 'LeBron James', playoffs='Playoffs'))
