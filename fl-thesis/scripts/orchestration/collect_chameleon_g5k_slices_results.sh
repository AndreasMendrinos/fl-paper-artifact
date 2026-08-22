#!/bin/bash
set -euo pipefail

RUN_ID="$1"
CHAMELEON_IP="$2"
CHAMELEON_KEY="$3"
G5K_SITE="$4"
G5K_NODE="$5"
G5K_JOB_ID="$6"
SLICES_HOST="$7"

PROJECT_DIR="$HOME/projects/fl-thesis"
LOCAL_DIR="$PROJECT_DIR/results/$RUN_ID"

mkdir -p "$LOCAL_DIR"/{chameleon,grid5000,slices}

echo "Collecting results for RUN_ID=$RUN_ID"
echo "Destination: $LOCAL_DIR"

echo
echo "1) Collecting Chameleon logs and outputs..."
mkdir -p "$LOCAL_DIR/chameleon"

scp -i "$CHAMELEON_KEY" -r \
  cc@"$CHAMELEON_IP":/home/cc/fl-thesis/logs/"$RUN_ID" \
  "$LOCAL_DIR/chameleon/logs"

scp -i "$CHAMELEON_KEY" -r \
  cc@"$CHAMELEON_IP":/home/cc/fl-thesis/outputs \
  "$LOCAL_DIR/chameleon/outputs"

echo
echo "2) Collecting Grid'5000 SuperNode logs..."
ssh -J ${G5K_USERNAME}@access.grid5000.fr ${G5K_USERNAME}@"${G5K_SITE}.grid5000.fr" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} '
mkdir -p ~/fl-thesis/logs/${RUN_ID}/grid5000_supernodes

cp ~/fl-thesis/g5k_supernode_*.log \
   ~/fl-thesis/logs/${RUN_ID}/grid5000_supernodes/ 2>/dev/null || true

cp ~/fl-thesis/g5k_supernode_*.nohup \
   ~/fl-thesis/logs/${RUN_ID}/grid5000_supernodes/ 2>/dev/null || true

cp ~/fl-thesis/g5k_supernode_*.pid \
   ~/fl-thesis/logs/${RUN_ID}/grid5000_supernodes/ 2>/dev/null || true
'
"

scp -r \
  ${G5K_USERNAME}@access.grid5000.fr:"${G5K_SITE}/fl-thesis/logs/${RUN_ID}" \
  "$LOCAL_DIR/grid5000/logs"

echo
echo "3) Collecting SLICES SuperNode logs..."
ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
mkdir -p ~/fl-thesis/logs/${RUN_ID}/slices_supernodes

cp ~/fl-thesis/supernode_*.log \
   ~/fl-thesis/logs/${RUN_ID}/slices_supernodes/ 2>/dev/null || true

cp ~/fl-thesis/supernode_*.nohup \
   ~/fl-thesis/logs/${RUN_ID}/slices_supernodes/ 2>/dev/null || true
"

scp -J proxy@bastion2.slices-be.eu -r \
  ubuntu@"$SLICES_HOST":/home/ubuntu/fl-thesis/logs/"$RUN_ID" \
  "$LOCAL_DIR/slices/logs"

echo
echo "Done."
echo "Open results with:"
echo "explorer.exe $LOCAL_DIR"