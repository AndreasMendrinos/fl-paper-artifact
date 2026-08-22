#!/bin/bash
set -euo pipefail

SLICES_HOST="$1"
G5K_IPV6="$2"
NUM_CLIENTS="${3:-2}"

echo "Starting $NUM_CLIENTS SLICES SuperNodes..."
echo "SLICES_HOST=$SLICES_HOST"
echo "G5K_IPV6=$G5K_IPV6"

ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
pkill -9 -f flower-supernode || true
pkill -9 -f flower-superexec || true
sleep 2
ps aux | grep flower || true
" || true


for ((i=0; i<NUM_CLIENTS; i++)); do
  PORT=$((9094 + i))
  echo "Starting SuperNode $i on port $PORT"

  ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
source ~/miniforge3/etc/profile.d/conda.sh
conda activate flwr310
cd ~/fl-thesis
nohup bash scripts/providers/slices/launch_supernode.sh '$G5K_IPV6' '$i' '$NUM_CLIENTS' '$PORT' ~/fl-thesis/supernode_${i}.log > ~/fl-thesis/supernode_${i}.nohup 2>&1 &
"
done

sleep 3

ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "ps aux | grep flower"
