#!/bin/bash
set -euo pipefail

CHAMELEON_IP="$1"
CHAMELEON_KEY="$2"

ssh -i "$CHAMELEON_KEY" cc@"$CHAMELEON_IP" "
IPV4=\$(curl -s ifconfig.me || true)
HAS_IPV6=false

if ip -6 route | grep -q '^default'; then
  HAS_IPV6=true
fi

cat <<EOF
{
  \"provider\": \"chameleon\",
  \"ssh_user\": \"cc\",
  \"public_ipv4\": \"\$IPV4\",
  \"has_global_ipv6\": \$HAS_IPV6,
  \"can_host_superlink_ipv4\": true,
  \"can_reach_grid5000_ipv6\": \$HAS_IPV6
}
EOF
"
