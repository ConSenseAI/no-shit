#!/usr/bin/env python3
"""noshit-f1-twenty — API client + seeding (build-plan §2.3 bulk content).

Two roles:

  1. `TwentyClient` — a stdlib HTTP client for Twenty v2.20.0's real API. Twenty
     splits its GraphQL by schema scope (verified against the running image):
       * /metadata  — AUTH + admin surface: signUp, signUpInNewWorkspace,
                      getLoginTokenFromCredentials, getAuthTokensFromLoginToken,
                      activateWorkspace, getRoles, sendInvitations, createApiKey,
                      generateApiKeyToken.  (AuthResolver is @MetadataResolver().)
       * /graphql   — per-workspace DATA API: createCompanies/createPeople,
                      companies/people { totalCount }.  (needs a workspace token)
       * /rest      — REST mirror of the data API (bearer token; batch endpoint
                      POST /rest/batch/<plural> takes a bare JSON array).

  2. Seeding — bootstrap the first workspace via Twenty's own signup, then create
     >=100 companies AND >=100 people in one deterministic, batched pass, and
     verify by reading totalCount back.

FRESH-INSTANCE BOOTSTRAP (one-shot per DB; signUp is disabled once a workspace
exists — single-tenant):
    signUp(email,password)                      -> workspace-agnostic token
    signUpInNewWorkspace(displayName)           -> loginToken + workspace.id
    getAuthTokensFromLoginToken(loginToken)     -> access token (pre-activation)
    activateWorkspace(displayName)              -> provisions Company/Person schema
    getLoginTokenFromCredentials -> getAuthTokensFromLoginToken -> FRESH token
DEVIATION (load-bearing): the token minted BEFORE activateWorkspace has no
workspace-member/actor context, so data writes fail with "no valid actor
information". You MUST re-mint a token AFTER activation. seed.py always logs in
again for a fresh actor-bearing token before seeding.

The founder email + generated password + workspace id are persisted to a 0600
state file under the durable runtime dir (OUTSIDE the repo, gitignored location)
so warm re-runs and demo.py log in with the same credentials. `--reset` wipes it.

Stdlib only. Idempotent: seeding is gated on the live totalCount.
"""
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --- fixture constants (shared with demo.py) --------------------------------
APP_URL = os.environ.get("TWENTY_URL", "http://localhost:3001")
SINK_URL = os.environ.get("MAILSINK_URL", "http://localhost:8030")
META_URL = APP_URL + "/metadata"
DATA_URL = APP_URL + "/graphql"
REST_URL = APP_URL + "/rest"

FOUNDER_EMAIL = os.environ.get("TWENTY_FOUNDER_EMAIL", "founder@fixture.test")
WORKSPACE_NAME = os.environ.get("TWENTY_WORKSPACE_NAME", "F1 Bench Workspace")
TARGET_COMPANIES = int(os.environ.get("SEED_COMPANIES", "120"))
TARGET_PEOPLE = int(os.environ.get("SEED_PEOPLE", "120"))
BATCH = int(os.environ.get("SEED_BATCH", "50"))
STATE_PATH = os.environ.get(
    "TWENTY_STATE_PATH", "/home/user/fixture-runtime/twenty/seed-state.json")

JOB_TITLES = ["Founder", "Engineer", "Designer", "Analyst", "Operator",
              "Manager", "Recruiter", "Marketer", "Advisor", "Support"]


class TwentyError(RuntimeError):
    pass


class TwentyClient:
    def __init__(self, app_url=APP_URL, timeout=90):
        self.app = app_url.rstrip("/")
        self.meta = self.app + "/metadata"
        self.data = self.app + "/graphql"
        self.rest_base = self.app + "/rest"
        self.timeout = timeout

    # -- low level -----------------------------------------------------------
    def _gql(self, url, query, variables=None, token=None, tries=3):
        hdrs = {"Content-Type": "application/json"}
        if token:
            hdrs["Authorization"] = f"Bearer {token}"
        body = json.dumps({"query": query, "variables": variables or {}}).encode()
        last_exc = None
        for attempt in range(tries):
            req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                # A GraphQL error is still a JSON body — return it, don't retry.
                try:
                    return json.loads(e.read().decode())
                except Exception:
                    return {"errors": [{"message": f"HTTP {e.code}"}]}
            except OSError as e:
                last_exc = e
                time.sleep(0.5 * (attempt + 1))
        raise TwentyError(f"connection failed to {url}: {last_exc}")

    def gql(self, url, query, variables=None, token=None):
        """Return data or raise TwentyError with the server's message."""
        resp = self._gql(url, query, variables, token)
        if resp.get("errors"):
            e0 = resp["errors"][0]
            sub = (e0.get("extensions") or {}).get("subCode") or (e0.get("extensions") or {}).get("code")
            raise TwentyError(f"{e0.get('message')} [{sub}]")
        return resp.get("data")

    def rest(self, path, method="GET", payload=None, token=None):
        hdrs = {"Content-Type": "application/json"}
        if token:
            hdrs["Authorization"] = f"Bearer {token}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self.app + path, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode())
            except Exception:
                return e.code, {}

    # -- auth (all on /metadata) --------------------------------------------
    def check_user_exists(self, email):
        d = self.gql(self.meta,
                     'query($e:String!){ checkUserExists(email:$e){ exists } }',
                     {"e": email})
        return bool(d["checkUserExists"]["exists"])

    def sign_up(self, email, password):
        d = self.gql(self.meta,
                     'mutation($e:String!,$p:String!){ signUp(email:$e,password:$p){ '
                     'tokens{ accessOrWorkspaceAgnosticToken{ token } } } }',
                     {"e": email, "p": password})
        return d["signUp"]["tokens"]["accessOrWorkspaceAgnosticToken"]["token"]

    def sign_up_in_new_workspace(self, display_name, token):
        d = self.gql(self.meta,
                     'mutation($n:String){ signUpInNewWorkspace(input:{displayName:$n}){ '
                     'loginToken{ token } workspace{ id } } }',
                     {"n": display_name}, token=token)
        node = d["signUpInNewWorkspace"]
        return node["loginToken"]["token"], node["workspace"]["id"]

    def access_from_login_token(self, login_token):
        d = self.gql(self.meta,
                     'mutation($lt:String!,$o:String!){ getAuthTokensFromLoginToken('
                     'loginToken:$lt,origin:$o){ tokens{ accessOrWorkspaceAgnosticToken{ token } } } }',
                     {"lt": login_token, "o": self.app})
        return d["getAuthTokensFromLoginToken"]["tokens"]["accessOrWorkspaceAgnosticToken"]["token"]

    def login(self, email, password):
        """getLoginTokenFromCredentials -> getAuthTokensFromLoginToken -> access token."""
        d = self.gql(self.meta,
                     'mutation($e:String!,$p:String!,$o:String!){ getLoginTokenFromCredentials('
                     'email:$e,password:$p,origin:$o){ loginToken{ token } } }',
                     {"e": email, "p": password, "o": self.app})
        return self.access_from_login_token(d["getLoginTokenFromCredentials"]["loginToken"]["token"])

    def activate_workspace(self, display_name, token):
        return self.gql(self.meta,
                        'mutation($n:String){ activateWorkspace(data:{displayName:$n}){ id } }',
                        {"n": display_name}, token=token)["activateWorkspace"]["id"]

    def get_roles(self, token):
        return self.gql(self.meta, '{ getRoles{ id label } }', token=token)["getRoles"]

    def role_id(self, token, label):
        for r in self.get_roles(token):
            if (r.get("label") or "").lower() == label.lower():
                return r["id"]
        return None

    def send_invitations(self, emails, role_id, token):
        return self.gql(self.meta,
                        'mutation($e:[String!]!,$r:UUID!){ sendInvitations(emails:$e,roleId:$r){ '
                        'success result{ email } } }',
                        {"e": emails, "r": role_id}, token=token)["sendInvitations"]

    def create_api_key(self, name, expires_at, role_id, token):
        return self.gql(self.meta,
                        'mutation($i:CreateApiKeyInput!){ createApiKey(input:$i){ id name } }',
                        {"i": {"name": name, "expiresAt": expires_at, "roleId": role_id}},
                        token=token)["createApiKey"]["id"]

    def generate_api_key_token(self, api_key_id, expires_at, token):
        return self.gql(self.meta,
                        'mutation($a:UUID!,$e:String!){ generateApiKeyToken(apiKeyId:$a,expiresAt:$e){ token } }',
                        {"a": api_key_id, "e": expires_at}, token=token)["generateApiKeyToken"]["token"]

    # -- data (on /graphql) --------------------------------------------------
    def count_companies(self, token):
        return self.gql(self.data, '{ companies{ totalCount } }', token=token)["companies"]["totalCount"]

    def count_people(self, token):
        return self.gql(self.data, '{ people{ totalCount } }', token=token)["people"]["totalCount"]

    def create_companies(self, records, token):
        d = self.gql(self.data,
                     'mutation($d:[CompanyCreateInput!]!){ createCompanies(data:$d){ id } }',
                     {"d": records}, token=token)
        return len(d["createCompanies"])

    def create_people(self, records, token):
        d = self.gql(self.data,
                     'mutation($d:[PersonCreateInput!]!){ createPeople(data:$d){ id } }',
                     {"d": records}, token=token)
        return len(d["createPeople"])


# --- health / state ---------------------------------------------------------
def wait_healthy(app_url=APP_URL, timeout=240, need_consecutive=2):
    """Poll the unauthenticated /healthz until 200 `need_consecutive` times."""
    deadline = time.monotonic() + timeout
    ok = 0
    last = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(app_url.rstrip("/") + "/healthz", timeout=5) as r:
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
    raise TimeoutError(f"Twenty not healthy at {app_url}/healthz within {timeout}s ({last})")


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
    # Guarantees upper+lower+digit+symbol and length >= 20 (Twenty's policy).
    return "Fx1!" + secrets.token_urlsafe(18)


def ensure_workspace(client):
    """Ensure the founder + activated workspace exist; return (access_token, state).
    Fresh DB -> full signup+activate; warm -> login (+activate if needed)."""
    state = load_state()
    exists = client.check_user_exists(FOUNDER_EMAIL)

    if not exists:
        password = gen_password()
        print("[seed] fresh instance: signing up the founder + first workspace ...", flush=True)
        agnostic = client.sign_up(FOUNDER_EMAIL, password)
        login_token, ws_id = client.sign_up_in_new_workspace(WORKSPACE_NAME, agnostic)
        pre_access = client.access_from_login_token(login_token)
        client.activate_workspace(WORKSPACE_NAME, pre_access)
        state = {"email": FOUNDER_EMAIL, "password": password, "workspace_id": ws_id}
        save_state(state)
        # Re-mint a token AFTER activation (actor context now exists).
        access = client.login(FOUNDER_EMAIL, password)
        print(f"[seed] workspace created + activated (id={ws_id})", flush=True)
        return access, state

    # Warm: the founder already exists -> we must know the password.
    if not state.get("password"):
        raise TwentyError(
            f"founder {FOUNDER_EMAIL} exists but no saved credentials at {STATE_PATH}; "
            f"run ./demo.sh --reset for a clean bootstrap")
    access = client.login(state["email"], state["password"])
    # Ensure the workspace is activated (idempotent safety for a half-bootstrapped DB).
    try:
        client.count_companies(access)
    except TwentyError:
        print("[seed] workspace not activated yet; activating ...", flush=True)
        client.activate_workspace(WORKSPACE_NAME, access)
        access = client.login(state["email"], state["password"])
    print(f"[seed] warm start: logged in as founder (workspace id={state.get('workspace_id')})", flush=True)
    return access, state


def _company_records(start, count):
    return [{"name": f"Fixture Company {i:04d}"} for i in range(start, start + count)]


def _person_records(start, count):
    out = []
    for i in range(start, start + count):
        out.append({
            "name": {"firstName": "Fixture", "lastName": f"Person {i:04d}"},
            "emails": {"primaryEmail": f"person-{i:04d}@people.fixture.test"},
            "jobTitle": JOB_TITLES[i % len(JOB_TITLES)],
        })
    return out


def _seed_kind(kind, current, target, create_fn, count_fn, token, batch=BATCH):
    """Idempotent: create only up to `target` (gated on live count). Returns
    (created, final_total, wall_seconds)."""
    t0 = time.monotonic()
    created = 0
    need = max(0, target - current)
    i = current
    while created < need:
        n = min(batch, need - created)
        recs = (_company_records(i, n) if kind == "companies" else _person_records(i, n))
        got = create_fn(recs, token)
        if got != n:
            raise TwentyError(f"{kind}: batch created {got}/{n}")
        created += got
        i += got
    final = count_fn(token)
    return created, final, time.monotonic() - t0


def seed_records(client, token, target_companies=TARGET_COMPANIES, target_people=TARGET_PEOPLE):
    cur_c = client.count_companies(token)
    cur_p = client.count_people(token)
    c_created, c_final, c_wall = _seed_kind(
        "companies", cur_c, target_companies, client.create_companies, client.count_companies, token)
    p_created, p_final, p_wall = _seed_kind(
        "people", cur_p, target_people, client.create_people, client.count_people, token)
    return {
        "companies_created": c_created, "companies_total": c_final, "companies_wall": c_wall,
        "people_created": p_created, "people_total": p_final, "people_wall": p_wall,
        "wall": c_wall + p_wall,
    }


def main():
    client = TwentyClient()
    print(f"[seed] waiting for Twenty at {APP_URL} ...", flush=True)
    wait_healthy(APP_URL, timeout=300)

    access, state = ensure_workspace(client)

    r = seed_records(client, access)
    total_created = r["companies_created"] + r["people_created"]
    print(f"[seed] companies: created={r['companies_created']} total={r['companies_total']} "
          f"in {r['companies_wall']:.2f}s", flush=True)
    print(f"[seed] people:    created={r['people_created']} total={r['people_total']} "
          f"in {r['people_wall']:.2f}s", flush=True)
    if total_created:
        print(f"[seed] BULK PASS: {total_created} records created in {r['wall']:.2f}s "
              f"({total_created / r['wall']:.0f}/s)", flush=True)
    else:
        print("[seed] idempotent: targets already met, nothing to create", flush=True)

    # Prove the API-KEY surface (mint + use for a real read). Best-effort — a
    # quirk here must not fail the bulk seed, which is already done above.
    try:
        admin_role = client.role_id(access, "Admin")
        exp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() + 7 * 86400)) + ".000Z"
        ak_id = client.create_api_key("f1-seed-key", exp, admin_role, access)
        ak_token = client.generate_api_key_token(ak_id, exp, access)
        st, body = client.rest("/rest/companies?limit=1", token=ak_token)
        tc = body.get("totalCount") if isinstance(body, dict) else None
        print(f"[seed] API key minted + used: REST /rest/companies read -> HTTP {st}, totalCount={tc}", flush=True)
    except (TwentyError, KeyError, TypeError) as e:
        print(f"[seed] API-key mint (bonus) skipped: {type(e).__name__}: {e}", flush=True)

    if r["companies_total"] < TARGET_COMPANIES or r["people_total"] < TARGET_PEOPLE:
        raise TwentyError(
            f"post-seed verify FAILED: companies={r['companies_total']} people={r['people_total']} "
            f"(want >= {TARGET_COMPANIES}/{TARGET_PEOPLE})")
    print(f"[seed] verified totals: companies={r['companies_total']} people={r['people_total']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (TwentyError, TimeoutError) as e:
        print(f"[seed] FAIL: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
