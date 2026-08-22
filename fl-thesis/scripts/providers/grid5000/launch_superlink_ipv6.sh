#!/bin/bash
set -euo pipefail

RUN_DIR="${1:-$HOME/fl-thesis/logs/cross_test}"

mkdir -p "$RUN_DIR"

source ~/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd ~/fl-thesis

pkill -f flower-superlink || true
sleep 5
#pkill -f flower-superexec || true


nohup flower-superlink \
  --insecure \
  --fleet-api-address "[::]:9092" \
  --control-api-address "[::]:9093" \
  > "$RUN_DIR/superlink.log" 2>&1 &
  
echo $! > "$RUN_DIR/superlink.pid"

echo "Started SuperLink. PID: $(cat "$RUN_DIR/superlink.pid")"
echo "Log: $RUN_DIR/superlink.log"
