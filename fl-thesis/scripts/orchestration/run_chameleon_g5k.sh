#!/bin/bash

set -euo pipefail

CHAMELEON_IP="$1"
CHAMELEON_KEY="$2"
G5K_SITE="$3"
G5K_NODE="$4"
G5K_JOB_ID="$5"
G5K_CLIENTS="${6:-2}"

NUM_CLIENTS="$G5K_CLIENTS"

PROJECT_DIR="$HOME/projects/fl-thesis"

RUN_ID="chameleon_g5k_${G5K_SITE}_${G5K_JOB_ID}_$(date +%Y%m%d_%H%M%S)"
RUN_DIR="/home/cc/fl-thesis/logs/${RUN_ID}"

RUN_CONFIG="num-server-rounds=4 num-clients=${NUM_CLIENTS} local-epochs=2 learning-rate=0.01 batch-size=16 partition-strategy=\\\"dirichlet\\\" dirichlet-alpha=0.8"

echo "=========================================="
echo "Chameleon + Grid'5000 FL deployment"
echo "=========================================="
echo "CHAMELEON_IP=$CHAMELEON_IP"
echo "G5K_SITE=$G5K_SITE"
echo "G5K_NODE=$G5K_NODE"
echo "G5K_JOB_ID=$G5K_JOB_ID"
echo "G5K_CLIENTS=$G5K_CLIENTS"
echo "RUN_ID=$RUN_ID"
echo

TOTAL_START=$(date +%s)

cd "$PROJECT_DIR"

echo
echo "1) Sync project to Chameleon..."
START=$(date +%s)

bash scripts/providers/chameleon/sync_project.sh \
  "$CHAMELEON_IP" \
  "$CHAMELEON_KEY" \
  "$PROJECT_DIR"

END=$(date +%s)
echo "TIMING sync_chameleon=$((END - START))s"

echo
echo "2) Setup Chameleon environment..."
START=$(date +%s)

bash scripts/providers/chameleon/setup_env_remote.sh \
  "$CHAMELEON_IP" \
  "$CHAMELEON_KEY"

END=$(date +%s)
echo "TIMING setup_chameleon=$((END - START))s"

echo
echo "3) Sync scripts to Grid'5000..."
START=$(date +%s)

rsync -avz "$PROJECT_DIR/scripts/" \
  "${G5K_USERNAME}@access.grid5000.fr:${G5K_SITE}/fl-thesis/scripts/"

END=$(date +%s)
echo "TIMING sync_grid5000=$((END - START))s"

echo
echo "4) Start SuperLink on Chameleon..."
START=$(date +%s)

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
cd /home/cc/fl-thesis
bash scripts/providers/chameleon/start_superlink.sh '$RUN_DIR'
"

END=$(date +%s)
echo "TIMING start_superlink=$((END - START))s"

echo
echo "5) Test local -> Chameleon connectivity..."

nc -vz -w 5 "$CHAMELEON_IP" 9092

echo
echo "6) Test Grid'5000 -> Chameleon connectivity..."
START=$(date +%s)

ssh -J ${G5K_USERNAME}@access.grid5000.fr \
  ${G5K_USERNAME}@"${G5K_SITE}.grid5000.fr" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} 'nc -vz -w 5 ${CHAMELEON_IP} 9092'
"

END=$(date +%s)
echo "TIMING connectivity_g5k_chameleon=$((END - START))s"

echo
echo "7) Stop old Grid'5000 SuperNodes..."

ssh -J ${G5K_USERNAME}@access.grid5000.fr \
  ${G5K_USERNAME}@"${G5K_SITE}.grid5000.fr" "
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
echo "8) Start ${G5K_CLIENTS} Grid'5000 SuperNode(s)..."
START=$(date +%s)

PARTITION_ID=0

for ((i=0; i<G5K_CLIENTS; i++)); do
  PORT=$((9094 + i))

  echo \
    "Starting Grid'5000 client $((i + 1))/${G5K_CLIENTS}, partition ${PARTITION_ID}/${NUM_CLIENTS}"

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

END=$(date +%s)
echo "TIMING start_g5k_clients=$((END - START))s"

echo
echo "9) Run Flower app on Chameleon..."
FL_START=$(date +%s)

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
cd /home/cc/fl-thesis

bash scripts/providers/chameleon/run_flwr_app.sh \
  '$RUN_DIR' \
  \"$RUN_CONFIG\"
"

FL_END=$(date +%s)

echo "TIMING fl_execution=$((FL_END - FL_START))s"

TOTAL_END=$(date +%s)

echo
echo "=========================================="
echo "Experiment finished successfully"
echo "=========================================="
echo "RUN_ID=$RUN_ID"
echo "Chameleon logs: $RUN_DIR"
echo "FL execution time: $((FL_END - FL_START)) s"
echo "Total script time: $((TOTAL_END - TOTAL_START)) s"