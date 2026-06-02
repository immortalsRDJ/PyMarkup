#!/usr/bin/env bash
# Monthly refresh job for the PyMarkup dashboard.
#
# Runs the full estimation pipeline, rebuilds the dashboard parquet, and
# restarts the Dash service so the new data is served.
#
# Scheduled from cron, e.g.:
#   0 3 1 * * /home/ec2-user/PyMarkup/scripts/monthly_refresh.sh
#
# Prerequisites on the host (one-time setup):
#   - ~/.pgpass with WRDS credentials (mode 600)
#   - config.yaml in repo root with fred_api_key + wrds_username
#   - /etc/sudoers.d/pymarkup granting NOPASSWD for: systemctl restart pymarkup
#   - /var/log/pymarkup-refresh.log writable by this user

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG=/var/log/pymarkup-refresh.log
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "[$TS] === Starting monthly refresh ===" >> "$LOG"

cd "$REPO"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[$TS] Step 1/3: pymarkup run-all" >> "$LOG"
pymarkup run-all --config config.yaml >> "$LOG" 2>&1

echo "[$TS] Step 2/3: build dashboard parquet" >> "$LOG"
python scripts/build_dashboard_data.py >> "$LOG" 2>&1

echo "[$TS] Step 3/3: restart dashboard service" >> "$LOG"
sudo systemctl restart pymarkup

echo "[$TS] === Refresh complete ===" >> "$LOG"
