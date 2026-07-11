#!/usr/bin/env python3
"""noshit-f1-listmonk — API client + seeding (build-plan §2.3 bulk content).

Two roles:

  1. `ListmonkAdmin` — a stdlib HTTP client for listmonk v6's real API. Auth in
     v6 is session-cookie or API-token only (legacy BasicAuth-with-admin was
     removed in v4); this client logs in as the auto-created Super Admin at
     POST /admin/login, carries the `session` cookie, and re-logs-in on 403
     (the session survives listmonk's settings-save reload, but re-login is
     cheap insurance). API responses are wrapped in {"data": ...}.

  2. Seeding — point listmonk's DB-backed SMTP settings at the mailpit sink,
     create the fixture list, and register >=200 subscribers in one
     deterministic pass (member-NNN@fixture.test), recording wall-time.

Run standalone to (re)seed against a running stack:

    LISTMONK_ADMIN_USER=admin LISTMONK_ADMIN_PASSWORD=... python3 seed.py

Idempotent: existing subscribers are skipped, settings are converged.
Stdlib only.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --- fixture constants (shared with demo.py) --------------------------------
APP_URL = os.environ.get("LISTMONK_URL", "http://localhost:9002")
SINK_URL = os.environ.get("MAILSINK_URL", "http://localhost:8029")
MAIN_LIST = "F1 Fixture List"
OPTIN_LIST = "F1 Opt-in List"
SUB_PREFIX = "member"
SUB_DOMAIN = "fixture.test"
SUB_COUNT = int(os.environ.get("SUB_COUNT", "200"))
SMTP_HOST = "mailpit"      # in-network mailpit hostname
SMTP_PORT = 1025


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Don't auto-follow 3xx — we need to capture Set-Cookie off the login 302."""

    def redirect_request(self, *args, **kwargs):
        return None


class ListmonkAdmin:
    def __init__(self, base=APP_URL, username=None, password=None, timeout=30):
        self.base = base.rstrip("/")
        self.username = username or os.environ["LISTMONK_ADMIN_USER"]
        self.password = password or os.environ["LISTMONK_ADMIN_PASSWORD"]
        self.timeout = timeout
        self.cookies = {}
        self.opener = urllib.request.build_opener(_NoRedirect)

    # -- low level -----------------------------------------------------------
    def _store_cookies(self, headers):
        for sc in headers.get_all("Set-Cookie", []) or []:
            first = sc.split(";", 1)[0].strip()
            if "=" not in first:
                continue
            name, val = first.split("=", 1)
            if val in ("", "deleted"):
                self.cookies.pop(name, None)
            else:
                self.cookies[name] = val

    def _raw(self, method, path, json_body=None, form=None, tries=3):
        url = self.base + path
        data, hdrs = None, {"Accept": "application/json"}
        if self.cookies:
            hdrs["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if json_body is not None:
            data = json.dumps(json_body).encode()
            hdrs["Content-Type"] = "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        # Retry transient connection resets (e.g. the brief HTTP-server bounce a
        # settings-save reload causes). HTTPError is a real response -> returned,
        # not retried. Requests here are idempotent by unique key server-side.
        for attempt in range(tries):
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
            try:
                with self.opener.open(req, timeout=self.timeout) as r:
                    self._store_cookies(r.headers)
                    return r.status, r.read().decode()
            except urllib.error.HTTPError as e:
                self._store_cookies(e.headers)
                return e.code, e.read().decode()
            except OSError:
                if attempt == tries - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def req(self, method, path, json_body=None, form=None, _retry=True):
        """Authenticated request that returns (status, parsed-data-or-text).
        Re-logs-in once on 403 (e.g. if the session was dropped by a reload)."""
        st, body = self._raw(method, path, json_body=json_body, form=form)
        if st == 403 and _retry and path != "/admin/login":
            self.login()
            return self.req(method, path, json_body=json_body, form=form, _retry=False)
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            return st, body
        if isinstance(parsed, dict) and "data" in parsed:
            return st, parsed["data"]
        return st, parsed

    # -- auth ----------------------------------------------------------------
    def login(self):
        st, _ = self._raw(
            "POST", "/admin/login",
            form={"username": self.username, "password": self.password, "next": "/admin/"},
        )
        if "session" not in self.cookies:
            raise RuntimeError(f"login failed (HTTP {st}): no session cookie set")
        return st

    # -- settings ------------------------------------------------------------
    def get_settings(self):
        return self.req("GET", "/api/settings")

    def put_settings(self, obj):
        return self.req("PUT", "/api/settings", json_body=obj)

    # -- lists / subscribers / campaigns -------------------------------------
    def get_lists(self):
        st, data = self.req("GET", "/api/lists?per_page=100")
        results = (data or {}).get("results", []) if isinstance(data, dict) else (data or [])
        return st, results

    def create_list(self, name, ltype="public", optin="single", description=""):
        return self.req("POST", "/api/lists", json_body={
            "name": name, "type": ltype, "optin": optin,
            "tags": ["f1-fixture"], "description": description,
        })

    def get_list(self, list_id):
        return self.req("GET", f"/api/lists/{list_id}")

    def create_subscriber(self, email, name, list_ids, preconfirm=True):
        return self.req("POST", "/api/subscribers", json_body={
            "email": email, "name": name, "status": "enabled",
            "lists": list_ids, "preconfirm_subscriptions": preconfirm,
        })

    def get_subscriber(self, sub_id):
        return self.req("GET", f"/api/subscribers/{sub_id}")

    def query_subscribers(self, list_id, subscription_status=None, per_page=1):
        q = {"list_id": list_id, "per_page": per_page}
        if subscription_status:
            q["subscription_status"] = subscription_status
        st, data = self.req("GET", "/api/subscribers?" + urllib.parse.urlencode(q))
        results = (data or {}).get("results", []) if isinstance(data, dict) else []
        total = (data or {}).get("total", 0) if isinstance(data, dict) else 0
        return st, results, total

    def create_campaign(self, name, subject, list_ids, body_html,
                        from_email, template_id=None, content_type="html"):
        payload = {
            "name": name, "subject": subject, "lists": list_ids,
            "type": "regular", "content_type": content_type,
            "body": body_html, "from_email": from_email, "messenger": "email",
        }
        if template_id:
            payload["template_id"] = template_id
        return self.req("POST", "/api/campaigns", json_body=payload)

    def start_campaign(self, camp_id):
        return self.req("PUT", f"/api/campaigns/{camp_id}/status",
                        json_body={"status": "running"})

    def get_campaign(self, camp_id):
        return self.req("GET", f"/api/campaigns/{camp_id}")

    def get_default_template_id(self):
        st, data = self.req("GET", "/api/templates")
        results = (data or {}).get("results", []) if isinstance(data, dict) else data
        for t in results or []:
            if t.get("is_default") and t.get("type", "campaign") == "campaign":
                return t["id"]
        # fall back to the first campaign-type template
        for t in results or []:
            if t.get("type", "campaign") == "campaign":
                return t["id"]
        return None


# --- health / settings-apply waits ------------------------------------------
def wait_healthy(base=APP_URL, timeout=120, need_consecutive=1):
    """Poll the unauthenticated /health until it returns 200 `need_consecutive`
    times in a row (event-based readiness, not a fixed sleep). NB: /api/health
    requires auth in listmonk v6 — /health is the public one."""
    deadline = time.monotonic() + timeout
    ok = 0
    last = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base.rstrip("/") + "/health", timeout=5) as r:
                if r.status == 200:
                    ok += 1
                    if ok >= need_consecutive:
                        return True
                    time.sleep(0.5)
                    continue
        except (urllib.error.URLError, OSError) as e:
            last = str(e)
            ok = 0
        time.sleep(1)
    raise TimeoutError(f"listmonk not healthy at {base} within {timeout}s ({last})")


def configure_messaging(admin, root_url, smtp_host=SMTP_HOST, smtp_port=SMTP_PORT):
    """Point listmonk's DB-backed SMTP at the mailpit sink and fix root_url so
    {{ UnsubscribeURL }} resolves to a host-reachable URL. Saving settings makes
    listmonk reload; we wait until it comes back reporting the new root_url."""
    st, settings = admin.get_settings()
    if st != 200 or not isinstance(settings, dict):
        raise RuntimeError(f"GET /api/settings -> {st}: {str(settings)[:160]}")

    # Idempotent: if already pointed at the sink with the right root_url, don't
    # PUT (a settings save triggers a reload we'd otherwise pay for every run).
    smtp_cur = settings.get("smtp") or []
    if (settings.get("app.root_url") == root_url
            and any(s.get("enabled") and s.get("host") == smtp_host for s in smtp_cur)):
        return True

    settings["app.root_url"] = root_url
    # Crank the sender for a deterministic, fast fixture delivery (the default
    # message_rate of 10/s would stretch a 200-recipient campaign to ~20s).
    settings["app.message_rate"] = 1000
    settings["app.concurrency"] = 10
    settings["app.batch_size"] = 1000
    settings["smtp"] = [{
        "name": "mailpit",
        "enabled": True,
        "host": smtp_host,
        "port": int(smtp_port),
        "hello_hostname": "",
        "auth_protocol": "none",
        "username": "",
        "password": "",
        "email_headers": [],
        "max_conns": 10,
        "max_msg_retries": 2,
        "msg_retry_delay": "1s",
        "idle_timeout": "15s",
        "wait_timeout": "5s",
        "tls_type": "none",
        "tls_skip_verify": True,
        "from_addresses": [],
    }]

    try:
        admin.put_settings(settings)
    except OSError:
        pass  # the reload can reset the PUT connection; the waits below are authoritative

    # A settings save schedules a reload ~500ms later that bounces the HTTP
    # server. Wait PAST that bounce, then require health to be stably up (several
    # consecutive OKs) so the reloaded process is serving before we proceed —
    # otherwise later requests race the bounce and get connection-reset.
    time.sleep(1.5)
    wait_healthy(admin.base, timeout=90, need_consecutive=3)

    # Confirm the new setting is live on the reloaded process.
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            gst, cur = admin.get_settings()
            if gst == 200 and isinstance(cur, dict) and cur.get("app.root_url") == root_url:
                return True
        except OSError:
            pass
        time.sleep(1.0)
    raise TimeoutError(f"settings did not converge (root_url={root_url}) within window")


def ensure_list(admin, name, optin="single", ltype="public", description=""):
    st, lists = admin.get_lists()
    for l in lists or []:
        if l.get("name") == name:
            return l
    st, data = admin.create_list(name, ltype, optin, description)
    if st not in (200, 201) or not isinstance(data, dict):
        raise RuntimeError(f"create list {name!r} -> {st}: {str(data)[:160]}")
    return data


def seed_subscribers(admin, list_id, count=SUB_COUNT, prefix=SUB_PREFIX,
                     domain=SUB_DOMAIN, preconfirm=True):
    """Register `count` subscribers in one deterministic pass. Returns
    (created, existing, wall_seconds). Idempotent — duplicates are skipped."""
    created = existing = 0
    t0 = time.monotonic()
    for i in range(1, count + 1):
        email = f"{prefix}-{i:03d}@{domain}"
        name = f"Member {i:03d}"
        st, body = admin.create_subscriber(email, name, [list_id], preconfirm)
        text = json.dumps(body) if not isinstance(body, str) else body
        if st in (200, 201):
            created += 1
        elif st == 409 or "exist" in text.lower() or "conflict" in text.lower():
            existing += 1
        else:
            raise RuntimeError(f"create subscriber {email} -> {st}: {text[:160]}")
    return created, existing, time.monotonic() - t0


def main():
    admin = ListmonkAdmin()
    print(f"[seed] waiting for listmonk at {APP_URL} ...", flush=True)
    wait_healthy(APP_URL, timeout=120)
    admin.login()
    print("[seed] logged in as Super Admin", flush=True)

    print(f"[seed] pointing SMTP at {SMTP_HOST}:{SMTP_PORT}, root_url={APP_URL} ...", flush=True)
    configure_messaging(admin, APP_URL)
    print("[seed] messaging configured (settings reload converged)", flush=True)

    lst = ensure_list(admin, MAIN_LIST, optin="single")
    print(f"[seed] list ready: {MAIN_LIST!r} id={lst['id']} uuid={lst['uuid']}", flush=True)

    created, existing, wall = seed_subscribers(admin, lst["id"], SUB_COUNT)
    print(f"[seed] subscribers: created={created} existing={existing} "
          f"total={created + existing} in {wall:.2f}s "
          f"({(created + existing) / wall:.0f}/s)", flush=True)

    st, l2 = admin.get_list(lst["id"])
    print(f"[seed] list now holds subscriber_count={l2.get('subscriber_count')} "
          f"statuses={l2.get('subscriber_statuses')}", flush=True)


if __name__ == "__main__":
    main()
