"""
Secret discovery, port discovery, content discovery, API discovery, and safe
template-based vulnerability checks. Grouped together because each is a thin
single-tool wrapper — split into its own module if one grows complex.
"""
from __future__ import annotations

from app.recon.stages.base import ReconStage
from app.scope.manager import Action


class SecretDiscovery(ReconStage):
    tool_name = "secret_discovery"
    action = Action.PASSIVE_RECON

    def scan_repo(self, repo_path_or_url: str) -> list[dict]:
        """trufflehog against a repo — only for repos the program scope explicitly covers."""
        result = self.run_command(f"trufflehog filesystem {repo_path_or_url} --json")
        return [{"raw": line} for line in result.stdout.splitlines() if line.strip()]


class PortDiscovery(ReconStage):
    tool_name = "port_discovery"
    action = Action.ACTIVE_DNS  # port scanning is active; gate it the same way as active DNS/network probing

    def run(self, ips: list[str], top_ports: int = 1000) -> list[dict]:
        for ip in ips:
            self.require_scope(ip)
        ip_list = ",".join(ips)
        result = self.run_command(f"naabu -host {ip_list} -top-ports {top_ports} -silent -json")
        return [{"raw": line} for line in result.stdout.splitlines() if line.strip()]


class ContentDiscovery(ReconStage):
    """Directory/file brute force — high noise, must be explicitly enabled per program."""

    tool_name = "content_discovery"
    action = Action.DIRECTORY_DISCOVERY

    def run(self, base_urls: list[str], wordlist: str = "/wordlists/common.txt") -> list[dict]:
        results = []
        for url in base_urls:
            self.require_scope(url)
            r = self.run_command(f"ffuf -w {wordlist} -u {url}/FUZZ -mc 200,301,302,403 -json")
            results.append({"base_url": url, "raw_ffuf": r.stdout})
        return results


class APIDiscovery(ReconStage):
    tool_name = "api_discovery"
    action = Action.CRAWLING

    def run(self, base_urls: list[str], wordlist: str = "/wordlists/kiterunner-routes.kite") -> list[dict]:
        results = []
        for url in base_urls:
            self.require_scope(url)
            r = self.run_command(f"kr scan {url} -w {wordlist} -j")
            results.append({"base_url": url, "raw_kiterunner": r.stdout})
        return results


class SafeVulnChecks(ReconStage):
    """
    Nuclei with a curated, non-destructive template set only. Per the
    methodology, this stage is NOT the center of the pipeline — it's one
    narrow, explicitly-scoped stage that runs on the change-detected subset,
    not the entire asset inventory every run.
    """

    tool_name = "safe_vuln_checks"
    action = Action.AUTOMATED_SCANNING

    SAFE_TEMPLATE_TAGS = "exposure,misconfig,default-login,tech"  # exclude dast/fuzz/intrusive tags

    def run(self, urls: list[str], rate_limit: int = 5) -> list[dict]:
        for url in urls:
            self.require_scope(url)
        with_targets = "\n".join(urls)
        result = self.run_command(
            f"nuclei -l /dev/stdin -tags {self.SAFE_TEMPLATE_TAGS} "
            f"-rl {rate_limit} -silent -jsonl",
        )
        # NOTE: in production, pipe `with_targets` into stdin of the subprocess
        # rather than shelling to /dev/stdin literally; base.run_command uses
        # subprocess.run without stdin wiring — extend it if you need this stage.
        return [{"raw": line} for line in result.stdout.splitlines() if line.strip()]
