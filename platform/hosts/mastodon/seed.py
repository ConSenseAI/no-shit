#!/usr/bin/env python3
"""noshit-f1-mastodon — API clients + bulk seeding (FIXTURES §2.3 bulk content).

Two roles (imported by demo.py, runnable standalone against a running stack):

  1. HTTP clients for Mastodon's REAL surfaces, wired for this leg's loopback
     bench:
       * MastoApi   — token (OAuth Bearer) REST client for /api/*.
       * MastoWeb   — cookie/session client for the settings web flows (CSV
                      export, archive request, account deletion) that are NOT
                      OAuth-accessible.
     Both send `X-Forwarded-Proto: https` (Mastodon production force_ssl treats
     the request as TLS-terminated — the standard reverse-proxy model — so it
     serves over the plaintext loopback port instead of 301-ing to https), and
     both mark cookies non-secure so requests will send the Secure session cookie
     back over http. Emitted https://localhost/... links are rewritten to the
     mapped loopback (http://localhost:3002) to be followed. See README.

  2. Seeding — create >=3 local accounts (tootctl), give them a known password +
     mint write tokens (rails runner Doorkeeper), establish a deterministic
     follow graph, and post >=100 statuses across them in one pass; verify counts
     back via the API. Idempotent: existing accounts/relations/statuses are
     reused, so warm re-runs stay green.

Stdlib + requests (as the sibling discourse leg).
"""
import os
import re
import shlex
import subprocess
import sys
import time
import http.cookiejar as cookiejar

import requests

# --- fixture constants (shared with demo.py) --------------------------------
PROJECT = "noshit-f1-mastodon"
APP_URL = os.environ.get("MASTO_URL", "http://localhost:3002")   # == 127.0.0.1:3002
SINK_URL = os.environ.get("MAILSINK_URL", "http://127.0.0.1:8032")
FWD = {"X-Forwarded-Proto": "https"}                             # production TLS-proxy model
EMAIL_DOMAIN = "localhost"          # must resolve — Mastodon signup validates MX/A
SEED_USERS = ["f1seed_a", "f1seed_b", "f1seed_c"]
# deterministic follow graph among the seed accounts (follower -> [followees]).
FOLLOW_GRAPH = {
    "f1seed_a": ["f1seed_b", "f1seed_c"],
    "f1seed_b": ["f1seed_c"],
    "f1seed_c": ["f1seed_a"],
}
STATUS_TARGET = int(os.environ.get("STATUS_TARGET", "102"))      # >=100, split across accounts


class MastoError(Exception):
    pass


# --- host-side docker helpers (provisioning via the container) --------------
def _sg(inner, timeout=180):
    """Run one shell command through `sg docker -c` (this machine's docker
    access pattern). `inner` is a single already-quoted command string."""
    r = subprocess.run(["sg", "docker", "-c", inner],
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def dc_exec(service, args, timeout=180):
    """docker compose exec -T <service> <args...>  (args: list, shell-quoted)."""
    inner = (f"docker compose -p {PROJECT} exec -T {service} "
             + " ".join(shlex.quote(a) for a in args))
    rc, out, err = _sg(inner, timeout=timeout)
    if rc != 0:
        raise MastoError(f"exec {args[:3]}... rc={rc}: {(err or out).strip()[-400:]}")
    return out


def rails_runner(script, *args, service="web", timeout=200):
    return dc_exec(service, ["bin/rails", "runner", f"/provision/{script}", *map(str, args)],
                   timeout=timeout)


def tootctl_create(username, email):
    """Create a confirmed local account; returns True if created, False if it
    already existed (idempotent). Requires registrations open (auto-approved)."""
    inner = (f"docker compose -p {PROJECT} exec -T web bin/tootctl accounts create "
             f"{shlex.quote(username)} --email {shlex.quote(email)} --confirmed")
    rc, out, err = _sg(inner, timeout=120)
    blob = (out + err)
    if rc == 0 and "OK" in out:
        return True
    if "taken" in blob or "already" in blob or "exist" in blob.lower():
        return False
    # tootctl returns nonzero on a duplicate; treat a known-duplicate as existing
    if rc != 0 and ("USERNAME" in blob or "EMAIL" in blob or "taken" in blob):
        return False
    if rc != 0:
        raise MastoError(f"tootctl create {username} rc={rc}: {blob.strip()[-300:]}")
    return False


def sidekiq_drain(max_seconds=60):
    """Drain sidekiq (mail/backup/deletion) to enqueued=0 busy=0 — the absence
    anchor (an EVENT, not a timer). Returns the final stats line."""
    out = rails_runner("sidekiq_drain.rb", max_seconds, service="web", timeout=max_seconds + 40)
    lines = [ln for ln in out.strip().splitlines() if ln.startswith("enqueued=")]
    return lines[-1] if lines else out.strip().splitlines()[-1]


def mint_tokens(usernames, password, scopes="read+write+follow"):
    """tootctl-created accounts -> set known password + mint a token each (one
    rails-runner pass). Returns {username: {"token":..., "id":...}}."""
    out = rails_runner("prepare_accounts.rb", ",".join(usernames), password, scopes)
    tokens = {}
    for ln in out.splitlines():
        m = re.match(r"NOSHIT_TOKEN=([^:]+):([^:]+):(\d+)", ln.strip())
        if m:
            tokens[m.group(1)] = {"token": m.group(2), "id": m.group(3)}
    return tokens


# --- cookie policy: send Secure cookies over the http loopback --------------
class _AllowSecureOverHTTP(cookiejar.DefaultCookiePolicy):
    def return_ok_secure(self, cookie, request):   # noqa: N802 (stdlib signature)
        return True


def _to_local(url):
    """Rewrite an emitted https://localhost[:port]/… link to the mapped loopback
    http port so it can be followed. The token/path is what the server checks."""
    return re.sub(r"https?://localhost(?::\d+)?", APP_URL, url or "")


# --- token REST client ------------------------------------------------------
class MastoApi:
    def __init__(self, token, base=APP_URL, timeout=40):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers.update(FWD)
        self.s.headers["Authorization"] = f"Bearer {token}"
        self.s.headers["User-Agent"] = "noshit-f1-mastodon/1.0"

    def req(self, method, path, expect=None, **kw):
        r = self.s.request(method, self.base + path, timeout=self.timeout,
                           allow_redirects=False, **kw)
        if expect is not None and r.status_code not in expect:
            raise MastoError(f"{method} {path} -> {r.status_code} (want {expect}): {r.text[:200]}")
        return r

    def verify(self):
        return self.req("GET", "/api/v1/accounts/verify_credentials", expect=(200,)).json()

    def account(self, acct_id):
        return self.req("GET", f"/api/v1/accounts/{acct_id}", expect=(200,)).json()

    def lookup(self, acct):
        """Public account (with statuses_count/following_count/…) by username."""
        return self.req("GET", "/api/v1/accounts/lookup", params={"acct": acct}, expect=(200,)).json()

    def relationships(self, acct_id):
        r = self.req("GET", "/api/v1/accounts/relationships", params={"id[]": acct_id}, expect=(200,))
        arr = r.json()
        return arr[0] if arr else {}

    def follow(self, acct_id):
        return self.req("POST", f"/api/v1/accounts/{acct_id}/follow", expect=(200,)).json()

    def post_status(self, text, visibility="unlisted"):
        return self.req("POST", "/api/v1/statuses",
                        data={"status": text, "visibility": visibility}, expect=(200,)).json()


# --- admin REST client (owner token; admin:read/admin:write) ----------------
class MastoAdmin(MastoApi):
    def account_by_username(self, username):
        r = self.req("GET", "/api/v1/admin/accounts", params={"username": username}, expect=(200,))
        for a in r.json():
            if a.get("username") == username:
                return a
        return None


# --- cookie/session web client (settings flows) -----------------------------
class MastoWeb:
    def __init__(self, base=APP_URL, timeout=60):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers.update(FWD)
        self.s.headers["User-Agent"] = "noshit-f1-mastodon/1.0 (web)"
        self.s.cookies.set_policy(_AllowSecureOverHTTP())

    def _desec(self):
        for c in self.s.cookies:
            c.secure = False

    def get(self, path_or_url, follow=True):
        url = path_or_url if path_or_url.startswith("http") else self.base + path_or_url
        r = self.s.get(url, timeout=self.timeout, allow_redirects=False)
        self._desec()
        while follow and r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            r = self.s.get(_to_local(r.headers["Location"]), timeout=self.timeout, allow_redirects=False)
            self._desec()
        return r

    def post(self, path, data):
        r = self.s.post(self.base + path, data=data, timeout=self.timeout, allow_redirects=False)
        self._desec()
        return r

    @staticmethod
    def csrf(text):
        m = re.search(r'name="authenticity_token"[^>]*value="([^"]+)"', text)
        if not m:
            m = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', text)
        return m.group(1) if m else None

    def login(self, email, password):
        r = self.get("/auth/sign_in", follow=False)
        tok = self.csrf(r.text)
        r = self.post("/auth/sign_in", {
            "authenticity_token": tok, "user[email]": email, "user[password]": password,
        })
        # 302 -> "/" on success
        if r.status_code != 302:
            raise MastoError(f"web login {email} -> {r.status_code} (expected 302)")
        return r


# --- health / readiness -----------------------------------------------------
def wait_healthy(base=APP_URL, timeout=180):
    """Poll Mastodon's public /health (200 'OK' over plain http) until ready."""
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            r = requests.get(base.rstrip("/") + "/health", timeout=5)
            if r.status_code == 200:
                return True
            last = f"status {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(2)
    raise TimeoutError(f"Mastodon not healthy at {base} within {timeout}s ({last})")


# --- seeding ----------------------------------------------------------------
def ensure_seed_accounts(password):
    """Create the seed accounts (idempotent) and mint their write tokens.
    Returns {username: {"token","id"}}."""
    created = 0
    for u in SEED_USERS:
        if tootctl_create(u, f"{u}@{EMAIL_DOMAIN}"):
            created += 1
    tokens = mint_tokens(SEED_USERS, password)
    missing = [u for u in SEED_USERS if u not in tokens]
    if missing:
        raise MastoError(f"failed to provision/mint tokens for {missing}")
    return created, tokens


def establish_follows(tokens):
    """Deterministic follow graph among seed accounts (idempotent)."""
    made = 0
    for follower, followees in FOLLOW_GRAPH.items():
        api = MastoApi(tokens[follower]["token"])
        for followee in followees:
            target_id = tokens[followee]["id"]
            rel = api.relationships(target_id)
            if rel.get("following"):
                continue
            api.follow(target_id)
            made += 1
    return made


def seed_statuses(tokens, target=STATUS_TARGET):
    """Post `target` statuses spread deterministically across the seed accounts,
    in one pass. Idempotent: if the accounts already hold >= target statuses in
    total, skip. Returns (posted, total_after, wall_seconds)."""
    apis = {u: MastoApi(tokens[u]["token"]) for u in SEED_USERS}
    existing = sum(apis[u].verify().get("statuses_count", 0) for u in SEED_USERS)
    if existing >= target:
        return 0, existing, 0.0
    to_post = target - existing
    t0 = time.monotonic()
    posted = 0
    i = 0
    while posted < to_post:
        u = SEED_USERS[i % len(SEED_USERS)]
        idx = existing + posted
        text = (f"F1 bench seed status #{idx:03d} by @{u} — deterministic bulk content "
                f"for the Mastodon nli★ leg (no study content).")
        try:
            apis[u].post_status(text)
            posted += 1
        except MastoError as e:
            if "429" in str(e):
                time.sleep(2)
                continue
            raise
        i += 1
    wall = time.monotonic() - t0
    total_after = sum(apis[u].verify().get("statuses_count", 0) for u in SEED_USERS)
    return posted, total_after, wall


def main():
    print(f"[seed] waiting for Mastodon at {APP_URL} ...", flush=True)
    wait_healthy(APP_URL)
    password = os.environ["MASTO_SEED_PASSWORD"]

    created, tokens = ensure_seed_accounts(password)
    print(f"[seed] seed accounts ready: {SEED_USERS} (created={created}, existing={len(SEED_USERS)-created})",
          flush=True)

    made = establish_follows(tokens)
    graph_desc = ", ".join(f"{k}->{','.join(v)}" for k, v in FOLLOW_GRAPH.items())
    print(f"[seed] follow graph: {graph_desc} (new edges this pass: {made})", flush=True)

    posted, total, wall = seed_statuses(tokens)
    if posted:
        print(f"[seed] statuses: posted={posted} in {wall:.2f}s "
              f"({posted/wall:.0f}/s), total now {total} across {len(SEED_USERS)} accounts",
              flush=True)
    else:
        print(f"[seed] statuses: {total} already present (>= target {STATUS_TARGET}); skipped (idempotent)",
              flush=True)

    # verify counts back via the API
    for u in SEED_USERS:
        acct = MastoApi(tokens[u]["token"]).verify()
        print(f"[seed]   @{u}: statuses={acct.get('statuses_count')} "
              f"following={acct.get('following_count')} followers={acct.get('followers_count')}",
              flush=True)
    print("[seed] done.", flush=True)


if __name__ == "__main__":
    main()
