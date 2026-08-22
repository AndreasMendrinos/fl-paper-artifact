#!/usr/bin/env bash
set -euo pipefail

IOTLAB_USER="${1:?Usage: $0 <iotlab-user> <site>}"
IOTLAB_SITE="${2:?Usage: $0 <iotlab-user> <site>}"

FRONTEND="${IOTLAB_USER}@${IOTLAB_SITE}.iot-lab.info"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOCAL_A8_DIR="${PROJECT_ROOT}/experiments/iot_numpy_fl/a8"
REMOTE_DIR="shared/fl-thesis"

if [[ ! -f "${LOCAL_A8_DIR}/agent.py" ]]; then
    echo "ERROR: ${LOCAL_A8_DIR}/agent.py not found."
    exit 1
fi

echo "Creating IoT-LAB shared directory..."
ssh "${FRONTEND}" \
    "mkdir -p ~/${REMOTE_DIR}"

echo "Synchronizing A8 client files..."
rsync -avz --delete \
    "${LOCAL_A8_DIR}/" \
    "${FRONTEND}:~/${REMOTE_DIR}/"

echo "Checking Python 3.8 syntax on the frontend..."
ssh "${FRONTEND}" \
    "python3 -m py_compile ~/${REMOTE_DIR}/agent.py"

echo "IoT-LAB agent synchronized successfully."
