---
name: recon-tooling-reference
description: Command reference for the recon pipeline's underlying CLI tools - not judgment, just correct invocation
---

# Recon Tooling Reference

Pure command reference, mirroring Strix's `/tooling` skill category
convention (command playbooks for nmap/nuclei/httpx/ffuf/subfinder/naabu/
sqlmap). This is intentionally NOT where judgment calls live — see
`recon/asset_discovery.md` and `triage/ai_triage.md` for that.

## Passive subdomain enumeration
```
subfinder -d example.com -all -recursive -silent -oJ
assetfinder --subs-only example.com
amass enum -passive -d example.com -silent
findomain -t example.com -q
chaos -d example.com -silent          # requires CHAOS_API_KEY
github-subdomains -d example.com -raw # requires GH token
curl -s 'https://crt.sh/?q=%25.example.com&output=json' | jq -r '.[].name_value'
```

## Active DNS / subdomain enumeration (requires active_dns: true)
```
puredns bruteforce wordlist.txt example.com --resolvers resolvers.txt -q
dnsx -d example.com -silent -json
ffuf -w wordlist.txt -u http://IP -H 'Host: FUZZ.example.com' -mc 200,301,302,403
```

## Live host discovery
```
httpx -l hosts.txt -sc -title -server -td -tls-grab -favicon -cl -location -json -silent
```

## URL discovery
```
waybackurls example.com
gau example.com
waymore -i example.com -mode U
katana -u https://example.com -d 3 -jc -kf -silent -jsonl
hakrawler -d 3
arjun -u https://example.com/endpoint -oJ out.json
```

## JavaScript
```
subjs -i https://example.com
curl -s -A 'Mozilla/5.0' https://example.com/app.js
```

## Secrets
```
trufflehog filesystem ./repo --json
```

## Ports
```
naabu -host IP -top-ports 1000 -silent -json
```

## Content discovery (requires directory_discovery: true)
```
ffuf -w common.txt -u https://example.com/FUZZ -mc 200,301,302,403 -json
dirsearch -u https://example.com
feroxbuster -u https://example.com
```

## API discovery
```
kr scan https://example.com/api -w routes.kite -j
```

## Safe template-based checks (requires automated_scanning: true)
```
nuclei -l targets.txt -tags exposure,misconfig,default-login,tech -rl 5 -silent -jsonl
```

## Summary

Every command here corresponds 1:1 to a method in
`api/app/recon/stages/*.py`. If you add a new tool to the pipeline, add its
invocation here too so the reference stays authoritative.
