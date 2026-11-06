"""
ttfl_stats.py - every derived table and every query, as Polars expressions.

Replaces: calc_TTFL_stats, calc_nemesis, calc_min_resriction, calc_team_recent_wins, calc_streak,
update_avg_TTFL_per_pos(_per_opp), update_rel_player_avg_ttfl_v_opp, update_absent_teammate_rel_impact,
updates_games_missed_by_players, update_opp_pos_avg_per_game, update_helper_tables, add_pos_to_rosters,
add_missing_pos_to_rosters, update_tables, topTTFL_query, run_sql_query and the query_* functions.

Design:
  * each derived stat is a pure function  LazyFrame -> LazyFrame  (no connection, no side effects),
    so it can be tested on a 10-row DataFrame and inspected with .collect() at any step;
  * nothing derived is persisted: build_derived() computes everything in one pass (pl.collect_all
    shares the common scans) and get_derived() caches the result in-process;
  * the 4 helper tables (team_games, played, teammate_played, roster_pairs) no longer exist as tables.

Comments marked QUIRK are places where the SQL did something odd and I kept the behaviour so the
old-vs-new diff (validate_port.py) is clean. Fix them deliberately, afterwards.

Requires polars >= 1.0.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, fields
from functools import lru_cache

import polars as pl
import polars.selectors as cs

try:                                              # files side by side ...
    from ttfl_data import (
        DATA_DIR, SEASON, franchise_expr, latest_season, scan_boxscores, scan_injuries, scan_positions,
        scan_rosters, scan_schedule, to_date, to_pl, with_legacy_columns,
    )
except ImportError:                               # ... or imported as part of the `data` package
    from data.ttfl_data import (
        DATA_DIR, SEASON, franchise_expr, latest_season, scan_boxscores, scan_injuries, scan_positions,
        scan_rosters, scan_schedule, to_date, to_pl, with_legacy_columns,
    )

c = pl.col

# =====================================================================================
# Small helpers
# =====================================================================================
GAME_TYPE = {
    "Saison régulière": c("gameId").str.starts_with("002"),
    "Playoffs": c("gameId").str.starts_with("004"),
    "Les deux": c("gameId").str.starts_with("002") | c("gameId").str.starts_with("004"),
}
REGULAR = GAME_TYPE["Saison régulière"]


def rel_pct(x: pl.Expr, base: pl.Expr, require_x: bool = False) -> pl.Expr:
    """100 * (x - base) / base, null if base is null/0 (and x too if require_x). Replaces ~10 CASE WHEN blocks."""
    ok = base.is_not_null() & (base != 0)
    if require_x:
        ok = ok & x.is_not_null() & (x != 0)
    return pl.when(ok).then(100.0 * (x - base) / base)


def safe_div(a: pl.Expr, b: pl.Expr) -> pl.Expr:
    """a / b, null when b is 0/null (SQLite semantics; Polars would give inf/NaN)."""
    return pl.when(b != 0).then(a / b)


def _sum(col: str) -> pl.Expr:
    """SUM with SQL semantics: NULL (not 0) when there is no non-null value."""
    x = c(col)
    return pl.when(x.count() > 0).then(x.sum())


def played(bs: pl.LazyFrame) -> pl.LazyFrame:
    return bs.filter(c("seconds") > 0)


def regular_played(bs: pl.LazyFrame) -> pl.LazyFrame:
    return bs.filter((c("seconds") > 0) & REGULAR)


def _has_team() -> pl.Expr:
    return c("teamTricode").is_not_null() & (c("teamTricode") != "")


def select_games(bs: pl.LazyFrame, playoffs: str = "Saison régulière", seasons=(), team: str = "") -> pl.LazyFrame:
    """The 'selector' CTE that was rebuilt with f-strings in five functions."""
    lf = bs.filter((c("seconds") > 0) & GAME_TYPE[playoffs])
    if seasons:
        lf = lf.filter(c("season").is_in(list(seasons)))
    if team:
        lf = lf.filter(franchise_expr(team))
    return lf


# =====================================================================================
# Positions / rosters  (replaces add_pos_to_rosters, add_missing_pos_to_rosters, position_expansion CTE)
# =====================================================================================
def current_rosters(rosters: pl.LazyFrame, positions: pl.LazyFrame, bs: pl.LazyFrame) -> pl.LazyFrame:
    """playerName, teamTricode, position.
    position = player_positions.position, else inferred from boxscores (no position -> '?',
    several -> 'G-F' in sorted order; the SQL's GROUP_CONCAT order was arbitrary). Players with
    neither stay NULL and are therefore excluded from position-based stats, as before."""
    nonempty = (c("position_boxscores").is_not_null()) & (c("position_boxscores") != "")
    inferred = (
        bs.group_by("playerName")
        .agg(_pl=c("position_boxscores").filter(nonempty).unique().sort())
        .select("playerName",
                inferred_pos=pl.when(c("_pl").list.len() == 0).then(pl.lit("?")).otherwise(c("_pl").list.join("-")))
    )
    base = rosters.select("playerName", "teamTricode")
    if "playerName" in positions.collect_schema().names():
        base = base.join(positions.select("playerName", "position").unique(subset="playerName"),
                         on="playerName", how="left")
    else:
        base = base.with_columns(position=pl.lit(None, dtype=pl.Utf8))
    return (base.join(inferred, on="playerName", how="left")
                .with_columns(position=pl.coalesce("position", "inferred_pos"))
                .select("playerName", "teamTricode", "position"))


def pos_expansion(rosters: pl.LazyFrame) -> pl.LazyFrame:
    """One row per (player, single position): 'G-F' -> two rows. Same as the LIKE '%G%' UNION ALL ... CTE."""
    parts = [rosters.filter(c("position").str.contains(p)).select("playerName", pos=pl.lit(p)) for p in "GFC"]
    parts.append(rosters.filter(c("position") == "?").select("playerName", pos=pl.lit("?")))
    return pl.concat(parts)


# =====================================================================================
# Per-player stats  (calc_TTFL_stats)
# =====================================================================================
def _ttfl_stats(sfx: str = "") -> list[pl.Expr]:
    t = c("TTFL")
    return [t.median().alias(f"median_TTFL{sfx}"), t.mean().alias(f"avg_TTFL{sfx}"),
            t.std().alias(f"stddev_TTFL{sfx}")]


def player_overall(bs: pl.LazyFrame) -> pl.LazyFrame:
    """One row per player over whatever scope `bs` covers (one season, or career). 2-decimal rounding as before."""
    return (regular_played(bs).group_by("playerName").agg(_ttfl_stats())
            .with_columns(cs.float().round(2)))


def player_avg_ttfl(bs: pl.LazyFrame) -> pl.LazyFrame:
    """Old `player_avg_TTFL` table: per (player, season) + the scope-wide ('overall') numbers repeated."""
    per_season = regular_played(bs).group_by("playerName", "season").agg(_ttfl_stats("_season"))
    return (per_season.join(player_overall(bs), on="playerName", how="left", validate="m:1")
            .with_columns(cs.float().round(2)))


def _ha_aggs(sfx: str) -> list[pl.Expr]:
    t, home, away = c("TTFL"), c("isHome") == 1, c("isHome") == 0
    return [t.filter(home).mean().alias(f"home_avg_TTFL{sfx}"), t.filter(away).mean().alias(f"away_avg_TTFL{sfx}"),
            home.sum().alias(f"n_home_games{sfx}"), away.sum().alias(f"n_away_games{sfx}"),
            t.mean().alias(f"overall_avg_TTFL{sfx}")]


HA_COLS = ["playerName", "season", "home_avg_TTFL", "away_avg_TTFL", "home_rel_TTFL", "away_rel_TTFL",
           "n_home_games", "n_away_games", "home_avg_TTFL_season", "away_avg_TTFL_season",
           "home_rel_TTFL_season", "away_rel_TTFL_season", "n_home_games_season", "n_away_games_season"]


def home_away(bs: pl.LazyFrame) -> pl.LazyFrame:
    """Old `home_away_rel_TTFL`: five groupby/merge blocks in pandas -> two aggregations."""
    reg = regular_played(bs)
    season = reg.group_by("playerName", "season").agg(_ha_aggs("_season"))
    overall = reg.group_by("playerName").agg(_ha_aggs(""))
    return (season.join(overall, on="playerName", how="left", validate="m:1")
            .with_columns(
                home_rel_TTFL=rel_pct(c("home_avg_TTFL"), c("overall_avg_TTFL")),
                away_rel_TTFL=rel_pct(c("away_avg_TTFL"), c("overall_avg_TTFL")),
                home_rel_TTFL_season=rel_pct(c("home_avg_TTFL_season"), c("overall_avg_TTFL_season")),
                away_rel_TTFL_season=rel_pct(c("away_avg_TTFL_season"), c("overall_avg_TTFL_season")))
            .select(HA_COLS).with_columns(cs.float().round(2)))


BTB_COLS = ["playerName", "season", "btbTTFL", "n_btb", "rel_btb_TTFL",
            "btbTTFL_season", "n_btb_season", "rel_btb_TTFL_season"]


def back_to_back(bs: pl.LazyFrame, avgs: pl.LazyFrame) -> pl.LazyFrame:
    """Old `rel_btb_TTFL`. A game is the 2nd night of a back-to-back when the player's previous played
    regular-season game was exactly one day earlier (no need for prev_gameDate_ymd or a self-merge).
    Like the original, only (player, season) rows with at least one back-to-back exist."""
    flagged = (regular_played(bs).select("playerName", "season", "TTFL", "gameDate_ymd")
               .sort("playerName", "gameDate_ymd")
               .with_columns(_gap=(c("gameDate_ymd") - c("gameDate_ymd").shift(1).over("playerName")).dt.total_days())
               .filter(c("_gap") == 1))
    season = flagged.group_by("playerName", "season").agg(
        btbTTFL_season=c("TTFL").mean(), n_btb_season=pl.len())
    overall = flagged.group_by("playerName").agg(btbTTFL=c("TTFL").mean(), n_btb=pl.len())
    base = avgs.select("playerName", "season", "avg_TTFL", "avg_TTFL_season")
    return (season.join(overall, on="playerName", how="left", validate="m:1")
            .join(base, on=["playerName", "season"], how="left", validate="m:1")
            .with_columns(rel_btb_TTFL=rel_pct(c("btbTTFL"), c("avg_TTFL")),
                          rel_btb_TTFL_season=rel_pct(c("btbTTFL_season"), c("avg_TTFL_season")))
            .select(BTB_COLS).with_columns(cs.float().round(2)))


def rel_avg_opp_ttfl(bs: pl.LazyFrame) -> pl.LazyFrame:
    """Old `rel_avg_opp_TTFL`. QUIRK: averages over player rows (DNPs included), so each game is weighted by
    how many players are listed. For a true per-game average dedupe on (gameId, teamTricode) first."""
    t = (bs.group_by("teamTricode").agg(avg_team_TTFL=c("teamTTFL").mean(), avg_opp_TTFL=c("opponentTTFL").mean())
         .with_columns(overall_avg_team_TTFL=c("avg_team_TTFL").mean(), overall_avg_opp_TTFL=c("avg_opp_TTFL").mean()))
    return (t.with_columns(rel_team_avg_TTFL=rel_pct(c("avg_team_TTFL"), c("overall_avg_team_TTFL")),
                           rel_opp_avg_TTFL=rel_pct(c("avg_opp_TTFL"), c("overall_avg_opp_TTFL")))
             .sort("avg_opp_TTFL"))


# =====================================================================================
# Position-based stats  (update_avg_TTFL_per_pos, update_avg_TTFL_per_pos_per_opp)
# QUIRK: these use every boxscore row (DNPs and playoffs included), unlike player_avg_TTFL.
# =====================================================================================
def avg_ttfl_per_pos(bs: pl.LazyFrame, pos_exp: pl.LazyFrame) -> pl.LazyFrame:
    return (bs.select("playerName", "TTFL").join(pos_exp, on="playerName")
            .group_by("pos").agg(avg_TTFL=c("TTFL").mean()).rename({"pos": "position"}))


def avg_ttfl_per_pos_per_opp(bs: pl.LazyFrame, pos_exp: pl.LazyFrame) -> pl.LazyFrame:
    return (bs.select("playerName", "opponent", "TTFL").join(pos_exp, on="playerName")
            .group_by("pos", "opponent").agg(avg_TTFL=c("TTFL").mean()).rename({"pos": "position"}))


def rel_patop(bs: pl.LazyFrame, overall: pl.LazyFrame) -> pl.LazyFrame:
    """Old `rel_patop` (player vs opponent). The SQL filtered `minutes > 0` on a TEXT column; I use
    seconds > 0 (identical except for strings like '0:00')."""
    patop = played(bs).group_by("playerName", "opponent").agg(_avg=c("TTFL").mean(), n_games_played=pl.len())
    return (patop.join(overall.select("playerName", c("avg_TTFL").alias("_base")), on="playerName")
            .select("playerName", "opponent", "n_games_played",
                    rel_TTFL_v_opp=rel_pct(c("_avg"), c("_base"), require_x=True)))


# =====================================================================================
# Form / usage  (calc_team_recent_wins, calc_streak, calc_min_resriction)
# =====================================================================================
def team_recent_wins(bs: pl.LazyFrame) -> pl.LazyFrame:
    """'LLWLLWWLLL', oldest -> newest (the SQL built it newest-first and Python reversed it)."""
    res = pl.when(c("win") == 1).then(pl.lit("W")).otherwise(pl.lit("L"))
    return (bs.select("teamTricode", "win", "gameDate_ymd").unique()
            .sort("teamTricode", "gameDate_ymd")
            .group_by("teamTricode", maintain_order=True)
            .agg(last_wins=res.tail(10).str.join("")))


def recent_streaks(bs: pl.LazyFrame, overall: pl.LazyFrame) -> pl.LazyFrame:
    last5 = (played(bs).sort("gameDate_ymd").group_by("playerName")
             .agg(recent_TTFL=c("TTFL").tail(5).mean()))
    return (last5.join(overall.select("playerName", "avg_TTFL"), on="playerName")
            .filter(c("avg_TTFL") > 15)
            .with_columns(rel_recent=100.0 * (c("recent_TTFL") - c("avg_TTFL")) / c("avg_TTFL"))
            .select("playerName", "avg_TTFL", "recent_TTFL", "rel_recent")
            .with_columns(cs.float().round(1))
            .sort("rel_recent", descending=True))


def min_restrictions(bs: pl.LazyFrame) -> pl.LazyFrame:
    p = played(bs).sort("gameDate_ymd")
    out = p.group_by("playerName").agg(
        avg_sec=c("seconds").mean(), last_sec=c("seconds").last(),
        last_5=(c("seconds").tail(5) // 60).cast(pl.Utf8).str.join(" - "))   # oldest -> newest, whole minutes
    return (out.filter(c("avg_sec") > 15 * 60)
            .with_columns(avg_min=c("avg_sec") / 60,
                          rel_last=100.0 * (c("last_sec") - c("avg_sec")) / c("avg_sec"))
            .filter(c("rel_last") < -15)
            .with_columns(min_restr=pl.format("Moyenne : {} min, récents : {}",
                                              c("avg_min").cast(pl.Int64), c("last_5")))
            .select("playerName", "avg_min", "rel_last", "last_5", "min_restr"))


# =====================================================================================
# Absences / injuries  (games_missed_by_players, opp_pos_avg_per_game, absent_teammate_rel_impact)
# =====================================================================================
def team_games(bs: pl.LazyFrame) -> pl.LazyFrame:
    return bs.select("teamTricode", "gameId").unique()


def games_missed(bs: pl.LazyFrame, rosters: pl.LazyFrame, overall: pl.LazyFrame) -> pl.LazyFrame:
    """(gameId, team, did_not_play): rostered players who did not play in a game of their team."""
    played_set = played(bs).select("gameId", "playerName").unique()
    r = rosters.filter(_has_team()).select("playerName", "teamTricode")
    has_avg = overall.filter(c("avg_TTFL").is_not_null()).select("playerName")
    return (team_games(bs).join(r, on="teamTricode")
            .join(played_set, on=["gameId", "playerName"], how="anti")
            .join(has_avg, on="playerName", how="semi")
            .select("gameId", c("teamTricode").alias("team"), c("playerName").alias("did_not_play"))
            .sort("gameId", "team", "did_not_play"))


def opp_pos_avg_per_game(bs: pl.LazyFrame, pos_exp: pl.LazyFrame) -> pl.LazyFrame:
    """For each team-game: average TTFL of the OPPONENT's players at each position.
    QUIRK: the SQL joined the opponent's position rows against *every* position row of the team, so each
    row appears once per team position (9 rows instead of 3). The downstream AVG is mostly unaffected.
    To get one row per (game, team, opp_pos), add .unique() on the t1 side below."""
    tpa = (bs.select("gameId", "teamTricode", "opponent", "TTFL", "playerName").join(pos_exp, on="playerName")
           .group_by("gameId", "pos", "teamTricode", "opponent")
           .agg(_avg=c("TTFL").mean(), _n=pl.len()))
    t2 = tpa.select("gameId", c("teamTricode").alias("_t2_team"), c("opponent").alias("_t2_opp"),
                    c("pos").alias("opp_pos"), c("_avg").alias("opp_pos_avg_TTFL"),
                    c("_n").alias("opp_pos_n_players"))
    return (tpa.join(t2, left_on=["gameId", "opponent", "teamTricode"], right_on=["gameId", "_t2_team", "_t2_opp"])
            .select("gameId", "teamTricode", c("opponent").alias("opp_team"),
                    "opp_pos", "opp_pos_avg_TTFL", "opp_pos_n_players"))


def rel_ttfl_when_missing(missed: pl.LazyFrame, opp_pos: pl.LazyFrame, avg_pos_opp: pl.LazyFrame) -> pl.LazyFrame:
    """Old CTE `player_avg_rel_TTFL_per_opp_pos`: how the opposing position group scored (vs a baseline)
    when a given player did not play.
    QUIRK / probable bug: the baseline is avg_TTFL_per_pos_per_opp(position=opp_pos, opponent=opp_team), i.e.
    how that position scores AGAINST the opponent's own team. The label suggests it should be against the
    absent player's team: use right_on ['opp_pos', 'teamTricode'] by renaming `opponent` -> `teamTricode`."""
    base = avg_pos_opp.select(c("position").alias("opp_pos"), c("opponent").alias("opp_team"),
                              c("avg_TTFL").alias("_base"))
    return (missed.join(opp_pos, left_on=["gameId", "team"], right_on=["gameId", "teamTricode"])
            .join(base, on=["opp_pos", "opp_team"])
            .group_by("did_not_play", "opp_pos")
            .agg(avg_rel_TTFL_per_opp_pos=rel_pct(c("opp_pos_avg_TTFL"), c("_base")).mean()))


def absent_teammate_impact(bs: pl.LazyFrame, rosters: pl.LazyFrame, overall: pl.LazyFrame) -> pl.LazyFrame:
    """Old `absent_teammate_rel_impact`: how a player's TTFL changes when a given teammate is out.

    The SQL built roster_pairs x team_games (~1M rows) and left-joined three tables onto it. Here we start
    from the player's own played games (28k rows), attach the teammates, and anti-join "teammate played".
    Pairs with zero shared absences are kept (count 0, rel NULL), like before. Blank-team players are
    dropped: the old roster_pairs contained 3,192 junk pairs of them that never matched a game."""
    r = rosters.filter(_has_team()).select("playerName", "teamTricode")
    pairs = (r.join(r, on="teamTricode", suffix="_tm").filter(c("playerName") != c("playerName_tm"))
             .select(c("playerName").alias("playerA"), c("playerName_tm").alias("teammate"), "teamTricode"))
    p = played(bs).select(c("playerName").alias("playerA"), "gameId", c("TTFL").alias("player_TTFL"))
    teammate_played = p.select(c("playerA").alias("teammate"), "gameId")
    absent = (p.join(team_games(bs), on="gameId")                          # the game's two teams
              .join(pairs, on=["playerA", "teamTricode"])                  # keep A's current team + its teammates
              .join(teammate_played, on=["teammate", "gameId"], how="anti")
              .group_by("playerA", "teammate", "teamTricode")
              .agg(games_absent_count=pl.len(), _avg=c("player_TTFL").mean()))
    return (pairs.join(absent, on=["playerA", "teammate", "teamTricode"], how="left")
            .with_columns(c("games_absent_count").fill_null(0))
            .join(overall.select(c("playerName").alias("playerA"), c("avg_TTFL").alias("_base")),
                  on="playerA", how="left")
            .select(c("playerA").alias("playerName"), "teammate", "teamTricode", "games_absent_count",
                    rel_TTFL_teammate_absent=rel_pct(c("_avg"), c("_base"), require_x=True)))


# =====================================================================================
# Nemesis  (calc_nemesis). Heavy part: pairs of current players over the whole history.
# =====================================================================================
def _nemesis_base(hist: pl.LazyFrame, active: pl.LazyFrame) -> pl.LazyFrame:
    return (hist.filter((c("seconds") > 600) & REGULAR)
            .select("gameId", "teamTricode", "opponent", "playerName", "TTFL")
            .join(active.select("playerName"), on="playerName", how="semi"))


def _z_filter(lf: pl.LazyFrame, value: str, min_games: int, z_min: float) -> pl.LazyFrame:
    """z-score of `value` within each player (population std, like std(ddof=0)), computed BEFORE the
    games filter as in the original. Window expressions replace groupby().transform(lambda ...)."""
    x = c(value)
    std = x.std(ddof=0).over("playerName")
    return (lf.with_columns(_z=pl.when(std > 0).then((x - x.mean().over("playerName")) / std))
              .filter((c("_games") >= min_games) & (c("_z").abs() >= z_min)))


def player_nemesis(hist, active, overall_hist, curr_team, min_games: int = 5, z_min: float = 1.5):
    g = _nemesis_base(hist, active).select("gameId", "teamTricode", "playerName", "TTFL")
    pairs = (g.join(g, on="gameId", suffix="_opp")
             .filter(c("teamTricode") != c("teamTricode_opp"))
             .group_by("playerName", "playerName_opp")
             .agg(_v=c("TTFL").mean(), _games=pl.len()))
    teams = curr_team.select(c("playerName").alias("playerName_opp"), c("teamTricode").alias("opp_curr_team"))
    return (_z_filter(pairs, "_v", min_games, z_min)
            .join(overall_hist.select("playerName", c("avg_TTFL").alias("_avg")), on="playerName")
            .filter(c("_avg") > 20)
            .with_columns(rel_v_player=rel_pct(c("_v"), c("_avg")).round(2))
            .join(teams, on="playerName_opp")
            .select(c("playerName").alias("player"), c("playerName_opp").alias("opp_player"),
                    "opp_curr_team", "rel_v_player", c("_games").alias("games_v_player")))


def team_nemesis(hist, active, overall_hist, min_games: int = 5, z_min: float = 1.5):
    """NB: unlike player_nemesis there is NO `avg_TTFL > 20` filter here and the averages are LEFT-joined
    (the original calc_nemesis behaves that way; the first version of this port wrongly copied the filter)."""
    g = _nemesis_base(hist, active)
    pairs = g.group_by("playerName", "opponent").agg(_v=c("TTFL").mean(), _games=pl.len())
    return (_z_filter(pairs, "_v", min_games, z_min)
            .join(overall_hist.select("playerName", c("avg_TTFL").alias("_avg")), on="playerName", how="left")
            .with_columns(rel_v_team=rel_pct(c("_v"), c("_avg")).round(2))
            .select(c("playerName").alias("player"), c("opponent").alias("opp_team"),
                    "rel_v_team", c("_games").alias("games_v_team")))


def graph_data(bs: pl.LazyFrame) -> pl.LazyFrame:
    """The four graph_* GROUP_CONCATs (which had no ORDER BY) as aligned, chronologically sorted lists."""
    return (played(bs).sort("gameDate_ymd").group_by("playerName", maintain_order=True)
            .agg(graph_dates=c("gameDate_ymd").dt.strftime("%d/%m/%Y"), graph_opps=c("opponent"),
                 graph_TTFLs=c("TTFL"), graph_wins=c("win")))


# =====================================================================================
# Build everything once
# =====================================================================================
@dataclass
class Derived:
    stats_season: str
    rosters: pl.DataFrame
    pos_exp: pl.DataFrame
    overall: pl.DataFrame
    avgs: pl.DataFrame
    home_away: pl.DataFrame
    btb: pl.DataFrame
    rel_avg_opp: pl.DataFrame
    avg_pos: pl.DataFrame
    avg_pos_opp: pl.DataFrame
    rel_patop: pl.DataFrame
    team_wins: pl.DataFrame
    streaks: pl.DataFrame
    min_restr: pl.DataFrame
    games_missed: pl.DataFrame
    opp_pos: pl.DataFrame
    rel_missed: pl.DataFrame
    absent: pl.DataFrame
    nemesis_player: pl.DataFrame
    nemesis_team: pl.DataFrame
    graph: pl.DataFrame


def build_derived(stats_season: str | None = None, roster_season: str = SEASON, rosters=None) -> Derived:
    """Compute every derived table for one season of boxscores (+ the whole history for nemesis).
    `rosters` (playerName, teamTricode, position) overrides the roster lookup - used by validate_port.py."""
    stats_season = stats_season or latest_season()
    bs, hist = scan_boxscores([stats_season]), scan_boxscores()
    if rosters is None:
        r = current_rosters(scan_rosters(roster_season), scan_positions(), bs)
    else:
        r = to_pl(rosters).lazy().select("playerName", "teamTricode", "position")
    pos_exp = pos_expansion(r)
    overall, avgs = player_overall(bs), player_avg_ttfl(bs)
    avg_pos_opp = avg_ttfl_per_pos_per_opp(bs, pos_exp)
    missed, opp_pos = games_missed(bs, r, overall), opp_pos_avg_per_game(bs, pos_exp)
    active = bs.select("playerName").unique()
    overall_hist = player_overall(hist)

    lazy = {
        "rosters": r, "pos_exp": pos_exp, "overall": overall, "avgs": avgs,
        "home_away": home_away(bs), "btb": back_to_back(bs, avgs), "rel_avg_opp": rel_avg_opp_ttfl(bs),
        "avg_pos": avg_ttfl_per_pos(bs, pos_exp), "avg_pos_opp": avg_pos_opp,
        "rel_patop": rel_patop(bs, overall), "team_wins": team_recent_wins(bs),
        "streaks": recent_streaks(bs, overall), "min_restr": min_restrictions(bs),
        "games_missed": missed, "opp_pos": opp_pos,
        "rel_missed": rel_ttfl_when_missing(missed, opp_pos, avg_pos_opp),
        "absent": absent_teammate_impact(bs, r, overall),
        "nemesis_player": player_nemesis(hist, active, overall_hist, r.select("playerName", "teamTricode").unique()),
        "nemesis_team": team_nemesis(hist, active, overall_hist),
        "graph": graph_data(bs),
    }
    frames = pl.collect_all(list(lazy.values()))      # one pass, shared scans
    return Derived(stats_season=stats_season, **dict(zip(lazy, frames)))


def data_version() -> tuple:
    return tuple(sorted((p.name, p.stat().st_mtime_ns) for p in DATA_DIR.rglob("*.parquet")))


@lru_cache(maxsize=2)
def _cached(stats_season: str, version: tuple) -> Derived:
    return build_derived(stats_season)


def get_derived() -> Derived:
    """Cached per process; recomputed automatically when any parquet file changes."""
    season = latest_season()
    if season is None:
        raise RuntimeError("no boxscores found - run ttfl_data.migrate_from_sqlite() first")
    return _cached(season, data_version())


# =====================================================================================
# topTTFL_query  (one ~200-line SQL statement with ~17 CTEs)
# =====================================================================================
LIST_COLS = ["player_nemesis", "rel_TTFL_v_player_nemesis", "games_v_player_nemesis",
             "injured_teammates", "simp_statuses", "inj_teammates_TTFLs", "rel_TTFL_inj_teammate_abs",
             "inj_teammates_abs_count", "inj_opponents", "inj_opponents_simp_statuses", "inj_opponents_TTFLs",
             "pos_rel_TTFL_when_inj_opp", "graph_dates", "graph_opps", "graph_TTFLs", "graph_wins"]

TOP_COLS = ["playerName", "pos", "isHome", "team", "teamWins", "teamLosses", "opponent", "oppWins", "oppLosses",
            "avg_TTFL", "stddev_TTFL", "median_TTFL", "injury_status", "details", "min_restr",
            "pos_rel_TTFL_v_team", "rel_TTFL_v_opp", "ha_rel_TTFL", "rel_opp_avg_TTFL", "rel_btb_TTFL", "n_btb",
            "is_b2b", "recent_TTFL", "rel_recent", "team_nemesis", "rel_TTFL_v_team_nemesis",
            "games_v_team_nemesis", "player_nemesis", "rel_TTFL_v_player_nemesis", "games_v_player_nemesis",
            "injured_teammates", "simp_statuses", "inj_teammates_TTFLs", "rel_TTFL_inj_teammate_abs",
            "inj_teammates_abs_count", "inj_opponents", "inj_opponents_simp_statuses", "inj_opponents_TTFLs",
            "pos_rel_TTFL_when_inj_opp", "team_last_wins", "opp_last_wins",
            "graph_dates", "graph_opps", "graph_TTFLs", "graph_wins"]


def top_ttfl(game_date, d: Derived | None = None, injuries: pl.DataFrame | None = None,
             as_strings: bool = True, fill_zero: bool = True) -> pl.DataFrame:
    """One row per (player, position) playing on `game_date`, same columns/order as topTTFL_query.

    The SQL left-joined several one-to-many tables (injured teammates x injured opponents x nemeses)
    onto each player row and then GROUP_CONCAT-ed, which repeats entries. Here each one-to-many source is
    first reduced to ONE row per player (lists), then joined 1:1 (`validate='m:1'` guards that).

    as_strings=True  -> list columns come back as comma-joined strings, like GROUP_CONCAT (drop-in for the page)
    as_strings=False -> real list columns (cleaner; update the page to stop calling .split(',')).

    fill_zero=True   -> missing 'relative TTFL when absent' values become 0.0 (the SQL's COALESCE; keeps the diff
                        against topTTFL_query clean)
    fill_zero=False  -> they stay null, so the display layer can say "N/A" instead of a misleading "+0.0%"."""
    d = d or get_derived()
    day = to_date(game_date)
    sched = scan_schedule().filter(c("gameDate_ymd") == day).collect()
    yday = scan_schedule().filter(c("gameDate_ymd") == day - dt.timedelta(days=1)).collect()
    inj = (injuries if injuries is not None else scan_injuries().collect())
    inj = inj.unique(subset="player_name", keep="last", maintain_order=True)

    # ---- tonight's players: one row per (player, single position) --------------------------------
    def side(me: str, other: str, is_home: int) -> pl.DataFrame:
        return sched.select(
            c(f"{me}Team").alias("team"), c(f"{me}Team_wins").alias("teamWins"),
            c(f"{me}Team_losses").alias("teamLosses"), c(f"{other}Team").alias("opponent"),
            c(f"{other}Team_wins").alias("oppWins"), c(f"{other}Team_losses").alias("oppLosses"),
            pl.lit(is_home, dtype=pl.Int8).alias("isHome"))

    sides = pl.concat([side("home", "away", 1), side("away", "home", 0)])
    b2b = (pl.DataFrame({"team": yday["homeTeam"].to_list() + yday["awayTeam"].to_list()},
                        schema={"team": pl.Utf8}).unique()
           .with_columns(is_b2b=pl.lit(1, dtype=pl.Int8)))
    players = (d.rosters.select("playerName", c("teamTricode").alias("team"))
               .join(sides, on="team").join(d.pos_exp, on="playerName")
               .join(b2b, on="team", how="left").with_columns(c("is_b2b").fill_null(0)))

    # ---- 1:1 lookups ------------------------------------------------------------------------------
    avg1 = d.overall.select("playerName", c("avg_TTFL").round(1).alias("_avg1"))
    pos_rel = (d.avg_pos_opp.join(d.avg_pos.select("position", c("avg_TTFL").alias("_base")), on="position")
               .select("opponent", c("position").alias("pos"),
                       rel_pct(c("avg_TTFL"), c("_base")).alias("pos_rel_TTFL_v_team")))
    team_nem = d.nemesis_team.select(
        c("player").alias("playerName"), c("opp_team").alias("opponent"), c("opp_team").alias("team_nemesis"),
        c("rel_v_team").alias("rel_TTFL_v_team_nemesis"), c("games_v_team").alias("games_v_team_nemesis"))
    wins = d.team_wins

    # ---- one-to-many sources -> one row per player (lists) -----------------------------------------
    player_nem = (d.nemesis_player.sort("player", "opp_curr_team", "opp_player")
                  .group_by("player", "opp_curr_team", maintain_order=True)
                  .agg(player_nemesis=c("opp_player"), rel_TTFL_v_player_nemesis=c("rel_v_player"),
                       games_v_player_nemesis=c("games_v_player"))
                  .rename({"player": "playerName", "opp_curr_team": "opponent"}))

    rel_abs = c("rel_TTFL_teammate_absent")
    rel_abs = rel_abs.fill_null(0.0) if fill_zero else rel_abs
    inj_tm = (inj.select(c("player_name").alias("injured_player"), c("simplified_status").alias("_simp"))
              .join(d.absent.select(c("playerName").alias("playing_teammate"), c("teammate").alias("injured_player"),
                                    "games_absent_count", "rel_TTFL_teammate_absent"), on="injured_player")
              .join(d.overall.select(c("playerName").alias("injured_player"),
                                     c("avg_TTFL").round(1).alias("_inj_avg")), on="injured_player", how="left")
              .sort("playing_teammate", "injured_player")
              .group_by("playing_teammate", maintain_order=True)
              .agg(injured_teammates=c("injured_player"), simp_statuses=c("_simp"),
                   inj_teammates_TTFLs=c("_inj_avg"),
                   rel_TTFL_inj_teammate_abs=rel_abs,
                   inj_teammates_abs_count=c("games_absent_count").fill_null(0))
              .rename({"playing_teammate": "playerName"}))

    opp_inj_base = (d.rosters.select(c("playerName").alias("_opp_player"), c("teamTricode").alias("opponent"))
                    .join(inj.select(c("player_name").alias("_opp_player"), c("simplified_status").alias("_simp")),
                          on="_opp_player")
                    .join(d.overall.select(c("playerName").alias("_opp_player"),
                                           c("avg_TTFL").round(1).alias("_opp_avg")), on="_opp_player", how="left"))
    opp_inj = (players.select("playerName", "pos", "opponent")
               .join(opp_inj_base, on="opponent")
               .join(d.rel_missed, left_on=["_opp_player", "pos"], right_on=["did_not_play", "opp_pos"], how="left"))
    if fill_zero:
        opp_inj = opp_inj.with_columns(c("avg_rel_TTFL_per_opp_pos").fill_null(0.0))
    opp_inj = (opp_inj
               .sort("playerName", "pos", "_opp_player")
               .group_by("playerName", "pos", maintain_order=True)
               .agg(inj_opponents=c("_opp_player"), inj_opponents_simp_statuses=c("_simp"),
                    inj_opponents_TTFLs=c("_opp_avg"), pos_rel_TTFL_when_inj_opp=c("avg_rel_TTFL_per_opp_pos")))

    # ---- assemble ---------------------------------------------------------------------------------
    out = (
        players
        .join(d.overall.select("playerName", "avg_TTFL", "stddev_TTFL", "median_TTFL"),
              on="playerName", how="left", validate="m:1")
        .join(inj.select(c("player_name").alias("playerName"), "injury_status", "details"),
              on="playerName", how="left", validate="m:1")
        .join(d.min_restr.select("playerName", "min_restr"), on="playerName", how="left", validate="m:1")
        .join(pos_rel, on=["opponent", "pos"], how="left", validate="m:1")
        .join(d.rel_patop.select("playerName", "opponent", "rel_TTFL_v_opp"),
              on=["playerName", "opponent"], how="left", validate="m:1")
        .join(d.home_away.select("playerName", "home_rel_TTFL", "away_rel_TTFL"),
              on="playerName", how="left", validate="m:1")
        .with_columns(ha_rel_TTFL=pl.when(c("isHome") == 1).then(c("home_rel_TTFL")).otherwise(c("away_rel_TTFL")))
        .join(d.rel_avg_opp.select(c("teamTricode").alias("opponent"), "rel_opp_avg_TTFL"),
              on="opponent", how="left", validate="m:1")
        .join(d.btb.select("playerName", "rel_btb_TTFL", "n_btb"), on="playerName", how="left", validate="m:1")
        .join(d.streaks.select("playerName", "recent_TTFL", "rel_recent"), on="playerName", how="left", validate="m:1")
        .join(team_nem, on=["playerName", "opponent"], how="left", validate="m:1")
        .join(player_nem, on=["playerName", "opponent"], how="left", validate="m:1")
        .join(inj_tm, on="playerName", how="left", validate="m:1")
        .join(opp_inj, on=["playerName", "pos"], how="left", validate="m:1")
        .join(wins.select(c("teamTricode").alias("team"), c("last_wins").alias("team_last_wins")),
              on="team", how="left", validate="m:1")
        .join(wins.select(c("teamTricode").alias("opponent"), c("last_wins").alias("opp_last_wins")),
              on="opponent", how="left", validate="m:1")
        .join(d.graph, on="playerName", how="left", validate="m:1")
        .select(TOP_COLS)
        .sort("avg_TTFL", descending=True, nulls_last=True)      # SQLite put NULLs last on DESC
    )
    if as_strings:
        out = out.with_columns([c(n).cast(pl.List(pl.Utf8)).list.join(",") for n in LIST_COLS])
    return out


# =====================================================================================
# query_* functions (Streamlit pages)
# =====================================================================================
_PER_GAME = [("Pts", "points"), ("Ast", "assists"), ("Stl", "steals"), ("Blk", "blocks"), ("Stk", None),
             ("Reb", "reboundsTotal"), ("Oreb", "reboundsOffensive"), ("Dreb", "reboundsDefensive"),
             ("Tov", "turnovers"), ("FGM", "fieldGoalsMade"), ("FGA", "fieldGoalsAttempted"),
             ("FG3M", "threePointersMade"), ("FG3A", "threePointersAttempted"), ("FTM", "freeThrowsMade"),
             ("FTA", "freeThrowsAttempted"), ("PM", "plusMinusPoints")]


def _box_spec() -> list[tuple[str, pl.Expr]]:
    """The two copy-pasted 40-line agg_cols blocks, once. Order == the SQL's column order."""
    spec = [("GP", pl.len()), ("SECONDS", c("seconds").mean().round(1)), ("TOT_SECONDS", _sum("seconds"))]
    for alias, col in _PER_GAME:
        if col is None:
            spec += [("Stk", c("steals").mean() + c("blocks").mean()), ("TOT_Stk", _sum("steals") + _sum("blocks"))]
        else:
            spec += [(alias, c(col).mean()), (f"TOT_{alias}", _sum(col))]
    fgm, fga = c("fieldGoalsMade").sum(), c("fieldGoalsAttempted").sum()
    spec += [
        ("TOT_TTFL", _sum("TTFL")),
        ("FG_PCT", safe_div(fgm, fga)),
        ("FG3_PCT", safe_div(c("threePointersMade").sum(), c("threePointersAttempted").sum())),
        ("FT_PCT", safe_div(c("freeThrowsMade").sum(), c("freeThrowsAttempted").sum())),
        ("EFG", safe_div(fgm + 0.5 * c("threePointersMade").sum(), fga)),
        ("TS", safe_div(c("points").sum(), 2 * (fga + 0.44 * c("freeThrowsAttempted").sum()))),
        ("ast_to_tov", safe_div(c("assists").sum(), c("turnovers").sum())),
        # the SQL divided by SUM(seconds)/60 in INTEGER arithmetic (truncated minutes); this uses real minutes
        ("ttfl_per_min", safe_div(c("TTFL").sum(), c("seconds").sum() / 60)),
        ("max_ttfl", c("TTFL").max()), ("min_ttfl", c("TTFL").min()),
    ]
    return spec


BOX_COLS = [n for n, _ in _box_spec()]


def box_aggs() -> list[pl.Expr]:
    return [e.alias(n) for n, e in _box_spec()]


def _scope(alltime: bool, seasons) -> list[str] | None:
    seasons = list(seasons or [])
    return seasons if seasons else (None if alltime else [latest_season()])


@lru_cache(maxsize=4)
def _overall_cached(alltime: bool, version: tuple) -> dict:
    bs = scan_boxscores(None if alltime else [latest_season()])
    avgs = player_avg_ttfl(bs)
    lazy = {
        "avg": player_overall(bs).select("playerName", c("avg_TTFL").alias("TTFL"), "stddev_TTFL", "median_TTFL"),
        "ha": home_away(bs).select("playerName", "home_rel_TTFL", "away_rel_TTFL", "home_avg_TTFL",
                                   "away_avg_TTFL").unique(subset="playerName"),
        "btb": back_to_back(bs, avgs).select("playerName", "btbTTFL", "rel_btb_TTFL", "n_btb")
                                     .unique(subset="playerName"),
    }
    return dict(zip(lazy, pl.collect_all(list(lazy.values()))))


def overall_tables(alltime: bool) -> dict:
    """Per-player career (alltime) or latest-season numbers; ignore the page's season/team filters, as before."""
    return _overall_cached(alltime, data_version())


def query_player_stats(alltime: bool = False, only_active_players: bool = False, seasons=(),
                       playoffs: str = "Saison régulière", team: str = "") -> pl.DataFrame:
    sel = select_games(scan_boxscores(_scope(alltime, seasons)), playoffs, team=team)
    agg = sel.sort("gameDate_ymd").group_by("playerName").agg(*box_aggs(), c("teamTricode").last())  # last team = last game
    if only_active_players:
        active = scan_boxscores([latest_season()]).select("playerName").unique()
        agg = agg.join(active, on="playerName", how="semi")
    t = overall_tables(alltime)
    out = (agg.collect()
           .join(t["avg"], on="playerName", how="left")
           .join(t["ha"], on="playerName", how="left")
           .join(t["btb"], on="playerName", how="left"))
    cols = (["playerName", "TTFL", *BOX_COLS, "median_TTFL", "stddev_TTFL", "home_rel_TTFL", "away_rel_TTFL",
             "home_avg_TTFL", "away_avg_TTFL", "btbTTFL", "rel_btb_TTFL", "n_btb"])
    return out.select(cols if alltime else cols + ["teamTricode"])


def query_player_stats_by_season(player: str, seasons=(), playoffs: str = "Saison régulière",
                                 team: str = "") -> pl.DataFrame:
    """'Global' row + one row per season. Unlike the SQL (inner joins), a season/player without any
    back-to-back game is kept, with NULL btb columns, instead of vanishing."""
    career = scan_boxscores().filter(c("playerName") == player)       # unfiltered: the avg/ha/btb stats
    sel = select_games(career, playoffs, seasons, team)
    avgs = player_avg_ttfl(career)
    ha, btb = home_away(career), back_to_back(career, avgs)

    glob = (sel.select(c("playerName").first(), *box_aggs()).with_columns(season=pl.lit("Global")).collect()
            .join(player_overall(career).select("playerName", c("avg_TTFL").alias("TTFL"), "stddev_TTFL",
                                                "median_TTFL").collect(), on="playerName", how="left")
            .join(ha.select("playerName", "home_rel_TTFL", "away_rel_TTFL", "home_avg_TTFL", "away_avg_TTFL")
                    .unique(subset="playerName").collect(), on="playerName", how="left")
            .join(btb.select("playerName", "btbTTFL", "rel_btb_TTFL", "n_btb")
                     .unique(subset="playerName").collect(), on="playerName", how="left"))
    by_season = (sel.group_by("season").agg(c("playerName").first(), *box_aggs()).collect()
                 .join(avgs.select("season", c("avg_TTFL_season").alias("TTFL"),
                                   c("stddev_TTFL_season").alias("stddev_TTFL"),
                                   c("median_TTFL_season").alias("median_TTFL")).collect(), on="season", how="left")
                 .join(ha.select("season", c("home_rel_TTFL_season").alias("home_rel_TTFL"),
                                 c("away_rel_TTFL_season").alias("away_rel_TTFL"),
                                 c("home_avg_TTFL_season").alias("home_avg_TTFL"),
                                 c("away_avg_TTFL_season").alias("away_avg_TTFL")).collect(), on="season", how="left")
                 .join(btb.select("season", c("btbTTFL_season").alias("btbTTFL"),
                                  c("rel_btb_TTFL_season").alias("rel_btb_TTFL"),
                                  c("n_btb_season").alias("n_btb")).collect(), on="season", how="left")
                 .sort("season", descending=True))
    cols = ["season", "playerName", *BOX_COLS, "TTFL", "stddev_TTFL", "median_TTFL", "home_rel_TTFL",
            "away_rel_TTFL", "home_avg_TTFL", "away_avg_TTFL", "btbTTFL", "rel_btb_TTFL", "n_btb"]
    return pl.concat([glob.select(cols), by_season.select(cols)], how="diagonal_relaxed")


def query_player_v_team(player: str, alltime: bool = False, seasons=(), playoffs: str = "Saison régulière",
                        team: str = "") -> pl.DataFrame:
    bs = scan_boxscores(_scope(alltime, seasons)).filter(c("playerName") == player)
    sel = select_games(bs, playoffs, team=team)
    m = lambda col: c(col).mean()                                    # noqa: E731
    fga = m("fieldGoalsAttempted")
    return (sel.group_by("opponent").agg(
        pl.len().alias("GP"), m("TTFL").alias("TTFL"), m("points").alias("Pts"), m("assists").alias("Ast"),
        m("reboundsTotal").alias("Reb"), m("steals").alias("Stl"), m("blocks").alias("Blk"),
        m("turnovers").alias("Tov"), m("fieldGoalsMade").alias("FGM"), fga.alias("FGA"),
        m("threePointersMade").alias("FG3M"), m("threePointersAttempted").alias("FG3A"),
        m("freeThrowsMade").alias("FTM"), m("freeThrowsAttempted").alias("FTA"),
        m("plusMinusPoints").alias("PM"), m("seconds").alias("seconds"),
        m("reboundsOffensive").alias("Oreb"), m("reboundsDefensive").alias("Dreb"),
        safe_div(m("fieldGoalsMade"), fga).alias("FG_PCT"),
        safe_div(m("threePointersMade"), m("threePointersAttempted")).alias("FG3_PCT"),
        safe_div(m("freeThrowsMade"), m("freeThrowsAttempted")).alias("FT_PCT"),
        (100 * safe_div(m("fieldGoalsMade") + 0.5 * m("threePointersMade"), fga)).round(1).alias("EFG"),
        (100 * safe_div(c("points").sum(), 2 * (c("fieldGoalsAttempted").sum()
                                                 + 0.44 * c("freeThrowsAttempted").sum()))).round(1).alias("TS"),
        safe_div(m("assists"), m("turnovers")).round(1).alias("ast_to_tov"),
    ).collect())


def query_historique_des_perfs(player: str, alltime: bool = False, seasons=(), playoffs: str = "Saison régulière",
                               team: str = "") -> pl.DataFrame:
    """Raw game log. with_legacy_columns re-adds gameDate/minutes/homeTeam/... so existing pages keep working."""
    bs = scan_boxscores(_scope(alltime, seasons)).filter(c("playerName") == player)
    return with_legacy_columns(select_games(bs, playoffs, team=team).sort("gameDate_ymd")).collect()


def query_opp_team_avgs(seasons=()) -> pl.DataFrame:
    """What each team allows per game. NOTE: `wins` = SUM(win) of the players FACING that team, i.e. the
    team's LOSSES (kept as is). Use (n_games - wins) if you meant the team's own wins."""
    bs = scan_boxscores(list(seasons) or [latest_season()])
    per_gid = played(bs).group_by("gameId", "opponent").agg(
        pts=_sum("points"), ast=_sum("assists"), reb=_sum("reboundsTotal"), Oreb=_sum("reboundsOffensive"),
        Dreb=_sum("reboundsDefensive"), tov=_sum("turnovers"), stl=_sum("steals"), blk=_sum("blocks"),
        FGM=_sum("fieldGoalsMade"), FGA=_sum("fieldGoalsAttempted"), FG3M=_sum("threePointersMade"),
        FG3A=_sum("threePointersAttempted"), FTM=_sum("freeThrowsMade"), FTA=_sum("freeThrowsAttempted"),
        win=c("win").min())
    m = lambda col: c(col).mean()                                    # noqa: E731
    return (per_gid.group_by("opponent").agg(
        m("pts").alias("pts"), m("ast").alias("ast"), m("reb").alias("reb"), m("Oreb").alias("Oreb"),
        m("Dreb").alias("Dreb"), m("tov").alias("tov"), m("stl").alias("stl"), m("blk").alias("blk"),
        m("FGM").alias("opp_FGM"), m("FGA").alias("opp_FGA"), (100 * safe_div(m("FGM"), m("FGA"))).alias("opp_FG_PCT"),
        m("FG3M").alias("opp_FG3M"), m("FG3A").alias("opp_FG3A"), (100 * safe_div(m("FG3M"), m("FG3A"))).alias("opp_FG3_PCT"),
        m("FTM").alias("opp_FTM"), m("FTA").alias("opp_FTA"), (100 * safe_div(m("FTM"), m("FTA"))).alias("opp_FT_PCT"),
        (100 * safe_div(c("FGM").sum() + 0.5 * c("FG3M").sum(), c("FGA").sum())).alias("opp_EFG"),
        (100 * safe_div(c("pts").sum(), 2 * (c("FGA").sum() + 0.44 * c("FTA").sum()))).alias("opp_TS"),
        c("win").sum().alias("wins"))
        .rename({"opponent": "teamTricode"})
        .sort("pts", descending=True)
        .collect())


if __name__ == "__main__":
    import sys
    import time
    day = sys.argv[1] if len(sys.argv) > 1 else "2026-01-01"
    t0 = time.perf_counter()
    d = get_derived()
    t1 = time.perf_counter()
    df = top_ttfl(day, d)
    t2 = time.perf_counter()
    print(f"build_derived({d.stats_season}): {t1 - t0:.2f}s | top_ttfl({day}): {t2 - t1:.3f}s | {df.height} rows")
    print(df.select("playerName", "pos", "team", "opponent", "avg_TTFL", "rel_recent", "is_b2b").head(10))
