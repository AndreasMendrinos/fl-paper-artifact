#!/usr/bin/env bash
set -euo pipefail

IOTLAB_USER="${1:?Usage: $0 <user> <site> <node-id> [node-id...]}"
IOTLAB_SITE="${2:?Usage: $0 <user> <site> <node-id> [node-id...]}"

shift 2
NODE_IDS=("$@")

FRONTEND="${IOTLAB_USER}@${IOTLAB_SITE}.iot-lab.info"

for NODE_ID in "${NODE_IDS[@]}"; do
    NODE_HOST="node-a8-${NODE_ID}"

    echo
    echo "===== ${NODE_HOST} ====="

    ssh "$FRONTEND" \
        "ssh \
          -o StrictHostKeyChecking=accept-new \
          -o ConnectTimeout=15 \
          root@${NODE_HOST} \
          'hostname
           python3 --version
           free -h | head -2
           pgrep -af \"[a]gent.py\" || true
           tail -8 /home/root/shared/fl-thesis/logs/${NODE_HOST}.log 2>/dev/null || true'"
done