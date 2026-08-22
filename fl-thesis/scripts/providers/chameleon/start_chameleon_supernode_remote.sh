#!/bin/bash
set -euo pipefail

CHAMELEON_IP="$1"
CHAMELEON_KEY="$2"
G5K_IPV6="$3"
PARTITION_ID="$4"
NUM_PARTITIONS="$5"
CLIENTAPPIO_PORT="${6:-9096}"

echo "Starting Chameleon SuperNode..."
echo "CHAMELEON_IP=$CHAMELEON_IP"
echo "G5K_IPV6=$G5K_IPV6"
echo "PARTITION_ID=$PARTITION_ID"
echo "NUM_PARTITIONS=$NUM_PARTITIONS"
echo "CLIENTAPPIO_PORT=$CLIENTAPPIO_PORT"

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
pkill -9 -f flower-supernode || true
pkill -9 -f flower-superexec || true
sleep 2
"

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
source /home/cc/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd /home/cc/fl-thesis
nohup bash scripts/providers/chameleon/launch_supernode.sh \
  '$G5K_IPV6' \
  '$PARTITION_ID' \
  '$NUM_PARTITIONS' \
  '$CLIENTAPPIO_PORT' \
  /home/cc/fl-thesis/chameleon_supernode.log \
  > /home/cc/fl-thesis/chameleon_supernode.nohup 2>&1 &
"

sleep 3

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "ps aux | grep flower || true"
