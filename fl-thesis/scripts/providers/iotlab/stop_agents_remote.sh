#!/usr/bin/env bash
set -euo pipefail

IOTLAB_USER="${1:?Usage: $0 <user> <site> <node-id> [node-id...]}"
IOTLAB_SITE="${2:?Usage: $0 <user> <site> <node-id> [node-id...]}"

shift 2
NODE_IDS=("$@")

FRONTEND="${IOTLAB_USER}@${IOTLAB_SITE}.iot-lab.info"
REMOTE_LOG_DIR="/home/root/shared/fl-thesis/logs"

for NODE_ID in "${NODE_IDS[@]}"; do
    NODE_HOST="node-a8-${NODE_ID}"
    PID_FILE="${REMOTE_LOG_DIR}/${NODE_HOST}.pid"

    echo "Stopping agent on ${NODE_HOST}..."

    ssh "$FRONTEND" \
        "ssh \
          -o StrictHostKeyChecking=accept-new \
          -o ConnectTimeout=15 \
          root@${NODE_HOST} \
          'if [ -f ${PID_FILE} ]; then
               PID=\$(cat ${PID_FILE} 2>/dev/null || true)

               if [ -n \"\$PID\" ] && kill -0 \"\$PID\" 2>/dev/null; then
                   kill \"\$PID\" 2>/dev/null || true
                   sleep 1
               fi

               rm -f ${PID_FILE}
           fi'"
done
