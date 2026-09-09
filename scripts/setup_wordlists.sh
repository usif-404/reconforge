#!/usr/bin/env bash
# One-time setup for wordlists referenced by the recon stages
# (subdomain brute force, content discovery, kiterunner routes).
set -euo pipefail

mkdir -p wordlists
cd wordlists

[ -f subdomains.txt ] || curl -sSL -o subdomains.txt \
  https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt

[ -f resolvers.txt ] || curl -sSL -o resolvers.txt \
  https://raw.githubusercontent.com/trickest/resolvers/main/resolvers.txt

[ -f common.txt ] || curl -sSL -o common.txt \
  https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt

echo "Wordlists ready in ./wordlists — mount this into the containers if you"
echo "change docker-compose.yml's volume paths from the /wordlists default."
