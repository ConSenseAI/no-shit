#!/usr/bin/env python3
"""Seed Ghost direct-key settings without printing credentials."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import requests

GHOST_URL = "http://localhost:2368"


def wait_ghost() -> None:
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            if requests.get(GHOST_URL + "/ghost/api/admin/authentication/setup/", headers={"Host": "localhost:2368", "X-Forwarded-Proto": "https"}, timeout=5).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("Ghost did not become ready")


def exec_node(script: str, env: dict[str, str]) -> None:
    assignments = " ".join(f"{key}={env[key]}" for key in env)
    command = f"docker exec -i -w /var/lib/ghost/current noshit-f0-ghost-app env {assignments} node -"
    result = subprocess.run(["sg", "docker", "-c", command], input=script, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError("could not seed Ghost Stripe settings")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", choices=("sqlite", "mysql"), required=True)
    args = parser.parse_args()
    secret = os.environ.get("STRIPE_SECRET_KEY", "")
    publishable = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    if not secret.startswith(("rk_test_", "sk_test_")) or not publishable.startswith("pk_test_"):
        raise RuntimeError("missing test Stripe keys")
    wait_ghost()
    driver = "sqlite3" if args.db == "sqlite" else "mysql2"
    config = "{filename:'/var/lib/ghost/content/data/ghost-f0.db'}" if args.db == "sqlite" else "{host:'mysql',user:'ghost',password:'ghost-local',database:'ghost'}"
    script = f"""
const knex=require('knex')({{client:'{driver}',connection:{config},useNullAsDefault:true}});
(async()=>{{
  for (const [key,value] of [['stripe_secret_key',process.env.STRIPE_SECRET_KEY],['stripe_publishable_key',process.env.STRIPE_PUBLISHABLE_KEY]]) {{
    await knex('settings').where({{key}}).update({{value,updated_at:new Date()}});
  }}
  await knex.destroy();
}})().catch(() => process.exit(1));
"""
    exec_node(script, {"STRIPE_SECRET_KEY": secret, "STRIPE_PUBLISHABLE_KEY": publishable})
    print(f"[ok] Ghost direct Stripe settings seeded ({args.db})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"FATAL: {error}", file=sys.stderr)
        sys.exit(1)
