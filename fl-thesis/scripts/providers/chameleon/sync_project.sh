#!/bin/bash
set -euo pipefail

CHAMELEON_IP="$1"
CHAMELEON_KEY="$2"

PROJECT_ROOT="${3:-$HOME/projects/fl-thesis}"
REMOTE_DIR="/home/cc/fl-thesis"

echo "Syncing project to Chameleon..."
echo "CHAMELEON_IP=$CHAMELEON_IP"
echo "PROJECT_ROOT=$PROJECT_ROOT"

cd "$HOME/projects"

rm -f fl-thesis.tar.gz

tar --exclude='fl-thesis/outputs' \
    --exclude='fl-thesis/logs' \
    --exclude='fl-thesis/.git' \
    --exclude='__pycache__' \
    -czf fl-thesis.tar.gz fl-thesis

scp -i "$CHAMELEON_KEY" fl-thesis.tar.gz cc@"$CHAMELEON_IP":/home/cc/fl-thesis.tar.gz

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
cd /home/cc
rm -rf fl-thesis
tar -xzf fl-thesis.tar.gz
chmod +x ${REMOTE_DIR}/scripts/providers/chameleon/*.sh || true
chmod +x ${REMOTE_DIR}/scripts/providers/slices/*.sh || true
chmod +x ${REMOTE_DIR}/scripts/providers/grid5000/*.sh || true
chmod +x ${REMOTE_DIR}/scripts/orchestration/*.sh || true
"

echo "Chameleon project sync complete."
