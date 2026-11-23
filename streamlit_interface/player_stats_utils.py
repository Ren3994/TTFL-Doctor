"""Player-stats page backend, polars-first.

Everything stays in polars until the very last step. The two public functions that feed
the UI (`get_all_player_stats`, `historique_des_perfs`) convert to pandas ONCE, at the
boundary, because Styler / `df_to_html` still expect pandas. Drop that conversion as soon
as the consumers accept polars.
"""
import os
import sys

import numpy as np
import polars as pl
import polars.selectors as cs
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.ttfl_stats import (query_player_stats, query_player_stats_by_season, query_player_v_team,
                             query_historique_des_perfs, distinct_seasons, sql_sum)
from data.ttfl_data import scan_boxscores, latest_season, franchise_expr
from streamlit_interface.streamlit_utils import uspace, french_flag_expr
from streamlit_interface.JDP_utils import match_player, match_team
from streamlit_interface.classement_TTFL_utils import df_to_html
from streamlit_interface.plotting_utils import interactive_plot


# ───────────────────────────── constants ─────────────────────────────

GAME_DATE_FORMAT = '%d/%m/%Y'      # gameDate comes back from the backend as a string in this format
PER36_SECONDS = 36 * 60

FRENCH_MONTHS = {1: 'jan', 2: 'fév', 3: 'mar', 4: 'avr', 5: 'mai', 6: 'juin',
                 7: 'juil', 8: 'aoû', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'déc'}

AGG_MODES = ('Moyennes', 'Totaux', 'Moyennes par 36 min')

COUNTING = ['Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Stk', 'Tov', 'PM']
PER36_COLS = ['TTFL', *COUNTING, 'FGM', 'FGA', 'FG2M', 'FG2A', 'FG3M', 'FG3A', 'FTM', 'FTA']

# stored as fractions -> displayed as percentages
PCT_COLS = ['EFG', 'TS', 'FG_PCT', 'FG3_PCT', 'FT_PCT']

# A ratio is UNDEFINED (null, shown blank) when its denominator is zero: never display it as 0.
# Conditions use the TOT_ columns: exact, and independent of how the source defines each ratio.
DEFINED_IF = {
    'FG_PCT': pl.col('TOT_FGA') > 0,
    'FG3_PCT': pl.col('TOT_FG3A') > 0,
    'FT_PCT': pl.col('TOT_FTA') > 0,
    'EFG': pl.col('TOT_FGA') > 0,
    'TS': (pl.col('TOT_FGA') + pl.col('TOT_FTA')) > 0,
    'ast_to_tov': pl.col('TOT_Tov') > 0,
    'btbTTFL': pl.col('n_btb') > 0,
    'rel_btb_TTFL': pl.col('n_btb') > 0,
}
# can legitimately be missing: NaN / inf are turned into null, never into 0
NULLABLE_COLS = ['Oreb', 'Dreb', 'PM', 'home_avg_TTFL', 'away_avg_TTFL', 'home_rel_TTFL', 'away_rel_TTFL']
# real counts: a missing value does mean 0
COUNT_COLS = ['n_btb']
# totals of columns that are null in some games: without any data there is no total (a sum of nothing is not 0)
TOTAL_NEEDS_DATA = {'TOT_Oreb': 'Oreb', 'TOT_Dreb': 'Dreb', 'TOT_PM': 'PM'}
# player-vs-team table: percentage -> attempts column that must be > 0
VS_TEAM_PCT = {'FG_PCT': 'FGA', 'FG3_PCT': 'FG3A', 'FT_PCT': 'FTA'}

TTFL_COLS = ['playerName', 'TTFL', 'stddev_TTFL', 'median_TTFL', 'max_ttfl', 'min_ttfl',
             'home_avg_TTFL', 'away_avg_TTFL', 'home_rel_TTFL', 'away_rel_TTFL',
             'btbTTFL', 'rel_btb_TTFL', 'n_btb']

VS_TEAM_COLS = ['opponent', 'GP', 'MINUTES', 'TTFL', 'Pts', 'Ast', 'Reb', 'Oreb', 'Dreb', 'Stl', 'Blk', 'Tov',
                'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'PM']

HISTORY_RENAME = {
    'playerName': 'Joueur', 'minutes': 'Min', 'points': 'Pts', 'assists': 'Ast',
    'reboundsTotal': 'Reb', 'reboundsOffensive': 'Oreb', 'reboundsDefensive': 'Dreb',
    'steals': 'Stl', 'blocks': 'Blk', 'turnovers': 'Tov',
    'fieldGoalsMade': 'FGM', 'fieldGoalsAttempted': 'FGA',
    'threePointersMade': 'FG3M', 'threePointersAttempted': 'FG3A',
    'freeThrowsMade': 'FTM', 'freeThrowsAttempted': 'FTA',
    'plusMinusPoints': 'Pm', 'gameDate': 'Date',
}
HISTORY_SHOW_COLS = ['Date', 'teamTricode', 'opponent', 'isHome', 'TTFL', 'Min', 'Pts', 'Ast', 'Reb',
                     'Stl', 'Blk', 'Tov', 'FG', 'FG3', 'FT', 'Pm', 'win']

# plot label -> column of the history frame (see get_plot for the derived ones)
PLOT_STATS = {
    'TTFL': 'TTFL', 'Min': 'minutes', 'Pts': 'points', 'Reb': 'reboundsTotal', 'Ast': 'assists',
    'Stl': 'steals', 'Blk': 'blocks', 'Tov': 'turnovers',
    'FG': 'fieldGoalsMade', 'FGA': 'fieldGoalsAttempted', 'FG%': 'FGpct',
    'FG3': 'threePointersMade', 'FG3A': 'threePointersAttempted', 'FG3%': 'FG3pct',
    'FT': 'freeThrowsMade', 'FTA': 'freeThrowsAttempted', 'FT%': 'FTpct',
    '±': 'plusMinusPoints',
}
HOVER_COLS = {'pts': 'points', 'reb': 'reboundsTotal', 'ast': 'assists', 'opp': 'opponent',
              'FGA': 'fieldGoalsAttempted', 'FGM': 'fieldGoalsMade',
              'FG3A': 'threePointersAttempted', 'FG3M': 'threePointersMade',
              'FTA': 'freeThrowsAttempted', 'FTM': 'freeThrowsMade', 'win': 'strwin'}
# how each box-score line contributes to TTFL (misses and turnovers count negatively)
TTFL_DETAILS = {
    'Pts': pl.col('points'), 'Reb': pl.col('reboundsTotal'), 'Ast': pl.col('assists'),
    'Stl': pl.col('steals'), 'Blk': pl.col('blocks'),
    'FG': pl.col('fieldGoalsMade'), 'FG3': pl.col('threePointersMade'), 'FT': pl.col('freeThrowsMade'),
    'Tov': -pl.col('turnovers'),
    'FG ratés': pl.col('fieldGoalsMade') - pl.col('fieldGoalsAttempted'),
    'FG3 ratés': pl.col('threePointersMade') - pl.col('threePointersAttempted'),
    'FT ratés': pl.col('freeThrowsMade') - pl.col('freeThrowsAttempted'),
}

# (slider key, session key of its max, key in get_maximums(), rounding step, divisor)
SLIDERS = (
    ('slider_gp',  'max_games',  'GP',  10, 5),
    ('slider_pts', 'max_points', 'Pts', 10, 10),
    ('slider_fg',  'max_fg',     'FG',  10, 10),
    ('slider_fg3', 'max_fg3',    'FG3', 10, 10),
    ('slider_ft',  'max_ft',     'FT',  10, 10),
)
# (label shown in the expander title, slider key) -- in display order
FILTER_LABELS = (('GP', 'slider_gp'), ('min', 'slider_min'), ('Pts', 'slider_pts'),
                 ('FG', 'slider_fg'), ('FG3', 'slider_fg3'), ('FT', 'slider_ft'))
DEFAULT_MAXIMUMS = {'GP': 1, 'Pts': 1, 'FG': 1, 'FG3': 1, 'FT': 1, 'MIN': 48}


# ───────────────────────────── small helpers ─────────────────────────────

def _ensure_polars(df) -> pl.DataFrame:
    """Accept whatever the data layer returns (DataFrame, LazyFrame, pandas) and give back an eager polars frame."""
    if isinstance(df, pl.DataFrame):
        return df
    if isinstance(df, pl.LazyFrame):
        return df.collect()
    return pl.from_pandas(df)


def _filter_scope():
    """The 4 session-state values that define which games are in scope."""
    ss = st.session_state
    return (ss.get('player_alltime_stats', False),
            ss.get('selected_seasons', []),
            ss.get('playoffs', 'Saison régulière'),
            ss.get('matched_team', ''))


def _fill_zero(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Replace null (and NaN, for float columns) with 0, keeping each column's dtype."""
    float_cols = df.select(cols).select(cs.float()).columns     # fill_nan only makes sense on floats
    if float_cols:
        df = df.with_columns(pl.col(float_cols).fill_nan(0))
    return df.with_columns(pl.col(cols).fill_null(0))


def _nan_to_null(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """NaN / inf -> null (float columns only), so 'undefined' is never displayed as a number."""
    float_cols = df.select(cols).select(cs.float()).columns
    return df.with_columns([pl.when(pl.col(c).is_finite()).then(pl.col(c)).alias(c) for c in float_cols])


def _defined_value(col: str) -> pl.Expr:
    """Column (x100 if it is a fraction), or null where its denominator is zero."""
    value = pl.col(col) * 100 if col in PCT_COLS else pl.col(col)
    return pl.when(DEFINED_IF[col]).then(value).otherwise(None).alias(col)


def _pct(made: pl.Expr, att: pl.Expr, digits: int = 1) -> pl.Expr:
    """100 * made / att, or null (undefined) when there are no attempts."""
    return pl.when(att > 0).then((100 * made / att).round(digits)).otherwise(None)


def _mmss(seconds: str) -> pl.Expr:
    """Seconds column -> 'MM:SS' string. Rounds first, so 59.7 s can never display as '12:60'."""
    total = pl.col(seconds).cast(pl.Float64).round(0).cast(pl.Int64)
    mm = (total // 60).cast(pl.String).str.zfill(2)
    ss = (total % 60).cast(pl.String).str.zfill(2)
    return pl.concat_str([mm, ss], separator=':')


def _parse_game_dates(df: pl.DataFrame) -> pl.DataFrame:
    """gameDate ('dd/mm/YYYY' string) -> pl.Date."""
    return df.with_columns(pl.col('gameDate').str.to_date(GAME_DATE_FORMAT))


def _plot_values(s: pl.Series) -> list:
    """Series -> list for plotly. Nulls become NaN (what pandas used to give) so max()/min() downstream keep working."""
    if s.null_count():
        s = s.cast(pl.Float64).fill_null(float('nan'))
    return s.to_list()


# ───────────────────────────── player stats tables ─────────────────────────────

@st.cache_data(show_spinner=False)
def cached_player_stats(alltime, only_active, seasons, playoffs, team):
    return query_player_stats(alltime, only_active, seasons, playoffs, team)


@st.cache_data(show_spinner=False)
def cached_player_stats_by_season(player, seasons, playoffs, team):
    return query_player_stats_by_season(player, seasons, playoffs, team)


def _threshold_filters() -> list[pl.Expr]:
    """Slider-driven minimums. Applied after the cached query so moving a slider never re-queries."""
    ss = st.session_state
    return [
        pl.col('GP') >= ss.get('slider_gp', 5),
        pl.col('SECONDS') >= 60 * ss.get('slider_min', 0),     # avg seconds/game >= N whole minutes
        pl.col('TOT_FGM') >= ss.get('slider_fg', 0),
        pl.col('TOT_FG3M') >= ss.get('slider_fg3', 0),
        pl.col('TOT_FTM') >= ss.get('slider_ft', 0),
        pl.col('TOT_Pts') >= ss.get('slider_pts', 0),
    ]


def _add_derived_columns(df: pl.DataFrame) -> pl.DataFrame:
    fg2m = pl.col('FGM') - pl.col('FG3M')
    fg2a = pl.col('FGA') - pl.col('FG3A')
    df = _fill_zero(_nan_to_null(df, NULLABLE_COLS), COUNT_COLS)
    return df.with_columns(
        *[_defined_value(c) for c in DEFINED_IF],
        *[pl.when(pl.col(avg).is_not_null()).then(pl.col(tot)).otherwise(None).alias(tot)
          for tot, avg in TOTAL_NEEDS_DATA.items()],
        MINUTES=_mmss('SECONDS'),
        TOT_MINUTES=_mmss('TOT_SECONDS'),
        FG2M=fg2m,
        FG2A=fg2a,
        TOT_FG2M=pl.col('TOT_FGM') - pl.col('TOT_FG3M'),
        TOT_FG2A=pl.col('TOT_FGA') - pl.col('TOT_FG3A'),
        FG2_PCT=_pct(fg2m, fg2a),
        FG3_ratio=_pct(pl.col('FG3A'), pl.col('FGA')),
    )


def _to_per36(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns([
        pl.when(pl.col('SECONDS') > 0)
          .then(pl.col(c) * PER36_SECONDS / pl.col('SECONDS'))
          .otherwise(None)
          .alias(c)
        for c in PER36_COLS
    ])


def _column_sets(agg: str, alltime: bool, byseason: bool):
    """(columns, sort column) for the basic / shooting / TTFL tables."""
    team = [] if alltime else ['teamTricode']
    pre = 'TOT_' if agg == 'Totaux' else ''

    if agg == 'Totaux':
        basic = ['GP', 'TOT_MINUTES', 'TOT_TTFL', *[f'TOT_{c}' for c in COUNTING]]
        basic_sort = 'TOT_TTFL'
    else:
        basic = ['GP', 'MINUTES', 'TTFL',
                 *(['ttfl_per_min'] if agg == 'Moyennes' else []),
                 *COUNTING]
        basic_sort = 'TTFL'

    shooting = [col for s in ('FG', 'FG2', 'FG3', 'FT') for col in (f'{pre}{s}M', f'{pre}{s}A', f'{s}_PCT')]
    shooting += ['EFG', 'TS', 'ast_to_tov', 'FG3_ratio']

    sets = {
        'Statistiques basiques':         (['playerName', *team, *basic], basic_sort),
        'Statistiques de tir/avancées':  (['playerName', *shooting],     f'{pre}FGM'),
        'Statistiques TTFL':             (TTFL_COLS,                     'TTFL'),
    }
    if byseason:   # one player, one row per season: the first column becomes the season
        sets = {name: (['season', *cols[1:]], 'season') for name, (cols, _) in sets.items()}
    return sets


def get_all_player_stats(matched=()):
    ss = st.session_state
    matched = [matched] if isinstance(matched, str) else list(matched)
    alltime, seasons, playoffs, team = _filter_scope()
    agg = ss.get('player_stats_agg', AGG_MODES[0])
    if agg not in AGG_MODES:
        agg = AGG_MODES[0]

    byseason = alltime and len(matched) == 1
    if byseason:
        df = cached_player_stats_by_season(matched[0], seasons, playoffs, team)
    else:
        df = cached_player_stats(alltime, ss.get('only_active_players', False), seasons, playoffs, team)
    df = _ensure_polars(df)

    if matched:
        df = df.filter(pl.col('playerName').is_in(matched))
    if len(matched) != 1:
        df = df.filter(_threshold_filters())
    if df.is_empty():
        return {'Statistiques basiques': df.to_pandas()}

    df = _add_derived_columns(df)
    if agg == 'Moyennes par 36 min':
        df = _to_per36(df)
    if not byseason:   # the name column is replaced by 'season' in that case
        df = df.with_columns(french_flag_expr('playerName'))

    tables = {
        name: (df.sort(sort_col, descending=True, nulls_last=True, maintain_order=True)
                 .select(cols)
                 .with_columns(cs.float().round(3)))
        for name, (cols, sort_col) in _column_sets(agg, alltime, byseason).items()
    }
    tables['Statistiques du joueur par adversaire'] = player_v_team(matched)

    # single conversion to pandas, at the UI boundary
    return {name: t.to_pandas() for name, t in tables.items()}


# ───────────────────────────── player vs team ─────────────────────────────

@st.cache_data(show_spinner=False)
def cached_player_v_team(player, alltime, seasons, playoffs, team):
    return query_player_v_team(player, alltime, seasons, playoffs, team)


def player_v_team(player_list) -> pl.DataFrame:
    if len(player_list) != 1:
        return pl.DataFrame()

    df = _ensure_polars(cached_player_v_team(player_list[0], *_filter_scope()))
    if df.is_empty():
        return pl.DataFrame()

    return (_nan_to_null(df, ['PM', 'Oreb', 'Dreb'])
              .with_columns(MINUTES=_mmss('seconds'),
                            **{c: pl.when(pl.col(att) > 0).then((pl.col(c) * 100).round(1)).otherwise(None)
                               for c, att in VS_TEAM_PCT.items()})
              .select(VS_TEAM_COLS)
              .with_columns(cs.float().round(3)))


# ───────────────────────────── game log ─────────────────────────────

@st.cache_data(show_spinner=False)
def cached_historique_des_perfs(player, alltime, seasons, playoffs, team):
    return query_historique_des_perfs(player, alltime, seasons, playoffs, team)


def _pct_label(made: str, att: str) -> pl.Expr:
    """'' if no attempts, '100%' if perfect, else 'xx.x%' (tooltip text)."""
    m, a = pl.col(made), pl.col(att)
    return (pl.when(a == 0).then(pl.lit(''))
              .when(a == m).then(pl.lit('100%'))
              .otherwise(pl.concat_str([(100 * m / a).round(1), pl.lit('%')])))


def historique_des_perfs(player):
    scope = _filter_scope()
    alltime = scope[0]
    df = _ensure_polars(cached_historique_des_perfs(player, *scope))
    if df.is_empty():
        return ''

    df = (_parse_game_dates(df)
          .rename({k: v for k, v in HISTORY_RENAME.items() if k in df.columns})
          .sort('Date', descending=True, maintain_order=True))

    day = pl.col('Date').dt.day().cast(pl.String).str.zfill(2)
    month = pl.col('Date').dt.month().replace_strict(FRENCH_MONTHS, return_dtype=pl.String)
    year = pl.col('Date').dt.year().cast(pl.String).str.zfill(4)
    if alltime:
        date_label = pl.concat_str([day, pl.lit(' '), month, pl.lit('. '), year])
    else:
        date_label = pl.concat_str([pl.lit(' '), day, pl.lit(' '), month, pl.lit('.')])   # leading space kept from the original

    minutes = pl.col('Min').cast(pl.String)
    oreb = pl.col('Oreb').cast(pl.Float64).fill_nan(None)
    dreb = pl.col('Dreb').cast(pl.Float64).fill_nan(None)
    pm = pl.col('Pm').cast(pl.Float64).fill_nan(None).cast(pl.Int64)

    df = df.with_columns(
        Date=date_label,
        Min=pl.when(minutes.str.contains(':')).then(minutes).otherwise(pl.concat_str([minutes, pl.lit(':00')])),
        FG=pl.concat_str([pl.col('FGM'), pl.lit('/'), pl.col('FGA')]),
        FG3=pl.concat_str([pl.col('FG3M'), pl.lit('/'), pl.col('FG3A')]),
        FT=pl.concat_str([pl.col('FTM'), pl.lit('/'), pl.col('FTA')]),
        rebSplit=(pl.when(oreb.is_null() | dreb.is_null()).then(pl.lit(''))
                    .otherwise(pl.concat_str([pl.lit('Off : '), oreb.cast(pl.Int64),
                                              pl.lit(' - Def : '), dreb.cast(pl.Int64)]))),
        FGpct=_pct_label('FGM', 'FGA'),
        FG3pct=_pct_label('FG3M', 'FG3A'),
        FTpct=_pct_label('FTM', 'FTA'),
        Pm=(pl.when(pm.is_null()).then(pl.lit(''))                 # no plus/minus recorded: blank, not '+0'
              .when(pm < 0).then(pm.cast(pl.String))
              .otherwise(pl.concat_str([pl.lit('+'), pm]))),
        win=pl.concat_str([pl.when(pl.col('win') == 1).then(pl.lit('W')).otherwise(pl.lit('L')),
                           pl.lit(' ('), pl.col('teamPoints'), pl.lit('-'), pl.col('opponentPoints'), pl.lit(')')]),
        isHome=pl.when(pl.col('isHome') == 1).then(pl.lit('Dom.')).otherwise(pl.lit('Ext.')),
    )

    return df_to_html(df.to_pandas(), show_cols=HISTORY_SHOW_COLS,
                      tooltips={'FG': 'FGpct', 'FG3': 'FG3pct', 'FT': 'FTpct', 'Reb': 'rebSplit'},
                      show_index=False,
                      col_header_tooltips=[],
                      plot_tooltips=[],
                      color_tooltip_pct=False,
                      highlight_index=None,
                      col_header_labels={'FG3': '3FG', 'Pm': '±', 'win': 'W/L', 'isHome': 'Dom/Ext',
                                         'opponent': 'Adv.', 'teamTricode': 'Équipe'})


# ───────────────────────────── plot ─────────────────────────────

def _lowess_trend(x: np.ndarray, series: pl.Series, frac: float) -> np.ndarray:
    """LOWESS over the games where the stat exists; NaN (a gap in the line) for the others."""
    import statsmodels.api as sm     # heavy import, only when needed
    y = series.cast(pl.Float64).fill_nan(None).to_numpy()      # nulls -> nan
    ok = ~np.isnan(y)
    trend = np.full(len(y), np.nan)
    if ok.sum() >= 3:
        trend[ok] = sm.nonparametric.lowess(endog=y[ok], exog=x[ok], frac=frac, return_sorted=False).round(2)
    return trend


def _team_stints(df: pl.DataFrame) -> dict:
    """Team labels / label positions / trade dates for the plot. `df` must be sorted by gameDate."""
    stints = (df.group_by(pl.col('teamTricode').rle_id().alias('stint'), maintain_order=True)
                .agg(team=pl.col('teamTricode').first(), start=pl.col('gameDate').min()))
    starts, teams = stints['start'].to_list(), stints['team'].to_list()
    last = df['gameDate'][-1]
    if starts[0] == last:      # single game: interactive_plot divides by (last - first), so give it nothing
        return {}
    ends = starts[1:] + [last]
    mids = [s + (e - s) / 2 for s, e in zip(starts, ends)]      # where each team label sits
    return {'mid_dates': [starts[0], *mids, last], 'teams': teams, 'trade_dates': starts[1:]}


def get_plot(player, stats, show_lines, show_scatter, show_avg,
             show_lowess, lambda_lowess, show_teams, hide_legend,
             show_ttfl_details):
    df = _ensure_polars(cached_historique_des_perfs(player, *_filter_scope()))
    if df.is_empty():
        return None
    if isinstance(stats, str):
        stats = [stats]

    FGM, FGA = pl.col('fieldGoalsMade'), pl.col('fieldGoalsAttempted')
    FG3M, FG3A = pl.col('threePointersMade'), pl.col('threePointersAttempted')
    FTM, FTA = pl.col('freeThrowsMade'), pl.col('freeThrowsAttempted')

    df = (_parse_game_dates(df)
          .with_columns(pl.col('gameDate').cast(pl.Datetime('us')))
          .sort('gameDate', maintain_order=True)
          .with_columns(FGpct=_pct(FGM, FGA, 0),
                        FG3pct=_pct(FG3M, FG3A, 0),
                        FTpct=_pct(FTM, FTA, 0),
                        minutes=(pl.col('seconds') / 60).round(1),
                        strwin=pl.col('win').replace_strict({0: 'Défaite', 1: 'Victoire'})))

    hover_info = {key: df[col].to_list() for key, col in HOVER_COLS.items()}
    hover_info['date'] = df['gameDate'].dt.strftime('%d %b. %y').to_list()
    hover_info['min'] = (df['seconds'] / 60).cast(pl.Int64).to_list()

    stats_to_plot, avgs_to_plot, trends = {}, {}, {}
    x = df['gameDate'].dt.epoch('d').to_numpy() if show_lowess else None

    for stat in stats:
        series = df[PLOT_STATS[stat]]
        stats_to_plot[stat] = _plot_values(series)
        if show_avg:
            mean = series.mean()
            avgs_to_plot[stat] = [round(mean, 1) if mean is not None else float('nan')] * df.height
        if show_lowess:
            trends[stat] = _lowess_trend(x, series, lambda_lowess)

    player_teams = _team_stints(df) if show_teams else {}
    ttfl_details = df.select(**TTFL_DETAILS).to_dict(as_series=False) if show_ttfl_details else {}

    return interactive_plot(player, df['gameDate'].to_list(), stats_to_plot, show_lines, show_scatter,
                            avgs_to_plot, trends, player_teams, hover_info, hide_legend,
                            show_ttfl_details, ttfl_details)


# ───────────────────────────── search / compare callbacks ─────────────────────────────

def clear_search():
    st.session_state.player_stats_matched = ''
    st.session_state.search_player_indiv_stats = ''
    st.session_state.search_team_indiv_stats = ''
    st.session_state.matched_team = ''
    st.session_state.compare_players = []


def add_compare():
    matched = st.session_state.player_stats_matched
    if isinstance(matched, str):
        matched = [matched]
    for player in matched:
        if player and player not in st.session_state.compare_players:
            st.session_state.compare_players.append(player)


def on_search_player_stats():
    player_name = st.session_state.search_player_indiv_stats
    if player_name == '':
        clear_search()
    else:
        matched_player = match_player(player_name, alltime=st.session_state.player_alltime_stats)
        st.session_state.search_player_indiv_stats = matched_player
        st.session_state.player_stats_matched = matched_player


def on_search_team_stats():
    team_name = st.session_state.search_team_indiv_stats
    if team_name == '':
        clear_search()
    else:
        matched_team = match_team(team_name)
        st.session_state.search_team_indiv_stats = matched_team
        st.session_state.matched_team = matched_team


# ───────────────────────────── filters ─────────────────────────────

@st.cache_data(show_spinner=False)
def cached_maximums(alltime, seasons: tuple):
    """Largest per-player GP / Pts / FG / FG3 / FT totals and avg minutes, used to size the sliders."""
    bs = scan_boxscores(list(seasons) or (None if alltime else [latest_season()]))
    row = (bs.group_by('playerName')
             .agg(GP=pl.len(),
                  Pts=sql_sum('points'),
                  FG=sql_sum('fieldGoalsMade'),
                  FG3=sql_sum('threePointersMade'),
                  FT=sql_sum('freeThrowsMade'),
                  MIN=pl.col('seconds').mean() / 60)
             .select(pl.col('GP', 'Pts', 'FG', 'FG3', 'FT', 'MIN').max())
             .collect()
             .row(0, named=True))

    maximums = {k: (DEFAULT_MAXIMUMS[k] if row[k] is None else row[k]) for k in DEFAULT_MAXIMUMS}
    maximums['MIN'] = int(maximums['MIN'])
    return maximums


def get_maximums():
    alltime = st.session_state.get('player_alltime_stats', False)
    seasons = tuple(st.session_state.get('selected_seasons', []))
    return cached_maximums(alltime, seasons)


def _default_threshold(maximum, step, divisor):
    return round(maximum / divisor / step) * step


def set_filters_default():
    ss = st.session_state
    ss.player_alltime_stats_default = False
    ss.only_active_players_default = False
    ss.selected_seasons = []

    maximums = get_maximums()
    for slider, max_key, stat, step, divisor in SLIDERS:
        ss[max_key] = maximums[stat]
        ss[f'{slider}_default'] = _default_threshold(maximums[stat], step, divisor)
    ss.max_min = maximums['MIN']
    ss.slider_min_default = 10
    ss.player_stats_agg_default = 'Moyennes'
    ss.color_cells_default = False


def reset_filters():
    ss = st.session_state
    set_filters_default()
    for slider, *_ in SLIDERS:
        ss[slider] = ss[f'{slider}_default']
    ss.slider_min = ss.slider_min_default
    ss.player_stats_agg = ss.player_stats_agg_default
    ss.color_cells = ss.color_cells_default
    ss.player_alltime_stats = ss.player_alltime_stats_default
    ss.only_active_players = ss.only_active_players_default


def filters_to_zero():
    ss = st.session_state
    ss.slider_gp = 10 if ss.player_alltime_stats else 0
    ss.slider_pts = 0
    ss.slider_min = 0
    ss.slider_fg = 0
    ss.slider_fg3 = 0
    ss.slider_ft = 0
    if not ss.player_alltime_stats:
        ss.only_active_players = False


def alltime_checked():
    set_filters_default()
    filters_to_zero()
    st.session_state.color_cells = False


def filter_expander_vars():
    ss = st.session_state
    sep = f' {uspace(1)} ● {uspace(1)} '
    parts = ['Stats historiques' if ss.player_alltime_stats else 'Saison actuelle',
             ss.player_stats_agg,
             *[f'{name} {uspace(1)} ≥ {uspace(1)} {ss[key]}' for name, key in FILTER_LABELS]]

    label = 'Filtres' + ''.join(sep + p for p in parts)

    agg_changed = ss.player_stats_agg != ss.player_stats_agg_default
    changed = agg_changed or any(ss[key] != ss[f'{key}_default'] for _, key in FILTER_LABELS)
    all_zero = not agg_changed and all(ss[key] == 0 for _, key in FILTER_LABELS)
    return label, changed and not all_zero


# ───────────────────────────── page update ─────────────────────────────

def update_player_stats(players_to_show):
    ss = st.session_state
    ss.player_stats = get_all_player_stats(matched=players_to_show)
    ss.massive_tables = len(ss.player_stats['Statistiques basiques']) > 550

    alltime = ss.get('player_alltime_stats', False)
    team = ss.get('matched_team', '')

    filters = []
    if len(players_to_show) > 0:
        filters.append(pl.col('playerName').is_in(list(players_to_show)))
    if team != '':
        filters.append(franchise_expr(team))

    bs = scan_boxscores(None if alltime else [latest_season()])
    ss.available_seasons = distinct_seasons(bs.filter(*filters) if filters else bs)