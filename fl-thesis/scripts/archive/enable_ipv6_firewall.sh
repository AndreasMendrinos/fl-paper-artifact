#!/bin/bash
set -euo pipefail

SITE="$1"
JOB_ID="$2"
NODE_HOSTNAME="$3"

NODE_SHORT="${NODE_HOSTNAME%%.*}"
IPV6_NODE="${NODE_SHORT}-ipv6.${SITE}.grid5000.fr"

sudo-g5k dhclient -6 br0 || true

curl -i "https://api.grid5000.fr/stable/sites/${SITE}/firewall/${JOB_ID}" \
  -d "[{\"addr\":\"${IPV6_NODE}\",\"port\":9092},{\"addr\":\"${IPV6_NODE}\",\"port\":9093}]"

ip -6 addr | awk '/scope global/ {print $2}' | cut -d/ -f1 | head -1
