"""Tests for the orchestration watchdog (Phase 6.5).

The watchdog must time out a hung turn, restart it, and let the run recover;
give up with a :class:`WatchdogError` once restarts are exhausted; and re-raise
a *fatal* error (e.g. budget exhaustion) immediately without retrying.
"""

from __future__ import annotations

import time

import pytest

from debate.orchestration.watchdog import Watchdog, WatchdogError


def test_hung_turn_is_timed_out_then_restarted_and_recovers() -> None:
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            time.sleep(1.0)  # overruns the keep-alive on the first attempt
        return "recovered"

    watchdog = Watchdog(keepalive_seconds=0.05, max_restarts=2)
    assert watchdog.run("turn", flaky) == "recovered"
    assert attempts["n"] == 2


def test_gives_up_after_max_restarts() -> None:
    attempts = {"n": 0}

    def boom() -> str:
        attempts["n"] += 1
        raise RuntimeError("always fails")

    watchdog = Watchdog(keepalive_seconds=1.0, max_restarts=2)
    with pytest.raises(WatchdogError):
        watchdog.run("turn", boom)
    assert attempts["n"] == 3  # initial attempt + 2 restarts


def test_fatal_error_bypasses_restart() -> None:
    class FatalError(RuntimeError):
        pass

    attempts = {"n": 0}

    def fn() -> str:
        attempts["n"] += 1
        raise FatalError("budget exhausted")

    watchdog = Watchdog(keepalive_seconds=1.0, max_restarts=3, fatal=(FatalError,))
    with pytest.raises(FatalError):
        watchdog.run("turn", fn)
    assert attempts["n"] == 1
