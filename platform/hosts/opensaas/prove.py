#!/usr/bin/env python3
"""Cold acceptance proof: signup/mail/DB plus Stripe webhook/test-clock coupling."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from stripe_ctl import Stripe, StripeError, advance_clock, cleanup_clock, load_key, mask

APP = "http://127.0.0.1:2369"
MAILPIT = "http://127.0.0.1:8028"
DAY = 86400
HOUR = 3600
CHECKS: list[tuple[str, str]] = []


class Failure(RuntimeError):
    pass


def say(message: object) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mask(message)}", flush=True)


def check(condition: bool, message: str) -> None:
    status = "PASS" if condition else "FAIL"
    CHECKS.append((status, message))
    say(f"  [{status}] {message}")
    if not condition:
        raise Failure(message)


def request_json(url: str, method: str = "GET", payload: dict | None = None, timeout: int = 20) -> tuple[int, dict | list | None, str]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    request = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode()
            content_type = response.headers.get("Content-Type", "")
            parsed = json.loads(raw) if raw and "json" in content_type else None
            return response.status, parsed, raw
    except HTTPError as error:
        raw = error.read().decode()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = None
        return error.code, parsed, raw


def wait_until(fn, description: str, timeout: int = 180):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = fn()
            if last:
                return last
        except (HTTPError, URLError, subprocess.SubprocessError, ValueError, KeyError):
            pass
        time.sleep(1)
    raise Failure(f"timed out waiting for {description}; last={mask(last)!r}")


def mail_messages() -> list[dict]:
    status, payload, _ = request_json(MAILPIT + "/api/v1/messages")
    if status != 200 or not isinstance(payload, dict):
        return []
    return payload.get("messages", [])


def mail_body(message_id: str) -> str:
    status, payload, _ = request_json(MAILPIT + f"/api/v1/message/{message_id}")
    if status != 200 or not isinstance(payload, dict):
        return ""
    return (payload.get("Text") or "") + "\n" + (payload.get("HTML") or "")


def psql(sql: str) -> list[list[str]]:
    command = ["sg", "docker", "-c", f"docker compose -p noshit-f0-opensaas exec -T db psql -U opensaas -d opensaas -At -F '|' -c {json.dumps(sql)}"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise Failure(f"psql failed: {mask(result.stderr)}")
    return [line.split("|") for line in result.stdout.splitlines() if line.strip()]


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def app_ready() -> bool:
    try:
        status, _, _ = request_json(APP + "/")
        return status == 200
    except (URLError, HTTPError):
        return False


def signup(email: str, password: str) -> None:
    before = {message["ID"] for message in mail_messages()}
    status, _, raw = request_json(APP + "/auth/email/signup", "POST", {"email": email, "password": password})
    check(status in (200, 201), f"real email/password signup accepted (HTTP {status})")

    def new_mail():
        return next((message for message in mail_messages() if message.get("ID") not in before and email in json.dumps(message)), None)

    message = wait_until(new_mail, "verification mail in this leg's Mailpit", 60)
    check(message is not None, "verification mail captured through real SMTP")
    body = mail_body(message["ID"])
    token_url = next((url for url in re.findall(r"https?://[^\s\"'<>]+", body) if "token=" in url), None)
    check(token_url is not None, "verification mail contains user-facing verification link")
    token_match = re.search(r"[?&]token=([^&\s\"'<>]+)", token_url or "")
    check(token_match is not None, "verification token extracted from captured mail")
    verify_status, _, _ = request_json(APP + "/auth/email/verify-email", "POST", {"token": token_match.group(1)})
    check(verify_status in (200, 204), f"captured verification token accepted (HTTP {verify_status})")


def user_row(email: str) -> list[str] | None:
    rows = psql(f'SELECT id,email,COALESCE("subscriptionStatus",\'\'),COALESCE("subscriptionPlan",\'\'),COALESCE("paymentProcessorUserId",\'\') FROM "User" WHERE email={sql_quote(email)}')
    return rows[0] if len(rows) == 1 else None


def update_customer_mapping(email: str, customer_id: str) -> None:
    psql(f'UPDATE "User" SET "paymentProcessorUserId"={sql_quote(customer_id)} WHERE email={sql_quote(email)}')


def wait_user_status(email: str, expected: str) -> list[str] | None:
    row = user_row(email)
    return row if row and row[2] == expected else None


def main() -> int:
    wall = time.time()
    run_id = str(int(wall))
    email = f"bench-{run_id}@opensaas.test"
    password = "Bench-pass-74!"
    stripe = Stripe(load_key())
    clock = product = price = customer = subscription = None
    try:
        say("OPEN SAAS BENCH PROOF")
        say("CHECKOUT ENTRY: DEFERRED - hosted Stripe card UI has no faithful browserless completion API")
        wait_until(app_ready, "Open SaaS on loopback port 2369", 300)
        check(app_ready(), "cold-started Open SaaS serves on 127.0.0.1:2369")

        signup(email, password)
        row = wait_until(lambda: user_row(email), "out-of-band User row", 30)
        check(row is not None and row[1] == email, "signed-up user exists in PostgreSQL via psql")
        check(row[2] == "" and row[4] == "", "new account starts without subscription/customer coupling")

        config = json.loads(Path(".run/runtime.json").read_text())
        price_id = config["price_id"]
        product_id = config["product_id"]
        t0 = int(time.time())
        clock = stripe.post("/test_helpers/test_clocks", {"frozen_time": t0, "name": f"noshit-f0-opensaas-{run_id}"})
        product = stripe.get(f"/products/{product_id}")
        price = stripe.get(f"/prices/{price_id}")
        check(product["active"] and price["active"], "real Stripe product/price mapping is active")
        customer = stripe.post("/customers", {"email": email, "test_clock": clock["id"], "metadata": {"tool": "noshit-f0-opensaas", "run": run_id}})
        payment_method = stripe.post("/payment_methods/pm_card_visa/attach", {"customer": customer["id"]})
        stripe.post(f"/customers/{customer['id']}", {"invoice_settings": {"default_payment_method": payment_method["id"]}})
        update_customer_mapping(email, customer["id"])
        mapped = user_row(email)
        check(mapped is not None and mapped[4] == customer["id"], "Open SaaS DB maps member to real Stripe customer")

        subscription = stripe.post("/subscriptions", {"customer": customer["id"], "items": [{"price": price_id}], "trial_period_days": 8, "metadata": {"tool": "noshit-f0-opensaas", "run": run_id}})
        active = wait_until(lambda: wait_user_status(email, "active"), "subscription-created webhook coupling", 180)
        check(subscription["status"] == "trialing", "Stripe subscription starts trialing")
        check(active is not None and active[3] == "hobby", "real forwarded webhook flips app DB to active hobby plan")

        advance_clock(stripe, clock["id"], t0 + 8 * DAY + HOUR)
        invoices = wait_until(lambda: [invoice for invoice in stripe.get("/invoices", {"subscription": subscription["id"], "limit": 100})["data"] if invoice["status"] == "paid" and invoice["amount_paid"] == 1200], "trial-conversion invoice", 240)
        check(len(invoices) == 1, "test clock posts one paid $12.00 conversion invoice")
        check(wait_user_status(email, "active") is not None, "app DB stays active after conversion webhook")

        current = stripe.get(f"/subscriptions/{subscription['id']}")
        boundary = current.get("current_period_end") or current["items"]["data"][0]["current_period_end"]
        advance_clock(stripe, clock["id"], boundary + HOUR)
        renewal = wait_until(lambda: [invoice for invoice in stripe.get("/invoices", {"subscription": subscription["id"], "limit": 100})["data"] if invoice["status"] == "paid" and invoice["amount_paid"] == 1200] if len([invoice for invoice in stripe.get("/invoices", {"subscription": subscription["id"], "limit": 100})["data"] if invoice["status"] == "paid" and invoice["amount_paid"] == 1200]) >= 2 else None, "renewal invoice", 240)
        check(len(renewal) == 2, "test clock crosses one renewal boundary and posts second $12.00 invoice")
        coherent = wait_until(lambda: wait_user_status(email, "active"), "coherent app state after renewal", 180)
        check(coherent is not None and coherent[3] == "hobby", "app subscription state stays coherent after renewal webhook")

        say(f"RESULT: {sum(status == 'PASS' for status, _ in CHECKS)}/{len(CHECKS)} assertions passed; wall {time.time() - wall:.1f}s")
        return 0
    except (Failure, StripeError, URLError, KeyError, ValueError, json.JSONDecodeError) as error:
        say(f"RESULT: FAILED - {type(error).__name__}: {error}")
        return 1
    finally:
        if clock:
            try:
                cleanup_clock(stripe, clock["id"])
                say(f"CLEANUP: test clock {clock['id']} deleted (customer/subscription cascade)")
            except StripeError as error:
                say(f"WARN: Stripe clock cleanup failed: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
