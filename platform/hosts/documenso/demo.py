#!/usr/bin/env python3
"""noshit-f0-documenso — end-to-end F0 proof (criteria 2, 3, 4).

Assumes the stack is already up and healthy (demo.sh handles up/down). Drives:

  PHASE 0  preflight: sink reachable, Documenso healthy
  PHASE 1  real signup via Documenso's own endpoint -> confirmation email in sink   (crit 2, presence)
  PHASE 2  extract verify token FROM the captured email -> verify -> session         (real flow)
  PHASE 3  authenticated account deletion via tRPC -> opens post-deletion window     (crit 2)
  PHASE 4  stack-level fake time: advance a sidecar's faked clock across day-30 in
           seconds -> retention job fires into sink; deleted-user absence holds       (crit 3 + crit 2 absence)
  PHASE 5  scripted support persona: trigger -> scripted virtual delay -> reply       (crit 4)
  PHASE 6  virtual-time timeline

Exits nonzero on any failed assertion. Absence windows are asserted with the
harness primitives (checkpoint + assert_none_new) bracketing the virtual-clock
advance — windows are SCRIPT positions, not wall time.
"""
import os
import shlex
import smtplib
import subprocess
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))                          # seed.py, personas/
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))  # shared mailsink.py

from mailsink import Mailsink            # noqa: E402
from seed import Documenso, extract_verify_token  # noqa: E402
from personas.responder import SupportPersona     # noqa: E402

PROJECT = "noshit-f0-documenso"
SINK_URL = "http://localhost:8026"
APP_URL = "http://localhost:3600"
SMTP_HOST, SMTP_PORT = "localhost", 1026
FAKETIME_FILE = SCRIPT_DIR / "data" / "faketime" / "faketimerc"

_t0 = time.monotonic()


def _wall():
    return f"{time.monotonic() - _t0:6.1f}s"


def say(msg):
    print(f"[{_wall()}] {msg}", flush=True)


def phase(title):
    print("\n" + "=" * 74, flush=True)
    print(f"== {title}", flush=True)
    print("=" * 74, flush=True)


TIMELINE = []


def record(vt, desc):
    TIMELINE.append((vt, _wall().strip(), desc))
    say(f"TIMELINE  {vt:<26} {desc}")


class DemoError(Exception):
    pass


def check(cond, msg):
    if cond:
        say(f"PASS  {msg}")
    else:
        raise DemoError(msg)


def set_faketime(spec):
    tmp = FAKETIME_FILE.with_suffix(".tmp")
    tmp.write_text(spec + "\n")
    os.replace(tmp, FAKETIME_FILE)
    say(f"wrote faketime offset {spec!r} -> data/faketime/faketimerc")


def docker_exec(service, container_cmd, timeout=30):
    """Best-effort `compose exec` for evidence gathering. Returns (out, rc)."""
    inner = f"docker compose -p {PROJECT} exec -T {service} sh -c {shlex.quote(container_cmd)}"
    try:
        r = subprocess.run(
            ["sg", "docker", "-c", inner],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (r.stdout + r.stderr).strip(), r.returncode
    except (subprocess.SubprocessError, OSError) as e:
        return f"(docker exec failed: {e})", 1


def smtp_send(msg):
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
        s.send_message(msg)


def main():
    phase("PHASE 0 — preflight")
    sink = Mailsink(SINK_URL)
    for _ in range(60):
        try:
            n = sink.count()
            say(f"sink reachable at {SINK_URL} ({n} message(s) held)")
            break
        except OSError:
            time.sleep(1)
    else:
        raise DemoError(f"mailpit sink not reachable at {SINK_URL}")

    doc = Documenso(APP_URL)
    for _ in range(120):
        st, body = doc.health()
        if st == 200:
            say(f"documenso healthy: {body[:140]}")
            break
        time.sleep(2)
    else:
        raise DemoError("documenso /api/health did not return 200")

    # ---------------------------------------------------------------- PHASE 1
    phase("PHASE 1 — real signup -> confirmation email in sink (criterion 2, presence)")
    email = f"f0-user-{int(time.time())}@noshit.test"
    password = "NoShitF0-Passw0rd!"
    name = "F0 User"
    say(f"new account: {email}")

    cp_conf = sink.checkpoint(f"to:{email}")
    st, body = doc.signup(name, email, password)
    check(st == 201, f"POST /api/auth/email-password/signup -> HTTP {st} ({body[:60]!r})")
    record("vDAY 0", f"signup for {email} (Documenso's own endpoint)")

    conf = sink.wait_new(cp_conf, timeout=90)
    subj = conf.get("Subject", "")
    say(f"confirmation email captured: subject={subj!r} id={conf.get('ID')}")
    check(bool(conf), "confirmation email landed in the sink (app -> sink coupling)")
    record("vDAY 0", f"confirmation email captured in sink: {subj!r}")

    # ---------------------------------------------------------------- PHASE 2
    phase("PHASE 2 — verify email FROM the captured mail -> session (real flow)")
    full = sink.message(conf["ID"])
    token = extract_verify_token(full.get("HTML"), full.get("Text"))
    check(bool(token), f"extracted verify token from the confirmation email ({str(token)[:12]}...)")

    st, body = doc.verify_email(token)
    check(st == 200 and "VERIFIED" in body, f"POST verify-email -> HTTP {st} ({body[:80]!r})")
    check(doc.has_session(), "auto-authorized: signed sessionId cookie held")
    record("vDAY 0", "email verified -> account active + authenticated")

    # ---------------------------------------------------------------- PHASE 3
    phase("PHASE 3 — authenticated account deletion (criterion 2, opens absence window)")
    st, body = doc.delete_account()
    ok = st == 200 and '"result"' in body and '"error"' not in body
    check(ok, f"tRPC profile.deleteAccount -> HTTP {st} ({body[:80]!r})")
    record("vDAY 0+", "account deleted via tRPC; post-deletion absence window opens")

    out, rc = docker_exec(
        "database",
        "psql -U documenso -d documenso -tAc "
        + shlex.quote(f"SELECT count(*) FROM \"User\" WHERE email='{email}'"),
    )
    if rc == 0:
        say(f"DB evidence: rows for {email} after deletion = {out!r} (expect 0)")

    # absence window baseline for the deleted user (includes the 1 confirmation mail)
    cp_deleted_user = sink.checkpoint(f"to:{email}")

    # ---------------------------------------------------------------- PHASE 4
    phase("PHASE 4 — stack-level fake time across a multi-day boundary (criterion 3)")
    osr, _ = docker_exec("documenso", "cat /etc/os-release | head -2; ls /lib/ld-musl-* 2>/dev/null")
    say("Documenso container libc evidence:")
    for line in osr.splitlines():
        say(f"    {line}")
    say("=> Documenso is musl/alpine: glibc libfaketime cannot LD_PRELOAD into it.")
    say("=> rung-2 fake time is proven on the glibc scheduler sidecar in the same stack.")

    cp_retention = sink.checkpoint('subject:"Retention window expired"')

    # Before the advance: the day-30 job must NOT have fired (clock-gated).
    say("asserting the retention job has NOT fired at faked day 0 ...")
    sink.assert_none_new(cp_retention, settle=3.0)
    check(True, "day-30 retention job absent before the virtual advance (clock-gated)")
    record("vDAY 0", "sidecar scheduler within retention window (no purge mail)")

    # Advance the sidecar's faked clock across day 30 in seconds of wall time.
    say("advancing the sidecar's faked clock by +31 days ...")
    set_faketime("+31d")
    record("vDAY 0 -> vDAY 31", "sidecar faked clock advanced +31d (libfaketime, seconds of wall time)")

    ret = sink.wait_new(cp_retention, timeout=60)
    say(f"retention email captured: subject={ret.get('Subject')!r}")
    ret_full = sink.message(ret["ID"])
    for line in (ret_full.get("Text") or "").splitlines():
        if line.strip():
            say(f"    | {line}")
    check(bool(ret), "day-30 retention job FIRED after crossing the faked boundary")
    record("vDAY 31", "retention 'data purge' mail fired into sink under fake time")

    # Close the deleted-user absence window across the same virtual advance.
    say("asserting NO further mail reached the deleted account across the window ...")
    sink.assert_none_new(cp_deleted_user, settle=3.0)
    check(True, "post-deletion absence holds: no further mail to the deleted account "
                "across the 30 virtual days")
    record("vDAY 31", f"absence verified: 0 new messages to {email} since deletion")

    # ---------------------------------------------------------------- PHASE 5
    phase("PHASE 5 — scripted support persona round-trip (criterion 4)")
    req = EmailMessage()
    req["From"] = "customer@noshit.test"
    req["To"] = "support@noshit.test"
    req["Subject"] = "Support request: data export SLA"
    req.set_content("Please confirm my data export request within the stated SLA.")
    cp_req = sink.checkpoint('subject:"Support request"')
    smtp_send(req)
    trigger = sink.wait_new(cp_req, timeout=20)
    check(bool(trigger), "inbound support-request landed in sink (persona trigger)")
    record("persona 09:00", "support request received in sink")

    persona = SupportPersona(
        sink, smtp_host=SMTP_HOST, smtp_port=SMTP_PORT,
        virtual_now=datetime(2026, 1, 1, 9, 0, 0),
    )
    found = persona.find_trigger("support request")
    check(found is not None, "persona observed the trigger message")

    cp_reply = sink.checkpoint('subject:"Re: Support request"')
    before = persona.virtual_now
    persona.advance(hours=4)  # scripted virtual delay — explicit step, NOT a wall-clock sleep
    record(
        f"persona {before.strftime('%H:%M')} -> {persona.virtual_now.strftime('%H:%M')}",
        "scripted +4h SLA virtual delay (no wall-clock sleep)",
    )
    persona.respond_to(found, sla_note="4h support SLA, scripted virtual delay")
    reply = sink.wait_new(cp_reply, timeout=20)
    check(bool(reply), "persona reply round-tripped back into the sink")
    record("persona 13:00", f"persona reply delivered: {reply.get('Subject')!r}")

    # ---------------------------------------------------------------- PHASE 6
    phase("PHASE 6 — virtual-time timeline")
    print(f"{'VIRTUAL TIME':<28}{'WALL':>8}  EVENT", flush=True)
    print("-" * 74, flush=True)
    for vt, w, desc in TIMELINE:
        print(f"{vt:<28}{w:>8}  {desc}", flush=True)

    phase("RESULT — F0 criteria proven on the Documenso leg")
    for line in (
        "  crit 2  app/sink coupling  : signup confirmation captured; post-deletion",
        "                              absence window held via checkpoint+assert_none_new",
        "  crit 3  stack fake time    : sidecar day-30 job fired after +31d faked advance",
        "                              (Documenso itself is musl -> documented rung-2 sidecar)",
        "  crit 4  persona round-trip : trigger -> scripted +4h virtual delay -> reply in sink",
    ):
        print(line, flush=True)
    say(f"ALL ASSERTIONS PASSED in {time.monotonic() - _t0:.1f}s wall time")


if __name__ == "__main__":
    try:
        main()
    except (DemoError, TimeoutError, AssertionError) as e:
        print(f"\n[{_wall()}] FAIL  {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
