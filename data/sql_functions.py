from typing import List, Optional, Union, Dict, Any
import streamlit as st
from tqdm import tqdm
import sqlite3
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetchers.player_position_fetcher import fetch_player_positions
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
    cursor=conn.cursor()
    try:
        cursor.execute(f"""SELECT * FROM {table};""")
        table_exists = True
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            table_exists = False
            if table == 'player_positions':
                tqdm.write(f"La table {table} est manquante. Téléchargement...")
                player_pos = fetch_player_positions()
                save_to_db(conn, player_pos, table, if_exists="replace")

                conn.execute("CREATE INDEX IF NOT EXISTS idx_player_positions_player ON player_positions(playerName);")
        else:
            raise
    return table_exists

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

    run_sql_query(
        conn,
        table="boxscores",
        select=["playerName", 
                "ROUND(AVG(TTFL), 1) AS avg_TTFL",
                "ROUND(" + \
                    "CASE WHEN COUNT(*) > 0 " + \
                        "THEN SQRT((SUM(TTFL * TTFL) - SUM(TTFL) * SUM(TTFL) / COUNT(*)) / (COUNT(*))) " + \
                        "ELSE 0.0 " + \
                    "END, 1) " + \
                "AS stddev_TTFL"],
        filters=["seconds > 0"],
        group_by="playerName",
        order_by="avg_TTFL DESC",
        output_table="player_avg_TTFL"
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
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_player_avg_TTFL_player ON player_avg_TTFL(playerName);""")
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

def update_tables(conn):

    conn.execute("PRAGMA journal_mode = WAL;")

    add_missing_pos_to_rosters(conn)
    update_helper_tables(conn)
    calc_median_TTFL(conn)
    update_home_away_rel_TTFL(conn)
    update_avg_TTFL_per_pos(conn)
    update_avg_TTFL_per_pos_per_opp(conn)
    update_rel_player_avg_ttfl_v_opp(conn)
    update_absent_teammate_rel_impact(conn)
    updates_games_missed_by_players(conn)
    update_opp_pos_avg_per_game(conn)
    update_back_to_back_rel_TTFL(conn)
    
    # conn.execute("ANALYZE;")
    # conn.execute("PRAGMA optimize;")

def calc_median_TTFL(conn):
    import pandas as pd

    query = """
    WITH ordered AS (
    SELECT
        playerName,
        TTFL,
        ROW_NUMBER() OVER (
        PARTITION BY playerName
        ORDER BY TTFL
        ) AS rn,
        COUNT(*) OVER (
        PARTITION BY playerName
        ) AS cnt
    FROM boxscores
    WHERE seconds > 0
    )
    SELECT
    playerName,
    AVG(TTFL) AS median_TTFL
    FROM ordered
    WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    GROUP BY playerName
    """
    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, "median_TTFL", if_exists="replace")

def update_home_away_rel_TTFL(conn):
    import pandas as pd

    query = """
    WITH home_away_TTFL AS (
    SELECT
        playerName,
        AVG(CASE WHEN isHome = 1 AND seconds > 0 THEN TTFL END) AS home_avg_TTFL,
        AVG(CASE WHEN isHome = 0 AND seconds > 0 THEN TTFL END) AS away_avg_TTFL,
        AVG(CASE WHEN seconds > 0 THEN TTFL END) AS overall_avg_TTFL,
        COUNT(CASE WHEN isHome = 1 AND seconds > 0 THEN 1 END) AS n_home_games,
        COUNT(CASE WHEN isHome = 0 AND seconds > 0 THEN 1 END) AS n_away_games
        
    FROM boxscores
    GROUP BY playerName
    )

    SELECT 
        playerName,
        home_avg_TTFL,
        away_avg_TTFL,
        CASE
            WHEN overall_avg_TTFL IS NULL OR overall_avg_TTFL = 0 THEN NULL
            ELSE (home_avg_TTFL - overall_avg_TTFL) * 100.0 / overall_avg_TTFL
        END AS home_rel_TTFL,
        CASE
            WHEN overall_avg_TTFL IS NULL OR overall_avg_TTFL = 0 THEN NULL
            ELSE (away_avg_TTFL - overall_avg_TTFL) * 100.0 / overall_avg_TTFL
        END AS away_rel_TTFL,
        n_home_games,
        n_away_games
    FROM home_away_TTFL
    """
    df = pd.read_sql_query(query, conn)
    save_to_db(conn, df, "home_away_rel_TTFL", if_exists="replace")

def update_back_to_back_rel_TTFL(conn):
    import pandas as pd

    query = """
    WITH back_to_back AS (
    SELECT curr.playerName AS playerName, AVG(curr.TTFL) as TTFL
    FROM boxscores curr
    JOIN boxscores prev
    ON curr.playerName = prev.playerName
    AND prev.gameDate_ymd = date(curr.gameDate_ymd, '-1 day')
    GROUP BY curr.playerName
    )

    SELECT pat.playerName,
        CASE 
            WHEN pat.avg_TTFL IS NULL OR pat.avg_TTFL = 0 THEN NULL
            ELSE 100 * (btb.TTFL - pat.avg_TTFL) / pat.avg_TTFL
        END AS rel_btb_TTFL

    FROM player_avg_TTFL pat
    LEFT JOIN back_to_back btb
    ON btb.playerName = pat.playerName
    """

    df = pd.read_sql_query(query, conn)
    df.to_sql('rel_btb_TTFL', conn, if_exists='replace', index=False)

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

def topTTFL_query(conn, game_date_ymd):
    import pandas as pd

    query = """

    WITH

    schedule_ajd AS ( 
    ------------------------------------ Les matchups du soir ---------------------------------------------
    -- homeTeam  |  homeTeam_wins  |  homeTeam_losses  |  awayTeam   |  awayTeam_wins  |  awayTeam_losses
    --   IND     |        0        |         1         |     OKC     |        2        |         0
    --   GSW     |        2        |         0         |     DEN     |        0        |         1

    SELECT homeTeam, homeTeam_wins, homeTeam_losses, awayTeam, awayTeam_wins, awayTeam_losses
    FROM schedule
    WHERE gameDate_ymd = :date
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
        FROM boxscores b
        WHERE b.playerName = ap.playerName
          AND b.seconds > 0
          AND b.gameDate_ymd = date(:date, '-1 day')
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

    SELECT p.playerName, p.avg_TTFL, p.stddev_TTFL, m.median_TTFL
    FROM player_avg_TTFL p
    JOIN median_TTFL m
    ON p.playerName = m.playerName
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
    pat.avg_TTFL AS injured_player_avg_TTFL

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
    pat.avg_TTFL AS opp_player_TTFL,
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
    ir.injury_status, ir.details,

    -- Relative info (player position vs opp team, player vs opp team, player home/away, all teams vs that opp)
    prtvt.pos_rel_TTFL_v_team,
    rpatop.rel_TTFL_v_opp,
    CASE 
        WHEN ap.isHome = 1 THEN hart.home_rel_TTFL
        ELSE hart.away_rel_TTFL
    END AS ha_rel_TTFL,
    raot.rel_opp_avg_TTFL,
    btb.rel_btb_TTFL, ibtb.is_b2b,

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
    JOIN rel_btb_TTFL btb
        ON btb.playerName = ap.playerName
    JOIN is_back_to_back ibtb
        ON ibtb.playerName = ap.playerName
    GROUP BY ap.playerName, ap.team, ap.pos
    ORDER BY pat.avg_TTFL DESC
        """

    df = pd.read_sql_query(query, conn, params={'date' : game_date_ymd})

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
    ):
    import pandas as pd

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

    Returns
    -------
    pandas.DataFrame | None
        Returns a DataFrame if `return_df=True` and `output_table` is not set.
        Returns None if data is written to a table or query fails.
    """

    def ensure_list(x):
        if x is None:
            return []
        return [x] if isinstance(x, str) else x

    select_cols = ensure_list(select)
    filters = ensure_list(filters)
    group_by = ensure_list(group_by)
    having = ensure_list(having)
    order_by = ensure_list(order_by)

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
    if filters:
        query += " WHERE " + " AND ".join(filters)
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

    if verbose:
        tqdm.write(f"\n📘 Executing SQL:\n{query}\n")

    try:
        df = pd.read_sql_query(query, conn, dtype=dtypes)

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
    """
    Return a DataFrame of missing games:
    - games that are completed in 'schedule'
    - games from the regular season (id starts with 002)
    - but not yet present in 'boxscores'
    """
    import pandas as pd

    cursor = conn.cursor()
    query = """
        SELECT s.gameId, s.gameDate, s.homeTeam, s.awayTeam
        FROM schedule s
        LEFT JOIN (
            SELECT DISTINCT gameId FROM boxscores
        ) b ON s.gameId = b.gameId
        WHERE s.gameStatus = 3 AND s.gameId LIKE '002%' AND b.gameId IS NULL
        ORDER BY gameDate ASC
    """

    try:
        cursor.execute("""SELECT * FROM boxscores;""")

    except sqlite3.OperationalError as e:
        if "no such table" in str(e): # boxscores table does not exist
            query = """
            SELECT gameId, gameDate, hometeam, awayTeam
            FROM schedule
            WHERE gameStatus = 3 AND gameId LIKE '002%'
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

if __name__ == '__main__':
    from misc.misc import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        check_table_exists(conn, 'player_positions')