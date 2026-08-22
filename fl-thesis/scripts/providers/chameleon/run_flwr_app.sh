#!/bin/bash
set -euo pipefail

RUN_DIR="$1"
RUN_CONFIG="$2"

source /home/cc/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd /home/cc/fl-thesis

mkdir -p ~/.flwr
mkdir -p "$RUN_DIR"

cat > ~/.flwr/config.toml <<EOF
[superlink.chameleon]
address = "127.0.0.1:9093"
insecure = true
EOF

echo "RUN_CONFIG=[$RUN_CONFIG]"

flwr run . chameleon --stream \
  --run-config="$RUN_CONFIG" \
  > "$RUN_DIR/flwr_run.log" 2>&1
