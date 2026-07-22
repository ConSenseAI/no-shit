#!/usr/bin/env python3
"""Masked Stripe helpers for the Open SaaS bench leg."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://api.stripe.com/v1"
TOOL = "noshit-f0-opensaas"
SECRET_RE = re.compile(r"\b(rk|sk|pk|whsec)_(?:(test|live)_)?[A-Za-z0-9*]+")
ACCT_RE = re.compile(r"\bacct_[A-Za-z0-9*]+")
LIVE_KEY = ""


def mask(value: object) -> str:
    text = str(value)
    if LIVE_KEY:
        text = text.replace(LIVE_KEY, "rk_test_***")
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}_{m.group(2)}_***" if m.group(2) else f"{m.group(1)}_***", text)
    return ACCT_RE.sub("acct_***", text)


def say(message: object) -> None:
    print(mask(message), flush=True)


def load_key() -> str:
    global LIVE_KEY
    key = os.environ.get("STRIPE_API_KEY", "").strip()
    if not key:
        for line in (Path(__file__).parent / ".env").read_text().splitlines():
            if line.startswith("STRIPE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key.startswith(("rk_test_", "sk_test_")):
        raise SystemExit("FATAL: .env needs a test-mode STRIPE_API_KEY")
    LIVE_KEY = key
    return key


class StripeError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(mask(f"HTTP {status}: {message}"))


class Stripe:
    def __init__(self, key: str):
        self.key = key

    def request(self, method: str, path: str, params: dict | None = None) -> dict:
        data = flatten(params or {})
        url = API_ROOT + path
        body = None
        if method == "GET" and data:
            url += "?" + urlencode(data)
        elif data:
            body = urlencode(data).encode()
        request = Request(url, data=body, method=method, headers={"Authorization": f"Bearer {self.key}", "Stripe-Version": "2025-04-30.basil"})
        try:
            with urlopen(request, timeout=45) as response:
                payload = response.read().decode()
                status = response.status
        except HTTPError as error:
            payload = error.read().decode()
            status = error.code
        parsed = json.loads(payload) if payload else {}
        if status >= 400:
            detail = parsed.get("error", {}).get("message", payload)
            raise StripeError(status, detail)
        return parsed

    def get(self, path: str, params: dict | None = None) -> dict:
        return self.request("GET", path, params)

    def post(self, path: str, params: dict | None = None) -> dict:
        return self.request("POST", path, params)

    def delete(self, path: str) -> dict:
        return self.request("DELETE", path)


def flatten(params: dict, parent: str | None = None) -> dict:
    result = {}
    for key, value in params.items():
        name = f"{parent}[{key}]" if parent else str(key)
        if isinstance(value, dict):
            result.update(flatten(value, name))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                result.update(flatten(item, f"{name}[{index}]") if isinstance(item, dict) else {f"{name}[{index}]": item})
        elif isinstance(value, bool):
            result[name] = "true" if value else "false"
        elif value is not None:
            result[name] = value
    return result


def poll_ready(stripe: Stripe, clock_id: str, timeout: int = 240) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        clock = stripe.get(f"/test_helpers/test_clocks/{clock_id}")
        if clock["status"] == "ready":
            return clock
        if clock["status"] == "internal_failure":
            raise StripeError(500, "test clock advance failed")
        time.sleep(2)
    raise StripeError(504, "test clock did not become ready")


def advance_clock(stripe: Stripe, clock_id: str, frozen_time: int) -> dict:
    poll_ready(stripe, clock_id)
    stripe.post(f"/test_helpers/test_clocks/{clock_id}/advance", {"frozen_time": frozen_time})
    return poll_ready(stripe, clock_id)


def cleanup_clock(stripe: Stripe, clock_id: str) -> None:
    poll_ready(stripe, clock_id)
    stripe.delete(f"/test_helpers/test_clocks/{clock_id}")


def doctor(stripe: Stripe) -> int:
    probes = (("products", "/products"), ("prices", "/prices"), ("customers", "/customers"), ("subscriptions", "/subscriptions"), ("invoices", "/invoices"), ("events", "/events"), ("test clocks", "/test_helpers/test_clocks"))
    denied = 0
    say("DOCTOR: Stripe scope pre-flight (key masked)")
    for label, path in probes:
        try:
            stripe.get(path, {"limit": 1})
            say(f"  [ok] {label}")
        except StripeError as error:
            denied += 1
            say(f"  [DENY] {label}: {error}")
    if denied:
        say(f"DOCTOR: {denied} required read scope(s) denied")
        return 1
    say("DOCTOR: required read scopes available")
    return 0


def cleanup_owned(stripe: Stripe) -> int:
    clocks = stripe.get("/test_helpers/test_clocks", {"limit": 100})["data"]
    ours = [clock for clock in clocks if (clock.get("name") or "").startswith(TOOL)]
    say(f"CLEANUP: found {len(ours)} tool-owned test clock(s)")
    for clock in ours:
        cleanup_clock(stripe, clock["id"])
        say(f"  deleted {clock['id']}")
    products = stripe.get("/products", {"limit": 100})["data"]
    for product in products:
        if product.get("metadata", {}).get("tool") != TOOL:
            continue
        prices = stripe.get("/prices", {"product": product["id"], "limit": 100})["data"]
        for price in prices:
            if price.get("active"):
                stripe.post(f"/prices/{price['id']}", {"active": False})
                say(f"  archived {price['id']}")
        if product.get("active"):
            stripe.post(f"/products/{product['id']}", {"active": False})
            say(f"  archived {product['id']}")
    return 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "doctor"
    stripe = Stripe(load_key())
    if command == "doctor":
        return doctor(stripe)
    if command == "cleanup":
        return cleanup_owned(stripe)
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(mask(f"FATAL: {type(error).__name__}: {error}"), file=sys.stderr)
        raise SystemExit(1)
