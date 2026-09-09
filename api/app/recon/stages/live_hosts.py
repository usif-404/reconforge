"""Live host discovery — httpx probe of every candidate hostname."""
from __future__ import annotations

import json
import tempfile

from app.recon.stages.base import ReconStage
from app.scope.manager import Action


class LiveHostDiscovery(ReconStage):
    tool_name = "live_hosts"
    action = Action.PASSIVE_RECON  # probing a resolved host with a normal GET is treated as passive-ish here;
    # set to ACTIVE_DNS in your program config if a program considers probing "active"

    def run(self, hostnames: list[str]) -> list[dict]:
        for h in hostnames:
            self.require_scope(h)

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("\n".join(hostnames))
            hosts_file = f.name

        result = self.run_command(
            f"httpx -l {hosts_file} -sc -title -server -td -tls-grab -favicon "
            f"-cl -location -json -silent"
        )

        parsed = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return parsed
