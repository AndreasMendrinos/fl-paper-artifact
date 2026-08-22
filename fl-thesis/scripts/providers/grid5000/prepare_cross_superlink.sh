#!/bin/bash
set -euo pipefail

SITE="${1:-lyon}"
RUN_DIR="${2:-$HOME/fl-thesis/logs/cross_test}"

mkdir -p "$RUN_DIR"

JOB_ID="$OAR_JOB_ID"
NODE_HOSTNAME="$(hostname -f)"
NODE_SHORT="${NODE_HOSTNAME%%.*}"
IPV6_NODE="${NODE_SHORT}-ipv6.${SITE}.grid5000.fr"

echo "Grid5000 job id: $JOB_ID"
echo "Node hostname: $NODE_HOSTNAME"
echo "IPv6 DNS name: $IPV6_NODE"

echo "Enabling IPv6..."
sudo-g5k dhclient -6 br0 || true

G5K_IPV6=$(ip -6 addr | awk '/scope global/ {print $2}' | cut -d/ -f1 | head -1)

if [ -z "$G5K_IPV6" ]; then
  echo "ERROR: Could not find global IPv6 address."
  exit 1
fi

echo "$G5K_IPV6" > "$RUN_DIR/g5k_ipv6.txt"
echo "$JOB_ID" > "$RUN_DIR/g5k_job_id.txt"
echo "$NODE_HOSTNAME" > "$RUN_DIR/g5k_node.txt"
echo "$IPV6_NODE" > "$RUN_DIR/g5k_ipv6_dns.txt"

echo "Grid5000 IPv6 address: $G5K_IPV6"
echo "Saved metadata in: $RUN_DIR"
