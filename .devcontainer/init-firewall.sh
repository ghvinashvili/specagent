#!/usr/bin/env bash
# Egress allowlist for the dev container (needs NET_ADMIN and NET_RAW). Everything not listed is rejected.
set -euo pipefail
ALLOWED_DOMAINS=(api.anthropic.com github.com api.github.com pypi.org files.pythonhosted.org releases.astral.sh registry.npmjs.org code.claude.com platform.claude.com)
ALLOWED_CIDRS=(172.16.0.0/12)   # container networks, for the OpenTelemetry collector

iptables -F OUTPUT
ipset destroy allowed 2>/dev/null || true
ipset create allowed hash:ip
for domain in "${ALLOWED_DOMAINS[@]}"; do
  for ip in $(getent ahostsv4 "$domain" | awk '{print $1}' | sort -u); do
    ipset add allowed "$ip" -exist
  done
done
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -m set --match-set allowed dst -j ACCEPT
for cidr in "${ALLOWED_CIDRS[@]}"; do
  iptables -A OUTPUT -d "$cidr" -j ACCEPT
done
iptables -A OUTPUT -j REJECT
echo "egress restricted to: ${ALLOWED_DOMAINS[*]} ${ALLOWED_CIDRS[*]}"
