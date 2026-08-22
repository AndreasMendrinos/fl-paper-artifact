#!/bin/bash
set -euo pipefail

SUPERLINK_IPV6="$1"
PARTITION_ID="$2"
NUM_PARTITIONS="$3"
CLIENTAPPIO_PORT="$4"
LOG_FILE="$5"

source /home/cc/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd /home/cc/fl-thesis

flower-supernode \
  --insecure \
  --superlink "[${SUPERLINK_IPV6}]:9092" \
  --clientappio-api-address "127.0.0.1:${CLIENTAPPIO_PORT}" \
  --node-config "partition-id=${PARTITION_ID} num-partitions=${NUM_PARTITIONS}" \
  > "$LOG_FILE" 2>&1
  
