#!/bin/bash
# QuantumPACS failure notifier — wired as OnFailure= on the service units.
# Logs the failed unit's recent journal and, when configured, POSTs a
# webhook alert (Slack/Teams-style JSON: {"text": "..."}).
#
# Webhook config: /etc/quantumpacs/notify.env
#   QUANTUMPACS_NOTIFY_WEBHOOK=https://hooks.example.com/...
set -euo pipefail

UNIT="${1:-unknown-unit}"

echo "QuantumPACS unit failed: $UNIT" >&2
journalctl -u "$UNIT" -n 30 --no-pager >&2 2>/dev/null || true

if [ -n "${QUANTUMPACS_NOTIFY_WEBHOOK:-}" ]; then
  curl -sf -X POST -H 'Content-Type: application/json' \
    -d "{\"text\":\"QuantumPACS unit failed: $UNIT\"}" \
    "$QUANTUMPACS_NOTIFY_WEBHOOK" >/dev/null 2>&1 || true
fi
