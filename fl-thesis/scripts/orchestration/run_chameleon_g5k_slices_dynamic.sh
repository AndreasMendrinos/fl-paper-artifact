#!/bin/bash
set -euo pipefail

CHAMELEON_IP="$1"
CHAMELEON_KEY="$2"
G5K_SITE="$3"
G5K_NODE="$4"
G5K_JOB_ID="$5"
SLICES_HOST="$6"

G5K_CLIENTS="${7:-1}"
SLICES_CLIENTS="${8:-1}"

NUM_CLIENTS=$((G5K_CLIENTS + SLICES_CLIENTS))

PROJECT_DIR="$HOME/projects/fl-thesis"

RUN_ID="chameleon_g5k_slices_${G5K_SITE}_${G5K_JOB_ID}_$(date +%Y%m%d_%H%M%S)"
RUN_DIR="/home/cc/fl-thesis/logs/${RUN_ID}"

RUN_CONFIG="num-server-rounds=4 num-clients=${NUM_CLIENTS} local-epochs=2 learning-rate=0.01 batch-size=16 partition-strategy=\\\"dirichlet\\\" dirichlet-alpha=0.8"

echo "=== Chameleon + Grid5000 + SLICES deployment ==="
echo "CHAMELEON_IP=$CHAMELEON_IP"
echo "G5K_SITE=$G5K_SITE"
echo "G5K_NODE=$G5K_NODE"
echo "G5K_JOB_ID=$G5K_JOB_ID"
echo "SLICES_HOST=$SLICES_HOST"
echo "RUN_ID=$RUN_ID"

cd "$PROJECT_DIR"

echo
echo "1) Sync project to Chameleon..."
bash scripts/providers/chameleon/sync_project.sh "$CHAMELEON_IP" "$CHAMELEON_KEY" "$PROJECT_DIR"

echo
echo "2) Setup Chameleon environment..."
bash scripts/providers/chameleon/setup_env_remote.sh "$CHAMELEON_IP" "$CHAMELEON_KEY"

echo
echo "3) Sync project to SLICES..."
bash scripts/providers/slices/sync_project.sh "$SLICES_HOST" "$PROJECT_DIR"

echo
echo "4) Setup SLICES environment..."
bash scripts/providers/slices/setup_env_remote.sh "$SLICES_HOST"

echo
echo "5) Sync scripts to Grid'5000..."
rsync -avz "$PROJECT_DIR/scripts/" \
  "${G5K_USERNAME}@access.grid5000.fr:${G5K_SITE}/fl-thesis/scripts/"

echo
echo "6) Start SuperLink on Chameleon..."
ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
cd /home/cc/fl-thesis
bash scripts/providers/chameleon/start_superlink.sh '$RUN_DIR'
"

echo
echo "7) Test WSL -> Chameleon connectivity..."
nc -vz -w 5 "$CHAMELEON_IP" 9092

echo
echo "8) Test Grid'5000 -> Chameleon connectivity..."
ssh -J ${G5K_USERNAME}@access.grid5000.fr ${G5K_USERNAME}@"${G5K_SITE}.grid5000.fr" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} 'nc -vz -w 5 ${CHAMELEON_IP} 9092'
"

echo
echo "9) Test SLICES -> Chameleon connectivity..."
ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" \
  "nc -vz -w 5 ${CHAMELEON_IP} 9092"

echo "Stopping old Grid'5000 SuperNodes..."
ssh -J ${G5K_USERNAME}@access.grid5000.fr ${G5K_USERNAME}@"${G5K_SITE}.grid5000.fr" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} bash -lc '
pgrep -af flower || true
pkill -9 -x flower-supernode || true
pkill -9 -x flower-superexec || true
sleep 2
pgrep -af flower || true
'
"

echo
echo "Stopping old SLICES SuperNodes..."
ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
pgrep -af flower || true
pkill -9 -f flower-supernode || true
pkill -9 -f flower-superexec || true
sleep 2
pgrep -af flower || true
" || true


echo
echo "10) Start Grid'5000 SuperNode: partition 0/2..."
PARTITION_ID=0
for ((i=0; i<G5K_CLIENTS; i++)); do
  PORT=$((9094 + i))

  bash scripts/providers/grid5000/start_g5k_supernode_remote.sh \
    "$G5K_SITE" \
    "$G5K_NODE" \
    "$G5K_JOB_ID" \
    "$CHAMELEON_IP" \
    "$PARTITION_ID" \
    "$NUM_CLIENTS" \
    "$PORT" \
    "$RUN_ID"

  PARTITION_ID=$((PARTITION_ID + 1))
done

echo
echo "11) Start SLICES SuperNode: partition 1/2..."
for ((i=0; i<SLICES_CLIENTS; i++)); do
  PORT=$((9104 + i))

  bash scripts/providers/slices/start_slices_supernode_remote.sh \
    "$SLICES_HOST" \
    "$CHAMELEON_IP" \
    "$PARTITION_ID" \
    "$NUM_CLIENTS" \
    "$PORT" \
    "$RUN_ID"

  PARTITION_ID=$((PARTITION_ID + 1))
done



echo
echo "12) Run Flower app on Chameleon..."
ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
cd /home/cc/fl-thesis
bash scripts/providers/chameleon/run_flwr_app.sh '$RUN_DIR' \"$RUN_CONFIG\"
"

echo
echo "Finished."
echo "Chameleon logs: $RUN_DIR"
