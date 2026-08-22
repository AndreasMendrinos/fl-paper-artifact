#!/bin/bash
set -euo pipefail

#RUN_DIR="$1"
#RUN_CONFIG="$2"
RUN_DIR="${1:-$HOME/fl-thesis/logs/cross_test}"
RUN_CONFIG="${2:-num-server-rounds=3 num-clients=2 local-epochs=2 learning-rate=0.01 batch-size=16 partition-strategy='iid'}"

source ~/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd ~/fl-thesis

mkdir -p ~/.flwr

cat > ~/.flwr/config.toml <<EOF
[superlink.cross]
address = "[::1]:9093"
insecure = true
EOF

echo "RUN_CONFIG=[$RUN_CONFIG]"
flwr run . cross --stream \
  --run-config="$RUN_CONFIG" \
  > "$RUN_DIR/flwr_run.log" 2>&1
echo "COMMAND:"
echo flwr run . cross --stream "--run-config=$RUN_CONFIG"


LATEST_OUTPUT_DIR=$(find "$HOME/fl-thesis/outputs" -mindepth 2 -maxdepth 2 -type d | sort | tail -1)

echo "Latest output directory: $LATEST_OUTPUT_DIR" | tee -a "$RUN_DIR/flwr_run.log"

python -m fl_thesis.plot_metrics --run-dir "$LATEST_OUTPUT_DIR" \
  >> "$RUN_DIR/flwr_run.log" 2>&1
