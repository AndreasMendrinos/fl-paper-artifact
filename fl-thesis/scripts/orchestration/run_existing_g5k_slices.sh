#!/bin/bash
set -euo pipefail

SLICES_HOST="$1"
G5K_SITE="${2:-lyon}"
G5K_NODE="$3"
G5K_JOB_ID="$4"
NUM_CLIENTS="${5:-2}"

G5K_USER="${G5K_USERNAME}"
G5K_ACCESS="access.grid5000.fr"
G5K_FRONTEND="${G5K_SITE}.grid5000.fr"

PROJECT_DIR="$HOME/projects/fl-thesis"
RUN_ID="cross_${G5K_SITE}_${G5K_JOB_ID}_$(date +%Y%m%d_%H%M%S)"
RUN_DIR="\$HOME/fl-thesis/logs/${RUN_ID}"


RUN_CONFIG="num-server-rounds=4 num-clients=${NUM_CLIENTS} local-epochs=2 learning-rate=0.01 batch-size=16 partition-strategy=\\\"dirichlet\\\" dirichlet-alpha=0.5"


echo "=== Cross-testbed deployment ==="
echo "SLICES_HOST=$SLICES_HOST"
echo "G5K_SITE=$G5K_SITE"
echo "G5K_NODE=$G5K_NODE"
echo "G5K_JOB_ID=$G5K_JOB_ID"
echo "NUM_CLIENTS=$NUM_CLIENTS"
echo "RUN_ID=$RUN_ID"

echo
echo "1) Sync project to SLICES..."
cd "$HOME/projects"
rm -f fl-thesis.tar.gz
tar --exclude='fl-thesis/outputs' \
    --exclude='fl-thesis/logs' \
    --exclude='fl-thesis/.git' \
    --exclude='__pycache__' \
    -czf fl-thesis.tar.gz fl-thesis

scp -J proxy@bastion2.slices-be.eu \
  fl-thesis.tar.gz \
  ubuntu@"$SLICES_HOST":/home/ubuntu/fl-thesis.tar.gz

ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
cd ~
rm -rf fl-thesis
tar -xzf fl-thesis.tar.gz
chmod +x ~/fl-thesis/scripts/providers/slices/*.sh
chmod +x ~/fl-thesis/scripts/orchestration/*.sh
"

echo
echo "2) Setup SLICES environment..."
cd "$PROJECT_DIR"
bash scripts/providers/slices/setup_env_remote.sh "$SLICES_HOST"

echo
echo "3) Sync scripts to Grid'5000..."
rsync -avz "$PROJECT_DIR/scripts/" \
  "${G5K_USER}@${G5K_ACCESS}:${G5K_SITE}/fl-thesis/scripts/"

echo
echo "4) Prepare Grid'5000 node: IPv6..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} '
cd ~/fl-thesis
mkdir -p ${RUN_DIR}
bash scripts/providers/grid5000/prepare_cross_superlink.sh ${G5K_SITE} ${RUN_DIR}
'
"

echo
echo "5) Read Grid'5000 IPv6 metadata..."
G5K_IPV6=$(ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" \
  "cat ~/fl-thesis/logs/${RUN_ID}/g5k_ipv6.txt")

G5K_IPV6_DNS=$(ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" \
  "cat ~/fl-thesis/logs/${RUN_ID}/g5k_ipv6_dns.txt")

echo "G5K_IPV6=$G5K_IPV6"
echo "G5K_IPV6_DNS=$G5K_IPV6_DNS"

echo
echo "6) Open Grid'5000 firewall..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
cd ~/fl-thesis
bash scripts/providers/grid5000/open_cross_firewall.sh ${G5K_SITE} ${G5K_JOB_ID} ${G5K_IPV6_DNS}
"

echo
echo "7) Start SuperLink on Grid'5000..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} '
cd ~/fl-thesis
bash scripts/providers/grid5000/launch_superlink_ipv6.sh ${RUN_DIR}
ss -tlnp | grep 909 || true
'
"

echo
echo "8) Test SLICES -> Grid'5000 connectivity..."
#ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" \
#  "nc -vz -w 5 ${G5K_IPV6} 9092"
echo "Waiting for SuperLink to accept connections..."

for attempt in {1..12}; do
  if ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" \
    "nc -vz -w 5 ${G5K_IPV6} 9092"; then
    echo "SuperLink is reachable from SLICES."
    break
  fi

  echo "Attempt $attempt failed. Retrying in 5 seconds..."
  sleep 5

  if [ "$attempt" -eq 12 ]; then
    echo "ERROR: SuperLink did not become reachable from SLICES."
    exit 1
  fi
done


echo
echo "9) Start SLICES SuperNodes..."
bash scripts/orchestration/start_slices_supernodes.sh "$SLICES_HOST" "$G5K_IPV6" "$NUM_CLIENTS"

echo
echo "10) Run Flower app on Grid'5000..."
ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
export OAR_JOB_ID=${G5K_JOB_ID}
oarsh ${G5K_NODE} '
cd ~/fl-thesis
bash scripts/providers/grid5000/run_cross_flwr_app.sh ${RUN_DIR} \"${RUN_CONFIG}\"
'
"

echo
echo "Cross-testbed run finished."
echo "Grid'5000 logs: ~/fl-thesis/logs/${RUN_ID}"
