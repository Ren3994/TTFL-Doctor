"""
NBA endpoint diagnostics for Streamlit (local or Community Cloud).

What it does
- Runs your normal nba_api calls and logs, for EVERY HTTP request actually sent:
  the real URL (with query string), status / error type, seconds, raw size
  (decompressed) and wire size (bytes actually transferred = what a proxy bills).
- Lets you route only the stats.nba.com calls through a proxy.
- Tests the static cdn.nba.com schedule file next to ScheduleLeagueV2.
- Estimates monthly proxy traffic for your sync pattern.

Run:  streamlit run nba_diagnostics.py
"""
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import (
    BoxScoreTraditionalV3,
    CommonAllPlayers,
    ScheduleLeagueV2,
    commonplayerinfo,
    leaguedashteamstats,
    scoreboardv2,
)

GAME_ID = "0022501227"
PLAYER_ID = "1630164"
SEASON = "2026-27"

ESPN_INJURIES = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
CDN_SCHEDULE = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

# Browser-like headers; people report the cdn schedule file needing these.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Calls that make up one "sync" in your app (used for the traffic estimate).
SYNC_BOXSCORE = "BoxScoreTraditionalV3"
SYNC_OTHERS = ["CommonAllPlayers", "ScheduleLeagueV2", "LeagueDashTeamStats"]


# --------------------------------------------------------------------------
# Request logger: wraps requests.Session.send, which every nba_api call and
# every plain requests.get() goes through. Installed once per process.
# --------------------------------------------------------------------------
@st.cache_resource
def install_logger():
    log = []
    orig_send = requests.Session.send

    # urllib3 does not update its bytes-read counter for chunked responses
    # (Transfer-Encoding: chunked), so resp.raw.tell() returns 0 for them and
    # the wire size would silently fall back to the raw size. Count the chunks.
    from urllib3.response import HTTPResponse
    if hasattr(HTTPResponse, "_handle_chunk"):
        orig_handle_chunk = HTTPResponse._handle_chunk

        def counting_handle_chunk(self, amt):
            data = orig_handle_chunk(self, amt)
            self._fp_bytes_read = getattr(self, "_fp_bytes_read", 0) + len(data)
            return data

        HTTPResponse._handle_chunk = counting_handle_chunk

    def logged_send(self, request, **kwargs):
        t0 = time.time()
        try:
            resp = orig_send(self, request, **kwargs)
        except Exception as e:  # timeouts, connection errors...
            log.append({
                "url": request.url,
                "status": type(e).__name__,
                "seconds": round(time.time() - t0, 1),
                "raw_kb": 0.0,
                "wire_kb": 0.0,
                "encoding": "",
                "error": str(e)[:300],
            })
            raise

        raw = len(resp.content)
        try:
            wire = resp.raw.tell()  # compressed bytes actually read from the socket
        except Exception:
            wire = 0
        note = ""
        if not wire:
            cl = resp.headers.get("Content-Length")
            wire = int(cl) if cl else raw
            if not cl and resp.headers.get("Content-Encoding"):
                note = "wire not measurable, shows raw"

        log.append({
            "url": request.url,
            "status": resp.status_code,
            "seconds": round(time.time() - t0, 1),
            "raw_kb": round(raw / 1024, 1),
            "wire_kb": round(wire / 1024, 1),
            "encoding": resp.headers.get("Content-Encoding", ""),
            "error": note,
        })
        return resp

    requests.Session.send = logged_send
    return log


def build_tests(proxy: str, timeout: int) -> dict:
    """name -> zero-arg callable. Only stats.nba.com calls get the proxy."""
    s = {"timeout": timeout}          # stats.nba.com calls
    if proxy:
        s["proxy"] = proxy
    d = {"timeout": timeout}          # cdn.nba.com / ESPN: always direct

    today_paris = datetime.now(ZoneInfo("Europe/Paris")).date()

    tests = {
        "ESPN injuries": lambda: requests.get(ESPN_INJURIES, timeout=timeout),
        SYNC_BOXSCORE: lambda: BoxScoreTraditionalV3(
            game_id=GAME_ID, start_period=1, end_period=10,
            start_range=0, end_range=0, range_type=0, **s,
        ),
        "CommonPlayerInfo": lambda: commonplayerinfo.CommonPlayerInfo(PLAYER_ID, **s),
        "CommonAllPlayers": lambda: CommonAllPlayers(
            is_only_current_season=1, league_id="00", season=SEASON, **s,
        ),
        "ScheduleLeagueV2": lambda: ScheduleLeagueV2(
            league_id="00", season=SEASON, **s,
        ),
        "LeagueDashTeamStats": lambda: leaguedashteamstats.LeagueDashTeamStats(
            season=SEASON, measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame", league_id_nullable="00", **s,
        ),
        "ScoreBoard (live, cdn)": lambda: scoreboard.ScoreBoard(**d),
        "ScoreboardV2": lambda: scoreboardv2.ScoreboardV2(game_date=today_paris, **s),
        "cdn static schedule (direct)": lambda: requests.get(
            CDN_SCHEDULE, headers=BROWSER_HEADERS, timeout=timeout
        ),
    }
    return tests


def mask(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


def proxy_selftest(proxy: str, timeout: int):
    """Step-by-step check that tells you WHERE the proxy path breaks."""
    if not proxy:
        st.warning("Enter a proxy URL first.")
        return
    px = {"http": proxy, "https": proxy}
    checks = [
        ("1. Proxy itself (ip.decodo.com)", "https://ip.decodo.com/json", {}),
        ("2. NBA cdn through proxy", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
         BROWSER_HEADERS),
    ]
    for label, url, headers in checks:
        t0 = time.time()
        try:
            r = requests.get(url, proxies=px, headers=headers, timeout=timeout)
            st.write(f"**{label}** -> HTTP {r.status_code} in {time.time() - t0:.1f}s")
            st.code(r.text[:300] or "(empty body)")
        except Exception as e:
            st.write(f"**{label}** -> FAILED in {time.time() - t0:.1f}s")
            st.code(mask(f"{type(e).__name__}: {e}", proxy)[:600])

    t0 = time.time()
    try:
        CommonAllPlayers(is_only_current_season=1, league_id="00", season=SEASON,
                         proxy=proxy, timeout=timeout)
        st.write(f"**3. stats.nba.com through proxy (nba_api)** -> OK in {time.time() - t0:.1f}s")
    except Exception as e:
        st.write(f"**3. stats.nba.com through proxy (nba_api)** -> FAILED in {time.time() - t0:.1f}s")
        st.code(mask(f"{type(e).__name__}: {e}", proxy)[:600])

    st.markdown(
        "**Reading the result**\n"
        "- **1 fails (407 / connect error):** credentials, sub-user, endpoint or port problem.\n"
        "- **1 works, 3 fails instantly with a proxy/403/5xx error:** likely a restricted target "
        "(the provider refusing the site) - contact support.\n"
        "- **1 and 2 work, 3 times out:** the proxy is fine but NBA is dropping that exit IP; retry a few times.\n"
        "- **All work:** the problem is in how the proxy URL reaches the app (see the main table)."
    )


def run(selected, tests, log, pause):
    rows = []
    bar = st.progress(0.0)
    for i, name in enumerate(selected):
        n0 = len(log)
        t0 = time.time()
        error = ""
        try:
            tests[name]()
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        new = log[n0:]
        if not new:  # nothing went over HTTP (e.g. failed before sending)
            rows.append({"test": name, "url": "(no request sent)", "status": error or "?",
                         "seconds": round(time.time() - t0, 1), "raw_kb": 0.0,
                         "wire_kb": 0.0, "encoding": "", "error": error})
        for r in new:
            rows.append({"test": name, **r})
        bar.progress((i + 1) / len(selected))
        if i < len(selected) - 1:
            time.sleep(pause)
    return rows


def main():
    st.set_page_config(page_title="NBA diagnostics", layout="wide")
    st.title("NBA endpoint diagnostics")
    log = install_logger()

    try:
        default_proxy = st.secrets.get("PROXY_URL", "")
    except Exception:  # no secrets.toml locally
        default_proxy = ""

    c1, c2, c3 = st.columns(3)
    proxy = c1.text_input(
        "Proxy URL for stats.nba.com calls (blank = direct)",
        value=default_proxy, type="password",
        help="http://user:pass@host:port",
    )
    timeout = c2.number_input("Timeout (s)", 5, 120, 30)
    pause = c3.number_input("Pause between tests (s)", 0, 30, 2)

    if st.button("Proxy self-test (run this first)"):
        proxy_selftest(proxy, int(timeout))
        st.divider()

    names = list(build_tests("", 1).keys())
    selected = st.multiselect("Tests", names, default=names)

    if st.button("Run tests", type="primary") and selected:
        rows = run(selected, build_tests(proxy, int(timeout)), log, pause)
        st.session_state["rows"] = rows

    rows = st.session_state.get("rows")
    if not rows:
        return

    st.subheader("Every HTTP request that was sent")
    st.dataframe(rows, use_container_width=True)
    with st.expander("Copy-paste URLs"):
        st.code("\n".join(f"{r['test']}: {r['url']}" for r in rows))

    ok = [r for r in rows if r["status"] == 200]
    st.caption(f"{len(ok)}/{len(rows)} requests returned HTTP 200. "
               f"Total wire traffic this run: {sum(r['wire_kb'] for r in rows):.0f} KB.")

    # ---- monthly traffic estimate -------------------------------------
    st.subheader("Monthly traffic estimate (stats.nba.com calls only)")
    box = next((r for r in ok if r["test"] == SYNC_BOXSCORE), None)
    others = [r for r in ok if r["test"] in SYNC_OTHERS]
    if not box or len(others) < len(SYNC_OTHERS):
        st.info("Run BoxScoreTraditionalV3, CommonAllPlayers, ScheduleLeagueV2 and "
                "LeagueDashTeamStats successfully to get an estimate.")
        return

    e1, e2 = st.columns(2)
    games = e1.number_input("Games per sync", 1, 30, 8)
    syncs = e2.number_input("Syncs per month", 1, 200, 30)
    for label, key in (("Wire (what the proxy bills)", "wire_kb"), ("Raw (worst case)", "raw_kb")):
        per_sync_mb = (box[key] * games + sum(r[key] for r in others)) / 1024
        st.write(f"**{label}:** {per_sync_mb:.2f} MB per sync, "
                 f"**{per_sync_mb * syncs:.0f} MB per month**")


if __name__ == "__main__":
    main()
