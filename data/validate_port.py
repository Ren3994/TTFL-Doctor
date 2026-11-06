"""
validate_port.py - diff the Polars port against the SQLite tables you already have.

    python validate_port.py                    # every derived table vs data_<LAST_SEASON>.db
    python validate_port.py --top 2026-01-01   # also topTTFL_query (old) vs top_ttfl (new)

Run ttfl_data.py once first (SQLite -> Parquet). The new side is computed from the Parquet files with
rosters and injuries taken from the same .db as the old tables, so roster/position drift can't show up as
a false difference.

If rel_patop or the nemesis tables differ, run diagnose_diffs.py: it shows the offending rows and tells a
logic difference from a stale old table (the old nemesis/avg tables are only refreshed when you rebuild them).

Reading the report:  only_old / only_new = rows present on one side only; each mismatching column lists
how many matched rows differ (numeric tolerance `tol`) and the largest difference.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

import polars as pl
import polars.selectors as cs

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from misc.misc import DB_PATH_LAST_SEASON, LAST_SEASON  # noqa: E402

import ttfl_stats as S  # noqa: E402

c = pl.col


def load_old_module():
    """Your existing sql_functions, whether it is importable as `sql_functions` or `data.sql_functions`."""
    import importlib
    try:
        return importlib.import_module("sql_functions")
    except ModuleNotFoundError as e:
        if e.name != "sql_functions":
            raise
        return importlib.import_module("data.sql_functions")


def read_old(conn, table: str) -> pl.DataFrame:
    return pl.read_database(f"SELECT * FROM {table}", conn, infer_schema_length=None)


def diff_tables(name: str, old: pl.DataFrame, new: pl.DataFrame, keys: list[str], tol: float = 1e-6,
                null_as_zero: tuple = ()) -> bool:
    """null_as_zero: columns where the old table has NULL for 'no such rows' and the port has 0 (pandas concat
    left NaN counts for e.g. a player with no away games). Treated as equal."""
    old = old.with_columns([c(col).fill_null(0) for col in null_as_zero if col in old.columns])
    new = new.select([col for col in old.columns if col in new.columns])
    cols = new.columns
    missing = [col for col in old.columns if col not in cols]
    head = f"{name:28s} old={old.height:>8,} new={new.height:>8,}"
    old = old.select(cols)

    if old.select(keys).is_duplicated().any() or new.select(keys).is_duplicated().any():
        # keys are not unique (e.g. opp_pos_avg_per_game): compare as multisets of whole rows
        norm = lambda df: df.with_columns(cs.float().round(4)).group_by(cols).len()          # noqa: E731
        j = norm(old).join(norm(new), on=cols, how="full", suffix="_new", coalesce=True)
        bad = j.filter(c("len").is_null() | c("len_new").is_null() | (c("len") != c("len_new")))
        ok = bad.is_empty() and not missing
        print(f"{'OK ' if ok else 'DIFF'} {head} (multiset compare) differing row groups={bad.height}"
              + (f" missing cols={missing}" if missing else ""))
        if not bad.is_empty():
            print(bad.head(3))
        return ok

    o = old.with_columns(_in_old=pl.lit(True))
    n = new.with_columns(_in_new=pl.lit(True))
    j = o.join(n, on=keys, how="full", suffix="_new", coalesce=True)
    only_old = j.filter(c("_in_new").is_null()).height
    only_new = j.filter(c("_in_old").is_null()).height
    both = j.filter(c("_in_old").is_not_null() & c("_in_new").is_not_null())
    problems = []
    for col in cols:
        if col in keys:
            continue
        a, b = c(col), c(f"{col}_new")
        if old.schema[col].is_numeric():
            d = (a.cast(pl.Float64) - b.cast(pl.Float64)).abs()
            bad = (d > tol).fill_null(False) | (a.is_null() != b.is_null())
        else:
            d = pl.lit(0.0)
            bad = a.ne_missing(b)
        sub = both.filter(bad)
        if sub.height:
            mx = sub.select(d.max()).item() if old.schema[col].is_numeric() else None
            msg = f"{col}: {sub.height} rows" + (f", max diff {mx:.4g}" if mx is not None else "")
            problems.append((msg, sub.select(*keys, a.alias("old"), b.alias("new")).head(3)))
    ok = not (only_old or only_new or problems or missing)
    print(f"{'OK ' if ok else 'DIFF'} {head} only_old={only_old} only_new={only_new}"
          + (f" missing cols={missing}" if missing else ""))
    for msg, example in problems:
        print("      -", msg)
        print("\n".join("          " + line for line in str(example).splitlines()))
    only = j.filter(c("_in_new").is_null() | c("_in_old").is_null())
    if not only.is_empty():
        print("      rows on one side only (first 3):")
        print("\n".join("          " + line for line in str(only.select(*keys, "_in_old", "_in_new").head(3)).splitlines()))
    return ok


def _tokens(s):
    """Normalise a GROUP_CONCAT string: unordered, de-duplicated, numbers rounded."""
    if s is None:
        return None
    out = set()
    for t in s.split(","):
        try:
            out.add(str(round(float(t), 3)))
        except ValueError:
            out.add(t)
    return ",".join(sorted(out))


def compare_top(conn, date: str, d: S.Derived, rosters: pl.DataFrame, injuries: pl.DataFrame) -> bool:
    old = pl.from_pandas(load_old_module().topTTFL_query(conn, date))
    new = S.top_ttfl(date, d, injuries=injuries, as_strings=True)
    norm = lambda df: df.with_columns([c(x).map_elements(_tokens, return_dtype=pl.Utf8)   # noqa: E731
                                       for x in S.LIST_COLS if x in df.columns])
    return diff_tables("topTTFL_query", norm(old), norm(new), ["playerName", "pos"], tol=0.011)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", help="also compare topTTFL_query for this date (YYYY-MM-DD)")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH_LAST_SEASON)
    rosters = read_old(conn, "rosters")
    injuries = read_old(conn, "injury_report")
    print(f"building derived tables for {LAST_SEASON} from parquet ...")
    d = S.build_derived(stats_season=LAST_SEASON, roster_season=LAST_SEASON, rosters=rosters)

    checks = [   # (old table, new frame, keys, tol)
        ("player_avg_TTFL", d.avgs, ["playerName", "season"], 0.011),
        ("home_away_rel_TTFL", d.home_away, ["playerName", "season"], 0.011),
        ("rel_btb_TTFL", d.btb, ["playerName", "season"], 0.011),
        ("rel_avg_opp_TTFL", d.rel_avg_opp, ["teamTricode"], 1e-6),
        ("avg_TTFL_per_pos", d.avg_pos, ["position"], 1e-6),
        ("avg_TTFL_per_pos_per_opp", d.avg_pos_opp, ["position", "opponent"], 1e-6),
        ("rel_patop", d.rel_patop, ["playerName", "opponent"], 1e-6),
        ("team_recent_wins", d.team_wins, ["teamTricode"], 0),
        ("recent_streaks", d.streaks, ["playerName"], 0.11),
        ("min_restrictions", d.min_restr, ["playerName"], 1e-6),
        ("games_missed_by_players", d.games_missed, ["gameId", "team", "did_not_play"], 0),
        ("opp_pos_avg_per_game", d.opp_pos, ["gameId", "teamTricode", "opp_team", "opp_pos"], 1e-6),
        ("absent_teammate_rel_impact", d.absent, ["playerName", "teammate", "teamTricode"], 1e-6),
        ("player_nemesis", d.nemesis_player, ["player", "opp_player"], 0.011),
        ("team_nemesis", d.nemesis_team, ["player", "opp_team"], 0.011),
    ]
    zero_cols = {"home_away_rel_TTFL": ("n_home_games", "n_away_games", "n_home_games_season", "n_away_games_season")}
    results = []
    for table, new, keys, tol in checks:
        try:
            results.append(diff_tables(table, read_old(conn, table), new, keys, tol, zero_cols.get(table, ())))
        except Exception as e:                                   # keep going, show the failing table
            print(f"ERR  {table}: {type(e).__name__}: {e}")
            results.append(False)
    if args.top:
        try:
            results.append(compare_top(conn, args.top, d, rosters, injuries))
        except Exception as e:
            print(f"ERR  topTTFL_query: {type(e).__name__}: {e}")
            results.append(False)
    print(f"\n{sum(results)}/{len(results)} identical within tolerance")


if __name__ == "__main__":
    main()
