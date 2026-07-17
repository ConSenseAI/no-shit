#!/usr/bin/env python3
"""Real Ghost <-> Stripe subscription lifecycle through forwarded webhooks.

Hosted Checkout completion is intentionally not claimed: Stripe provides no
browserless API that faithfully completes its hosted card UI. This proof starts
with a real Ghost signup, creates the same member/customer mapping Checkout
would create, then drives real Stripe subscription events through Ghost.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent.parent / "harness"
sys.path.insert(0, str(HARNESS))
from mailsink import Mailsink  # noqa: E402

spec = importlib.util.spec_from_file_location("clockctl", HERE / "stripe-clockctl.py")
clockctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clockctl)

GHOST_URL = "http://localhost:2368"
GHOST_CANONICAL_URL = "https://localhost:2368"
MAILPIT_URL = "http://127.0.0.1:8027"
ORIGIN = {"Origin": GHOST_CANONICAL_URL, "Host": "localhost:2368", "X-Forwarded-Proto": "https", "Content-Type": "application/json"}
OWNER_EMAIL = "owner@f0-ghost.test"
OWNER_PASSWORD = "8fJq-Wm2p-Zx6t-Rn3v"
DAY = 86400
HOUR = 3600
CHECKS: list[tuple[str, str]] = []


class ProofFailure(Exception):
    pass


def say(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {clockctl.mask(message)}", flush=True)


def check(condition: bool, message: str) -> None:
    status = "PASS" if condition else "FAIL"
    CHECKS.append((status, message))
    say(f"  [{status}] {message}")
    if not condition:
        raise ProofFailure(message)


def wait_until(fn, description: str, timeout: int = 90):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = fn()
            if last:
                return last
        except (requests.RequestException, KeyError, ValueError):
            pass
        time.sleep(1)
    raise ProofFailure(f"timed out waiting for {description}; last={last!r}")


def ensure_setup(session: requests.Session) -> None:
    wait_until(lambda: session.get(GHOST_URL + "/ghost/api/admin/authentication/setup/", headers={"Host": "localhost:2368", "X-Forwarded-Proto": "https"}, timeout=5).status_code == 200, "Ghost readiness", 180)
    state = session.get(GHOST_URL + "/ghost/api/admin/authentication/setup/", headers={"Host": "localhost:2368", "X-Forwarded-Proto": "https"}, timeout=10).json()
    if state.get("setup", [{}])[0].get("status"):
        return
    response = session.post(
        GHOST_URL + "/ghost/api/admin/authentication/setup/",
        headers=ORIGIN,
        json={"setup": [{"name": "F0 Owner", "email": OWNER_EMAIL, "password": OWNER_PASSWORD, "blogTitle": "No Shit F0 Ghost"}]},
        timeout=30,
    )
    check(response.status_code < 400, f"Ghost owner setup accepted (HTTP {response.status_code})")


def signup_member(portal: requests.Session, sink: Mailsink, email: str) -> None:
    checkpoint = sink.checkpoint(f"to:{email}")
    response = portal.post(
        GHOST_URL + "/members/api/send-magic-link/",
        headers=ORIGIN,
        json={"email": email, "emailType": "signup", "name": "Coupling Member"},
        timeout=20,
    )
    check(response.status_code in (200, 201), f"Ghost signup accepted (HTTP {response.status_code})")
    message = sink.wait_new(checkpoint, timeout=30)
    check(message is not None, "Ghost signup mail arrived in Mailpit")
    full = sink.message(message["ID"])
    body = (full.get("Text") or "") + "\n" + (full.get("HTML") or "")
    link = next((url for url in re.findall(r"https?://[^\s\"'<>)]+", body) if "token=" in url), None)
    check(link is not None, "signup mail contains a magic link")
    browserless_link = link.replace(GHOST_CANONICAL_URL, GHOST_URL, 1)
    proxy_headers = {"Host": "localhost:2368", "X-Forwarded-Proto": "https"}
    followed = portal.get(browserless_link, headers=proxy_headers, timeout=20, allow_redirects=False)
    check(followed.status_code < 400, f"member followed magic link (HTTP {followed.status_code})")
    for cookie in list(portal.cookies):
        if cookie.name == "ghost-members-ssr":
            portal.cookies.set(cookie.name, cookie.value, domain="localhost", path="/", secure=False)


def member_view(portal: requests.Session) -> dict | None:
    response = portal.get(GHOST_URL + "/members/api/member/", headers={"Host": "localhost:2368", "X-Forwarded-Proto": "https"}, timeout=10)
    if response.status_code == 200 and response.text.strip():
        return response.json()
    return None


def docker_node(script: str, input_text: str | None = None) -> str:
    command = ["sg", "docker", "-c", "docker exec -i -w /var/lib/ghost/current noshit-f0-ghost-app node -"]
    payload = script + "\n"
    if input_text is not None:
        payload = script.replace("__SQL__", json.dumps(input_text))
    result = subprocess.run(command, input=payload, capture_output=True, text=True, timeout=60)
    if result.returncode:
        safe_error = clockctl.mask(result.stderr.strip())
        raise ProofFailure(f"container DB command failed (rc={result.returncode}): {safe_error}")
    return result.stdout


def sqlite_query(sql: str) -> list[dict]:
    script = """
const sqlite3=require('sqlite3').verbose();
const db=new sqlite3.Database('/var/lib/ghost/content/data/ghost-f0.db');
const sql=__SQL__;
db.all(sql,(e,r)=>{if(e){console.error(e.message);process.exit(1)}console.log(JSON.stringify(r));db.close()});
"""
    return json.loads(docker_node(script, sql) or "[]")


def mysql_query(sql: str) -> list[dict]:
    script = """
const mysql=require('mysql2/promise');
(async()=>{try{const c=await mysql.createConnection({host:'mysql',user:'ghost',password:'ghost-local',database:'ghost'});const [r]=await c.query(__SQL__);console.log(JSON.stringify(r));await c.end()}catch(e){console.error(e.message);process.exit(1)}})();
"""
    return json.loads(docker_node(script, sql) or "[]")


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def db_query(engine: str, sql: str) -> list[dict]:
    return sqlite_query(sql) if engine == "sqlite" else mysql_query(sql)


def ghost_member(engine: str, email: str) -> dict:
    rows = db_query(engine, f"SELECT id,status FROM members WHERE email={quote(email)}")
    check(len(rows) == 1, "Ghost DB contains exactly one signed-up member")
    return rows[0]


def map_customer(engine: str, member_id: str, customer: dict, run_id: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    mapping_id = ("c" + run_id)[-24:].rjust(24, "0")
    sql = (
        "INSERT INTO members_stripe_customers "
        "(id,member_id,customer_id,name,email,created_at,created_by) VALUES ("
        + ",".join(map(quote, [mapping_id, member_id, customer["id"], customer.get("name") or "Coupling Member", customer["email"], now, member_id]))
        + ")"
    )
    db_query(engine, sql)
    rows = db_query(engine, f"SELECT member_id,customer_id FROM members_stripe_customers WHERE customer_id={quote(customer['id'])}")
    check(len(rows) == 1 and rows[0]["member_id"] == member_id, "Ghost DB maps member to real Stripe customer")


def ghost_subscription(engine: str, subscription_id: str) -> dict | None:
    rows = db_query(
        engine,
        "SELECT s.status,s.cancel_at_period_end,s.current_period_end,s.mrr,s.trial_start_at,s.trial_end_at,"
        "g.status AS ghost_status,g.type AS ghost_type "
        "FROM members_stripe_customers_subscriptions s "
        "LEFT JOIN subscriptions g ON g.id=s.ghost_subscription_id "
        f"WHERE s.subscription_id={quote(subscription_id)}",
    )
    return rows[0] if rows else None


def member_status(engine: str, member_id: str) -> str | None:
    rows = db_query(engine, f"SELECT status FROM members WHERE id={quote(member_id)}")
    return rows[0]["status"] if rows else None


def create_tier_records(engine: str, member_id: str, run_id: str, product: dict, price: dict) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    tier_id = ("t" + run_id)[-24:].rjust(24, "0")
    stripe_product_row = ("p" + run_id)[-24:].rjust(24, "0")
    stripe_price_row = ("r" + run_id)[-24:].rjust(24, "0")
    columns = {row["name"] for row in db_query(engine, "PRAGMA table_info(products)")} if engine == "sqlite" else {row["Field"] for row in db_query(engine, "SHOW COLUMNS FROM products")}
    values = {"id": tier_id, "name": "Coupling Paid Tier", "slug": f"coupling-paid-tier-{run_id}", "description": "Lifecycle coupling proof", "type": "paid", "active": 1, "visibility": "public", "created_at": now, "trial_days": 8, "currency": "usd", "monthly_price": 1200}
    chosen = [(key, value) for key, value in values.items() if key in columns]
    db_query(engine, "INSERT INTO products (" + ",".join(key for key, _ in chosen) + ") VALUES (" + ",".join(quote(str(value)) for _, value in chosen) + ")")
    db_query(engine, "INSERT INTO stripe_products (id,product_id,stripe_product_id,created_at) VALUES (" + ",".join(map(quote, [stripe_product_row, tier_id, product["id"], now])) + ")")
    interval_column = '"interval"' if engine == "sqlite" else '`interval`'
    db_query(engine, "INSERT INTO stripe_prices (id,stripe_price_id,stripe_product_id,active,nickname,currency,amount,type," + interval_column + ",created_at) VALUES (" + ",".join(map(quote, [stripe_price_row, price["id"], product["id"], "1", "Coupling monthly", "usd", "1200", "recurring", "month", now])) + ")")
    if "monthly_price_id" in columns:
        db_query(engine, f"UPDATE products SET monthly_price_id={quote(stripe_price_row)} WHERE id={quote(tier_id)}")
    check(len(db_query(engine, f"SELECT id FROM stripe_prices WHERE stripe_price_id={quote(price['id'])}")) == 1, "Ghost DB recognizes Stripe product/price as a paid tier")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", choices=("sqlite", "mysql"), required=True)
    args = parser.parse_args()
    wall = time.time()
    run_id = str(int(time.time()))
    email = f"coupling-{args.db}-{run_id}@f0-ghost.test"
    stripe = clockctl.Stripe(clockctl.load_key(), api_version="2020-08-27")
    sink = Mailsink(base_url=MAILPIT_URL)
    admin, portal = requests.Session(), requests.Session()
    clock = product = price = customer = subscription = None
    initial_mail = sink.checkpoint(f"to:{email}")

    try:
        say(f"GHOST <-> STRIPE LIFECYCLE COUPLING ({args.db})")
        say("CHECKOUT ENTRY: DEFERRED — hosted card UI has no faithful browserless completion API")
        ensure_setup(admin)
        signup_member(portal, sink, email)
        member = ghost_member(args.db, email)
        member_id = member["id"]
        check(member["status"] == "free", "Ghost DB marks signed-up member free")

        t0 = int(time.time())
        product = stripe.post("/products", {"name": f"Ghost Coupling {args.db} {run_id}", "metadata": {"tool": "noshit-f0-ghost-coupling", "run": run_id}})
        price = stripe.post("/prices", {"product": product["id"], "unit_amount": 1200, "currency": "usd", "recurring": {"interval": "month"}, "metadata": {"tool": "noshit-f0-ghost-coupling", "run": run_id}})
        create_tier_records(args.db, member_id, run_id, product, price)
        clock = stripe.post("/test_helpers/test_clocks", {"frozen_time": t0, "name": f"noshit-f0-ghost-coupling-{args.db}-{run_id}"})
        customer = stripe.post("/customers", {"name": "Coupling Member", "email": email, "test_clock": clock["id"], "metadata": {"tool": "noshit-f0-ghost-coupling", "run": run_id}})
        payment_method = stripe.post("/payment_methods/pm_card_visa/attach", {"customer": customer["id"]})
        stripe.post(f"/customers/{customer['id']}", {"invoice_settings": {"default_payment_method": payment_method["id"]}})
        map_customer(args.db, member_id, customer, run_id)

        subscription = stripe.post("/subscriptions", {"customer": customer["id"], "items": [{"price": price["id"]}], "trial_period_days": 8, "metadata": {"tool": "noshit-f0-ghost-coupling", "run": run_id}})
        sub_id = subscription["id"]
        row = wait_until(lambda: ghost_subscription(args.db, sub_id), "Ghost subscription-created webhook")
        check(row["status"] == "trialing", "Ghost DB records Stripe subscription as trialing")
        check(row["ghost_type"] in (None, "paid"), "Ghost accepts trial subscription webhook")
        live_status = wait_until(lambda: (status if (status := member_status(args.db, member_id)) == "paid" else None), "member paid state")
        check(live_status == "paid", "Ghost member record becomes paid after real webhook")

        clockctl.advance_clock(stripe, clock["id"], t0 + 8 * DAY + HOUR)
        row = wait_until(lambda: (r if (r := ghost_subscription(args.db, sub_id)) and r["status"] == "active" else None), "trial conversion webhook", 180)
        check(row["status"] == "active", "Ghost DB reflects trial conversion to active")
        invoices = stripe.get("/invoices", {"subscription": sub_id, "limit": 100})["data"]
        paid = [invoice for invoice in invoices if invoice["status"] == "paid" and invoice["amount_paid"] == 1200]
        check(len(paid) == 1, "Stripe conversion invoice paid exactly $12.00")

        first_boundary = stripe.get(f"/subscriptions/{sub_id}")["current_period_end"]
        clockctl.advance_clock(stripe, clock["id"], first_boundary + HOUR)
        renewal_invoices = wait_until(lambda: [i for i in stripe.get("/invoices", {"subscription": sub_id, "limit": 100})["data"] if i["status"] == "paid" and i["amount_paid"] == 1200] if len([i for i in stripe.get("/invoices", {"subscription": sub_id, "limit": 100})["data"] if i["status"] == "paid" and i["amount_paid"] == 1200]) >= 2 else None, "renewal invoice", 180)
        row = wait_until(lambda: (r if (r := ghost_subscription(args.db, sub_id)) and r["status"] == "active" else None), "Ghost renewal webhook", 180)
        check(row["status"] == "active", "Ghost Stripe subscription stays active after renewal")
        check(member_status(args.db, member_id) == "paid", "Ghost member stays paid after renewal")
        check(len(renewal_invoices) == 2, "Stripe has conversion plus one renewal charge")

        stripe.post(f"/subscriptions/{sub_id}", {"cancel_at_period_end": True})
        row = wait_until(lambda: (r if (r := ghost_subscription(args.db, sub_id)) and bool(r["cancel_at_period_end"]) else None), "Ghost cancel-at-period-end update", 120)
        check(bool(row["cancel_at_period_end"]), "Ghost reflects cancel_at_period_end before boundary")
        cancel_boundary = stripe.get(f"/subscriptions/{sub_id}")["current_period_end"]
        clockctl.advance_clock(stripe, clock["id"], cancel_boundary + HOUR)
        row = wait_until(lambda: (r if (r := ghost_subscription(args.db, sub_id)) and r["status"] == "canceled" else None), "Ghost cancellation webhook", 180)
        check(row["status"] == "canceled", "Ghost reflects terminal cancellation at boundary")
        ended_status = wait_until(lambda: (status if (status := member_status(args.db, member_id)) == "free" else None), "member free after cancellation", 120)
        check(ended_status == "free", "Ghost member record returns to free after cancellation")
        final_paid = [i for i in stripe.get("/invoices", {"subscription": sub_id, "limit": 100})["data"] if i["status"] == "paid" and i["amount_paid"] > 0]
        check(len(final_paid) == 2, "no charge occurs after cancellation")

        extra_mail = sink.wait_new(initial_mail, timeout=3)
        check(extra_mail is not None, "member-facing signup mail remained captured in Mailpit")
        say(f"RESULT: {sum(1 for status, _ in CHECKS if status == 'PASS')}/{len(CHECKS)} passed; wall {time.time()-wall:.1f}s")
        return 0
    except (ProofFailure, clockctl.StripeError, requests.RequestException, KeyError, ValueError) as error:
        say(f"RESULT: FAILED — {type(error).__name__}: {error}")
        return 1
    finally:
        if clock:
            try:
                clockctl.delete_clock(stripe, clock["id"])
            except clockctl.StripeError as error:
                say(f"WARN: clock cleanup failed: {error}")
        for obj, path in ((price, "prices"), (product, "products")):
            if obj:
                try:
                    stripe.post(f"/{path}/{obj['id']}", {"active": False})
                except clockctl.StripeError:
                    pass


if __name__ == "__main__":
    sys.exit(main())
