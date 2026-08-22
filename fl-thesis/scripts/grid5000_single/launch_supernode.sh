#!/bin/bash
set -euo pipefail

SUPERLINK_NODE="$1"
PARTITION_ID="$2"
NUM_PARTITIONS="$3"
RUN_DIR="$4"

source ~/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd ~/fl-thesis

flower-supernode \
  --insecure \
  --superlink "${SUPERLINK_NODE}:9092" \
  --clientappio-api-address 127.0.0.1:9094 \
  --node-config "partition-id=${PARTITION_ID} num-partitions=${NUM_PARTITIONS}" \
  > "$RUN_DIR/supernode_${PARTITION_ID}.log" 2>&1
