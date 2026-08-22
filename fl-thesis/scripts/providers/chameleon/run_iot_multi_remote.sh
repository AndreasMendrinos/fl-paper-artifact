#!/usr/bin/env bash
set -euo pipefail

NUM_ROUNDS="${1:?Usage: $0 <rounds> <local-epochs> <learning-rate> <node-id> [node-id...]}"
LOCAL_EPOCHS="${2:?Usage: $0 <rounds> <local-epochs> <learning-rate> <node-id> [node-id...]}"
LEARNING_RATE="${3:?Usage: $0 <rounds> <local-epochs> <learning-rate> <node-id> [node-id...]}"

shift 3
NODE_IDS=("$@")

NUM_CLIENTS="${#NODE_IDS[@]}"

if [[ "$NUM_CLIENTS" -lt 1 ]]; then
    echo "ERROR: At least one IoT node is required."
    exit 1
fi

PROJECT_ROOT="$HOME/fl-thesis"
APP_DIR="${PROJECT_ROOT}/experiments/iot_numpy_fl"
RESULTS_ROOT="${PROJECT_ROOT}/results/iot_numpy_fl"

source "$HOME/flwr-venv/bin/activate"

RUN_ID="iot_multi_${NUM_CLIENTS}nodes_$(date +%Y%m%d_%H%M%S)_$$"
RUN_DIR="${RESULTS_ROOT}/${RUN_ID}"

mkdir -p \
    "${RUN_DIR}/logs" \
    "${RUN_DIR}/metrics" \
    "${RUN_DIR}/plots"

RESULTS_FILE="${RUN_DIR}/metrics/results.jsonl"

if [[ -e "$RESULTS_FILE" ]]; then
    echo "ERROR: Results file already exists:"
    echo "  $RESULTS_FILE"
    echo "Refusing to append to an existing experiment."
    exit 1
fi

export RUN_ID
export RUN_DIR
export IOT_RESULTS_DIR="${RUN_DIR}/metrics"

echo "RUN_ID=${RUN_ID}"
echo "RUN_DIR=${RUN_DIR}"
echo "NUM_CLIENTS=${NUM_CLIENTS}"
echo "NODES=${NODE_IDS[*]}"

# Store node IDs as valid JSON.
NODE_JSON="$(
    printf '%s\n' "${NODE_IDS[@]}" |
    python -c '
import json
import sys
print(json.dumps(["node-a8-" + line.strip() for line in sys.stdin if line.strip()]))
'
)"

cat > "${RUN_DIR}/experiment_metadata.json" <<EOF
{
  "run_id": "${RUN_ID}",
  "architecture": "chameleon-superlink-iotlab-multi-a8-proxy",
  "server_provider": "chameleon",
  "client_provider": "iot-lab",
  "iot_site": "grenoble",
  "iot_nodes": ${NODE_JSON},
  "iot_architecture": "armv7l",
  "iot_python": "3.8.11",
  "iot_numpy": "1.17.4",
  "iot_memory_mb": 244,
  "num_clients": ${NUM_CLIENTS},
  "num_rounds": ${NUM_ROUNDS},
  "local_epochs": ${LOCAL_EPOCHS},
  "learning_rate": ${LEARNING_RATE},
  "model": "numpy-linear-regression",
  "target_weight": 2.0,
  "target_bias": 1.0
}
EOF

echo "Stopping old Chameleon services..."

pkill -9 -f flower-supernode 2>/dev/null || true
pkill -9 -f flower-superexec 2>/dev/null || true
pkill -9 -f flower-superlink 2>/dev/null || true
pkill -f 'iot_fl/broker.py' 2>/dev/null || true

sleep 2

OLD_BROKER_PID="$(
    ss -ltnp 2>/dev/null |
    awk '
        /:8081 / {
            if (match($0, /pid=[0-9]+/)) {
                print substr($0, RSTART + 4, RLENGTH - 4)
            }
        }
    ' |
    head -1
)"

if [[ -n "$OLD_BROKER_PID" ]]; then
    echo "Stopping existing broker PID=${OLD_BROKER_PID}"
    kill "$OLD_BROKER_PID" 2>/dev/null || true
    sleep 2
fi

if ss -ltn | grep -q ':8081 '; then
    echo "ERROR: Port 8081 is still occupied."
    ss -ltnp | grep ':8081' || true
    exit 1
fi

echo "Starting broker..."

nohup python \
    "${APP_DIR}/iot_fl/broker.py" \
    > "${RUN_DIR}/logs/broker.log" 2>&1 < /dev/null &

BROKER_PID=$!
echo "$BROKER_PID" > "${RUN_DIR}/logs/broker.pid"

sleep 2

curl --fail --silent \
    http://127.0.0.1:8081/health \
    > "${RUN_DIR}/logs/broker_health.json"

echo "Starting SuperLink..."

nohup flower-superlink \
    --insecure \
    --fleet-api-address "0.0.0.0:9092" \
    --control-api-address "127.0.0.1:9093" \
    > "${RUN_DIR}/logs/superlink.log" 2>&1 < /dev/null &

SUPERLINK_PID=$!
echo "$SUPERLINK_PID" > "${RUN_DIR}/logs/superlink.pid"

sleep 3

if ! ss -tlnp | grep -q ':9092'; then
    echo "ERROR: SuperLink Fleet API is not listening."
    tail -50 "${RUN_DIR}/logs/superlink.log"
    exit 1
fi

echo "Starting ${NUM_CLIENTS} IoT proxy SuperNodes..."

for INDEX in "${!NODE_IDS[@]}"; do
    NODE_ID="${NODE_IDS[$INDEX]}"
    NODE_NAME="node-a8-${NODE_ID}"
    CLIENTAPPIO_PORT="$((9094 + INDEX))"

    LOG_FILE="${RUN_DIR}/logs/proxy_supernode_${INDEX}_${NODE_NAME}.log"
    PID_FILE="${RUN_DIR}/logs/proxy_supernode_${INDEX}_${NODE_NAME}.pid"

    echo "  partition=${INDEX}/${NUM_CLIENTS}"
    echo "  IoT node=${NODE_NAME}"
    echo "  ClientAppIo port=${CLIENTAPPIO_PORT}"

    nohup flower-supernode \
        --insecure \
        --superlink "127.0.0.1:9092" \
        --clientappio-api-address "127.0.0.1:${CLIENTAPPIO_PORT}" \
        --node-config \
        "partition-id=${INDEX} num-partitions=${NUM_CLIENTS} broker-url='http://127.0.0.1:8081' iot-node-id='${NODE_NAME}'" \
        > "$LOG_FILE" 2>&1 < /dev/null &

    echo $! > "$PID_FILE"
done

sleep 5

RUNNING_SUPERNODES="$(
    pgrep -fc flower-supernode || true
)"

echo "Running proxy SuperNodes: ${RUNNING_SUPERNODES}/${NUM_CLIENTS}"

if [[ "$RUNNING_SUPERNODES" -lt "$NUM_CLIENTS" ]]; then
    echo "ERROR: Not all proxy SuperNodes started."

    for LOG_FILE in "${RUN_DIR}"/logs/proxy_supernode_*.log; do
        echo
        echo "===== ${LOG_FILE} ====="
        tail -50 "$LOG_FILE" || true
    done

    exit 1
fi

echo "Starting Flower run..."

cd "$APP_DIR"

set +e

flwr run . iot-local --stream \
    --run-config="num-server-rounds=${NUM_ROUNDS} num-clients=${NUM_CLIENTS} learning-rate=${LEARNING_RATE} local-epochs=${LOCAL_EPOCHS}" \
    2>&1 | tee "${RUN_DIR}/logs/flwr_run.log"

FLOWER_EXIT_CODE="${PIPESTATUS[0]}"

set -e

echo "$FLOWER_EXIT_CODE" > "${RUN_DIR}/flower_exit_code.txt"

if [[ "$FLOWER_EXIT_CODE" -ne 0 ]]; then
    echo "ERROR: Flower run failed with exit code ${FLOWER_EXIT_CODE}."
    exit "$FLOWER_EXIT_CODE"
fi

echo "Generating metrics and plots..."

python \
    "${APP_DIR}/scripts/analyze_results.py" \
    --run-dir "$RUN_DIR"

echo "$RUN_DIR" > "${RESULTS_ROOT}/latest_run.txt"

echo
echo "Experiment completed successfully."
echo "RUN_ID=${RUN_ID}"
echo "RUN_DIR=${RUN_DIR}"
