"""
diagnose_diffs.py - explains the differences validate_port.py reports. Read-only on your databases.

    python diagnose_diffs.py            # fast: queries only (seconds)
    python diagnose_diffs.py --full     # + rebuilds the OLD nemesis tables on temporary copies of your .db files
                                        #   (runs your old calc_nemesis; takes a few minutes) and diffs them with the port

What each section settles
  1. rel_patop      -> rows where the old filter (`minutes > 0`, a TEXT comparison) and `seconds > 0` disagree
  2. home_away      -> the NULL-vs-0 counts (pandas concat left NaN for 'no home / no away games')
  3. data sync      -> accounts for every game that is in the SQLite hist db but not in the parquet files (your
                       SQLite keeps receiving games after the migration: re-run `python ttfl_data.py` to sync), and
                       checks that the hist `player_avg_TTFL` the old nemesis divides by is not stale.
  4. --full         -> a CONTROLLED test: your old calc_nemesis and the port both read the SAME data and the SAME
                       active-player table from temporary copies of the .db files. Identical = the port is right;
                       different = a real logic difference (send me the output).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile

import polars as pl

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from misc.misc import DB_PATH_HISTORICAL, DB_PATH_LAST_SEASON, LAST_SEASON  # noqa: E402

import ttfl_stats as S  # noqa: E402
import validate_port as V  # noqa: E402
from ttfl_data import scan_boxscores  # noqa: E402

c = pl.col


def q(conn, query: str) -> pl.DataFrame:
    return pl.read_database(query, conn, infer_schema_length=None)


def section(title: str) -> None:
    print(f"\n=== {title}")


def check_minutes_vs_seconds(conn) -> None:
    section("1. rel_patop: rows where `minutes > 0` and `seconds > 0` disagree")
    rows = q(conn, """SELECT playerName, opponent, gameId, minutes, seconds, TTFL,
                             COALESCE(minutes > 0, 0) AS old_counts_it, COALESCE(seconds > 0, 0) AS port_counts_it
                      FROM boxscores WHERE COALESCE(minutes > 0, 0) != COALESCE(seconds > 0, 0)""")
    print(f"{rows.height} rows (old_counts_it=1/port_counts_it=0 means a game with 0 seconds was counted as played)")
    if rows.height:
        print(rows.head(15))
        print(rows.group_by("minutes", "seconds", "old_counts_it").len().sort("len", descending=True).head(5))
    print("-> if these rows explain the 1 pair only in the old table and the 2 count/rel differences, the port is"
          " right (a game with 0 seconds is not a game played) and the old filter was the bug.")


def check_home_away(conn) -> None:
    section("2. home_away_rel_TTFL: NULL counts in the old table")
    r = q(conn, "SELECT playerName, season, n_home_games, n_away_games, home_avg_TTFL, away_avg_TTFL "
                "FROM home_away_rel_TTFL WHERE n_home_games IS NULL OR n_away_games IS NULL")
    print(f"{r.filter(c('n_home_games').is_null()).height} players with NULL n_home_games, "
          f"{r.filter(c('n_away_games').is_null()).height} with NULL n_away_games (you saw 3 and 8)")
    print(r.head(5))
    print("-> NULL = the player had no home (or no away) games; the port stores 0. Same information, validate_port"
          " now treats them as equal.")


def check_nemesis_inputs(hist) -> None:
    section("3. data sync: SQLite hist db vs parquet, and stored averages")
    sql_games = q(hist, "SELECT gameId, MIN(gameDate_ymd) AS date, COUNT(*) AS n_sql FROM boxscores GROUP BY gameId")
    pq_games = scan_boxscores().group_by("gameId").agg(pl.len().alias("n_pq")).collect()
    only_sql = sql_games.join(pq_games, on="gameId", how="anti")
    only_pq = pq_games.join(sql_games, on="gameId", how="anti")
    both = sql_games.join(pq_games, on="gameId")
    partial = both.filter(c("n_sql") != c("n_pq"))
    total_diff = sql_games["n_sql"].sum() - pq_games["n_pq"].sum()
    print(f"SQLite: {sql_games['n_sql'].sum():,} rows / {sql_games.height:,} games   parquet: {pq_games['n_pq'].sum():,} rows / {pq_games.height:,} games")
    print(f"games only in SQLite: {only_sql.height} ({only_sql['n_sql'].sum():,} rows), dates: "
          f"{sorted(only_sql['date'].unique().to_list())[:6]}")
    print(f"games only in parquet: {only_pq.height}")
    print(f"games present in both with a different row count: {partial.height} "
          f"(rows missing inside them: {(partial['n_sql'] - partial['n_pq']).sum()})")
    unexplained = total_diff - only_sql["n_sql"].sum() + only_pq["n_pq"].sum() - (partial["n_sql"] - partial["n_pq"]).sum()
    print(f"-> row difference not explained by the three lines above: {unexplained}")
    print("   If the games only in SQLite are recent, SQLite simply received them after the migration: "
          "run `python ttfl_data.py` again (it is idempotent) and this section should show 0 everywhere.")

    stored = q(hist, "SELECT DISTINCT playerName, avg_TTFL FROM player_avg_TTFL")
    fresh_sql = q(hist, "SELECT playerName, ROUND(AVG(TTFL), 2) AS avg_TTFL FROM boxscores "
                        "WHERE seconds > 0 AND gameId LIKE '002%' GROUP BY playerName")
    fresh_pq = S.player_overall(scan_boxscores()).select("playerName", "avg_TTFL").collect()

    def cmp(a, b, label):
        j = a.join(b, on="playerName", suffix="_b")
        d = (c("avg_TTFL") - c("avg_TTFL_b")).abs()
        bad = j.filter(d > 0.011)
        print(f"{label}: {j.height} players in both ({a.height} vs {b.height}); differ by > 0.011: {bad.height}"
              + (f", max {bad.select(d.max()).item():.2f}" if bad.height else ""))

    cmp(stored, fresh_sql, "stored hist player_avg_TTFL  vs  fresh average from the SQLite boxscores")
    cmp(fresh_sql, fresh_pq, "fresh average from SQLite        vs  parquet (what the port uses)")
    print("-> first line > 0 would mean the stored table is stale; the second line is expected to be > 0 only for "
          "players in the games not yet synced.")


def full_rebuild(rosters: pl.DataFrame) -> None:
    section("4. --full: controlled test - old calc_nemesis vs the port, SAME data, SAME active players")
    tmp = tempfile.mkdtemp()
    h, last = os.path.join(tmp, "hist.db"), os.path.join(tmp, "last.db")
    shutil.copy(DB_PATH_HISTORICAL, h)
    shutil.copy(DB_PATH_LAST_SEASON, last)
    old_mod = V.load_old_module()
    old_mod.conn_hist_db = lambda: sqlite3.connect(h)              # calc_nemesis reads the hist db through this
    print("refreshing player_avg_TTFL in the temporary hist db ...")
    ch = sqlite3.connect(h)
    old_mod.update_tables(ch, historical=True)
    ch.close()
    print("running old calc_nemesis (a few minutes) ...")
    cl = sqlite3.connect(last)
    old_mod.calc_nemesis(cl)

    # The port reads exactly what the old code reads: the temp hist `boxscores` and `current_boxscores`.
    ch = sqlite3.connect(h)
    hist = q(ch, "SELECT gameId, teamTricode, opponent, playerName, seconds, TTFL FROM boxscores").lazy()
    active = q(ch, "SELECT DISTINCT playerName FROM current_boxscores").lazy()
    print(f"same inputs for both: {hist.select(pl.len()).collect().item():,} boxscore rows, "
          f"{active.collect().height} active players (current_boxscores)")
    overall_hist = S.player_overall(hist)
    curr_team = rosters.lazy().select("playerName", "teamTricode").unique()
    new_pn = S.player_nemesis(hist, active, overall_hist, curr_team).collect()
    new_tn = S.team_nemesis(hist, active, overall_hist).collect()

    for table, new, keys in (("player_nemesis", new_pn, ["player", "opp_player"]),
                             ("team_nemesis", new_tn, ["player", "opp_team"])):
        print(f"\n-- {table}: old code re-run now  vs  port (identical inputs)")
        V.diff_tables(table, V.read_old(cl, table), new, keys, 0.011)
    print("\n-> identical = the port is correct. Any remaining difference is a real logic difference.")
    shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="also rebuild the old nemesis tables on temp copies")
    args = ap.parse_args()
    conn, hist = sqlite3.connect(DB_PATH_LAST_SEASON), sqlite3.connect(DB_PATH_HISTORICAL)
    check_minutes_vs_seconds(conn)
    check_home_away(conn)
    check_nemesis_inputs(hist)
    if args.full:
        full_rebuild(V.read_old(conn, "rosters"))


if __name__ == "__main__":
    main()
