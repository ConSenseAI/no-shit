#!/usr/bin/env python3
"""noshit-f1-mastodon — E2 proof (F1 Mastodon bench leg, the nli★ gold standard).

Assumes the stack is UP + provisioned (demo.sh handles bring-up, schema, the
owner+token, and seeding). Proves the platform's EXPORT / MIGRATION / DELETE
baseline on Mastodon — the reference CLEAN flows that later degradation implants
are measured against (FIXTURES §3 nli★ role). Every sink claim goes through
harness/mailsink.py; every absence window is anchored to a sidekiq drain event
(enqueued=0 busy=0), never a timer.

  PHASE 0  preflight: sink, /health, admin token, registrations open, seed present.
  PROOF 1  SIGNUP E2 MAIL ROUND-TRIP: register a NEW per-run account over plain
           HTTP (real /auth flow) -> confirmation mail in the sink -> follow the
           emailed token -> account confirmed (admin API).
  PROOF 2  nli★ CSV EXPORT: authenticated CSV downloads for a seeded account;
           following.csv data rows == the account's seeded following_count.
  PROOF 3  nli★ FULL ARCHIVE (headline): request the account archive for a per-run
           fresh account that has posted statuses -> sidekiq drain -> "archive
           ready" mail -> download the ZIP -> verify the ActivityPub actor/outbox
           (outbox.totalItems == posted count). Saved under captures/.
  PROOF 4  nli DELETION + ABSENCE: self-delete a per-run account over plain HTTP
           (password-confirmed) -> account gone (admin API + public 404) ->
           sidekiq drain -> per-address AND census-wide assert_none_new. The
           clean-deletion evidence the criterion certifies.
  PROOF 5  CLOCK-STORY NOTE for F2 (evidence only): libc / sidekiq / scheduled-job
           enumerability + the nli windows this host carries natively.

Exits nonzero on any failed assertion.
"""
import html
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))                             # seed.py
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))     # shared mailsink.py

from mailsink import Mailsink                                   # noqa: E402
import seed                                                     # noqa: E402
from seed import (                                              # noqa: E402
    MastoApi, MastoAdmin, MastoWeb, MastoError,
    APP_URL, SINK_URL, EMAIL_DOMAIN, SEED_USERS, FWD,
    wait_healthy, tootctl_create, mint_tokens, sidekiq_drain, rails_runner,
    _to_local,
)
import requests                                                 # noqa: E402

CAPTURES = "/home/user/fixture-runtime/mastodon/captures"
RUN = int(time.time())
REGISTRATION_MIN_WAIT = 4.0     # REGISTRATION_FORM_MIN_TIME = 3.seconds (anti-bot gate)

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


def record(desc):
    TIMELINE.append((_wall().strip(), desc))
    say(f"TIMELINE  {desc}")


class DemoError(Exception):
    pass


def check(cond, msg):
    if cond:
        say(f"PASS  {msg}")
    else:
        raise DemoError(msg)


def provision_account(username, password, scopes="read+write"):
    """tootctl-create a fresh local account + mint a write token (same-process,
    for the per-run proof accounts). Returns {'token','id'}."""
    tootctl_create(username, f"{username}@{EMAIL_DOMAIN}")
    toks = mint_tokens([username], password, scopes)
    if username not in toks:
        raise DemoError(f"could not provision @{username}")
    return toks[username]


def main():
    admin_token = os.environ.get("MASTO_ADMIN_TOKEN")
    seed_password = os.environ.get("MASTO_SEED_PASSWORD")
    if not admin_token or not seed_password:
        raise DemoError("MASTO_ADMIN_TOKEN / MASTO_SEED_PASSWORD missing — run ./demo.sh (it provisions them)")
    Path(CAPTURES).mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- PHASE 0
    phase("PHASE 0 — preflight (sink, /health, admin token, registrations, seed)")
    sink = Mailsink(SINK_URL)
    for _ in range(60):
        try:
            say(f"sink reachable at {SINK_URL} ({sink.count()} message(s) held)")
            break
        except OSError:
            time.sleep(1)
    else:
        raise DemoError(f"mailpit sink not reachable at {SINK_URL}")

    wait_healthy(APP_URL, timeout=180)
    admin = MastoAdmin(admin_token)
    who = admin.verify()
    say(f"Mastodon healthy at {APP_URL}; admin token valid (owner @{who.get('username')})")

    inst = requests.get(APP_URL + "/api/v2/instance", headers=FWD, timeout=15).json()
    ver = inst.get("version", "?")
    reg_open = inst.get("registrations", {}).get("enabled")
    check(reg_open is True, f"registrations OPEN on {inst.get('domain')} (Mastodon {ver})")

    seed_a = admin.account_by_username(SEED_USERS[0])
    check(seed_a is not None, f"seed account @{SEED_USERS[0]} present (id={seed_a and seed_a['id']})")
    record(f"Mastodon {ver} up on 127.0.0.1:3002 (web+sidekiq; NO streaming); admin @{who.get('username')}")

    # ---------------------------------------------------------------- PROOF 1
    phase("PROOF 1 — SIGNUP E2 mail round-trip (real /auth flow, plain HTTP)")
    web = MastoWeb()
    r = web.get("/auth/sign_up", follow=False)
    csrf = web.csrf(r.text)
    check(bool(csrf), "scraped authenticity_token (CSRF) from GET /auth/sign_up")
    signup_email = f"f1-signup-{RUN}@{EMAIL_DOMAIN}"
    signup_user = f"f1signup{RUN}"
    signup_pw = "F1-bench-Pass-234x"
    say("form requirements: authenticity_token (CSRF) + honeypots user[confirm_password]/user[website] "
        "left BLANK + user[agreement]=1; email domain must resolve (MX/A — @localhost does); and a "
        f">3s dwell (REGISTRATION_FORM_MIN_TIME anti-bot gate) — sleeping {REGISTRATION_MIN_WAIT}s")
    cp_signup = sink.checkpoint(f"to:{signup_email}")
    time.sleep(REGISTRATION_MIN_WAIT)
    r = web.post("/auth", {
        "authenticity_token": csrf,
        "user[account_attributes][username]": signup_user,
        "user[email]": signup_email,
        "user[password]": signup_pw,
        "user[password_confirmation]": signup_pw,
        "user[agreement]": "1",
        "user[confirm_password]": "",   # honeypot — blank
        "user[website]": "",            # honeypot — blank
    })
    check(r.status_code == 302 and "/auth/setup" in (r.headers.get("Location") or ""),
          f"POST /auth accepted -> {r.status_code} -> {r.headers.get('Location')} (account created, pending confirm)")
    record(f"signup POST accepted over plain HTTP (CSRF + honeypots + agreement + 3s gate); @{signup_user}")

    msg = sink.wait_new(cp_signup, timeout=60)
    full = sink.message(msg["ID"])
    body = (full.get("Text") or "") + "\n" + (full.get("HTML") or "")
    say(f"confirmation mail in sink: subject={msg.get('Subject')!r} to={signup_email}")
    m = re.search(r'(https?://[^\s"<>]+/auth/confirmation\?confirmation_token=[A-Za-z0-9_-]+)', html.unescape(body))
    check(bool(m), "confirmation email carries an /auth/confirmation?confirmation_token=<token> link")
    emailed = m.group(1)
    say(f"emailed link host: {re.match(r'https?://[^/]+', emailed).group(0)} "
        f"(rewritten to {APP_URL} to follow — token is what the server validates)")
    rc = web.get(_to_local(emailed), follow=False)
    check(rc.status_code in (302, 303) and "sign_in" not in (rc.headers.get("Location") or ""),
          f"followed emailed confirmation link -> {rc.status_code} -> {rc.headers.get('Location')}")
    acc = admin.account_by_username(signup_user)
    check(acc is not None and acc.get("confirmed") is True,
          f"admin API confirms @{signup_user} confirmed={acc and acc.get('confirmed')} "
          f"approved={acc and acc.get('approved')}")
    record(f"mail round-trip CLOSED: {signup_email} signed up -> emailed -> confirmed -> confirmed=true")

    # ---------------------------------------------------------------- PROOF 2
    phase("PROOF 2 — nli★ CSV EXPORT (settings exports; rows == seeded relations)")
    # The admin-API entity nests public counts under .account; use the public
    # lookup for the authoritative following_count.
    following_count = admin.lookup(SEED_USERS[0]).get("following_count")
    say(f"seeded @{SEED_USERS[0]} following_count (public API) = {following_count}")
    webA = MastoWeb()
    webA.login(f"{SEED_USERS[0]}@{EMAIL_DOMAIN}", seed_password)
    exports = {}
    for name in ("follows", "blocks", "mutes", "lists", "bookmarks"):
        rr = webA.get(f"/settings/exports/{name}.csv", follow=False)
        if rr.status_code != 200:
            say(f"  {name}.csv -> {rr.status_code} (skipped)")
            continue
        rows = [ln for ln in rr.text.splitlines() if ln.strip()]
        exports[name] = rows
        out = Path(CAPTURES) / f"{SEED_USERS[0]}-{name}.csv"
        out.write_text(rr.text)
        data_rows = max(0, len(rows) - 1)   # minus header
        say(f"  {name}.csv -> 200, {len(rows)} lines ({data_rows} data rows) saved {out.name}")
    check("follows" in exports, "following.csv served (200) for the seeded account")
    follow_data_rows = max(0, len(exports["follows"]) - 1)
    check(follow_data_rows == following_count,
          f"following.csv data rows ({follow_data_rows}) == seeded following_count ({following_count})")
    record(f"CSV export: following.csv {follow_data_rows} rows == following_count {following_count}; "
           f"{len(exports)} export files captured to captures/")

    # ---------------------------------------------------------------- PROOF 3
    phase("PROOF 3 — nli★ FULL ARCHIVE (headline: request -> drain -> mail -> ZIP)")
    arch_user = f"f1arch{RUN}"
    arch_email = f"{arch_user}@{EMAIL_DOMAIN}"
    arch = provision_account(arch_user, seed_password, scopes="read+write")
    say(f"per-run fresh archive account @{arch_user} (id={arch['id']}) — fresh per run keeps the "
        "7-day archive cooldown from blocking re-runs")
    arch_api = MastoApi(arch["token"])
    N_STATUSES = 6
    for i in range(N_STATUSES):
        arch_api.post_status(f"F1 archive-account status #{i:02d} run {RUN} — content for the outbox.")
    posted = arch_api.verify().get("statuses_count")
    check(posted == N_STATUSES, f"archive account posted {posted} statuses (== {N_STATUSES})")

    webArch = MastoWeb()
    webArch.login(arch_email, seed_password)
    r = webArch.get("/settings/export", follow=False)
    ecsrf = webArch.csrf(r.text)
    # Flush provisioning mail (the account's "Password changed" security notice)
    # to observable completion BEFORE the checkpoint, so wait_new below captures
    # the archive-ready mail specifically, not a straggling provisioning message.
    sidekiq_drain(max_seconds=60)
    cp_arch = sink.checkpoint(f"to:{arch_email}")
    r = webArch.post("/settings/export", {"authenticity_token": ecsrf})
    check(r.status_code in (302, 303), f"POST /settings/export (request archive) -> {r.status_code}")
    record(f"archive requested for @{arch_user} ({posted} statuses); awaiting BackupWorker via sidekiq")

    say("draining sidekiq to observable completion (BackupService runs here) ...")
    drain = sidekiq_drain(max_seconds=90)
    say(f"    sidekiq | {drain}")
    check("enqueued=0 busy=0" in drain, "sidekiq drained to enqueued=0 busy=0 (archive job has run)")

    msg = sink.wait_new(cp_arch, timeout=60)
    check("archive" in (msg.get("Subject") or "").lower(),
          f"'archive ready' mail in sink: {msg.get('Subject')!r} to {arch_email}")
    full = sink.message(msg["ID"])
    body = (full.get("Text") or "") + "\n" + (full.get("HTML") or "")
    m = re.search(r'(https?://[^\s"<>]+/backups/\d+/download[^\s"<>]*)', html.unescape(body))
    check(bool(m), "archive mail carries a /backups/<id>/download link")
    dl = webArch.get(_to_local(m.group(1)), follow=True)   # 302 -> /system/backups/....zip -> 200
    check(dl.status_code == 200 and dl.content[:2] == b"PK",
          f"downloaded archive -> {dl.status_code}, {len(dl.content)} bytes, ZIP magic present")
    art = Path(CAPTURES) / f"{arch_user}-archive.zip"
    art.write_bytes(dl.content)
    z = zipfile.ZipFile(io.BytesIO(dl.content))
    members = z.namelist()
    check("outbox.json" in members and "actor.json" in members,
          f"archive contains ActivityPub actor.json + outbox.json (members: {members})")
    outbox = json.loads(z.read("outbox.json"))
    actor = json.loads(z.read("actor.json"))
    check(outbox.get("totalItems") == posted,
          f"outbox.json totalItems ({outbox.get('totalItems')}) == posted statuses ({posted})")
    check(actor.get("preferredUsername") == arch_user,
          f"actor.json preferredUsername == @{arch_user} (type={actor.get('type')})")
    record(f"ARCHIVE headline CLOSED: request->drain->mail->download; ZIP outbox.totalItems={outbox.get('totalItems')} "
           f"== {posted}, actor @{actor.get('preferredUsername')}; saved {art.name}")

    # ---------------------------------------------------------------- PROOF 4
    phase("PROOF 4 — nli DELETION + ABSENCE (self-delete -> gone -> event-anchored absence)")
    del_user = f"f1del{RUN}"
    del_email = f"{del_user}@{EMAIL_DOMAIN}"
    delacct = provision_account(del_user, seed_password, scopes="read+write")
    del_id = delacct["id"]
    # provisioning set a password -> a "Password changed" security mail. Drain so
    # transactional mail settles, then count: this baseline is the "the msg channel
    # was LIVE to this address while the account was active" evidence that the clean
    # deletion then silences (a meaningful absence needs a live baseline).
    sidekiq_drain(max_seconds=60)
    baseline = sink.count(f"to:{del_email}")
    say(f"per-run delete account @{del_user} (id={del_id}); baseline mail to its address = {baseline} "
        "(the transactional 'live channel' the clean deletion then silences)")
    check(baseline >= 1,
          f"msg channel was LIVE to {del_email} while active (baseline={baseline} transactional mail)")

    webDel = MastoWeb()
    webDel.login(del_email, seed_password)
    r = webDel.get("/settings/delete", follow=False)
    dcsrf = webDel.csrf(r.text)
    check(bool(dcsrf), "loaded /settings/delete (password-confirmation form)")
    r = webDel.post("/settings/delete", {
        "_method": "delete",
        "authenticity_token": dcsrf,
        "form_delete_confirmation[password]": seed_password,
    })
    check(r.status_code in (302, 303) and "sign_in" in (r.headers.get("Location") or ""),
          f"POST /settings/delete (password-confirmed) -> {r.status_code} -> {r.headers.get('Location')} "
          "(deletion accepted, session ended)")
    record(f"@{del_user} self-deleted over plain HTTP (settings delete + password confirmation)")

    # Self-deletion suspends immediately and enqueues the async purge worker; drain
    # sidekiq FIRST so the purge has actually run before the gone-check (and so any
    # deletion-triggered mail has landed before the absence window opens).
    say("draining sidekiq to observable completion (deletion/purge worker + any mail) ...")
    drain = sidekiq_drain(max_seconds=90)
    say(f"    sidekiq | {drain}")
    check("enqueued=0 busy=0" in drain, "sidekiq drained to enqueued=0 busy=0 — purge ran, absence window may open")

    # gone check (admin API absence/suspension + public gone) — AFTER the purge
    gone_admin = admin.account_by_username(del_user)
    pub = requests.get(f"{APP_URL}/api/v1/accounts/{del_id}", headers=FWD, timeout=15, allow_redirects=False)
    check(gone_admin is None or gone_admin.get("suspended") is True,
          f"account gone/suspended per admin API (present={gone_admin is not None}, "
          f"suspended={gone_admin and gone_admin.get('suspended')})")
    check(pub.status_code in (404, 410, 403),
          f"public GET /api/v1/accounts/{del_id} -> {pub.status_code} (gone)")

    # absence: per-address AND census-wide, anchored to the drain event (not a timer)
    cp_addr = sink.checkpoint(f"to:{del_email}")   # AFTER drain: any deletion mail already counted
    cp_all = sink.checkpoint()
    sink.assert_none_new(cp_addr, settle=4.0)
    check(True, f"ABSENCE holds per-address: 0 further mail to {del_email} after deletion "
                f"(baseline stays {sink.count(f'to:{del_email}')}; settle covers delivery latency only)")
    sink.assert_none_new(cp_all, settle=0.5)
    check(True, "ABSENCE holds census-wide: no unexpected mail since the deletion drain")
    record(f"DELETION absence pair held: @{del_user} was live (baseline {baseline}) then SILENT after "
           "deletion (per-address + census, anchored to sidekiq drain)")

    # ---------------------------------------------------------------- PROOF 5
    phase("PROOF 5 — CLOCK-STORY NOTE for F2 (evidence only, no assertion)")
    note = rails_runner("clock_note.rb", service="sidekiq")
    for line in note.strip().splitlines():
        say(f"    clock | {line}")
    record("clock note captured (libc / sidekiq / scheduler enumerability + nli windows) — see PROOF 5")

    # ---------------------------------------------------------------- TIMELINE
    phase("TIMELINE")
    print(f"{'WALL':>8}  EVENT", flush=True)
    print("-" * 74, flush=True)
    for w, desc in TIMELINE:
        print(f"{w:>8}  {desc}", flush=True)

    phase("RESULT — F1 Mastodon nli★ bench proofs")
    for line in (
        f"  host     : Mastodon {ver} up on 127.0.0.1:3002 (web+sidekiq; streaming omitted — not needed)",
        f"  signup   : plain-HTTP /auth (CSRF+honeypots+agreement+3s gate) -> confirmation mail -> confirmed",
        f"  export   : following.csv {follow_data_rows} rows == following_count {following_count}; "
        f"{len(exports)} CSVs captured",
        f"  archive  : request->drain->mail->ZIP; outbox.totalItems={outbox.get('totalItems')}=={posted}, "
        f"actor @{actor.get('preferredUsername')}",
        f"  deletion : @{del_user} deleted -> gone (admin+404) -> absence per-address+census (sidekiq-anchored)",
    ):
        print(line, flush=True)
    say(f"ALL ASSERTIONS PASSED in {time.monotonic() - _t0:.1f}s (sink holds {sink.count()} message(s))")


if __name__ == "__main__":
    try:
        main()
    except (DemoError, MastoError, TimeoutError, AssertionError) as e:
        print(f"\n[{_wall()}] FAIL  {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
