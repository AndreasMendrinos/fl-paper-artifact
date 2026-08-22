#!/usr/bin/env bash
set -euo pipefail

IOTLAB_USER="${1:?Usage: $0 <user> <site> <broker-url> <node-id> [node-id...]}"
IOTLAB_SITE="${2:?Usage: $0 <user> <site> <broker-url> <node-id> [node-id...]}"
BROKER_URL="${3:?Usage: $0 <user> <site> <broker-url> <node-id> [node-id...]}"

shift 3
NODE_IDS=("$@")

if [[ "${#NODE_IDS[@]}" -eq 0 ]]; then
    echo "ERROR: At least one A8 node ID is required."
    exit 1
fi

FRONTEND="${IOTLAB_USER}@${IOTLAB_SITE}.iot-lab.info"

REMOTE_AGENT="/home/root/shared/fl-thesis/agent.py"
REMOTE_LOG_DIR="/home/root/shared/fl-thesis/logs"

for NODE_ID in "${NODE_IDS[@]}"; do
    NODE_HOST="node-a8-${NODE_ID}"
    LOG_FILE="${REMOTE_LOG_DIR}/${NODE_HOST}.log"
    PID_FILE="${REMOTE_LOG_DIR}/${NODE_HOST}.pid"

    echo "Starting agent on ${NODE_HOST}..."

    ssh "$FRONTEND" \
        "ssh \
          -o StrictHostKeyChecking=accept-new \
          -o ConnectTimeout=15 \
          root@${NODE_HOST} \
          'set -e

           mkdir -p ${REMOTE_LOG_DIR}

           if [ ! -f ${REMOTE_AGENT} ]; then
               echo \"ERROR: Agent not found at ${REMOTE_AGENT}\"
               exit 1
           fi

           if [ -f ${PID_FILE} ]; then
               OLD_PID=\$(cat ${PID_FILE} 2>/dev/null || true)

               if [ -n \"\$OLD_PID\" ] && kill -0 \"\$OLD_PID\" 2>/dev/null; then
                   echo \"Stopping previous agent PID=\$OLD_PID\"
                   kill \"\$OLD_PID\" 2>/dev/null || true

                   WAIT_COUNT=0
                   while kill -0 \"\$OLD_PID\" 2>/dev/null; do
                       WAIT_COUNT=\$((WAIT_COUNT + 1))

                       if [ \"\$WAIT_COUNT\" -ge 10 ]; then
                           echo \"Force-stopping PID=\$OLD_PID\"
                           kill -9 \"\$OLD_PID\" 2>/dev/null || true
                           break
                       fi

                       sleep 1
                   done
               fi
           fi

           rm -f ${PID_FILE}

           BROKER_URL=${BROKER_URL} \
           nohup python3 -u ${REMOTE_AGENT} \
               > ${LOG_FILE} 2>&1 < /dev/null &

           NEW_PID=\$!
           echo \"\$NEW_PID\" > ${PID_FILE}

           sleep 2

           if ! kill -0 \"\$NEW_PID\" 2>/dev/null; then
               echo \"ERROR: Agent failed to start on ${NODE_HOST}\"
               cat ${LOG_FILE} || true
               exit 1
           fi

           echo \"Agent started successfully\"
           echo \"PID=\$NEW_PID\"
           echo \"LOG=${LOG_FILE}\"
           tail -5 ${LOG_FILE} || true'"
done

echo
echo "All requested A8 agents were started successfully."
