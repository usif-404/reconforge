#!/usr/bin/env bash
# Run this ON YOUR WORKSTATION, not the VPS.
#
# Consumes only the `workstation` queue (Burp Assistant calls, browser
# automation needing human supervision). If your workstation is offline, the
# VPS keeps running and these tasks just queue up in Redis until you turn
# this back on.
#
# Prereqs:
#   - Tailscale connected, VPS reachable at its Tailscale IP/hostname
#   - Python venv with api/requirements.txt installed
#   - REDIS_URL pointed at the VPS over the tailnet, e.g.:
#       export REDIS_URL="redis://100.x.x.x:6379/0"
#   - DATABASE_URL likewise pointed at the VPS's Postgres over the tailnet

set -euo pipefail

: "${REDIS_URL:?Set REDIS_URL to the VPS's Tailscale address, e.g. redis://100.x.x.x:6379/0}"
: "${DATABASE_URL:?Set DATABASE_URL to the VPS's Postgres over Tailscale}"

cd "$(dirname "$0")/../api"
celery -A app.workers.celery_app worker -Q workstation --loglevel=info -c 2
