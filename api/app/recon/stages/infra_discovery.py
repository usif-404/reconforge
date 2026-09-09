"""ASN/BGP/WHOIS/PTR discovery — pivoting from known assets to owned ranges."""
from __future__ import annotations

import json
import urllib.request

from app.recon.stages.base import ReconStage
from app.scope.manager import Action


class InfraDiscovery(ReconStage):
    tool_name = "infra_discovery"
    action = Action.PASSIVE_RECON

    def crtsh_lookup(self, domain: str) -> list[str]:
        """Certificate transparency — free, no key, highest signal-to-effort ratio."""
        self.require_scope(domain)
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
        except Exception:
            return []
        names = set()
        for entry in data:
            for name in entry.get("name_value", "").split("\n"):
                names.add(name.strip().lstrip("*."))
        return sorted(names)

    def whois_asn(self, ip: str) -> dict:
        result = self.run_command(f"whois -h whois.cymru.com \" -v {ip}\"")
        return {"ip": ip, "raw": result.stdout}

    def reverse_dns(self, ip: str) -> list[str]:
        result = self.run_command(f"hakrevdns -d {ip}")
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def normalize_merge(self, *sources: list[str]) -> list[str]:
        """Dedup across sources — the `anew`-style step the methodology calls for."""
        seen: set[str] = set()
        for source in sources:
            for item in source:
                seen.add(item.strip().lower())
        return sorted(seen)
