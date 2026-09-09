"""Passive subdomain enumeration — never touches the target directly."""
from __future__ import annotations

from app.recon.stages.base import ReconStage
from app.scope.manager import Action


class PassiveSubdomainEnum(ReconStage):
    tool_name = "passive_subdomains"
    action = Action.PASSIVE_RECON

    # Each tool is independently toggleable via config so you can disable
    # ones you don't have API keys for without touching code.
    TOOLS = {
        "subfinder": "subfinder -d {domain} -all -recursive -silent -oJ",
        "assetfinder": "assetfinder --subs-only {domain}",
        "amass_passive": "amass enum -passive -d {domain} -silent",
        "findomain": "findomain -t {domain} -q",
        "chaos": "chaos -d {domain} -silent",
        "github_subdomains": "github-subdomains -d {domain} -raw",
        # crt.sh has no CLI tool, hit it directly (see infra_discovery.crtsh_lookup)
    }

    def run(self, targets: list[str], enabled_tools: list[str] | None = None) -> list[dict]:
        results = []
        enabled = enabled_tools or list(self.TOOLS.keys())
        for domain in targets:
            # Passive recon on the *root* domain is standard practice even
            # when the program scope is "*.example.com" — check the root,
            # not each not-yet-discovered subdomain (which doesn't exist yet).
            self.require_scope(domain)
            for tool in enabled:
                cmd_template = self.TOOLS.get(tool)
                if not cmd_template:
                    continue
                result = self.run_command(cmd_template.format(domain=domain))
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line:
                        results.append({"hostname": line, "source": tool, "domain": domain})
        return results
