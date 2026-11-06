"""
topTTFL_manager.py - builds the table shown on the topTTFL page.

Before: topTTFL_query (SQL, comma-joined strings) -> format_to_table (pandas: split, explode, drop_duplicates,
sort, groupby-lambda, merge, apply(axis=1) ... ~450 lines).
Now:    ttfl_stats.top_ttfl(as_strings=False) already returns real list columns, one row per (player, position),
        so format_to_table is a plain per-player loop with small formatting helpers (~250 lines, no pandas
        until the very last line). ~300 rows per day, so a Python loop is far below any visible cost and
        it is easy to read, debug and unit-test.

Bugs of the old version that disappear by construction:
  * multi-position players: position labels and their relative values were paired from two independent set()
    orderings, so a position could carry another position's number (or lose one when two values were equal);
  * graph_wins was not re-sorted with the other graph columns (flags no longer matched their games);
  * the "N/A -> last season" fallback crashed (.astype(float) on '28.4 🔥') whenever any other player tonight
    had a streak emoji, and it averaged ALL rows (DNPs, playoffs) instead of like the main TTFL column;
  * injured opponents were matched across positions by index in comma-split strings; two injured players with
    the same TTFL could duplicate a player's row after the merge;
  * players with no shared games showed "+0.0%" (the SQL's COALESCE 0); they now show "N/A".
Cosmetic differences from the old output: no stray blank line in 'nemesis' when a player has no individual
nemesis; positions inside the injured-opponent lines are alphabetical (like 'Poste'); a median of 24.5 is no
longer truncated to 24; a value that rounds to zero from below shows '+0.0%' instead of '-0.0%'.
"""
from __future__ import annotations

import math

HOT3, HOT1, COLD3, COLD1 = " 🔥🔥🔥", " 🔥", " ❄️❄️❄️", " ❄️"

COLUMNS = [
    "Joueur", "Poste", "Lieu", "Équipe", "Adversaire", "TTFL", "stdTTFL", "median_TTFL", "is_b2b", "n_btb",
    "Statut", "details", "team_nemesis", "player_nemesis", "nemesis", "streak_str", "streak_indicator",
    "graph_dates", "graph_opps", "graph_TTFLs", "graph_wins", "rel_opp_avg_TTFL", "rel_btb_TTFL",
    "rel_btb_TTFL_with_br", "team_injury_status", "opp_inj_status", "allrel", "team_info", "opp_info",
]
# Dropped vs the old output: the three graph_*_split leftovers and clean_team/clean_opp/opp (all dead weight).
# If a page reads a column that is missing here, add it to _player_row and to COLUMNS.


# ----------------------------------------------------------------------------------------------------
# Public entry points
# ----------------------------------------------------------------------------------------------------
def _load(name: str):
    """Import ttfl_stats / ttfl_data whether they sit next to this file or in the `data` package."""
    import importlib
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name != name:
            raise
        return importlib.import_module(f"data.{name}")


def get_top_TTFL(game_date_ymd: str):
    """Drop-in for the old function: pandas DataFrame, same column names the page used."""
    S = _load("ttfl_stats")
    d = S.get_derived()
    df = S.top_ttfl(game_date_ymd, d, as_strings=False, fill_zero=False)
    last_avgs, label = _last_season_avgs(d, df)
    return format_to_table(df, last_avgs, label)


def format_to_table(df, last_avgs: dict | None = None, last_label: str = ""):
    """df: Polars frame from top_ttfl(..., as_strings=False, fill_zero=False) (or a list of row dicts).
    last_avgs: {player: last-season average TTFL}, used only for players with no average this season."""
    import pandas as pd

    rows = df if isinstance(df, list) else df.to_dicts()
    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    by_player: dict[str, list[dict]] = {}
    for r in rows:                                          # rows of one player are the positions he can play
        by_player.setdefault(r["playerName"], []).append(r)

    table = [_player_row(g, last_avgs or {}, last_label) for g in by_player.values()]
    # best average first; players with no number at all go last (stable, so SQL order breaks ties)
    table.sort(key=lambda t: (t["_sort"] is None, -(t["_sort"] or 0.0)))
    return pd.DataFrame(table)[COLUMNS]


def _last_season_avgs(d, df) -> tuple[dict, str]:
    """Average TTFL in the previous season, only fetched when somebody tonight has no average this season.
    Same definition as the main TTFL column (regular season, seconds > 0) - the old query averaged every row."""
    if not any(r is None for r in df["avg_TTFL"].to_list()):
        return {}, ""
    data, S = _load("ttfl_data"), _load("ttfl_stats")
    seasons = data.available_seasons()
    i = seasons.index(d.stats_season) if d.stats_season in seasons else 0
    if i == 0:
        return {}, ""
    prev = seasons[i - 1]
    last = S.player_overall(data.scan_boxscores([prev])).select("playerName", "avg_TTFL").collect()
    return dict(zip(last["playerName"].to_list(), last["avg_TTFL"].to_list())), prev[2:]


# ----------------------------------------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------------------------------------
def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _r1(x: float) -> float:
    """Round to 1 decimal exactly like pandas/numpy did (multiply, round half-even, divide), so a stored 7.35
    still displays as 7.4. Python's round(7.35, 1) gives 7.3 (binary representation) and would change the page."""
    return round(x * 10) / 10


def f1(x: float) -> str:
    return f"{_r1(x):.1f}"


def pct(x, na: str = "N/A") -> str:
    """'+3.2%', '-1.0%', or 'N/A'."""
    return na if _missing(x) else f"{_r1(x):+.1f}%"


def _lists(r: dict, *cols: str) -> list[tuple]:
    """Rows of aligned list columns; a player without any (left join -> null) gives []."""
    return list(zip(*[r.get(c) or [] for c in cols]))


def _streak_indicator(rel) -> str:
    if _missing(rel):
        return ""
    if rel > 20:
        return " 🔥🔥🔥"
    if rel > 10:
        return " 🔥"
    if rel < -20:
        return " ❄️❄️❄️"
    if rel < -10:
        return " ❄️"
    return ""


def _injury_block(title_team: str, lines: list[str]) -> str:
    if not lines:
        return f"Pas de joueurs blessés chez {title_team}"
    return f"Joueurs blessés chez {title_team} :<hr style=\"margin:3px 0;\">" + "<br>".join(lines)


def _team_injuries(r: dict) -> str:
    """Injured teammates, highest TTFL first. Injured players with no TTFL this season are not listed."""
    items = [(n, s, t, rel, k) for n, s, t, rel, k in _lists(
        r, "injured_teammates", "simp_statuses", "inj_teammates_TTFLs",
        "rel_TTFL_inj_teammate_abs", "inj_teammates_abs_count") if t is not None]
    items.sort(key=lambda i: (-i[2], i[0]))
    return _injury_block(r["team"], [
        f"- {n} ({s}) - TTFL : {f1(t)} - Absent : {pct(rel)} ({k or 0} matchs)" for n, s, t, rel, k in items])


def _opp_injuries(rows: list[dict], positions: list[str]) -> str:
    """Injured opponents with, for each position the player can play, how that position scored when he was out.
    Built from (player, position) rows, so alignment never depends on list order or on ties."""
    opp: dict[str, list] = {}                               # name -> [status, ttfl, {pos: rel}]
    for r in rows:
        for n, s, t, rel in _lists(r, "inj_opponents", "inj_opponents_simp_statuses", "inj_opponents_TTFLs",
                                   "pos_rel_TTFL_when_inj_opp"):
            if t is not None:
                opp.setdefault(n, [s, t, {}])[2][r["pos"]] = rel
    lines = [f"- {n} ({s}) - TTFL : {f1(t)} : " + " - ".join(f"{p} : {pct(rels[p])}" for p in positions if p in rels)
             for n, (s, t, rels) in sorted(opp.items(), key=lambda kv: (-kv[1][1], kv[0]))]
    return _injury_block(rows[0]["opponent"], lines)


def _nemesis(r: dict) -> tuple[str, str]:
    """(team_nemesis, player_nemesis) display strings. Player nemeses: biggest positive impact first."""
    team = ""
    if r.get("team_nemesis"):
        team = (f"<br> - {r['team_nemesis']} : {pct(r['rel_TTFL_v_team_nemesis'])} "
                f"({r['games_v_team_nemesis']} matchs)")
    pl_items = sorted(_lists(r, "player_nemesis", "rel_TTFL_v_player_nemesis", "games_v_player_nemesis"),
                      key=lambda i: (-(i[1] if not _missing(i[1]) else -1e9), i[0]))
    player = "<br>".join(f" - {n} : {pct(rel)} ({g} matchs)" for n, rel, g in pl_items if not _missing(rel))
    return team, player


def _player_row(rows: list[dict], last_avgs: dict, last_label: str) -> dict:
    r = rows[0]                                             # everything except position-specific data is shared
    name, team, opp = r["playerName"], r["team"], r["opponent"]
    home = r["isHome"] == 1
    positions = sorted({x["pos"] for x in rows})
    pos_rel = {x["pos"]: x["pos_rel_TTFL_v_team"] for x in rows}

    # --- headline numbers -------------------------------------------------------------------------
    avg = None if _missing(r["avg_TTFL"]) else _r1(r["avg_TTFL"])
    std = "N/A" if _missing(r["stddev_TTFL"]) else _r1(r["stddev_TTFL"])
    med = "N/A" if _missing(r["median_TTFL"]) else (int(r["median_TTFL"]) if r["median_TTFL"] % 1 == 0
                                                    else r["median_TTFL"])      # 24.5 stays 24.5 (was truncated)
    indicator = _streak_indicator(r["rel_recent"])
    sort_key = avg
    if avg is not None:
        ttfl = f"{avg:.1f}"
    elif last_avgs.get(name) is not None:                   # no stats this season: show last season's average
        sort_key = _r1(last_avgs[name])
        ttfl = f"{sort_key:.1f} ({last_label})"
    else:
        ttfl = "N/A"

    # --- status -----------------------------------------------------------------------------------
    inj, details, restr = r["injury_status"] or "", r["details"] or "", r["min_restr"] or ""
    statut = inj or ("Restriction de minutes possible" if restr else "")
    details = details or restr

    # --- nemesis / streak -------------------------------------------------------------------------
    team_nem, player_nem = _nemesis(r)
    nemesis = ""
    if team_nem or player_nem:
        body = "<br>".join(x for x in (player_nem, team_nem.removeprefix("<br>")) if x)
        nemesis = f"<br><br>{name} all time vs. :<hr style=\"margin:0px 0;\">{body}"
    streak_str = ""
    if not _missing(r["rel_recent"]) and abs(r["rel_recent"]) > 10:
        streak_str = f"{name} récemment : {f1(r['recent_TTFL'])} ({pct(r['rel_recent'])})<br>"

    # --- relative stuff ---------------------------------------------------------------------------
    n_btb = 0 if _missing(r["n_btb"]) else int(r["n_btb"])
    btb = f"{name} en back to back : " + ("N/A<br>" if _missing(r["rel_btb_TTFL"])
                                          else f"{pct(r['rel_btb_TTFL'])} ({n_btb} matchs)<br>")
    btb_with_br = btb if r["is_b2b"] == 1 else ""
    rel_opp = f"Toutes les équipes contre {opp} : {pct(r['rel_opp_avg_TTFL'])}"
    rel_v_opp = f"{name} contre {opp} : {pct(r['rel_TTFL_v_opp'])}"
    rel_ha = f"{name}{' à la maison : ' if home else ' à l' + chr(39) + 'extérieur : '}{pct(r['ha_rel_TTFL'])}"
    pos_v_team = f"Postes contre {opp} : " + " - ".join(f"{p} : {pct(pos_rel[p])}" for p in positions)
    allrel = (streak_str + rel_opp + "<br>" + rel_v_opp + "<br>" + rel_ha + "<br>" + pos_v_team + "<br>"
              + btb_with_br + f"Médiane/Ecart-type : {med}/{std}" + nemesis)

    # --- injuries / form --------------------------------------------------------------------------
    team_inj, opp_inj = _team_injuries(r), _opp_injuries(rows, positions)
    team_info = f"{team_inj}<br><br>10 derniers matchs : {r['team_last_wins'] or ''}" if r["team_last_wins"] else ""
    opp_info = f"{opp_inj}<br><br>10 derniers matchs : {r['opp_last_wins'] or ''}" if r["opp_last_wins"] else ""

    return {
        "_sort": sort_key,
        "Joueur": name + (" (B2B)" if r["is_b2b"] else ""),
        "Poste": "-".join(positions),
        "Lieu": "Dom." if home else "Ext.",
        "Équipe": f"{team} ({r['teamWins'] or 0}W-{r['teamLosses'] or 0}L)",
        "Adversaire": f"{opp} ({r['oppWins'] or 0}W-{r['oppLosses'] or 0}L)",
        "TTFL": ttfl + indicator, "stdTTFL": std, "median_TTFL": med,
        "is_b2b": r["is_b2b"], "n_btb": None if _missing(r["n_btb"]) else n_btb,
        "Statut": statut, "details": details,
        "team_nemesis": team_nem, "player_nemesis": player_nem, "nemesis": nemesis,
        "streak_str": streak_str, "streak_indicator": indicator,
        # lists were sorted by date in top_ttfl, so the four series are aligned (graph_wins was not before)
        "graph_dates": ",".join(r["graph_dates"] or []), "graph_opps": ",".join(r["graph_opps"] or []),
        "graph_TTFLs": ",".join("" if x is None else str(x) for x in r["graph_TTFLs"] or []),
        "graph_wins": ",".join("" if x is None else str(x) for x in r["graph_wins"] or []),
        "rel_opp_avg_TTFL": rel_opp, "rel_btb_TTFL": btb, "rel_btb_TTFL_with_br": btb_with_br,
        "team_injury_status": team_inj, "opp_inj_status": opp_inj,
        "allrel": allrel, "team_info": team_info, "opp_info": opp_info,
    }
