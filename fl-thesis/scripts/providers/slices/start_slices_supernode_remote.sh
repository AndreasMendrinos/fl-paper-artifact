#!/bin/bash
set -euo pipefail

SLICES_HOST="$1"
SUPERLINK_HOST="$2"
PARTITION_ID="$3"
TOTAL_PARTITIONS="$4"
CLIENTAPPIO_PORT="$5"
RUN_ID="$6"

echo "Starting SLICES SuperNode partition ${PARTITION_ID}/${TOTAL_PARTITIONS}"

ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
set -e

cd ~/fl-thesis
RUN_DIR=~/fl-thesis/logs/${RUN_ID}
mkdir -p \"\$RUN_DIR\"

source ~/miniforge3/etc/profile.d/conda.sh
conda activate flwr310

nohup bash scripts/providers/slices/launch_supernode.sh \
  '$SUPERLINK_HOST' \
  '$PARTITION_ID' \
  '$TOTAL_PARTITIONS' \
  '$CLIENTAPPIO_PORT' \
  \"\$RUN_DIR/slices_supernode_${PARTITION_ID}.log\" \
  > \"\$RUN_DIR/slices_supernode_${PARTITION_ID}.nohup\" 2>&1 < /dev/null &

echo \$! > \"\$RUN_DIR/slices_supernode_${PARTITION_ID}.pid\"

sleep 2
ps aux | grep flower | grep -v grep || true
"