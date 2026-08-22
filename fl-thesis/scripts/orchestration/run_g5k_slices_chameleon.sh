#!/bin/bash
set -euo pipefail

SLICES_HOST="$1"
CHAMELEON_IP="$2"
CHAMELEON_KEY="$3"
G5K_SITE="$4"
G5K_NODE="$5"
G5K_JOB_ID="$6"

G5K_USER="${G5K_USERNAME}"
G5K_ACCESS="access.grid5000.fr"
G5K_FRONTEND="${G5K_SITE}.grid5000.fr"

NUM_CLIENTS=2
PROJECT_DIR="$HOME/projects/fl-thesis"

RUN_ID="cross_${G5K_SITE}_slices_chameleon_${G5K_JOB_ID}_$(date +%Y%m%d_%H%M%S)"
RUN_DIR="\$HOME/fl-thesis/logs/${RUN_ID}"

RUN_CONFIG="num-server-rounds=4 num-clients=${NUM_CLIENTS} local-epochs=2 learning-rate=0.01 batch-size=16 partition-strategy=\\\"iid\\\""

echo "=== Grid5000 + SLICES + Chameleon deployment ==="
echo "SLICES_HOST=$SLICES_HOST"
echo "CHAMELEON_IP=$CHAMELEON_IP"
echo "G5K_SITE=$G5K_SITE"
echo "G5K_NODE=$G5K_NODE"
echo "G5K_JOB_ID=$G5K_JOB_ID"
echo "RUN_ID=$RUN_ID"

cd "$PROJECT_DIR"

echo
echo "1) Sync project to SLICES..."
bash scripts/providers/slices/sync_project.sh "$SLICES_HOST" "$PROJECT_DIR"

echo
echo "2) Setup SLICES environment..."
bash scripts/providers/slices/setup_env_remote.sh "$SLICES_HOST"

echo
echo "3) Sync project to Chameleon..."
bash scripts/providers/chameleon/sync_project.sh "$CHAMELEON_IP" "$CHAMELEON_KEY" "$PROJECT_DIR"

echo
echo "4) Setup Chameleon environment..."
bash scripts/providers/chameleon/setup_env_remote.sh "$CHAMELEON_IP" "$CHAMELEON_KEY"

echo
echo "5) Sync scripts to Grid'5000..."
rsync -avz "$PROJECT_DIR/scripts/" \
  "${G5K_USER}@${G5K_ACCESS}:${G5K_SITE}/fl-thesis/scripts/"

echo
echo "6) Prepare Grid'5000 node: IPv6..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} '
cd ~/fl-thesis
mkdir -p ${RUN_DIR}
bash scripts/providers/grid5000/prepare_cross_superlink.sh ${G5K_SITE} ${RUN_DIR}
'
"

echo
echo "7) Read Grid'5000 IPv6 metadata..."
G5K_IPV6=$(ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" \
  "cat ~/fl-thesis/logs/${RUN_ID}/g5k_ipv6.txt")

G5K_IPV6_DNS=$(ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" \
  "cat ~/fl-thesis/logs/${RUN_ID}/g5k_ipv6_dns.txt")

echo "G5K_IPV6=$G5K_IPV6"
echo "G5K_IPV6_DNS=$G5K_IPV6_DNS"

echo
echo "8) Open Grid'5000 firewall..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
cd ~/fl-thesis
bash scripts/providers/grid5000/open_cross_firewall.sh ${G5K_SITE} ${G5K_JOB_ID} ${G5K_IPV6_DNS}
"

echo
echo "9) Start SuperLink on Grid'5000..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} '
cd ~/fl-thesis
bash scripts/providers/grid5000/launch_superlink_ipv6.sh ${RUN_DIR}
ss -tlnp | grep 909 || true
'
"

echo
echo "10) Test SLICES -> Grid'5000 connectivity..."
for attempt in {1..12}; do
  if ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" \
    "nc -vz -w 5 ${G5K_IPV6} 9092"; then
    echo "SLICES can reach SuperLink."
    break
  fi

  echo "SLICES attempt $attempt failed. Retrying in 5 seconds..."
  sleep 5

  if [ "$attempt" -eq 12 ]; then
    echo "ERROR: SuperLink not reachable from SLICES."
    exit 1
  fi
done

echo
echo "11) Test Chameleon -> Grid'5000 connectivity..."
for attempt in {1..12}; do
  if ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" \
    "nc -vz -w 5 ${G5K_IPV6} 9092"; then
    echo "Chameleon can reach SuperLink."
    break
  fi

  echo "Chameleon attempt $attempt failed. Retrying in 5 seconds..."
  sleep 5

  if [ "$attempt" -eq 12 ]; then
    echo "ERROR: SuperLink not reachable from Chameleon."
    exit 1
  fi
done

echo
echo "12) Start SLICES SuperNode: partition 0/2..."
bash scripts/providers/slices/start_slices_supernode_remote.sh \
  "$SLICES_HOST" \
  "$G5K_IPV6" \
  0 \
  2 \
  9094

echo
echo "13) Start Chameleon SuperNode: partition 1/2..."
bash scripts/providers/chameleon/start_chameleon_supernode_remote.sh \
  "$CHAMELEON_IP" \
  "$CHAMELEON_KEY" \
  "$G5K_IPV6" \
  1 \
  2 \
  9096

echo
echo "14) Run Flower app on Grid'5000..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} '
cd ~/fl-thesis
bash -x scripts/providers/grid5000/run_cross_flwr_app.sh ${RUN_DIR} \"${RUN_CONFIG}\"
'
"

echo
echo "Cross-testbed run finished."
echo "Grid'5000 logs: ~/fl-thesis/logs/${RUN_ID}"
