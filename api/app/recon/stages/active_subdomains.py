"""
Active DNS / subdomain enumeration — brute force and vhost fuzzing.
Requires Action.ACTIVE_DNS to be explicitly enabled per program, since this
generates real traffic against the target's DNS/HTTP infra.
"""
from __future__ import annotations

from app.recon.stages.base import ReconStage
from app.scope.manager import Action


class ActiveSubdomainEnum(ReconStage):
    tool_name = "active_subdomains"
    action = Action.ACTIVE_DNS

    def run(self, targets: list[str], wordlist: str = "/wordlists/subdomains.txt") -> list[dict]:
        results = []
        for domain in targets:
            self.require_scope(domain)

            puredns = self.run_command(
                f"puredns bruteforce {wordlist} {domain} --resolvers /wordlists/resolvers.txt -q"
            )
            for line in puredns.stdout.splitlines():
                if line.strip():
                    results.append({"hostname": line.strip(), "source": "puredns", "domain": domain})

            dnsx = self.run_command(f"dnsx -d {domain} -silent -json")
            for line in dnsx.stdout.splitlines():
                if line.strip():
                    results.append({"raw_dnsx": line, "source": "dnsx", "domain": domain})

        return results

    def vhost_fuzz(self, base_ip: str, wordlist: str, base_domain: str) -> list[dict]:
        """
        ffuf virtual-host enumeration. `base_ip` must already be authorized
        (i.e. resolved from an in-scope hostname) — do NOT fuzz arbitrary IPs.
        """
        self.require_scope(base_domain)
        result = self.run_command(
            f"ffuf -w {wordlist} -u http://{base_ip} -H 'Host: FUZZ.{base_domain}' "
            f"-mc 200,301,302,403 -fs 0 -json"
        )
        return [{"raw_ffuf": line, "source": "ffuf-vhost"} for line in result.stdout.splitlines() if line.strip()]
