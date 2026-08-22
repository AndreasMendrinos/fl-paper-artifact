#!/bin/bash
set -euo pipefail

SLICES_HOST="$1"

ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
set -e

cd ~

if [ ! -d ~/miniforge3 ]; then
  echo 'Installing Miniforge...'
  wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  bash Miniforge3-Linux-x86_64.sh -b -p \$HOME/miniforge3
fi

source ~/miniforge3/etc/profile.d/conda.sh

if ! conda env list | grep -q flwr310; then
  echo 'Creating conda env flwr310...'
  conda create -y -n flwr310 python=3.10
fi

conda activate flwr310

cd ~/fl-thesis
pip install --upgrade pip
pip install -e .
"
