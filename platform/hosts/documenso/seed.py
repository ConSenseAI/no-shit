#!/usr/bin/env python3
"""Scripted HTTP client for the real Documenso account lifecycle (v2.14.0).

Drives Documenso's OWN endpoints — no browser, no DB shortcuts for the flow:

  signup          POST /api/auth/email-password/signup      -> fires confirmation email
  verify email    POST /api/auth/email-password/verify-email -> auto-authorizes (sets session)
  delete account  POST /api/trpc/profile.deleteAccount        -> authenticated, silent delete

Documenso v2 auth is a Hono app at /api/auth issuing SIGNED cookies (keyed by
NEXTAUTH_SECRET). We carry them in a jar so the verify -> session -> delete
chain works exactly as a browser's would. tRPC uses the SuperJSON transformer;
deleteAccount takes no input, so a batched `{"0":{"json":null}}` body suffices.

Base URL uses `localhost` to match NEXT_PUBLIC_WEBAPP_URL. Documenso sets its
session cookie with `Domain=.localhost`, which Python's CookieJar refuses to
send back to host `localhost` (the "domain needs embedded dots" quirk). Since
this client only ever talks to one host, we skip the jar and echo Set-Cookie
values verbatim — exactly what a browser sends. Stdlib only.
"""
import json
import re
import urllib.error
import urllib.request

TOKEN_RE = re.compile(r"verify-email/([A-Za-z0-9._~-]+)")


class Documenso:
    def __init__(self, base="http://localhost:3600"):
        self.base = base.rstrip("/")
        self.cookies = {}

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

    def _req(self, method, path, body=None):
        url = self.base + path
        data = None
        headers = {"Accept": "application/json"}
        if self.cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        # NB: deliberately no Origin header — /api/auth rejects mismatched Origins.
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                self._store_cookies(r.headers)
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            self._store_cookies(e.headers)
            return e.code, e.read().decode()

    def health(self):
        return self._req("GET", "/api/health")

    def signup(self, name, email, password):
        return self._req(
            "POST",
            "/api/auth/email-password/signup",
            {"name": name, "email": email, "password": password},
        )

    def verify_email(self, token):
        return self._req(
            "POST", "/api/auth/email-password/verify-email", {"token": token}
        )

    def has_session(self):
        return "sessionId" in self.cookies

    def delete_account(self):
        # tRPC batched mutation (SuperJSON transformer, no input).
        status, raw = self._req(
            "POST", "/api/trpc/profile.deleteAccount?batch=1", {"0": {"json": None}}
        )
        if status == 404:  # fall back to a single (non-batched) call
            status, raw = self._req(
                "POST", "/api/trpc/profile.deleteAccount", {"json": None}
            )
        return status, raw


def extract_verify_token(*texts):
    """Pull the email-verification token from a captured confirmation email
    (searches any number of body parts, e.g. HTML and plaintext)."""
    for t in texts:
        if not t:
            continue
        m = TOKEN_RE.search(t)
        if m:
            return m.group(1)
    return None
