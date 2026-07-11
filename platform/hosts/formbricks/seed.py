#!/usr/bin/env python3
"""noshit-f1-formbricks — bootstrap + churn-survey seeding (build-plan §2.3 bulk content).

Two roles:

  1. `FormbricksClient` — a stdlib HTTP client for Formbricks v3.16.1's real
     surfaces: the createUser SERVER ACTION (signup over plain HTTP), the
     management REST API (x-api-key), and the public client REST API (displays +
     responses — the endpoints the survey widget itself uses).

  2. Seeding — bootstrap the first user + organization + environment, mint a
     management API key headlessly, create ONE link survey with a CHURN /
     cancellation shape (a required multiple-choice "why are you leaving?" plus an
     optional open-text follow-up), then submit >=100 responses in one
     deterministic pass through the public display->response API, and verify the
     count back via the management API.

FORMBRICKS REALITY (verified against the pinned image — see README deviations):
  * Signup is a Next.js SERVER ACTION, not a REST endpoint. It is driven over
    plain HTTP with a `Next-Action` header + a React-reply multipart body
    (field "0" = the single input object). The action id is deterministic for
    the digest-pinned image. createUser creates ONLY a User row (+ sends a
    verification email); it does NOT create the org/environment.
  * API keys are UI-only in Formbricks (no CLI / seed mint). The documented
    headless path is a direct row insert into "ApiKey" + "ApiKeyEnvironment":
    hashedKey = sha256_hex(key) (verified: an x-api-key with that hash
    authenticates the management API). Org/project/environment are likewise
    inserted directly (their DDL is simple; only Organization.billing needs a
    real JSON shape).
  * The public client API path segment is the ENVIRONMENT id.

Stdlib only. Idempotent: bootstrap is gated on the founder's existence; response
seeding is gated on the live response count.
"""
import hashlib
import json
import os
import re
import secrets
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --- fixture constants (shared with demo.py) --------------------------------
APP_URL = os.environ.get("FORMBRICKS_URL", "http://localhost:3003")
SINK_URL = os.environ.get("MAILSINK_URL", "http://localhost:8033")
PROJECT = os.environ.get("COMPOSE_PROJECT", "noshit-f1-formbricks")

FOUNDER_EMAIL = os.environ.get("FB_FOUNDER_EMAIL", "founder@fixture.test")
FOUNDER_PASSWORD = os.environ.get("FB_FOUNDER_PASSWORD", "")  # generated if empty
TARGET_RESPONSES = int(os.environ.get("SEED_RESPONSES", "120"))
STATE_PATH = os.environ.get(
    "FB_STATE_PATH", "/home/user/fixture-runtime/formbricks/seed-state.json")

# createUser server-action id — deterministic for the digest-pinned CE image.
CREATE_USER_ACTION = os.environ.get(
    "FB_CREATE_USER_ACTION", "7fdd8b958ae50176531ae8bcb1ea54ba27a8a28332")

# The churn / cancellation survey shape (the exit-survey pattern ndp/nst exercise).
CHURN_REASONS = [
    "Too expensive",
    "Missing features I need",
    "Switched to a competitor",
    "No longer needed",
    "Poor support experience",
]
FEEDBACK_SNIPPETS = [
    "Price increase pushed us over budget.",
    "Needed deeper integrations than were available.",
    "A competitor offered a better plan.",
    "Our project wrapped up, so we no longer need it.",
    "Support took too long to respond.",
    "",  # some responses leave the optional field blank
]


class FormbricksError(RuntimeError):
    pass


def gen_password():
    # upper+lower+digit+symbol, length >= 20 (satisfies common signup policies).
    return "Fx1!" + secrets.token_urlsafe(18)


def cuid():
    """A lowercase-alphanumeric id that satisfies Formbricks' cuid/cuid2 checks."""
    return "c" + "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(24))


# --- Postgres access (headless api-key mint + org/env bootstrap) -------------
def psql(sql, want_output=True):
    """Run SQL by piping it to psql over stdin (no inner -c "..." so JSON/quotes
    survive the sg-docker shell nesting)."""
    cmd = (f"docker compose -p {PROJECT} exec -T db "
           f"psql -U postgres -d formbricks -v ON_ERROR_STOP=1 -t -A")
    out = subprocess.run(["sg", "docker", "-c", cmd], input=sql,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise FormbricksError(f"psql failed: {out.stderr.strip()}\nSQL: {sql[:200]}")
    return out.stdout.strip()


class FormbricksClient:
    def __init__(self, app_url=APP_URL, timeout=60):
        self.app = app_url.rstrip("/")
        self.timeout = timeout

    # -- low-level HTTP ------------------------------------------------------
    def _req(self, method, path, body=None, headers=None, form=False):
        if body is None:
            data = None
        elif form:
            data = urllib.parse.urlencode(body).encode()
        else:
            data = json.dumps(body).encode()
        h = {}
        if data is not None and not form:
            h["Content-Type"] = "application/json"
        if data is not None and form:
            h["Content-Type"] = "application/x-www-form-urlencoded"
        if headers:
            h.update(headers)
        req = urllib.request.Request(self.app + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode(errors="replace")
                try:
                    return r.status, json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    return r.status, raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw

    # -- signup (Next.js server action over plain HTTP) ----------------------
    def create_user(self, name, email, password):
        """Register a user via the createUser server action. Returns True on
        {"success":true}. Sends a verification email as a side effect."""
        boundary = "----fb" + secrets.token_hex(8)
        payload = json.dumps([{"name": name, "email": email, "password": password}])
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="0"\r\n\r\n'
                f"{payload}\r\n--{boundary}--\r\n").encode()
        req = urllib.request.Request(self.app + "/setup/signup", data=body, method="POST",
                                     headers={
                                         "Next-Action": CREATE_USER_ACTION,
                                         "Content-Type": f"multipart/form-data; boundary={boundary}",
                                         "Accept": "text/x-component",
                                     })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                txt = r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="replace")
        if '"success":true' in txt:
            return True
        raise FormbricksError(f"createUser({email}) did not succeed: {txt[:160]}")

    # -- NextAuth credentials login (plain HTTP) -----------------------------
    def login(self, email, password):
        """getLoginTokenFromCredentials over NextAuth. Returns an opener with the
        session cookie set, or raises. Login is gated on email_verified, so a
        successful login proves an active/verified account."""
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        csrf = json.load(op.open(self.app + "/api/auth/csrf", timeout=self.timeout))["csrfToken"]
        data = urllib.parse.urlencode({
            "csrfToken": csrf, "email": email, "password": password,
            "callbackUrl": self.app, "json": "true"}).encode()
        req = urllib.request.Request(self.app + "/api/auth/callback/credentials", data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        op.open(req, timeout=self.timeout)
        sess = json.load(op.open(self.app + "/api/auth/session", timeout=self.timeout))
        if not (sess.get("user") or {}).get("id"):
            raise FormbricksError(f"login failed for {email}: no session user")
        return op, sess

    # -- management API (x-api-key) ------------------------------------------
    def me(self, api_key):
        return self._req("GET", "/api/v1/management/me", headers={"x-api-key": api_key})

    def create_survey(self, api_key, survey):
        return self._req("POST", "/api/v1/management/surveys", body=survey,
                         headers={"x-api-key": api_key})

    def list_surveys(self, api_key):
        return self._req("GET", "/api/v1/management/surveys", headers={"x-api-key": api_key})

    def response_count(self, api_key, survey_id):
        """Total responses for a survey via the management API (page through)."""
        total, skip = 0, 0
        while True:
            st, body = self._req(
                "GET", f"/api/v1/management/responses?surveyId={survey_id}&limit=100&skip={skip}",
                headers={"x-api-key": api_key})
            rows = body.get("data", []) if isinstance(body, dict) else []
            total += len(rows)
            if len(rows) < 100:
                break
            skip += 100
        return total

    # -- public client API (the endpoints the survey widget uses) ------------
    def create_display(self, env_id, survey_id):
        return self._req("POST", f"/api/v1/client/{env_id}/displays",
                         body={"surveyId": survey_id})

    def create_response(self, env_id, survey_id, data, display_id=None, finished=True):
        body = {"surveyId": survey_id, "finished": finished, "data": data}
        if display_id:
            body["displayId"] = display_id
        return self._req("POST", f"/api/v1/client/{env_id}/responses", body=body)


# --- health / state ----------------------------------------------------------
def wait_healthy(app_url=APP_URL, timeout=240, need_consecutive=2):
    deadline = time.monotonic() + timeout
    ok, last = 0, ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(app_url.rstrip("/") + "/health", timeout=5) as r:
                if r.status == 200:
                    ok += 1
                    if ok >= need_consecutive:
                        return True
                    time.sleep(0.5)
                    continue
        except (urllib.error.URLError, OSError) as e:
            last, ok = str(e), 0
        time.sleep(1)
    raise TimeoutError(f"Formbricks not healthy at {app_url}/health within {timeout}s ({last})")


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


# --- bootstrap ---------------------------------------------------------------
def founder_exists(email):
    n = psql(f"SELECT count(*) FROM \"User\" WHERE email='{email}';")
    return n not in ("", "0")


def bootstrap(client):
    """Ensure founder + org + project + prod/dev environments + api key + survey.
    Fresh DB -> real createUser signup (emits a verification email) + DB-insert of
    the org/environment/api-key. Warm -> reuse saved state. Idempotent."""
    state = load_state()

    if founder_exists(FOUNDER_EMAIL) and state.get("api_key") and state.get("survey_id"):
        print(f"[seed] warm start: founder + api key + survey present (env={state.get('prod_env_id')})", flush=True)
        return state

    password = state.get("founder_password") or FOUNDER_PASSWORD or gen_password()

    if not founder_exists(FOUNDER_EMAIL):
        print("[seed] fresh instance: registering founder via createUser (real signup + verification mail) ...", flush=True)
        client.create_user("F1 Bench Founder", FOUNDER_EMAIL, password)
        # The founder is a real signup; mark verified so it is usable as the org
        # owner (the emailed-token consumer is a client-side server action — see
        # README deviation #4; demo.py exercises the verification MAIL round-trip
        # on a separate fresh user).
        psql(f"UPDATE \"User\" SET \"email_verified\"=now() WHERE email='{FOUNDER_EMAIL}';")

    uid = psql(f"SELECT id FROM \"User\" WHERE email='{FOUNDER_EMAIL}';")

    # Org / project / prod+dev environments (created directly — createUser makes
    # only the User row; the org-creation step is itself a server action).
    org = state.get("org_id") or cuid()
    proj = state.get("project_id") or cuid()
    envp = state.get("prod_env_id") or cuid()
    envd = state.get("dev_env_id") or cuid()
    have_org = psql(f"SELECT count(*) FROM \"Organization\" WHERE id='{org}';") not in ("", "0")
    if not have_org:
        billing = ('{"plan":"free","period":"monthly","limits":'
                   '{"projects":3,"monthly":{"responses":1500,"miu":2000}},'
                   '"periodStart":"2026-07-11T00:00:00.000Z","stripeCustomerId":null}')
        psql(f'''INSERT INTO "Organization"(id,"updated_at",name,billing) VALUES('{org}',now(),'F1 Bench Org','{billing}'::jsonb);''')
        psql(f'''INSERT INTO "Project"(id,"updated_at",name,"organizationId") VALUES('{proj}',now(),'F1 Bench Project','{org}');''')
        psql(f'''INSERT INTO "Environment"(id,"updated_at",type,"projectId","appSetupCompleted") VALUES('{envp}',now(),'production','{proj}',true),('{envd}',now(),'development','{proj}',false);''')
        psql(f'''INSERT INTO "Membership"("organizationId","userId",accepted,role) VALUES('{org}','{uid}',true,'owner') ON CONFLICT DO NOTHING;''')
        print(f"[seed] org/project/environments created (prod env={envp})", flush=True)

    # API key (headless mint via direct insert; hashedKey = sha256_hex(key)).
    api_key = state.get("api_key")
    if not api_key:
        api_key = "fbk_" + secrets.token_hex(20)
        hashed = hashlib.sha256(api_key.encode()).hexdigest()
        akid = cuid()
        psql(f'''INSERT INTO "ApiKey"(id,label,"hashedKey","organizationId","organizationAccess") VALUES('{akid}','f1-seed-key','{hashed}','{org}','{{}}'::jsonb);''')
        psql(f'''INSERT INTO "ApiKeyEnvironment"(id,"updatedAt","apiKeyId","environmentId",permission) VALUES('{cuid()}',now(),'{akid}','{envp}','manage');''')
        st, me = client.me(api_key)
        if st != 200:
            raise FormbricksError(f"minted api key did not authenticate: HTTP {st} {str(me)[:120]}")
        print("[seed] management API key minted (sha256) + verified via /management/me", flush=True)

    state.update({
        "founder_email": FOUNDER_EMAIL, "founder_password": password,
        "org_id": org, "project_id": proj, "prod_env_id": envp, "dev_env_id": envd,
        "api_key": api_key,
    })
    save_state(state)
    return state


# --- churn survey ------------------------------------------------------------
def churn_survey_payload(env_id):
    return {
        "name": "Cancellation / Churn Survey",
        "type": "link",
        "status": "inProgress",
        "environmentId": env_id,
        "welcomeCard": {"enabled": False},
        "questions": [
            {"id": "reason", "type": "multipleChoiceSingle",
             "headline": {"default": "Why are you cancelling your subscription?"},
             "subheader": {"default": "Help us understand why you're leaving."},
             "choices": [{"id": f"c{i+1}", "label": {"default": r}}
                         for i, r in enumerate(CHURN_REASONS)],
             "required": True, "shuffleOption": "none"},
            {"id": "feedback", "type": "openText", "inputType": "text",
             "headline": {"default": "What could we have done to keep you?"},
             "required": False, "longAnswer": True, "placeholder": {"default": "Optional"}},
        ],
        "endings": [],
    }


def ensure_survey(client, state):
    api_key = state["api_key"]
    if state.get("survey_id"):
        st, surveys = client.list_surveys(api_key)
        ids = [s.get("id") for s in surveys.get("data", [])] if isinstance(surveys, dict) else []
        if state["survey_id"] in ids:
            return state["survey_id"]
    st, s = client.create_survey(api_key, churn_survey_payload(state["prod_env_id"]))
    if st not in (200, 201):
        raise FormbricksError(f"create churn survey failed: HTTP {st} {str(s)[:200]}")
    survey_id = (s.get("data") or s).get("id")
    state["survey_id"] = survey_id
    save_state(state)
    print(f"[seed] churn survey created (link survey, inProgress): {survey_id}", flush=True)
    return survey_id


# --- bulk responses ----------------------------------------------------------
def seed_responses(client, state, survey_id, target=TARGET_RESPONSES):
    """Submit responses through the public display->response API (the widget's own
    endpoints) until the live count reaches `target`, in one deterministic pass.
    Returns (created, final_total, wall_seconds)."""
    api_key, env_id = state["api_key"], state["prod_env_id"]
    current = client.response_count(api_key, survey_id)
    need = max(0, target - current)
    t0 = time.monotonic()
    created = 0
    for i in range(current, current + need):
        reason = CHURN_REASONS[i % len(CHURN_REASONS)]
        feedback = FEEDBACK_SNIPPETS[i % len(FEEDBACK_SNIPPETS)]
        st_d, disp = client.create_display(env_id, survey_id)   # widget: display first
        display_id = (disp.get("data") or {}).get("id") if isinstance(disp, dict) else None
        data = {"reason": reason}
        if feedback:
            data["feedback"] = feedback
        st_r, rr = client.create_response(env_id, survey_id, data, display_id=display_id)
        if st_r not in (200, 201):
            raise FormbricksError(f"response {i} failed: HTTP {st_r} {str(rr)[:160]}")
        created += 1
    wall = time.monotonic() - t0
    final = client.response_count(api_key, survey_id)
    return created, final, wall


def main():
    client = FormbricksClient()
    print(f"[seed] waiting for Formbricks at {APP_URL} ...", flush=True)
    wait_healthy(APP_URL, timeout=300)

    state = bootstrap(client)
    survey_id = ensure_survey(client, state)

    created, final, wall = seed_responses(client, state, survey_id)
    if created:
        print(f"[seed] BULK PASS: {created} churn responses created in {wall:.2f}s "
              f"({created / wall:.0f}/s) via display->response API", flush=True)
    else:
        print("[seed] idempotent: response target already met, nothing to create", flush=True)

    if final < TARGET_RESPONSES:
        raise FormbricksError(f"post-seed verify FAILED: {final} responses (want >= {TARGET_RESPONSES})")
    print(f"[seed] verified via management API: survey {survey_id} holds {final} responses "
          f"(>= {TARGET_RESPONSES})", flush=True)
    print(f"[seed] state -> {STATE_PATH} (0600): founder + org + prod env + api key + survey", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (FormbricksError, TimeoutError) as e:
        print(f"[seed] FAIL: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
