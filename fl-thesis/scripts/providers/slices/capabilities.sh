#!/bin/bash
set -euo pipefail

SLICES_HOST="$1"

ssh -J proxy@bastion2.slices-be.eu ubuntu@"$SLICES_HOST" "
HAS_IPV6=false

if ip -6 route | grep -q '^default'; then
  HAS_IPV6=true
fi

cat <<EOF
{
  \"provider\": \"slices\",
  \"ssh_user\": \"ubuntu\",
  \"private_ipv4\": \"$SLICES_HOST\",
  \"has_global_ipv6\": \$HAS_IPV6,
  \"can_host_superlink_ipv4\": false,
  \"uses_bastion\": true
}
EOF
"
