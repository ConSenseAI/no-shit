#!/usr/bin/env python3
"""
ghost_prove.py — No Shit / F0, Ghost membership + mail-sink proof.

The *target*-side Ghost proof for the Ghost + Stripe leg. It exercises the
Ghost host itself and the leg's Mailpit sink (FIXTURES §2.2), decoupled from
Stripe billing (the Stripe billing-coupling is BLOCKED by the restricted key's
scope — see README):

  user action  ->  observable outcome in the sink  ->  member state in Ghost

Flow (an acceptance test a user could have written):
  1. wait for Ghost; ensure first-run owner setup (idempotent)
  2. checkpoint the sink, then POST a member *signup* (public magic-link API)
  3. assert the signup email lands in this leg's Mailpit
  4. follow the magic link from that email (the user "clicks" it)
  5. assert Ghost now holds the member as a real record (member state)

Reuses the shared harness client platform/harness/mailsink.py (pointed at this
leg's Mailpit on :8027, not the harness default :8025).

Env overrides: GHOST_URL, MAILPIT_URL, GHOST_OWNER_EMAIL, GHOST_OWNER_PASSWORD.
Exit: 0 if every assertion passes, nonzero otherwise.
"""
from __future__ import annotations

import os
import re
import sys
import time

import requests

# import the shared harness (host-agnostic Mailpit client)
_HARNESS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
sys.path.insert(0, _HARNESS)
from mailsink import Mailsink  # noqa: E402

# must be localhost (not 127.0.0.1): Ghost's configured url is localhost:2368,
# so member magic-links and the ghost-members-ssr cookie are scoped to that host.
GHOST_URL = os.environ.get("GHOST_URL", "http://localhost:2368").rstrip("/")
MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://127.0.0.1:8027").rstrip("/")
OWNER_EMAIL = os.environ.get("GHOST_OWNER_EMAIL", "owner@f0-ghost.test")
# throwaway dev-instance password (not a secret); must pass Ghost's strength check
OWNER_PASSWORD = os.environ.get("GHOST_OWNER_PASSWORD", "8fJq-Wm2p-Zx6t-Rn3v")
BLOG_TITLE = "No Shit F0 Ghost"
ORIGIN = {"Origin": GHOST_URL, "Content-Type": "application/json"}

CHECKS = []


def say(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class AssertFail(Exception):
    pass


def check(cond, msg):
    status = "PASS" if cond else "FAIL"
    CHECKS.append((status, msg))
    say(f"  [{status}] {msg}")
    if not cond:
        raise AssertFail(msg)


def wait_ghost(timeout=150):
    say(f"waiting for Ghost at {GHOST_URL} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(GHOST_URL + "/", timeout=5)
            if r.status_code in (200, 301, 302):
                say("  Ghost is serving")
                return True
        except requests.RequestException:
            pass
        time.sleep(3)
    raise AssertFail("Ghost did not become reachable")


def ensure_setup(sess):
    st = sess.get(GHOST_URL + "/ghost/api/admin/authentication/setup/", timeout=10).json()
    if st.get("setup", [{}])[0].get("status"):
        say("  owner already set up")
        return
    say("  performing first-run owner setup")
    r = sess.post(GHOST_URL + "/ghost/api/admin/authentication/setup/",
                  headers=ORIGIN, json={"setup": [{
                      "name": "F0 Owner", "email": OWNER_EMAIL,
                      "password": OWNER_PASSWORD, "blogTitle": BLOG_TITLE}]}, timeout=30)
    if r.status_code >= 400:
        raise AssertFail(f"setup failed: {r.status_code} {r.text[:200]}")


def main():
    wall = time.time()
    member_email = f"f0-member-{int(time.time())}@f0-ghost.test"
    member_name = "F0 New Member"
    say("GHOST MEMBERSHIP + MAIL-SINK PROOF (target side; Stripe-decoupled)")
    say(f"  member under test: {member_email}")

    admin = requests.Session()
    portal = requests.Session()
    sink = Mailsink(base_url=MAILPIT_URL)

    try:
        wait_ghost()
        say("STEP 1  ensure owner setup")
        ensure_setup(admin)

        say("STEP 2  checkpoint sink, then POST member signup (magic-link API)")
        cp = sink.checkpoint(f"to:{member_email}")
        r = portal.post(GHOST_URL + "/members/api/send-magic-link/", headers=ORIGIN,
                        json={"email": member_email, "emailType": "signup",
                              "name": member_name}, timeout=20)
        check(r.status_code in (200, 201),
              f"signup accepted by Ghost (HTTP {r.status_code})")

        say("STEP 3  assert signup email arrives in this leg's Mailpit sink")
        msg = sink.wait_new(cp, timeout=30)
        check(msg is not None, "signup email captured in Mailpit sink")
        subj = msg.get("Subject", "")
        check("sign up" in subj.lower() or "complete" in subj.lower(),
              f"email is the signup/confirm mail (subject: {subj!r})")

        say("STEP 4  follow the magic link (user 'clicks' it)")
        full = sink.message(msg["ID"])
        body = (full.get("Text") or "") + "\n" + (full.get("HTML") or "")
        links = re.findall(r"https?://[^\s\"'<>)]+", body)
        magic = next((l for l in links if "token=" in l), None)
        check(magic is not None, "magic link present in the email body")
        say(f"  magic link: {magic.split('token=')[0]}token=***&{magic.split('&',1)[1] if '&' in magic else ''}")
        follow = portal.get(magic, timeout=15, allow_redirects=True)
        check(follow.status_code < 400, f"magic link followed (HTTP {follow.status_code})")

        say("STEP 5  assert member state now exists in Ghost (Members API)")
        # Ghost looks the member up in its DB by the signed-in session and
        # returns the stored record. (Admin-API session login is gated behind
        # email 2FA in Ghost 5 — see README; the Members API is the member's
        # own authenticated view and needs no staff 2FA.)
        member = None
        for _ in range(10):  # member creation is a hair async after token exchange
            me = portal.get(GHOST_URL + "/members/api/member/", timeout=10)
            if me.status_code == 200 and me.text.strip():
                member = me.json()
                break
            time.sleep(1)
        check(member is not None, "Ghost returns a stored member for the signed-in session")
        check(member.get("email") == member_email,
              f"member record matches the signup email ({member.get('email')})")
        check(bool(member.get("uuid")),
              f"member has a Ghost-assigned uuid ({member.get('uuid')})")
        check(not member.get("paid", False), "member is a free (unpaid) member")
        say(f"  member: email={member.get('email')} name={member.get('name')!r} "
            f"uuid={member.get('uuid')} paid={member.get('paid', False)}")

        say("")
        passed = sum(1 for s, _ in CHECKS if s == "PASS")
        say(f"RESULT: {passed}/{len(CHECKS)} assertions passed (wall {time.time()-wall:.1f}s)")
        say("GHOST TARGET (member + mail sink) proven. Billing-coupling BLOCKED by "
            "Stripe key scope — see README.")
        return 0
    except (AssertFail, requests.RequestException, KeyError) as e:
        say("")
        say(f"RESULT: FAILED — {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
