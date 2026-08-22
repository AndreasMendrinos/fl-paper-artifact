#!/bin/bash
set -euo pipefail

G5K_SITE="$1"
G5K_NODE="$2"
G5K_JOB_ID="$3"
SUPERLINK_HOST="$4"
PARTITION_ID="$5"
TOTAL_PARTITIONS="$6"
CLIENTAPPIO_PORT="$7"
RUN_ID="$8"

G5K_USER="${G5K_USERNAME}"
G5K_ACCESS="access.grid5000.fr"
G5K_FRONTEND="${G5K_SITE}.grid5000.fr"

echo "Starting Grid'5000 SuperNode partition ${PARTITION_ID}/${TOTAL_PARTITIONS}"

ssh -J "${G5K_USER}@${G5K_ACCESS}" "${G5K_USER}@${G5K_FRONTEND}" "
export OAR_JOB_ID=${G5K_JOB_ID}

oarsh ${G5K_NODE} bash -s -- \
  '${SUPERLINK_HOST}' \
  '${PARTITION_ID}' \
  '${TOTAL_PARTITIONS}' \
  '${CLIENTAPPIO_PORT}' \
  '${RUN_ID}' <<'REMOTE_SCRIPT'

set -e

SUPERLINK_HOST=\"\$1\"
PARTITION_ID=\"\$2\"
TOTAL_PARTITIONS=\"\$3\"
CLIENTAPPIO_PORT=\"\$4\"
RUN_ID=\"\$5\"

cd ~/fl-thesis
RUN_DIR=\"~/fl-thesis/logs/\${RUN_ID}\"
mkdir -p ~/fl-thesis/logs/\${RUN_ID}

nohup bash scripts/providers/grid5000/launch_supernode.sh \
  \"\$SUPERLINK_HOST\" \
  \"\$PARTITION_ID\" \
  \"\$TOTAL_PARTITIONS\" \
  \"\$CLIENTAPPIO_PORT\" \
  ~/fl-thesis/logs/\${RUN_ID}/g5k_supernode_\${PARTITION_ID}.log \
  > ~/fl-thesis/logs/\${RUN_ID}/g5k_supernode_\${PARTITION_ID}.nohup 2>&1 < /dev/null &

echo \$! > ~/fl-thesis/logs/\${RUN_ID}/g5k_supernode_\${PARTITION_ID}.pid

sleep 2
ps aux | grep flower | grep -v grep || true
ls -lh ~/fl-thesis/logs/\${RUN_ID}/g5k_supernode_\${PARTITION_ID}.* 2>/dev/null || true

REMOTE_SCRIPT
"