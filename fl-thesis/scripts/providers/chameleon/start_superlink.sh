#!/bin/bash
set -euo pipefail

RUN_DIR="${1:-/home/cc/fl-thesis/logs/chameleon_cross}"

mkdir -p "$RUN_DIR"

source /home/cc/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd /home/cc/fl-thesis

pkill -9 -f flower-superlink || true
pkill -9 -f flower-superexec || true
sleep 2

nohup flower-superlink \
  --insecure \
  --fleet-api-address "0.0.0.0:9092" \
  --control-api-address "127.0.0.1:9093" \
  > "$RUN_DIR/superlink.log" 2>&1 &

echo $! > "$RUN_DIR/superlink.pid"

sleep 3
ss -tlnp | grep 909 || true
