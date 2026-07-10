#!/usr/bin/env python3
"""F0 fake-time sidecar scheduler (FIXTURES §2.1 rung 2).

Runs under libfaketime (LD_PRELOAD, wired in docker-compose.yml). This process
has NO knowledge of faketime: it reads the wall clock via datetime.now() like
any host cron/queue worker would. libfaketime intercepts the clock and returns
a faked time governed by /faketime/faketimerc, which the demo rewrites at
runtime (FAKETIME_NO_CACHE=1 -> the offset is re-read on every call).

It models one app-side, clock-gated job: a day-N "retention window expired"
task that emails a data-purge notice into the shared Mailpit sink IFF its
faked clock has crossed N days past this process's start. The demo advances the
faked clock across that boundary in seconds of wall time; the job then fires.
This is the exact shape a real scheduled deletion/retention job has — only the
clock is faked, nothing in this code is.

Stdlib only.
"""
import os
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST", "mailpit")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "30"))
TO_ADDR = os.environ.get("RETENTION_ACCOUNT", "retention-subject@noshit.test")
FROM_ADDR = os.environ.get("RETENTION_FROM", "retention-bot@noshit.test")
SUBJECT = "Retention window expired - scheduled data purge"


def log(msg: str) -> None:
    print(
        f"[scheduler] wall={int(time.time())} "
        f"faked={datetime.now().isoformat(timespec='seconds')} :: {msg}",
        flush=True,
    )


def send_expiry_email(now: datetime) -> None:
    m = EmailMessage()
    m["From"] = FROM_ADDR
    m["To"] = TO_ADDR
    m["Subject"] = SUBJECT
    m.set_content(
        "libfaketime rung-2 proof (FIXTURES 2.1).\n\n"
        f"The {RETENTION_DAYS}-day retention window has elapsed on the app-side "
        "scheduler clock.\n"
        f"This day-{RETENTION_DAYS} job fired at faked clock {now.isoformat()} "
        "while wall-clock time advanced only seconds.\n"
    )
    last = None
    for _ in range(60):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
                s.send_message(m)
            log("expiry email delivered to sink")
            return
        except OSError as e:  # mailpit not up yet, transient network, etc.
            last = e
            time.sleep(1)
    log(f"FAILED to deliver expiry email after retries: {last}")


def main() -> None:
    start = datetime.now()
    target = start + timedelta(days=RETENTION_DAYS)
    log(
        f"boot; retention target = start + {RETENTION_DAYS}d = "
        f"{target.isoformat(timespec='seconds')}"
    )
    fired = False
    ticks = 0
    while True:
        now = datetime.now()  # libfaketime-intercepted
        if not fired and now >= target:
            log(f"BOUNDARY CROSSED (faked {now.isoformat()} >= target {target.isoformat()})")
            send_expiry_email(now)
            fired = True
        ticks += 1
        if not fired and ticks % 10 == 0:
            log("within retention window; day-N job not yet due")
        time.sleep(1)  # scheduler poll tick (real 1s; libfaketime does not scale sleep)


if __name__ == "__main__":
    main()
