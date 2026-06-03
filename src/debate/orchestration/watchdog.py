"""Watchdog — per-turn keep-alive with bounded kill & restart (Phase 6.5).

Each agent turn runs on a daemon worker thread joined with a keep-alive
deadline. If the turn overruns (a hung/stalled provider) or raises, the
watchdog abandons that worker — daemon threads die with the process — and
restarts the turn, up to ``max_restarts`` times before surfacing a
:class:`WatchdogError`. Errors listed in ``fatal`` (e.g. budget exhaustion)
bypass the restart loop and halt the run immediately.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class WatchdogError(RuntimeError):
    """Raised when a turn keeps failing past ``max_restarts``."""


class Watchdog:
    """Runs a callable under a timeout, restarting it on hang/failure."""

    def __init__(
        self,
        *,
        keepalive_seconds: float,
        max_restarts: int,
        logger: object | None = None,
        fatal: tuple[type[BaseException], ...] = (),
    ) -> None:
        self._timeout = keepalive_seconds
        self._max_restarts = max_restarts
        self._logger = logger
        self._fatal = fatal

    def run(self, label: str, fn: Callable[[], T]) -> T:
        """Execute ``fn`` with keep-alive; restart on hang/failure, else give up."""
        attempt = 0
        while True:
            try:
                return self._guarded(fn)
            except self._fatal:
                raise
            except Exception as exc:  # noqa: BLE001 - watchdog restarts on any failure
                attempt += 1
                self._log("watchdog_restart", label=label, attempt=attempt, error=str(exc))
                if attempt > self._max_restarts:
                    raise WatchdogError(
                        f"{label} failed after {attempt} attempt(s): {exc}"
                    ) from exc

    def _guarded(self, fn: Callable[[], T]) -> T:
        """Run ``fn`` on a daemon thread; raise ``TimeoutError`` if it overruns."""
        box: dict[str, object] = {}

        def worker() -> None:
            try:
                box["result"] = fn()
            except Exception as exc:  # noqa: BLE001 - propagated to the caller below
                box["error"] = exc

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(self._timeout)
        if thread.is_alive():
            raise TimeoutError(f"turn exceeded {self._timeout}s keep-alive")
        if "error" in box:
            raise box["error"]  # type: ignore[misc]
        return box["result"]  # type: ignore[return-value]

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
