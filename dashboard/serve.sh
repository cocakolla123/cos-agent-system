#!/bin/bash
# Starts the local CoS dashboard. Localhost only (127.0.0.1:8765). Run manually whenever you
# want to check it; not an always-on daemon — stop with Ctrl+C.
#
# Self-contained: with no arguments, reads config.json/writes workspace data inside this same
# dashboard/ directory. Pass --config/--workspace to point at a different deployment's files.
#
# Requires: python3 (stdlib only) and the `claude` CLI on PATH (needed for the "Approve & send"
# button — it shells out to `claude -p /cos-approve-confirmed <id>`). Run this from a shell
# that already has `claude` on PATH.
cd "$(dirname "$0")"
exec python3 server.py "$@"
