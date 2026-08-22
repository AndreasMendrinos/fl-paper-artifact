#!/bin/bash
set -euo pipefail

RUN_DIR="$1"

source ~/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd ~/fl-thesis

flower-superlink \
  --insecure \
  --fleet-api-address 0.0.0.0:9092 \
  --control-api-address 0.0.0.0:9093 \
  > "$RUN_DIR/superlink.log" 2>&1
