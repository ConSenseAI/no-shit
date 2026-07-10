#!/usr/bin/env python3
"""Thin stdlib-only client for Kill Bill's test clock (/1.0/kb/test/clock).

FIXTURES §2.1 rung 1: in test mode (org.killbill.server.test.mode=true) Kill
Bill runs a server-global, movable clock. This module drives it. It works as a
library (``from clockctl import Clock``) and as a CLI.

The date-vs-datetime gotcha (the deviation FIXTURES §9 warns about): the clock
accepts either a bare LocalDate ("2026-01-23") or a full DateTime
("2026-01-23T12:00:00"). A bare date is interpreted at 00:00:00, which can land
*before* an event scheduled later that same day — e.g. a trial that began at
08:00 has its phase change at 08:00 eight days on, so moving the clock to the
bare date "T0+8d" (00:00) is still inside the trial and NOTHING converts. Always
move the clock with an explicit DateTime strictly past the boundary you want to
cross. As a guard, set()/CLI `set` promote a bare date to noon of that day.

Config is read from the environment (overridable via constructor args):
  KB_BASE_URL (default http://127.0.0.1:8080)
  KB_ADMIN_USER / KB_ADMIN_PASSWORD (basic auth; default admin/password)
  KB_TENANT_API_KEY / KB_TENANT_API_SECRET (tenant headers, if a tenant exists)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = os.environ.get("KB_BASE_URL", "http://127.0.0.1:8080")
CLOCK_PATH = "/1.0/kb/test/clock"
QUEUES_PATH = "/1.0/kb/test/queues"


class Clock:
    """Client for the Kill Bill test-clock endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        user: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        created_by: str = "noshit-f0",
        timeout: float = 60.0,
    ) -> None:
        self.base = base_url.rstrip("/")
        self.user = user or os.environ.get("KB_ADMIN_USER", "admin")
        self.password = password or os.environ.get("KB_ADMIN_PASSWORD", "password")
        self.api_key = api_key or os.environ.get("KB_TENANT_API_KEY")
        self.api_secret = api_secret or os.environ.get("KB_TENANT_API_SECRET")
        self.created_by = created_by
        self.timeout = timeout

    # -- internals ---------------------------------------------------------
    def _headers(self, mutating: bool) -> dict[str, str]:
        token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        h = {"Accept": "application/json", "Authorization": "Basic " + token}
        if self.api_key:
            h["X-Killbill-ApiKey"] = self.api_key
        if self.api_secret:
            h["X-Killbill-ApiSecret"] = self.api_secret
        if mutating:
            h["X-Killbill-CreatedBy"] = self.created_by
            h["Content-Type"] = "application/json"
        return h

    def _req(self, method: str, path: str, params: dict | None = None, mutating: bool = False) -> dict:
        url = self.base + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        req = urllib.request.Request(url, method=method, headers=self._headers(mutating))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read().decode("utf-8")
                return json.loads(body) if body.strip() else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from None

    @staticmethod
    def to_datetime(when) -> str | None:
        """Promote a bare date to noon of that day; pass datetimes through.

        This is the guard against the FIXTURES §9 date-vs-datetime trap: bare
        dates land at midnight, which may be before the day's scheduled events.
        """
        if when is None:
            return None
        s = str(when).strip()
        if not s:
            return None
        if "T" in s:  # already a datetime
            return s
        return s + "T12:00:00"

    # -- API ---------------------------------------------------------------
    def get(self, time_zone: str | None = None) -> dict:
        """GET current clock -> {currentUtcTime, timeZone, localDate}."""
        return self._req("GET", CLOCK_PATH, {"timeZone": time_zone})

    def set(self, requested_date, timeout_sec: int = 5, time_zone: str | None = None) -> dict:
        """POST: move the clock to an absolute instant. Bare dates -> noon."""
        return self._req(
            "POST",
            CLOCK_PATH,
            {"requestedDate": self.to_datetime(requested_date), "timeoutSec": timeout_sec, "timeZone": time_zone},
            mutating=True,
        )

    def advance(self, days=None, weeks=None, months=None, years=None, timeout_sec: int = 5) -> dict:
        """PUT: advance the clock by a relative duration. Only the first of
        days/weeks/months/years is honored by the server."""
        return self._req(
            "PUT",
            CLOCK_PATH,
            {"days": days, "weeks": weeks, "months": months, "years": years, "timeoutSec": timeout_sec},
            mutating=True,
        )

    def wait_queues(self, timeout_sec: int = 10) -> dict:
        """GET: block until the notification/bus queues drain (or timeout).
        Use after a clock move so downstream invoicing/payment has run."""
        return self._req("GET", QUEUES_PATH, {"timeoutSec": timeout_sec})


# -- CLI -------------------------------------------------------------------
_USAGE = """usage: clockctl.py <command> [args]

  get [timezone]           print the current virtual clock
  set <date|datetime>      move the clock (bare date -> noon of that day)
  advance <days>           advance the clock by N days
  queues [timeoutSec]      wait for the notification queues to drain

env: KB_BASE_URL, KB_ADMIN_USER, KB_ADMIN_PASSWORD,
     KB_TENANT_API_KEY, KB_TENANT_API_SECRET
"""


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(_USAGE)
        return 0 if argv else 2
    clock = Clock()
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "get":
            out = clock.get(rest[0] if rest else None)
        elif cmd == "set":
            if not rest:
                print("set: need a date or datetime", file=sys.stderr)
                return 2
            out = clock.set(rest[0])
        elif cmd == "advance":
            if not rest:
                print("advance: need a number of days", file=sys.stderr)
                return 2
            out = clock.advance(days=int(rest[0]))
        elif cmd == "queues":
            out = clock.wait_queues(int(rest[0]) if rest else 10)
        else:
            print(_USAGE, file=sys.stderr)
            return 2
    except Exception as e:  # noqa: BLE001 - CLI surface
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
