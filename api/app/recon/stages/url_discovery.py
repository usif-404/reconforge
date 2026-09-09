"""URL discovery — archive-based and live crawling combined."""
from __future__ import annotations

from app.recon.stages.base import ReconStage
from app.scope.manager import Action


class ArchiveURLDiscovery(ReconStage):
    """Non-interactive, purely reads public archives — no traffic to the target."""

    tool_name = "archive_urls"
    action = Action.PASSIVE_RECON

    TOOLS = {
        "waybackurls": "waybackurls {domain}",
        "waymore": "waymore -i {domain} -mode U",
        "gau": "gau {domain}",
        "gauplus": "gauplus -t 5 {domain}",
    }

    def run(self, domains: list[str], enabled_tools: list[str] | None = None) -> list[dict]:
        results = []
        enabled = enabled_tools or list(self.TOOLS.keys())
        for domain in domains:
            self.require_scope(domain)
            for tool in enabled:
                cmd = self.TOOLS.get(tool)
                if not cmd:
                    continue
                r = self.run_command(cmd.format(domain=domain))
                for line in r.stdout.splitlines():
                    if line.strip():
                        results.append({"url": line.strip(), "source": tool})
        return results


class ActiveCrawl(ReconStage):
    """Actually visits the target — requires crawling: true in program rules."""

    tool_name = "active_crawl"
    action = Action.CRAWLING

    def run(self, seed_urls: list[str], depth: int = 3) -> list[dict]:
        results = []
        for seed in seed_urls:
            self.require_scope(seed)

            katana = self.run_command(f"katana -u {seed} -d {depth} -jc -kf -silent -jsonl")
            for line in katana.stdout.splitlines():
                if line.strip():
                    results.append({"raw": line, "source": "katana"})

            hakrawler = self.run_command(f"echo {seed} | hakrawler -d {depth}")
            for line in hakrawler.stdout.splitlines():
                if line.strip():
                    results.append({"url": line.strip(), "source": "hakrawler"})

        return results


class ParameterDiscovery(ReconStage):
    tool_name = "parameter_discovery"
    action = Action.CRAWLING

    def run(self, urls: list[str]) -> list[dict]:
        results = []
        for url in urls:
            self.require_scope(url)
            arjun = self.run_command(f"arjun -u {url} -oJ /dev/stdout")
            if arjun.stdout.strip():
                results.append({"url": url, "raw_arjun": arjun.stdout, "source": "arjun"})
        return results
