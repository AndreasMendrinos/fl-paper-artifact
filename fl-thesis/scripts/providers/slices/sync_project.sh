#!/bin/bash
set -euo pipefail

SLICES_HOST="$1"
PROJECT_ROOT="${2:-$HOME/projects/fl-thesis}"

echo "Syncing project to SLICES..."
echo "SLICES_HOST=$SLICES_HOST"
echo "PROJECT_ROOT=$PROJECT_ROOT"

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
cd /home/ubuntu
rm -rf fl-thesis
tar -xzf fl-thesis.tar.gz
chmod +x /home/ubuntu/fl-thesis/scripts/providers/slices/*.sh || true
chmod +x /home/ubuntu/fl-thesis/scripts/orchestration/*.sh || true
chmod +x /home/ubuntu/fl-thesis/scripts/providers/grid5000/*.sh || true
"

echo "SLICES project sync complete."
