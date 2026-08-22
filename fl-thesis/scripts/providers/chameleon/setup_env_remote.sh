#!/bin/bash
set -euo pipefail

CHAMELEON_IP="$1"
CHAMELEON_KEY="$2"

echo "Setting up Chameleon environment..."
echo "CHAMELEON_IP=$CHAMELEON_IP"

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
set -e

sudo apt update
sudo apt install -y python3-pip python3-venv wget git

sudo firewall-cmd --add-port=9092/tcp --permanent || true
sudo firewall-cmd --add-port=9093/tcp --permanent || true
sudo firewall-cmd --reload || true

cd /home/cc

if [ ! -d /home/cc/miniforge3 ]; then
  echo 'Installing Miniforge...'
  wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  bash Miniforge3-Linux-x86_64.sh -b -p /home/cc/miniforge3
fi

source /home/cc/miniforge3/etc/profile.d/conda.sh

if ! conda env list | grep -q flwr310; then
  echo 'Creating conda env flwr310...'
  conda create -y -n flwr310 python=3.10
fi

conda activate flwr310

cd /home/cc/fl-thesis
pip install --upgrade pip
pip install -e .
"

echo "Chameleon environment setup complete."
