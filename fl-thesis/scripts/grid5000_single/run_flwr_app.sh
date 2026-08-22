#!/bin/bash
set -euo pipefail

SUPERLINK_NODE="$1"
RUN_DIR="$2"
RUN_CONFIG="$3"

PROJECT_DIR="$HOME/fl-thesis"

source ~/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd "$PROJECT_DIR"

mkdir -p ~/.flwr

cp ~/.flwr/config.toml "$RUN_DIR/config_backup.toml" 2>/dev/null || true

cat > ~/.flwr/config.toml <<EOF
[superlink.g5k]
address = "${SUPERLINK_NODE}:9093"
insecure = true
EOF

flwr run . g5k --stream \
  --run-config="$RUN_CONFIG" \
  > "$RUN_DIR/flwr_run.log" 2>&1

LATEST_OUTPUT_DIR=$(find "$PROJECT_DIR/outputs" -mindepth 2 -maxdepth 2 -type d | sort | tail -1)

echo "Latest output directory: $LATEST_OUTPUT_DIR" | tee -a "$RUN_DIR/flwr_run.log"

python -m fl_thesis.plot_metrics --run-dir "$LATEST_OUTPUT_DIR" \
  >> "$RUN_DIR/flwr_run.log" 2>&1
