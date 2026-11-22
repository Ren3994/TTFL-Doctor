"""
net_utils.py - one place for every network retry / pacing / error-handling rule.

Python 3.9+. Standard library only (requests / curl_cffi / nba_api are used
duck-typed, never imported at module level except to discover exception types).

Building blocks
---------------
RetryPolicy   Frozen dataclass holding *every* retry knob. Presets: DEFAULT_POLICY,
              WEB, NBA_CDN, NBA_API. Tweak with `NBA_API.replace(max_attempts=3)`.
              There is exactly one place where a retry option is defined, so the
              wrappers below can never drift apart again.
RateLimiter   Thread-safe "minimum interval between request starts", applied before
              EVERY attempt (retries included). Share one instance per host.
retry_call()  The engine. Runs fn() under a policy and returns its result, or
              `default` / raises RetryFailed on failure.
http_request / http_get / http_json
              One logical HTTP request, HTTP-aware retry rules (see below).
nba_frames()  nba_api endpoint construction + retries -> get_data_frames()[frame].

What gets retried (the important part)
--------------------------------------
For an exception raised by fn(), in this order:
  1. InvalidResultError (validate() said no, or fn raised it)  -> retry, always
  2. isinstance(exc, policy.give_up_on)                        -> stop, failure
  3. NOT isinstance(exc, policy.retry_on)                      -> PROPAGATES unchanged
     (bugs such as TypeError/KeyError/AttributeError, and KeyboardInterrupt,
      are never retried or swallowed)
  4. policy.should_retry(exc) is False                         -> stop, failure
  5. otherwise                                                 -> retry with backoff

`retry_on` defaults to NETWORK_ERRORS (OSError covers requests' exceptions, plus
JSON decode errors, http.client errors and curl_cffi's exceptions when installed).
The HTTP presets add `status_retry()`: only 408/425/429/5xx are retried; 400/401/
403/404 are permanent and fail fast. `Retry-After` is honoured (capped).

"Failure" means: return `default` (None unless you say otherwise), or raise
RetryFailed(.attempts, .last_exception) when raise_on_failure=True. If you need to
tell "failed" from "legitimately returned None", use raise_on_failure=True or a
sentinel `default`.

Exceptions raised by *your* callbacks / validate() propagate (a broken validator
should be loud). Exceptions from on_retry / on_final_failure are logged, not raised.

Examples
--------
    CDN_LIMITER = RateLimiter((0.4, 0.9))        # random 0.4-0.9s between requests
    box = http_json(url, policy=NBA_CDN, limiter=CDN_LIMITER,
                    validate=lambda d: "game" in d)

    df = nba_frames(CommonAllPlayers, is_only_current_season=1, season=SEASON,
                    proxy=proxy, policy=NBA_API, validate=not_empty)

    # rotate proxy on every attempt
    df = nba_frames(LeagueGameLog, season=SEASON,
                    per_attempt=lambda n: {"proxy": proxies[n % len(proxies)]})
"""
from __future__ import annotations

import dataclasses
import email.utils
import http.client
import json
import logging
import random
import threading
import time
from dataclasses import dataclass
from datetime import timezone
from typing import Any, Callable, Mapping, TypeVar
from urllib.parse import urlsplit

__all__ = [
    "NETWORK_ERRORS", "RETRYABLE_STATUSES",
    "RetryPolicy", "DEFAULT_POLICY", "WEB", "NBA_CDN", "NBA_API",
    "RateLimiter", "InvalidResultError", "RetryFailed",
    "retry_call", "http_request", "http_get", "http_json", "nba_frames",
    "status_retry", "retry_after_hint", "not_empty", "close_shared_session",
]

T = TypeVar("T")
D = TypeVar("D")
ExcTypes = tuple[type[BaseException], ...]
LogTarget = "logging.Logger | Callable[[str], None] | None"

_LOGGER = logging.getLogger("net_utils")


# --------------------------------------------------------------------------- #
# Exceptions                                                                  #
# --------------------------------------------------------------------------- #
class InvalidResultError(Exception):
    """The call "succeeded" but its result is unusable (empty, truncated, wrong shape).

    Always retryable. validate() failures become this; fn may also raise it."""


class RetryFailed(Exception):
    """Raised instead of returning `default` when raise_on_failure=True."""

    def __init__(self, label: str, attempts: int, last_exception: BaseException):
        super().__init__(f"{label} : échec après {attempts} tentative(s) "
                         f"({_describe(last_exception)})")
        self.label = label
        self.attempts = attempts
        self.last_exception = last_exception


def _describe(exc: BaseException, limit: int = 200) -> str:
    """'TimeoutError' / 'HTTPError: 503 Server Error...' (never an empty string)."""
    text = str(exc).strip()
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    name = type(exc).__name__
    return f"{name}: {text}" if text else name


def _emit(log: Any, level: int, msg: str) -> None:
    if log is None:
        return
    if isinstance(log, logging.Logger):
        log.log(level, msg)
    else:
        log(msg)


def _safe_call(cb: Callable[..., Any] | None, *args: Any) -> None:
    """Run a user callback; a failing callback must never mask the real flow."""
    if cb is None:
        return
    try:
        cb(*args)
    except Exception as e:                                          # noqa: BLE001
        _LOGGER.warning("(callback %s en échec : %s)",
                        getattr(cb, "__name__", "?"), _describe(e))


# --------------------------------------------------------------------------- #
# Which exceptions count as "network trouble"                                 #
# --------------------------------------------------------------------------- #
def _build_network_errors() -> ExcTypes:
    errs: list[type[BaseException]] = [
        OSError,                    # ConnectionError, TimeoutError, requests.RequestException...
        EOFError,
        http.client.HTTPException,  # IncompleteRead, BadStatusLine...
        json.JSONDecodeError,       # truncated / HTML-instead-of-JSON bodies
    ]
    try:                            # curl_cffi's exceptions are NOT OSErrors
        from curl_cffi.requests import exceptions as cc                # type: ignore
        for name in ("RequestException", "RequestsError"):
            e = getattr(cc, name, None)
            if isinstance(e, type) and issubclass(e, BaseException):
                errs.append(e)
    except Exception:                                               # noqa: BLE001
        pass
    return tuple(dict.fromkeys(errs))


NETWORK_ERRORS: ExcTypes = _build_network_errors()
RETRYABLE_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


def _response_of(exc: BaseException) -> Any:
    return getattr(exc, "response", None)       # NB: never test it for truthiness:
                                                # requests.Response is falsy for 4xx/5xx


def status_retry(retryable: frozenset[int] | set[int] = RETRYABLE_STATUSES
                 ) -> Callable[[BaseException], bool]:
    """should_retry predicate: an exception carrying an HTTP response is retried only
    if its status is in `retryable`; anything without a response (connection reset,
    timeout, bad JSON...) is retried."""
    retryable = frozenset(retryable)

    def should_retry(exc: BaseException) -> bool:
        resp = _response_of(exc)
        status = getattr(resp, "status_code", None) if resp is not None else None
        return True if status is None else status in retryable

    return should_retry


def retry_after_hint(exc: BaseException) -> float | None:
    """wait_hint: seconds requested by a `Retry-After` header (delta or HTTP date)."""
    resp = _response_of(exc)
    headers = getattr(resp, "headers", None) if resp is not None else None
    if headers is None or not hasattr(headers, "get"):
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    raw = str(raw).strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, when.timestamp() - time.time())


# --------------------------------------------------------------------------- #
# Policy                                                                      #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RetryPolicy:
    """Every retry knob, in one immutable object.

    max_attempts   : total tries (>= 1).
    wait_base      : wait after the 1st failure, seconds.
    wait_factor    : geometric growth (2 = base, 2*base, 4*base...).
    wait_max       : HARD ceiling on any single backoff wait (jitter included).
    jitter         : relative jitter, 0.25 -> +/-25% (then re-clamped to wait_max).
    max_total_time : give up when the next wait would push the whole call past this
                     many seconds (None = no deadline). Does not interrupt a request
                     in flight: keep per-request timeouts sane too.
    retry_on       : exception types eligible for retry; others propagate.
    give_up_on     : exception types that stop immediately (checked first).
    should_retry   : extra predicate on retry_on exceptions; False -> stop.
    wait_hint      : exc -> seconds the server asked for (e.g. Retry-After); the wait
                     becomes max(backoff, min(hint, wait_hint_max)).
    """
    max_attempts: int = 5
    wait_base: float = 2.0
    wait_factor: float = 2.0
    wait_max: float = 60.0
    jitter: float = 0.25
    max_total_time: float | None = None
    retry_on: ExcTypes = NETWORK_ERRORS
    give_up_on: ExcTypes = ()
    should_retry: Callable[[BaseException], bool] | None = None
    wait_hint: Callable[[BaseException], float | None] | None = None
    wait_hint_max: float = 120.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.wait_base < 0 or self.wait_max < 0 or self.wait_hint_max < 0:
            raise ValueError("waits must be >= 0")
        if self.wait_factor < 1:
            raise ValueError("wait_factor must be >= 1")
        if not 0 <= self.jitter < 1:
            raise ValueError("jitter must be in [0, 1)")

    def replace(self, **changes: Any) -> "RetryPolicy":
        return dataclasses.replace(self, **changes)

    def delay(self, attempt: int, rng: Callable[[], float] = random.random) -> float:
        """Backoff after `attempt` failed attempts (1-based), jitter included,
        never above wait_max."""
        w = min(self.wait_base * self.wait_factor ** (attempt - 1), self.wait_max)
        if self.jitter:
            w *= 1.0 + self.jitter * (2.0 * rng() - 1.0)
        return min(max(w, 0.0), self.wait_max)


# Generic (non-HTTP) work: network-ish errors only, no status logic.
DEFAULT_POLICY = RetryPolicy()

# Misc. sites. Quick recovery from blips, fails fast on 4xx.
WEB = RetryPolicy(max_attempts=4, wait_base=2, wait_max=30,
                  should_retry=status_retry(), wait_hint=retry_after_hint)

# cdn.nba.com static JSON. 403/404 = "not published (yet)" -> permanent, no retry.
NBA_CDN = RetryPolicy(max_attempts=4, wait_base=1, wait_max=15,
                      should_retry=status_retry(), wait_hint=retry_after_hint)

# stats.nba.com via nba_api. Throttles by IP and often hangs, so back off hard.
# Waits ~10, 20, 40, 80s (+/-25%). If nba_api raises other exception types on garbled
# responses in your setup, ADD them to retry_on rather than widening to Exception.
NBA_API = RetryPolicy(max_attempts=5, wait_base=10, wait_max=90, max_total_time=300,
                      should_retry=status_retry(), wait_hint=retry_after_hint)


# --------------------------------------------------------------------------- #
# Rate limiter                                                                #
# --------------------------------------------------------------------------- #
class RateLimiter:
    """Minimum interval between request *starts*, safe across threads.

    min_interval: seconds, or (low, high) for a random interval per slot.
    Slots are reserved under a lock and slept for outside it, so N threads get
    evenly spaced slots instead of waking together.
    """

    def __init__(self, min_interval: float | tuple[float, float],
                 *, _sleep: Callable[[float], None] = time.sleep,
                 _clock: Callable[[], float] = time.monotonic,
                 _rng: Callable[[float, float], float] = random.uniform):
        lo, hi = ((min_interval, min_interval) if isinstance(min_interval, (int, float))
                  else min_interval)
        if lo < 0 or hi < lo:
            raise ValueError("min_interval must satisfy 0 <= low <= high")
        self._lo, self._hi = float(lo), float(hi)
        self._sleep, self._clock, self._rng = _sleep, _clock, _rng
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> float:
        """Block until this caller's slot; returns the seconds slept."""
        with self._lock:
            now = self._clock()
            start = max(now, self._next)
            self._next = start + (self._lo if self._lo == self._hi
                                  else self._rng(self._lo, self._hi))
        delay = start - now
        if delay > 0:
            self._sleep(delay)
        return max(delay, 0.0)


# --------------------------------------------------------------------------- #
# Engine                                                                      #
# --------------------------------------------------------------------------- #
_RETRY, _ABORT, _RAISE = "retry", "abort", "raise"


def _verdict(exc: Exception, policy: RetryPolicy) -> str:
    if isinstance(exc, InvalidResultError):
        return _RETRY
    if isinstance(exc, policy.give_up_on):
        return _ABORT
    if not isinstance(exc, policy.retry_on):
        return _RAISE
    if policy.should_retry is not None and not policy.should_retry(exc):
        return _ABORT
    return _RETRY


def _fail(failure: BaseException, label: str, attempts_made: int, why: str, *,
          default: Any, raise_on_failure: bool,
          on_final_failure: Callable[[BaseException], None] | None, log: Any) -> Any:
    _emit(log, logging.ERROR if attempts_made > 1 else logging.WARNING,
          f"{label} : {_describe(failure)}. {why}")
    _safe_call(on_final_failure, failure)
    if raise_on_failure:
        raise RetryFailed(label, attempts_made, failure) from failure
    return default


def retry_call(
    fn: Callable[..., T],
    *,
    label: str = "",
    policy: RetryPolicy | None = None,
    validate: Callable[[T], bool] | None = None,
    default: D = None,                                    # type: ignore[assignment]
    raise_on_failure: bool = False,
    pass_attempt: bool = False,
    limiter: RateLimiter | None = None,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    on_final_failure: Callable[[BaseException], None] | None = None,
    log: Any = _LOGGER,
    _sleep: Callable[[float], None] = time.sleep,
    _clock: Callable[[], float] = time.monotonic,
    _rng: Callable[[], float] = random.random,
) -> T | D:
    """Run fn() under `policy`. Returns its (validated) result, or `default` /
    RetryFailed once retrying is over. See the module docstring for the rules.

    validate         : result -> bool. False means InvalidResultError (retried);
                       it may also raise InvalidResultError("why") to explain itself.
    pass_attempt     : call fn(attempt) (1-based) so it can rotate proxies, etc.
    limiter          : RateLimiter waited on before every attempt.
    on_retry         : hook(attempt_that_failed, exception, wait_seconds), called
                       just before sleeping.
    on_final_failure : hook(last_exception) when giving up (not on success/propagation).
    log              : a logging.Logger (default), a callable(str), or None.
    _sleep/_clock/_rng : injection points for tests.
    """
    policy = policy if policy is not None else DEFAULT_POLICY
    label = label or getattr(fn, "__name__", "") or "appel réseau"
    attempts = policy.max_attempts
    started = _clock()
    fail_kw = dict(default=default, raise_on_failure=raise_on_failure,
                   on_final_failure=on_final_failure, log=log)

    for attempt in range(1, attempts + 1):
        if limiter is not None:
            limiter.wait()
        try:
            result = fn(attempt) if pass_attempt else fn()
        except Exception as exc:                  # KeyboardInterrupt etc. pass through
            verdict = _verdict(exc, policy)
            if verdict == _RAISE:
                raise                              # a bug or something not ours
            failure: BaseException = exc
        else:
            try:                                       # other errors in validate() propagate
                ok = validate is None or validate(result)
                failure = InvalidResultError("réponse invalide (vide ou inattendue)")
            except InvalidResultError as bad:          # validate() may explain itself
                ok, failure = False, bad
            if ok:
                return result
            verdict = _RETRY

        if verdict == _ABORT:
            return _fail(failure, label, attempt, "Abandon (erreur non réessayable)",
                         **fail_kw)
        if attempt >= attempts:
            plural = "s" if attempts > 1 else ""
            return _fail(failure, label, attempt,
                         f"Abandon après {attempts} tentative{plural}", **fail_kw)

        wait = policy.delay(attempt, _rng)
        if policy.wait_hint is not None:
            hint = policy.wait_hint(failure)
            if hint:
                wait = max(wait, min(hint, policy.wait_hint_max))
        if policy.max_total_time is not None and \
                (_clock() - started) + wait > policy.max_total_time:
            return _fail(failure, label, attempt,
                         f"Abandon (délai total de {policy.max_total_time:.0f}s dépassé "
                         f"après {attempt} tentative{'s' if attempt > 1 else ''})",
                         **fail_kw)

        _emit(log, logging.WARNING,
              f"{label} : {_describe(failure)}. "
              f"Nouvel essai dans {wait:.1f}s ({attempt + 1}/{attempts})")
        _safe_call(on_retry, attempt, failure, wait)
        if wait > 0:
            _sleep(wait)

    raise AssertionError("unreachable")            # pragma: no cover


# --------------------------------------------------------------------------- #
# HTTP                                                                        #
# --------------------------------------------------------------------------- #
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})

_shared: Any = None
_shared_lock = threading.Lock()


def _shared_session() -> Any:
    """Lazily-built requests.Session (thread-safe init), bigger pool, adapter-level
    retries disabled so attempts are never multiplied behind our back."""
    global _shared
    if _shared is None:
        with _shared_lock:
            if _shared is None:
                import requests
                from requests.adapters import HTTPAdapter
                s = requests.Session()
                adapter = HTTPAdapter(pool_connections=16, pool_maxsize=32, max_retries=0)
                s.mount("https://", adapter)
                s.mount("http://", adapter)
                _shared = s
    return _shared


def close_shared_session() -> None:
    global _shared
    with _shared_lock:
        if _shared is not None:
            _shared.close()
            _shared = None


def _redact(url: str, limit: int = 100) -> str:
    """host + path only: query strings may carry keys, proxy creds, tokens."""
    parts = urlsplit(url)
    out = f"{parts.netloc}{parts.path}" or url.split("?", 1)[0]
    return out if len(out) <= limit else out[: limit - 1] + "…"


def http_request(
    method: str,
    url: str,
    *,
    session: Any = None,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    proxies: Mapping[str, str] | None = None,
    timeout: float | tuple[float, float] = 10,
    request_kwargs: Mapping[str, Any] | None = None,
    parse_json: bool = False,
    per_attempt: Callable[[int], Mapping[str, Any]] | None = None,
    policy: RetryPolicy | None = None,
    retry_non_idempotent: bool = False,
    **engine: Any,
) -> Any:
    """One logical HTTP request with retries. Returns the Response (or the parsed
    JSON when parse_json=True), or the failure value (see retry_call).

    session          : requests.Session or curl_cffi Session (same .request API);
                       None -> shared pooled requests.Session.
    request_kwargs   : extra kwargs for session.request (json=, data=, stream=,
                       allow_redirects=...). Win over the named ones.
    per_attempt      : attempt -> dict of overrides for session/params/headers/
                       proxies/timeout, e.g. {"proxies": next_proxy()}.
    policy           : defaults to WEB.
    retry_non_idempotent : POST/PATCH are attempted once unless this is True.
    **engine         : forwarded to retry_call: label, validate, default,
                       raise_on_failure, limiter, on_retry, on_final_failure, log.
                       (An unknown name raises TypeError immediately, never retried.)
    """
    method = method.upper()
    policy = policy if policy is not None else WEB
    if method not in IDEMPOTENT_METHODS and not retry_non_idempotent \
            and policy.max_attempts > 1:
        policy = policy.replace(max_attempts=1)
    engine.setdefault("label", f"{method} {_redact(url)}")
    base = {"session": session, "params": params, "headers": headers,
            "proxies": proxies, "timeout": timeout}

    def _do(attempt: int) -> Any:
        opts = dict(base)
        if per_attempt is not None:
            opts.update(per_attempt(attempt))
        sess = opts.pop("session")
        if sess is None:
            sess = _shared_session()
        resp = sess.request(method, url, **{**opts, **(request_kwargs or {})})
        resp.raise_for_status()
        return resp.json() if parse_json else resp

    return retry_call(_do, policy=policy, pass_attempt=True, **engine)


def http_get(url: str, **kwargs: Any) -> Any:
    """GET -> Response (see http_request for every option)."""
    return http_request("GET", url, **kwargs)


def http_json(url: str, **kwargs: Any) -> Any:
    """GET -> parsed JSON; a truncated/invalid body is retried like any network error."""
    return http_request("GET", url, parse_json=True, **kwargs)


# --------------------------------------------------------------------------- #
# nba_api                                                                     #
# --------------------------------------------------------------------------- #
def not_empty(obj: Any) -> bool:
    """validate helper: not None and (if it has a length) non-empty. Works for
    DataFrames, lists, dicts."""
    if obj is None:
        return False
    try:
        return len(obj) > 0
    except TypeError:
        return True


def nba_frames(
    endpoint_cls: Callable[..., Any],
    *,
    frame: int = 0,
    label: str = "",
    policy: RetryPolicy | None = None,
    validate: Callable[[Any], bool] | None = None,
    default: Any = None,
    raise_on_failure: bool = False,
    limiter: RateLimiter | None = None,
    per_attempt: Callable[[int], Mapping[str, Any]] | None = None,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    on_final_failure: Callable[[BaseException], None] | None = None,
    log: Any = _LOGGER,
    **endpoint_kwargs: Any,
) -> Any:
    """Call an nba_api endpoint with retries; returns get_data_frames()[frame]
    (or the failure value).

    Retry options live in `policy` (default NBA_API; tweak with
    NBA_API.replace(...)) so they can never collide with endpoint kwargs.
    Everything else (season, game_id, proxy, headers, timeout, ...) goes to the
    endpoint constructor verbatim; per_attempt(attempt) may override any of it per
    try (proxy rotation). An endpoint that returns no frames at all is treated as
    an invalid response and retried; a `frame` index beyond what it returned raises
    IndexError at once (that is a bug in the call site, not in the network).
    """
    policy = policy if policy is not None else NBA_API

    def _do(attempt: int) -> Any:
        kwargs = dict(endpoint_kwargs)
        if per_attempt is not None:
            kwargs.update(per_attempt(attempt))
        frames = endpoint_cls(**kwargs).get_data_frames()
        if not frames:
            raise InvalidResultError("l'endpoint n'a renvoyé aucun tableau")
        return frames[frame]

    return retry_call(
        _do, label=label or getattr(endpoint_cls, "__name__", "nba_api"),
        policy=policy, validate=validate, default=default,
        raise_on_failure=raise_on_failure, pass_attempt=True, limiter=limiter,
        on_retry=on_retry, on_final_failure=on_final_failure, log=log)