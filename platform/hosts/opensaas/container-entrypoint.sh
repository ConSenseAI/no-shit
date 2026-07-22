#!/usr/bin/env bash
set -euo pipefail

cd /opt/opensaas

# Dependencies are lock-resolved during setup/build; runtime only migrates and starts.
wasp db migrate-dev --name bench_init
exec wasp start
