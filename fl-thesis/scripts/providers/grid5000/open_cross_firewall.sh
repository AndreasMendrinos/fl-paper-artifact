#!/bin/bash
set -euo pipefail

SITE="$1"
JOB_ID="$2"
IPV6_DNS="$3"

echo "Opening Grid5000 firewall:"
echo "SITE=$SITE"
echo "JOB_ID=$JOB_ID"
echo "IPV6_DNS=$IPV6_DNS"


curl -i "https://api.grid5000.fr/stable/sites/${SITE}/firewall/${JOB_ID}" \
  -d "[{\"addr\":\"${IPV6_DNS}\",\"port\":9092},{\"addr\":\"${IPV6_DNS}\",\"port\":9093}]" 2>&1
