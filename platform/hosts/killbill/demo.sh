#!/usr/bin/env bash
# noshit-f0-killbill end-to-end proof (FIXTURES §2.1 rung 1).
#
# Thin wrapper around demo.py, the deterministic driver. It cold-starts the
# stack (compose down -v && up), runs the trial→convert→charge→cancel cycle on
# the engine test clock, prints a virtual-time timeline, and tears down.
#
#   ./demo.sh            # full run, then tear down
#   ./demo.sh --keep     # leave the stack running afterwards
#
# Exits nonzero on any failed assertion. Docker is invoked as `sg docker -c ...`
# (group-session quirk on this host) from inside demo.py.
set -euo pipefail
cd "$(dirname "$0")"
exec python3 demo.py "$@"
