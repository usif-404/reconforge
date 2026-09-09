#!/usr/bin/env bash
# Run once on the VPS before docker compose up. Your box (t3.large, 2 vCPU,
# 7.6GB RAM, no swap) will OOM under katana + nuclei + Postgres + Redis +
# Python workers running concurrently without this.
set -euo pipefail

if swapon --show | grep -q .; then
  echo "Swap already active:"
  swapon --show
  exit 0
fi

SWAP_SIZE_GB="${1:-4}"

echo "Creating ${SWAP_SIZE_GB}G swapfile at /swapfile..."
sudo fallocate -l "${SWAP_SIZE_GB}G" /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

if ! grep -q '/swapfile' /etc/fstab; then
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# Bias toward keeping RAM for the active worker set rather than proactively
# swapping — on a 2 vCPU box you want swap as an OOM safety net, not as
# routinely-used memory (that would make everything slower under load).
sudo sysctl -w vm.swappiness=10
if ! grep -q '^vm.swappiness' /etc/sysctl.conf 2>/dev/null; then
  echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
fi

echo
free -h
echo
echo "Done. Swap is a safety net for OOM spikes (e.g. a katana crawl on a"
echo "large site) — it is not a substitute for the concurrency limits in"
echo "docker-compose.yml. Keep those as the primary control."
