#!/usr/bin/env python3
"""noshit-f1-plausible — API client + bootstrap + bulk EVENT seeding (build-plan §2.3).

Two roles:

  1. `PlausibleClient` — a stdlib HTTP client for Plausible CE v3.2.1's REAL
     surfaces (verified against the running image):
       * registration is a Phoenix LiveView (`phx-submit="register"`) — the
         form's non-JS `action="/login"` fallback does NOT create the user, so we
         drive the LiveView over its own websocket (a minimal Phoenix LV v2 client,
         `_LiveViewSocket`) to fire the `register` event that inserts the user +
         provisions the team, then complete login/activation over classic HTTP.
       * login (`POST /login`, register_action=login_form), site creation
         (`POST /sites`, classic controller: site[domain]/site[timezone]) and the
         authenticated dashboard JSON readback (`GET /api/stats/<domain>/top-stats`)
         are all classic HTTP.
       * event ingestion is the REAL tracking path: `POST /api/event` with a JSON
         body {name,url,domain,referrer} and User-Agent + X-Forwarded-For headers.
         The endpoint ALWAYS returns HTTP 202 — a dropped event is signalled by the
         `x-plausible-dropped` response header, which we check on every send.

  2. Seeding — bootstrap the founder (register + activate, idempotent) + a site,
     then fire >=500 events in ONE deterministic pass at POST /api/event, spread
     across a few virtual visitors / pages / referrers (header variation is DATA
     variation, not network reach — everything stays on loopback), and verify by
     reading the aggregates back until ClickHouse's buffered write flushes and the
     dashboard count CONVERGES to what we sent (the async-visibility caveat §2.3
     cares about).

The founder email + generated password + site domain are persisted to a 0600 state
file under the durable runtime dir (OUTSIDE the repo) so warm re-runs and demo.py
reuse them. `--reset` (demo.sh) wipes it with the datastores.

Stdlib only. Idempotent: seeding is delta-verified against the live pageview count.
"""
import base64
import http.cookiejar
import json
import os
import re
import secrets
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))  # shared mailsink.py
from mailsink import Mailsink                       # noqa: E402

# --- fixture constants (shared with demo.py) --------------------------------
APP_URL = os.environ.get("PLAUSIBLE_URL", "http://localhost:8085")
SINK_URL = os.environ.get("MAILSINK_URL", "http://localhost:8034")
STATE_PATH = os.environ.get(
    "PLAUSIBLE_STATE_PATH", "/home/user/fixture-runtime/plausible/seed-state.json")

FOUNDER_EMAIL = os.environ.get("PLAUSIBLE_FOUNDER_EMAIL", "founder@fixture.test")
FOUNDER_NAME = os.environ.get("PLAUSIBLE_FOUNDER_NAME", "F1 Bench Founder")
SITE_DOMAIN = os.environ.get("PLAUSIBLE_SITE_DOMAIN", "bench.fixture.test")
SITE_TZ = os.environ.get("PLAUSIBLE_SITE_TZ", "Etc/UTC")

# Bulk seed shape (>=500 events in one pass). Pageviews are the metric we assert
# readback equality on (custom events don't count as pageviews).
SEED_PAGEVIEWS = int(os.environ.get("SEED_PAGEVIEWS", "500"))
SEED_CUSTOM = int(os.environ.get("SEED_CUSTOM", "24"))
VISITORS = int(os.environ.get("SEED_VISITORS", "10"))   # distinct virtual visitors
PAGES = ["/", "/pricing", "/docs", "/blog/launch", "/about", "/features", "/contact", "/changelog"]
REFERRERS = ["", "https://news.ycombinator.com/", "https://twitter.com/",
             "https://duckduckgo.com/", "https://github.com/"]
# X-Forwarded-For per visitor: RFC 5737 documentation ranges (public, routable-
# looking; Plausible does not drop these — private/reserved IPs would be dropped).
UA_TEMPLATES = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/{n}.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1 Version/{n}.0 Safari/605.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/{n}.0",
]

PASSWORD_MIN = 12   # Plausible policy


class PlausibleError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Minimal Phoenix LiveView v2 websocket client — just enough to join the
# register LiveView and fire ONE form event. Client frames are masked per
# RFC6455; we read text frames and answer server pings.
# ---------------------------------------------------------------------------
class _LiveViewSocket:
    def __init__(self, host, port, path, cookie, origin, timeout=25):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
            f"Origin: {origin}\r\nCookie: {cookie}\r\n\r\n")
        self.sock.sendall(handshake.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise PlausibleError("websocket handshake: connection closed")
            buf += chunk
        status_line = buf.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise PlausibleError("websocket upgrade failed: " + status_line.decode(errors="replace"))
        self._tail = buf.split(b"\r\n\r\n", 1)[1]

    def _mask_send(self, opcode, payload):
        hdr = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126); hdr += n.to_bytes(2, "big")
        else:
            hdr.append(0x80 | 127); hdr += n.to_bytes(8, "big")
        mask = os.urandom(4)
        hdr += mask
        self.sock.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send(self, text):
        self._mask_send(0x1, text.encode())

    def _read(self, n):
        while len(self._tail) < n:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise PlausibleError("websocket: connection closed mid-frame")
            self._tail += chunk
        out, self._tail = self._tail[:n], self._tail[n:]
        return out

    def recv(self, timeout=20):
        self.sock.settimeout(timeout)
        while True:
            b0, b1 = self._read(2)
            opcode = b0 & 0x0F
            masked = b1 & 0x80
            ln = b1 & 0x7F
            if ln == 126:
                ln = int.from_bytes(self._read(2), "big")
            elif ln == 127:
                ln = int.from_bytes(self._read(8), "big")
            data = self._read(ln)
            if masked:
                m = data[:4]
                data = bytes(b ^ m[i % 4] for i, b in enumerate(data[4:]))
            if opcode == 0x1:      # text
                return data.decode("utf-8", "replace")
            if opcode == 0x9:      # ping -> pong
                self._mask_send(0xA, data); continue
            if opcode == 0x8:      # close
                raise PlausibleError("websocket closed by server")
            # 0xA pong / continuation: ignore and keep reading

    def close(self):
        try:
            self._mask_send(0x8, b"")
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not auto-follow redirects — we assert on the Location header."""
    def redirect_request(self, *a, **k):
        return None


class PlausibleClient:
    def __init__(self, app_url=APP_URL, timeout=30):
        self.app = app_url.rstrip("/")
        self.timeout = timeout
        self.cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj), _NoRedirect())
        host = urllib.parse.urlsplit(self.app)
        self.host = host.hostname
        self.port = host.port or 80

    # -- classic HTTP --------------------------------------------------------
    def _cookie_header(self):
        return "; ".join(f"{c.name}={c.value}" for c in self.cj)

    def get(self, path, accept="text/html"):
        req = urllib.request.Request(self.app + path, headers={"Accept": accept})
        try:
            r = self.op.open(req, timeout=self.timeout)
            return r.getcode(), r.read().decode("utf-8", "replace"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), e.headers

    def post(self, path, form):
        data = urllib.parse.urlencode(form).encode()
        req = urllib.request.Request(
            self.app + path, data=data, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            r = self.op.open(req, timeout=self.timeout)
            return r.getcode(), r.read().decode("utf-8", "replace"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), e.headers

    @staticmethod
    def _csrf(html):
        m = (re.search(r'name="_csrf_token"[^>]*value="([^"]+)"', html)
             or re.search(r'<meta name="csrf-token" content="([^"]+)"', html))
        if not m:
            raise PlausibleError("no _csrf_token in page")
        return m.group(1)

    # -- registration (LiveView over websocket) + activation (classic HTTP) --
    def register_and_activate(self, email, name, password, sink, timeout=40):
        """Full first-run round-trip: WS `register` event creates the user + team,
        classic POST /login logs in and triggers the activation-code email, we read
        the 4-digit code from the SINK, and POST /activate verifies. Returns the
        extracted activation code. Raises on any failure."""
        # 1) scrape the register LiveView connection tokens
        code, html, _ = self.get("/register")
        if code != 200:
            raise PlausibleError(f"GET /register -> HTTP {code}")
        meta = re.search(r'<meta name="csrf-token" content="([^"]+)"', html).group(1)
        sess = re.search(r'data-phx-session="([^"]+)"', html).group(1)
        stat = re.search(r'data-phx-static="([^"]+)"', html).group(1)
        cid = re.search(r'id="(phx-[^"]+)"', html).group(1)
        form_csrf = self._csrf(html)

        # 2) join the LiveView and fire the `register` event (creates the user)
        cp = sink.checkpoint(f"to:{email}")
        qs = urllib.parse.urlencode({"_csrf_token": meta, "vsn": "2.0.0"})
        ws = _LiveViewSocket(self.host, self.port, "/live/websocket?" + qs,
                             self._cookie_header(), self.app)
        try:
            topic = "lv:" + cid
            ws.send(json.dumps(["4", "1", topic, "phx_join", {
                "url": self.app + "/register",
                "params": {"_csrf_token": meta, "_mounts": 0},
                "session": sess, "static": stat}]))
            join = json.loads(ws.recv())
            if join[4].get("status") != "ok":
                raise PlausibleError(f"LiveView join failed: {json.dumps(join)[:200]}")
            form = urllib.parse.urlencode({
                "_csrf_token": form_csrf, "user[email]": email, "user[name]": name,
                "user[password]": password, "user[password_confirmation]": password,
                "user[register_action]": "register_form"})
            ws.send(json.dumps(["4", "2", topic, "event",
                                {"type": "form", "event": "register", "value": form}]))
            for _ in range(8):
                msg = json.loads(ws.recv())
                if msg[3] == "phx_reply" and msg[1] == "2":
                    if msg[4].get("status") != "ok":
                        raise PlausibleError(f"register event rejected: {json.dumps(msg)[:200]}")
                    break
        finally:
            ws.close()

        # 3) classic POST /login triggers session + activation-code email
        lc, _, lh = self.post("/login", {
            "_csrf_token": form_csrf, "user[email]": email, "user[name]": name,
            "user[password]": password, "user[password_confirmation]": password,
            "user[register_action]": "register_form"})
        loc = lh.get("Location", "")
        if lc != 302 or "/activate" not in loc:
            raise PlausibleError(f"POST /login after register -> {lc} loc={loc!r} "
                                 f"(user not created?)")

        # 4) read the activation code from the REAL email body in the sink
        msg = sink.wait_new(cp, timeout=timeout)
        full = sink.message(msg["ID"])
        subject = full.get("Subject") or ""
        blob = subject + "\n" + (full.get("Text") or "") + "\n" + (full.get("HTML") or "")
        m = (re.search(r'^\s*(\d{4})\b', subject)
             or re.search(r'\b(\d{4})\b', blob))
        if not m:
            raise PlausibleError(f"no 4-digit code in activation email (subject={subject!r})")
        act_code = m.group(1)

        # 5) POST /activate with the code -> verified
        _, act_html, _ = self.get("/activate")
        act_csrf = self._csrf(act_html) if "_csrf_token" in act_html else form_csrf
        ac, _, ah = self.post("/activate", {"_csrf_token": act_csrf, "code": act_code})
        if ac != 302:
            raise PlausibleError(f"POST /activate code={act_code} -> HTTP {ac}")
        return act_code

    def login(self, email, password):
        _, html, _ = self.get("/login")
        csrf = self._csrf(html)
        c, _, h = self.post("/login", {
            "_csrf_token": csrf, "user[email]": email, "user[password]": password,
            "user[register_action]": "login_form"})
        if c != 302:
            raise PlausibleError(f"POST /login -> HTTP {c} (bad credentials?)")
        return h.get("Location", "")

    # -- site creation (classic controller) ---------------------------------
    def create_site(self, domain, timezone=SITE_TZ):
        _, html, _ = self.get("/sites/new")
        csrf = self._csrf(html)
        c, _, h = self.post("/sites", {
            "_csrf_token": csrf, "site[domain]": domain, "site[timezone]": timezone})
        loc = h.get("Location", "")
        if c == 302 and (domain in loc or "installation" in loc):
            return True
        # already exists -> Plausible re-renders 200 with a changeset error
        if self.site_exists(domain):
            return True
        raise PlausibleError(f"POST /sites domain={domain} -> {c} loc={loc!r}")

    def site_exists(self, domain):
        c, _, _ = self.get(f"/{urllib.parse.quote(domain)}/settings/general")
        return c in (200, 302) and c != 404

    # -- ingestion: the REAL tracking path ----------------------------------
    def send_event(self, name, url, domain, referrer=None, user_agent="", xff=""):
        body = json.dumps({"name": name, "url": url, "domain": domain,
                           "referrer": referrer}).encode()
        req = urllib.request.Request(
            self.app + "/api/event", data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": user_agent or "Mozilla/5.0 (fixture)",
                     "X-Forwarded-For": xff or "203.0.113.1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                dropped = r.headers.get("x-plausible-dropped")
                return r.status, dropped
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("x-plausible-dropped")

    def wait_ingest_ready(self, domain, timeout=90, poll=1.0):
        """A just-created site is NOT immediately ingestible: Plausible serves
        ingestion from an in-memory `sites_by_domain` cache that refreshes on an
        interval, so events for the new domain are DROPPED (`x-plausible-dropped`)
        until the cache picks it up (~cache-refresh interval, observed ~25-30s).
        Poll with CUSTOM `cache_probe` events (they do NOT count as pageviews, so
        the readback stays exact) until one is accepted. Returns seconds waited.
        This is the ingestion-side async-visibility caveat (distinct from the
        ClickHouse buffered readback below) — an EVENT anchor, not a timer."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            st, dropped = self.send_event(
                "cache_probe", f"http://{domain}/", domain,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0 Safari/537.36",
                xff="9.9.9.9")
            if st == 202 and not dropped:
                return time.monotonic() - t0
            time.sleep(poll)
        raise PlausibleError(
            f"site {domain} never became ingestible within {timeout}s "
            f"(events kept returning x-plausible-dropped)")

    # -- authenticated dashboard JSON readback (ungated) --------------------
    def top_stats(self, domain, period="day"):
        path = f"/api/stats/{urllib.parse.quote(domain)}/top-stats/?period={period}"
        c, body, _ = self.get(path, accept="application/json")
        if c != 200:
            raise PlausibleError(f"top-stats {domain} -> HTTP {c}: {body[:160]}")
        data = json.loads(body)
        return {t["name"]: t["value"] for t in data.get("top_stats", [])}

    def pageviews(self, domain, period="day"):
        return int(self.top_stats(domain, period).get("Total pageviews", 0) or 0)

    def visitors(self, domain, period="day"):
        return int(self.top_stats(domain, period).get("Unique visitors", 0) or 0)


# --- health / state ---------------------------------------------------------
def wait_healthy(app_url=APP_URL, timeout=420, need_consecutive=2):
    """Poll the unauthenticated /api/health until 200 `need_consecutive` times.
    First boot runs migrations + a full cache warm before the HTTP endpoint
    accepts connections, so the timeout is generous."""
    deadline = time.monotonic() + timeout
    ok = 0
    last = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(app_url.rstrip("/") + "/api/health", timeout=5) as r:
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
    raise TimeoutError(f"Plausible not healthy at {app_url}/api/health within {timeout}s ({last})")


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, STATE_PATH)


def gen_password():
    # Guarantees upper+lower+digit+symbol and length >= PASSWORD_MIN.
    return "Fx1!" + secrets.token_urlsafe(16)


def ensure_founder(client, sink):
    """Ensure the founder exists + is activated; return (email, state). Fresh DB ->
    full register+activate round-trip; warm -> login with saved credentials."""
    state = load_state()
    if state.get("email") and state.get("password"):
        try:
            client.login(state["email"], state["password"])
            print(f"[seed] warm start: logged in as {state['email']}", flush=True)
            return state["email"], state
        except PlausibleError:
            print("[seed] saved credentials stale; re-bootstrapping founder", flush=True)

    password = gen_password()
    print(f"[seed] fresh instance: registering founder {FOUNDER_EMAIL} "
          f"(LiveView WS register -> activation-code round-trip) ...", flush=True)
    code = client.register_and_activate(FOUNDER_EMAIL, FOUNDER_NAME, password, sink)
    state = {"email": FOUNDER_EMAIL, "password": password, "domain": SITE_DOMAIN}
    save_state(state)
    print(f"[seed] founder registered + activated (code round-trip ok, code={code})", flush=True)
    return FOUNDER_EMAIL, state


def ensure_site(client, domain=SITE_DOMAIN):
    if client.site_exists(domain):
        print(f"[seed] site {domain} already exists", flush=True)
        return domain
    client.create_site(domain, SITE_TZ)
    print(f"[seed] created site {domain} (POST /sites, classic HTTP)", flush=True)
    return domain


# --- bulk event seeding (§2.3) ----------------------------------------------
def build_event_plan(pageviews=SEED_PAGEVIEWS, custom=SEED_CUSTOM, domain=SITE_DOMAIN):
    """Deterministic plan: `pageviews` pageview events + `custom` custom events,
    spread across VISITORS virtual visitors, PAGES paths and REFERRERS sources.
    Each virtual visitor = a distinct (User-Agent, X-Forwarded-For) pair."""
    plan = []
    for i in range(pageviews):
        v = i % VISITORS
        ua = UA_TEMPLATES[v % len(UA_TEMPLATES)].format(n=100 + v)
        xff = f"203.0.113.{v + 1}"
        page = PAGES[i % len(PAGES)]
        ref = REFERRERS[i % len(REFERRERS)]
        plan.append(("pageview", f"http://{domain}{page}", ref or None, ua, xff))
    for j in range(custom):
        v = j % VISITORS
        ua = UA_TEMPLATES[v % len(UA_TEMPLATES)].format(n=100 + v)
        xff = f"203.0.113.{v + 1}"
        name = ("Signup", "Download", "Purchase")[j % 3]
        plan.append((name, f"http://{domain}/", None, ua, xff))
    return plan


def seed_events(client, domain, sink=None, pageviews=SEED_PAGEVIEWS, custom=SEED_CUSTOM,
                converge_timeout=120):
    """Fire the plan in ONE pass at POST /api/event, then poll the dashboard until
    the pageview count CONVERGES (ClickHouse buffered-write visibility). Delta-based
    so warm re-runs (accumulating events) stay correct. Returns a stats dict."""
    # Ingestion-side async visibility: wait for the freshly-created site to enter
    # Plausible's ingestion cache BEFORE the bulk pass (else every event drops).
    ingest_ready = client.wait_ingest_ready(domain)
    baseline_pv = client.pageviews(domain)
    baseline_vis = client.visitors(domain)
    plan = build_event_plan(pageviews, custom, domain)

    t0 = time.monotonic()
    accepted = dropped = 0
    for name, url, ref, ua, xff in plan:
        st, drop = client.send_event(name, url, domain, ref, ua, xff)
        if st == 202 and not drop:
            accepted += 1
        else:
            dropped += 1
    send_wall = time.monotonic() - t0
    pv_sent = sum(1 for e in plan if e[0] == "pageview")

    # Convergence poll: the /api/event 202 is buffered — ClickHouse visibility is
    # ASYNC. Wait for the dashboard pageview count to reach baseline + pv_sent.
    target = baseline_pv + pv_sent
    t_conv0 = time.monotonic()
    converged_at = None
    seen = baseline_pv
    while time.monotonic() - t_conv0 < converge_timeout:
        seen = client.pageviews(domain)
        if seen >= target:
            converged_at = time.monotonic() - t_conv0
            break
        time.sleep(1)
    final_pv = client.pageviews(domain)
    final_vis = client.visitors(domain)

    return {
        "total_events": len(plan), "pageviews_sent": pv_sent, "custom_sent": custom,
        "accepted": accepted, "dropped": dropped, "send_wall": send_wall,
        "rate": len(plan) / send_wall if send_wall else 0.0,
        "baseline_pv": baseline_pv, "target_pv": target, "ingest_ready_secs": ingest_ready,
        "final_pv": final_pv, "final_vis": final_vis, "baseline_vis": baseline_vis,
        "converged": converged_at is not None, "converge_secs": converged_at,
    }


def main():
    client = PlausibleClient()
    sink = Mailsink(SINK_URL)
    print(f"[seed] waiting for Plausible at {APP_URL} ...", flush=True)
    wait_healthy(APP_URL)

    email, state = ensure_founder(client, sink)
    domain = ensure_site(client, state.get("domain", SITE_DOMAIN))

    print(f"[seed] bulk pass: firing {SEED_PAGEVIEWS} pageviews + {SEED_CUSTOM} custom "
          f"events at POST /api/event ...", flush=True)
    r = seed_events(client, domain, sink)
    print(f"[seed] ingestion-cache readiness: site became ingestible "
          f"~{r['ingest_ready_secs']:.1f}s after creation (events dropped until then)",
          flush=True)
    print(f"[seed] SENT {r['total_events']} events ({r['pageviews_sent']} pageviews) in "
          f"{r['send_wall']:.2f}s ({r['rate']:.0f} events/s); accepted={r['accepted']} "
          f"dropped={r['dropped']}", flush=True)
    if r["converged"]:
        print(f"[seed] ClickHouse buffered-visibility: dashboard pageviews converged "
              f"{r['baseline_pv']} -> {r['final_pv']} (+{r['pageviews_sent']}) in "
              f"~{r['converge_secs']:.1f}s after the send pass", flush=True)
    else:
        print(f"[seed] WARN: pageviews did not converge to {r['target_pv']} "
              f"(saw {r['final_pv']}) within the window", flush=True)

    if r["dropped"] > 0:
        raise PlausibleError(f"{r['dropped']} events were dropped (x-plausible-dropped)")
    if r["final_pv"] < r["target_pv"]:
        raise PlausibleError(
            f"readback FAILED: dashboard pageviews {r['final_pv']} < expected {r['target_pv']}")
    print(f"[seed] readback verified: dashboard Total pageviews={r['final_pv']} "
          f"(>= baseline {r['baseline_pv']} + {r['pageviews_sent']} sent), "
          f"Unique visitors={r['final_vis']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (PlausibleError, TimeoutError, AssertionError) as e:
        print(f"[seed] FAIL: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
