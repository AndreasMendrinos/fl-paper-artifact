#!/usr/bin/env bash
set -euo pipefail

IOTLAB_USER="${1:?Usage: $0 <iotlab-user> <iotlab-site> <chameleon-ip> <chameleon-key> <node-id> [node-id...]}"
IOTLAB_SITE="${2:?Usage: $0 <iotlab-user> <iotlab-site> <chameleon-ip> <chameleon-key> <node-id> [node-id...]}"
CHAMELEON_IP="${3:?Usage: $0 <iotlab-user> <iotlab-site> <chameleon-ip> <chameleon-key> <node-id> [node-id...]}"
CHAMELEON_KEY="${4:?Usage: $0 <iotlab-user> <iotlab-site> <chameleon-ip> <chameleon-key> <node-id> [node-id...]}"

shift 4
NODE_IDS=("$@")

if [[ "${#NODE_IDS[@]}" -lt 1 ]]; then
    echo "ERROR: At least one A8 node ID is required."
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

NUM_ROUNDS="${NUM_ROUNDS:-10}"
LOCAL_EPOCHS="${LOCAL_EPOCHS:-5}"
LEARNING_RATE="${LEARNING_RATE:-0.01}"

BROKER_URL="http://${CHAMELEON_IP}:8081"

echo "=========================================="
echo "Chameleon + IoT-LAB multi-A8 experiment"
echo "=========================================="
echo "Chameleon IP: ${CHAMELEON_IP}"
echo "IoT-LAB frontend: ${IOTLAB_SITE}.iot-lab.info"
echo "A8 nodes: ${NODE_IDS[*]}"
echo "Rounds: ${NUM_ROUNDS}"
echo "Local epochs: ${LOCAL_EPOCHS}"
echo "Learning rate: ${LEARNING_RATE}"
echo

echo "1) Checking SSH connectivity..."

ssh -i "$CHAMELEON_KEY" \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    "cc@${CHAMELEON_IP}" \
    "echo 'Chameleon SSH OK'"

ssh \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    "${IOTLAB_USER}@${IOTLAB_SITE}.iot-lab.info" \
    "echo 'IoT-LAB frontend SSH OK'"

echo "2) Preparing Chameleon directories..."

ssh -i "$CHAMELEON_KEY" \
  "cc@${CHAMELEON_IP}" \
  "mkdir -p \
     ~/fl-thesis/experiments/iot_numpy_fl \
     ~/fl-thesis/scripts/providers/chameleon \
     ~/fl-thesis/results/iot_numpy_fl"

echo "3) Synchronizing IoT Flower app to Chameleon..."

ssh -i "$CHAMELEON_KEY" \
    "cc@${CHAMELEON_IP}" \
    "mkdir -p ~/fl-thesis/experiments/iot_numpy_fl"

rsync -avz --delete \
    -e "ssh -i ${CHAMELEON_KEY}" \
    "${PROJECT_ROOT}/experiments/iot_numpy_fl/" \
    "cc@${CHAMELEON_IP}:~/fl-thesis/experiments/iot_numpy_fl/"

echo "4) Synchronizing provider scripts to Chameleon..."

ssh -i "$CHAMELEON_KEY" \
    "cc@${CHAMELEON_IP}" \
    "mkdir -p ~/fl-thesis/scripts/providers/chameleon"

rsync -avz \
    -e "ssh -i ${CHAMELEON_KEY}" \
    "${PROJECT_ROOT}/scripts/providers/chameleon/run_iot_multi_remote.sh" \
    "cc@${CHAMELEON_IP}:~/fl-thesis/scripts/providers/chameleon/"

ssh -i "$CHAMELEON_KEY" \
  "cc@${CHAMELEON_IP}" \
  "chmod +x ~/fl-thesis/scripts/providers/chameleon/run_iot_multi_remote.sh"

echo "5) Synchronizing A8 agent..."

bash "${PROJECT_ROOT}/scripts/providers/iotlab/sync_agent.sh" \
    "$IOTLAB_USER" \
    "$IOTLAB_SITE"

echo "6) Checking reserved A8 nodes..."

IOTLAB_FRONTEND="${IOTLAB_USER}@${IOTLAB_SITE}.iot-lab.info"

for NODE_ID in "${NODE_IDS[@]}"; do
    NODE_HOST="node-a8-${NODE_ID}"

    echo "Checking ${NODE_HOST}..."

    ssh "$IOTLAB_FRONTEND" \
        "ssh \
          -o StrictHostKeyChecking=accept-new \
          -o ConnectTimeout=15 \
          root@${NODE_HOST} \
          'set -e
           hostname
           python3 --version
           test -f /home/root/shared/fl-thesis/agent.py
           python3 -m py_compile /home/root/shared/fl-thesis/agent.py
           echo ${NODE_HOST}\ ready'"
done


echo "7) Preparing Chameleon Python environment..."

ssh -i "$CHAMELEON_KEY" \
    "cc@${CHAMELEON_IP}" \
    'bash -s' <<'REMOTE_SETUP'
set -euo pipefail

if [[ ! -d "$HOME/flwr-venv" ]]; then
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip

    python3 -m venv "$HOME/flwr-venv"
fi

source "$HOME/flwr-venv/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$HOME/fl-thesis/experiments/iot_numpy_fl[analysis]"

mkdir -p "$HOME/.flwr"

cat > "$HOME/.flwr/config.toml" <<'EOF'
[superlink.iot-local]
address = "127.0.0.1:9093"
insecure = true
EOF

python -c "import flwr, numpy, matplotlib; print('Runtime ready:', flwr.__version__)"
REMOTE_SETUP

echo "8) Opening Chameleon broker port..."

ssh -i "$CHAMELEON_KEY" \
    "cc@${CHAMELEON_IP}" \
    "sudo firewall-cmd --add-port=8081/tcp --permanent >/dev/null;
     sudo firewall-cmd --reload >/dev/null;
     sudo firewall-cmd --query-port=8081/tcp"


echo "9) Starting A8 agents..."

bash "${PROJECT_ROOT}/scripts/providers/iotlab/start_agents_remote.sh" \
    "$IOTLAB_USER" \
    "$IOTLAB_SITE" \
    "$BROKER_URL" \
    "${NODE_IDS[@]}"

sleep 4

echo "10) Checking agents..."

bash "${PROJECT_ROOT}/scripts/providers/iotlab/check_agents_remote.sh" \
    "$IOTLAB_USER" \
    "$IOTLAB_SITE" \
    "${NODE_IDS[@]}"

echo "11) Running multi-A8 Flower experiment on Chameleon..."

ssh -i "$CHAMELEON_KEY" \
    "cc@${CHAMELEON_IP}" \
    "bash ~/fl-thesis/scripts/providers/chameleon/run_iot_multi_remote.sh \
       '${NUM_ROUNDS}' \
       '${LOCAL_EPOCHS}' \
       '${LEARNING_RATE}' \
       ${NODE_IDS[*]}"

echo "12) Collecting results locally..."

LOCAL_RESULTS="${PROJECT_ROOT}/results/iot_numpy_fl"

mkdir -p "$LOCAL_RESULTS"

rsync -avz \
    -e "ssh -i ${CHAMELEON_KEY}" \
    "cc@${CHAMELEON_IP}:~/fl-thesis/results/iot_numpy_fl/" \
    "${LOCAL_RESULTS}/"

echo
echo "Experiment and result collection completed."
echo "Local results: ${LOCAL_RESULTS}"
