"""
ttfl_data.py - Parquet storage layer. Replaces the SQLite tables, indexes and the
per-table fetch/append plumbing in sql_functions.py.

Layout (everything under <project>/data/parquet/):

    boxscores/<season>.parquet   one file per season, ALL seasons in one dataset
    schedule.parquet             all seasons
    rosters.parquet              all seasons (has a `season` column)
    player_positions.parquet
    injury_report.parquet
    team_stats.parquet

What disappears compared to the SQLite version:
  * historical_boxscores / current_boxscores / boxscores (3 copies of the same rows)
  * the three .db files (current / last season / historical) - "current" is now a filter on `season`
  * every derived table (player_avg_TTFL, played, roster_pairs, ...) - computed in ttfl_stats.py
  * ~25 index definitions, sqlite_stat1, the .db.zst release asset (ship the parquet files instead)

`joueurs_deja_pick` (the user's picks) is mutable app state, not analytics data: leave it in SQLite.

Requires polars >= 1.0.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import polars as pl

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from misc.misc import BASE_DIR, SEASON, LAST_SEASON  # noqa: E402,F401

DATA_DIR = Path(BASE_DIR, "..", "data", "parquet").resolve()
BOX_DIR = DATA_DIR / "boxscores"

# --------------------------------------------------------------------------------------
# Schemas. Types are tightened (Int16/Int8, real Date) - this is most of the size/speed win.
# Dropped vs the SQLite boxscores (all derivable, see with_legacy_columns):
#   minutes (== seconds), gameDate (== gameDate_ymd), prev_gameDate_ymd (== gameDate_ymd - 1 day),
#   homeTeam / visitorTeam (== teamTricode / opponent depending on isHome)
# --------------------------------------------------------------------------------------
_I16, _I32, _I8, _F64, _STR = pl.Int16, pl.Int32, pl.Int8, pl.Float64, pl.Utf8

BOX_SCHEMA: dict = {
    "gameId": _STR, "season": _STR, "gameDate_ymd": pl.Date,
    "teamTricode": _STR, "opponent": _STR, "isHome": _I8,
    "playerName": _STR, "position_boxscores": _STR,
    "seconds": _I32, "points": _I16, "assists": _I16,
    "reboundsTotal": _I16, "reboundsOffensive": _I16, "reboundsDefensive": _I16,
    "steals": _I16, "blocks": _I16, "turnovers": _I16,
    "fieldGoalsMade": _I16, "fieldGoalsAttempted": _I16,
    "threePointersMade": _I16, "threePointersAttempted": _I16,
    "freeThrowsMade": _I16, "freeThrowsAttempted": _I16,
    "plusMinusPoints": _F64, "TTFL": _I32, "win": _I8,
    "teamPoints": _I16, "opponentPoints": _I16, "teamTTFL": _I32, "opponentTTFL": _I32,
}
LEGACY_BOX_COLS = ("minutes", "gameDate", "prev_gameDate_ymd", "homeTeam", "visitorTeam")

SCHEDULE_SCHEMA: dict = {
    "gameId": _STR, "season": _STR, "gameDate_ymd": pl.Date, "gameStatus": _I8,
    "homeTeam": _STR, "awayTeam": _STR,
    "homeTeam_wins": _I16, "homeTeam_losses": _I16, "awayTeam_wins": _I16, "awayTeam_losses": _I16,
    "postponed": _I8, "gameDateTimeUTC": _STR, "gameDateTime": _STR,
}
ROSTER_SCHEMA: dict = {"playerName": _STR, "teamTricode": _STR, "season": _STR, "position": _STR}


def to_pl(df) -> pl.DataFrame:
    """Accept a pandas or polars frame (the existing fetchers return pandas)."""
    return df if isinstance(df, pl.DataFrame) else pl.from_pandas(df)


def _parse_date(df: pl.DataFrame, col: str) -> pl.DataFrame:
    if col in df.columns and df.schema[col] != pl.Date:
        df = df.with_columns(pl.col(col).cast(_STR).str.to_date("%Y-%m-%d", strict=False))
    return df


def _conform(df: pl.DataFrame, schema: dict) -> pl.DataFrame:
    """Select exactly the schema's columns, in order, cast (non-strict); missing columns become null."""
    return df.select(
        [pl.col(n).cast(t, strict=False) if n in df.columns else pl.lit(None, dtype=t).alias(n)
         for n, t in schema.items()]
    )


# --------------------------------------------------------------------------------------
# Boxscores
# --------------------------------------------------------------------------------------
def box_path(season: str) -> Path:
    return BOX_DIR / f"{season}.parquet"


def available_seasons() -> list[str]:
    return sorted(p.stem for p in BOX_DIR.glob("*.parquet")) if BOX_DIR.exists() else []


def latest_season() -> str | None:
    """Newest season that has boxscores. Before opening night this is LAST_SEASON, so every
    'current season' stat falls back to last season automatically (no manual DB switching)."""
    s = available_seasons()
    return s[-1] if s else None


def normalize_boxscores(df: pl.DataFrame) -> pl.DataFrame:
    return _conform(_parse_date(to_pl(df), "gameDate_ymd"), BOX_SCHEMA)


def save_boxscores(df) -> None:
    """Merge new rows into the per-season files. This is the ONLY write path for boxscores and
    replaces check_boxscores_integrity (null-game filter + duplicate removal happen here).
    Call it wherever the downloader used `df.to_sql('boxscores', ..., if_exists='append')`."""
    BOX_DIR.mkdir(parents=True, exist_ok=True)
    df = normalize_boxscores(df)
    df = df.filter(pl.col("teamTTFL").fill_null(1) != 0)          # was: DELETE ... WHERE teamTTFL = 0
    for season in df["season"].drop_nulls().unique().to_list():
        new = df.filter(pl.col("season") == season)
        path = box_path(season)
        if path.exists():
            new = pl.concat([pl.read_parquet(path), new]).unique(
                subset=["gameId", "playerName"], keep="last", maintain_order=True)  # was: remove_duplicates
        new.sort(["gameDate_ymd", "gameId"]).write_parquet(path, compression="zstd")


def scan_boxscores(seasons=None) -> pl.LazyFrame:
    """seasons=None -> whole history; otherwise only those season files are opened."""
    if seasons:
        paths = [str(box_path(s)) for s in seasons if box_path(s).exists()]
    else:
        paths = [str(p) for p in sorted(BOX_DIR.glob("*.parquet"))] if BOX_DIR.exists() else []
    if not paths:
        return pl.LazyFrame(schema=BOX_SCHEMA)
    return pl.scan_parquet(paths)


def with_legacy_columns(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Re-create the columns the old boxscores table had, so existing Streamlit pages keep working.
    Delete this (and its call sites) once nothing reads them."""
    s = pl.col("seconds")
    is_home = pl.col("isHome") == 1
    return lf.with_columns(
        gameDate=pl.col("gameDate_ymd").dt.strftime("%d/%m/%Y"),
        prev_gameDate_ymd=(pl.col("gameDate_ymd") - pl.duration(days=1)).dt.strftime("%Y-%m-%d"),
        minutes=pl.format("{}:{}", s // 60, (s % 60).cast(pl.Utf8).str.zfill(2)),
        homeTeam=pl.when(is_home).then(pl.col("teamTricode")).otherwise(pl.col("opponent")),
        visitorTeam=pl.when(is_home).then(pl.col("opponent")).otherwise(pl.col("teamTricode")),
    ).with_columns(gameDate_ymd=pl.col("gameDate_ymd").dt.strftime("%Y-%m-%d"))


# --------------------------------------------------------------------------------------
# Small tables
# --------------------------------------------------------------------------------------
def scan_table(name: str) -> pl.LazyFrame:
    path = DATA_DIR / f"{name}.parquet"
    return pl.scan_parquet(str(path)) if path.exists() else pl.LazyFrame()


def save_table(name: str, df) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    to_pl(df).write_parquet(DATA_DIR / f"{name}.parquet", compression="zstd")


def _replace_seasons(name: str, new: pl.DataFrame, schema: dict) -> None:
    """Write `new`, replacing only the seasons it contains (other seasons are kept)."""
    path = DATA_DIR / f"{name}.parquet"
    if path.exists():
        old = _conform(pl.read_parquet(path), schema)
        new = pl.concat([old.filter(~pl.col("season").is_in(new["season"].unique().to_list())), new])
    save_table(name, new)


def save_schedule(df) -> None:
    df = _conform(_parse_date(to_pl(df), "gameDate_ymd"), SCHEDULE_SCHEMA)
    df = df.with_columns(pl.col("postponed").fill_null(0))
    _replace_seasons("schedule", df, SCHEDULE_SCHEMA)


def scan_schedule() -> pl.LazyFrame:
    # `gameDate` (dd/mm/yyyy text) is derived on read, it is no longer stored
    return scan_table("schedule").with_columns(
        gameDate=pl.col("gameDate_ymd").dt.strftime("%d/%m/%Y"))


def save_rosters(df, season: str = SEASON) -> None:
    df = to_pl(df)
    if "season" not in df.columns:
        df = df.with_columns(season=pl.lit(season))
    _replace_seasons("rosters", _conform(df, ROSTER_SCHEMA), ROSTER_SCHEMA)


def scan_rosters(season: str | None = None) -> pl.LazyFrame:
    lf = scan_table("rosters")
    return lf.filter(pl.col("season") == season) if season else lf


def scan_positions() -> pl.LazyFrame:
    return scan_table("player_positions")


def save_injuries(df) -> None:
    save_table("injury_report", df)


def scan_injuries() -> pl.LazyFrame:
    # the old table has names like ' Niederhauser' (leading space) which never matched a join
    return scan_table("injury_report").with_columns(pl.col("player_name").str.strip_chars())


# --------------------------------------------------------------------------------------
# Franchise filters: SQL strings -> data + one expression builder.
# (generated from your FRANCHISE_FILTERS dict; 68 franchises, 2 of them season-bounded)
# --------------------------------------------------------------------------------------
FRANCHISE_TRICODES: dict[str, tuple[str, ...]] = {
    "Washington Wizards": ("CAP", "BLT", "CHZ", "CHP"),
    "Chicago Packers": ("CHP",),
    "Chicago Zephyrs": ("CHZ",),
    "Washington Bullets": ("BLT",),
    "Capital Bullets": ("CAP",),
    "Toronto Huskies": ("HUS",),
    "New York Knicks": ("NYK",),
    "Boston Celtics": ("BOS",),
    "Chicago Stags": ("CHS",),
    "Providence Steamrollers": ("PRO",),
    "Detroit Falcons": ("DEF",),
    "St. Louis Bombers": ("BOM",),
    "Pittsburgh Ironmen": ("PIT",),
    "Cleveland Rebels": ("CLR",),
    "Golden State Warriors": ("PHW", "SFW", "GOS", "GSW"),
    "San Francisco Warriors": ("SFW",),
    "Philadelphia Warriors": ("PHW",),
    "Baltimore Bullets": ("BAL",),
    "Indianapolis Jets": ("JET",),
    "Detroit Pistons": ("FTW", "DET"),
    "Fort Wayne Pistons": ("FTW",),
    "Los Angeles Lakers": ("MNL", "LAL"),
    "Minneapolis Lakers": ("MNL",),
    "Sacramento Kings": ("ROC", "CIN", "KCK", "SAC"),
    "Rochester Royals": ("ROC",),
    "Cincinnati Royals": ("CIN",),
    "Kansas City Kings": ("KCK",),
    "Washington Capitols": (),
    "Atlanta Hawks": ("TCB", "MIH", "STL", "ATL"),
    "Tri-Cities Blackhawks": ("TCB",),
    "Milwaukee Hawks": ("MIH",),
    "St. Louis Hawks": ("STL",),
    "Denver Nuggets": ("DEN", "DN"),
    "Indianapolis Pacers": ("IND",),
    "Indianapolis Olympians": ("INO",),
    "Sheboygan Redskins": ("SHE",),
    "Waterloo Hawks": ("WAT",),
    "Anderson Packers": ("AND",),
    "Philadelphia 76ers": ("SYR", "PHL", "PHI"),
    "Syracuse Nationals": ("SYR",),
    "Chicago Bulls": ("CHI",),
    "Oklahoma City Thunder": ("SEA", "OKC"),
    "Seattle SuperSonics": ("SEA",),
    "Houston Rockets": ("SDR", "HOU"),
    "San Diego Rockets": ("SDR",),
    "Milwaukee Bucks": ("MIL",),
    "Phoenix Suns": ("PHX",),
    "Cleveland Cavaliers": ("CLE",),
    "Los Angeles Clippers": ("BUF", "SDC", "LAC"),
    "San Diego Clippers": ("SDC",),
    "Buffalo Braves": ("BUF",),
    "Portland Trail Blazers": ("POR",),
    "Utah Jazz": ("NOJ", "UTH", "UTA"),
    "New Orleans Jazz": ("NOJ",),
    "San Antonio Spurs": ("SAN", "SAS"),
    "Brooklyn Nets": ("NYN", "NJN", "BKN"),
    "New York Nets": ("NYN",),
    "New Jersey Nets": ("NJN",),
    "Dallas Mavericks": ("DAL",),
    "New Orleans Pelicans": ("NOH", "NOK", "NOP"),
    "New Orleans Hornets": ("NOH", "NOK"),
    "Miami Heat": ("MIA",),
    "Minnesota Timberwolves": ("MIN",),
    "Orlando Magic": ("ORL",),
    "Toronto Raptors": ("TOR",),
    "Memphis Grizzlies": ("VAN", "MEM"),
    "Vancouver Grizzlies": ("VAN",),
    "Charlotte Hornets": ("CHH", "CHA"),
}

# tricodes that only count within a season range: franchise -> (tricode, operator, season)
FRANCHISE_SEASON_BOUNDED: dict[str, tuple[str, str, str]] = {
    "Washington Wizards": ("WAS", ">=", "1974-75"),
    "Washington Capitols": ("WAS", "<=", "1950-51"),
}


def franchise_expr(name: str) -> pl.Expr:
    """Boolean expression over teamTricode/season for a franchise (replaces FRANCHISE_FILTERS[name])."""
    expr = pl.lit(False)
    codes = FRANCHISE_TRICODES[name]
    if codes:
        expr = pl.col("teamTricode").is_in(list(codes))
    if name in FRANCHISE_SEASON_BOUNDED:
        code, op, season = FRANCHISE_SEASON_BOUNDED[name]
        in_range = pl.col("season") >= season if op == ">=" else pl.col("season") <= season
        expr = expr | ((pl.col("teamTricode") == code) & in_range)
    return expr


# --------------------------------------------------------------------------------------
# Schedule helpers (get_missing_gameids / get_games_for_date)
# --------------------------------------------------------------------------------------
def to_date(d) -> dt.date:
    """Accept date, 'YYYY-MM-DD' or 'dd/mm/YYYY'."""
    if isinstance(d, dt.datetime):
        return d.date()
    if isinstance(d, dt.date):
        return d
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(d, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date: {d!r}")


def get_missing_gameids() -> pl.DataFrame:
    c = pl.col
    have = scan_boxscores().select("gameId").unique()
    return (
        scan_schedule()
        .filter((c("gameStatus") == 3) & (c("postponed") == 0)
                & (c("gameId").str.starts_with("002") | c("gameId").str.starts_with("004")))
        .join(have, on="gameId", how="anti")
        .sort("gameDate_ymd")       # the SQL sorted the dd/mm/yyyy *text*, i.e. not chronologically
        .select("gameId", "gameDate", "homeTeam", "awayTeam")
        .collect()
    )


def get_games_for_date(game_date) -> pl.DataFrame:
    """One row per matchup (the same pair listed twice, e.g. in-season-tournament placeholders, is collapsed)."""
    df = (scan_schedule().filter(pl.col("gameDate_ymd") == to_date(game_date)).collect()
          .with_columns(pl.col("homeTeam").fill_null("TBD"), pl.col("awayTeam").fill_null("TBD")))
    h, a = pl.col("homeTeam"), pl.col("awayTeam")
    pair = pl.when(h <= a).then(pl.concat_str([h, a], separator="|")).otherwise(pl.concat_str([a, h], separator="|"))
    return df.with_columns(_pair=pair).unique(subset="_pair", keep="first", maintain_order=True).drop("_pair")


# --------------------------------------------------------------------------------------
# Refresh of reference data (replaces init_db / check_table_exists)
# --------------------------------------------------------------------------------------
def refresh_reference_data(verbose: bool = True) -> None:
    """Re-download schedule, rosters, team stats (and player positions if the file is missing).
    Positions in rosters are no longer written back: they are resolved at read time
    (see ttfl_stats.current_rosters)."""
    from fetchers.schedule_fetcher import get_schedule
    from fetchers.rosters_fetcher import get_rosters
    from fetchers.team_stats_fetcher import get_team_stats
    from fetchers.player_position_fetcher import fetch_player_positions

    def say(msg):
        if verbose:
            print(msg)

    for label, fn, saver in (("schedule", get_schedule, save_schedule),
                             ("rosters", get_rosters, save_rosters),
                             ("team_stats", get_team_stats, lambda d: save_table("team_stats", d))):
        try:
            data = fn()
            if data is None:
                say(f"{label} is None - not saved")
            else:
                saver(to_pl(data))
        except Exception as e:                                   # network etc.
            say(f"error fetching {label}: {e}")
    if not (DATA_DIR / "player_positions.parquet").exists():
        save_table("player_positions", fetch_player_positions())


# --------------------------------------------------------------------------------------
# One-off migration from the three SQLite files
# --------------------------------------------------------------------------------------
def _sql(conn, query: str) -> pl.DataFrame:
    return pl.read_database(query, conn, infer_schema_length=None)


def _has_table(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate_from_sqlite(hist_db: str, last_season_db: str | None = None, current_db: str | None = None) -> None:
    """Non-destructive: only reads the .db files.

    * boxscores come from the HISTORICAL db's `boxscores` table (= historical_boxscores + current_boxscores)
    * schedule from historical (all seasons); the current-season db's schedule replaces its own season
    * rosters: historical (has `season`), last-season db (no season column -> LAST_SEASON), current db (SEASON)
    * injury_report / team_stats from the freshest db available
    """
    import sqlite3

    with sqlite3.connect(hist_db) as h:
        bs = _sql(h, "SELECT * FROM boxscores")
        print(f"boxscores: {bs.height:,} rows, {bs['gameId'].n_unique():,} games")

        if {"gameDate_ymd", "prev_gameDate_ymd"} <= set(bs.columns):
            d = bs.select(pl.col("gameDate_ymd").str.to_date("%Y-%m-%d", strict=False).alias("d"),
                          pl.col("prev_gameDate_ymd").str.to_date("%Y-%m-%d", strict=False).alias("p"))
            bad = d.filter(pl.col("p").is_not_null() & ((pl.col("d") - pl.col("p")).dt.total_days() != 1)).height
            print(f"check: prev_gameDate_ymd != gameDate_ymd - 1 day on {bad:,} rows "
                  f"({'safe to drop the column' if bad == 0 else 'NOT always D-1: back-to-back logic assumes it is'})")

        save_boxscores(bs)                                   # writes one file per season
        print("wrote boxscores/ ->", ", ".join(available_seasons()[-3:]), "...")

        if _has_table(h, "schedule"):
            save_schedule(_sql(h, "SELECT * FROM schedule"))
        if _has_table(h, "player_positions"):
            save_table("player_positions", _sql(h, "SELECT * FROM player_positions"))
        if _has_table(h, "rosters"):
            save_rosters(_sql(h, "SELECT * FROM rosters"))

    for path, season in ((last_season_db, LAST_SEASON), (current_db, SEASON)):
        if not path:
            continue
        with sqlite3.connect(path) as conn:
            if _has_table(conn, "rosters"):
                r = _sql(conn, "SELECT * FROM rosters")
                if "season" not in r.columns:
                    r = r.with_columns(season=pl.lit(season))
                save_rosters(r, season)
            if _has_table(conn, "schedule"):
                save_schedule(_sql(conn, "SELECT * FROM schedule"))
            if _has_table(conn, "team_stats"):
                save_table("team_stats", _sql(conn, "SELECT * FROM team_stats"))
            if _has_table(conn, "injury_report"):
                save_injuries(_sql(conn, "SELECT * FROM injury_report"))
    print("done ->", DATA_DIR)


if __name__ == "__main__":
    from misc.misc import DB_PATH, DB_PATH_LAST_SEASON, DB_PATH_HISTORICAL
    migrate_from_sqlite(DB_PATH_HISTORICAL, DB_PATH_LAST_SEASON, DB_PATH)
