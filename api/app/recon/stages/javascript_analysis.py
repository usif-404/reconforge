"""
JavaScript discovery + local analysis.

Important: this stage only fetches/hashes/regex-scans JS. The *interpretive*
work (extract API routes, role checks, feature flags — section 5's "AI #2")
is deliberately NOT done here with regex; it's handed to ai/agents/js_analyst.py
with only the new/changed files, per the methodology's explicit instruction
not to feed 50MB of raw JS to the AI every run.
"""
from __future__ import annotations

import hashlib
import re

from app.recon.stages.base import ReconStage
from app.scope.manager import Action

SECRET_PATTERNS = {
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_api_key": re.compile(r"(?i)(api[_-]?key|apikey)['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{20,}"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
}

ENDPOINT_PATTERN = re.compile(r"""['"](/[a-zA-Z0-9_\-/{}.]*(?:api|graphql|v[0-9]+)[a-zA-Z0-9_\-/{}.]*)['"]""")


class JavaScriptDiscovery(ReconStage):
    tool_name = "javascript_discovery"
    action = Action.PASSIVE_RECON

    def discover(self, page_urls: list[str]) -> list[dict]:
        results = []
        for url in page_urls:
            self.require_scope(url)
            subjs = self.run_command(f"subjs -i {url}")
            for line in subjs.stdout.splitlines():
                if line.strip():
                    results.append({"js_url": line.strip(), "source_page": url})
        return results

    def fetch_and_hash(self, js_url: str) -> dict:
        """Fetch a JS file, return content + hash. Caller diffs hash against DB to
        decide whether this file needs to go to the AI JS Analyst at all."""
        self.require_scope(js_url)
        result = self.run_command(f"curl -s -A 'Mozilla/5.0' {js_url}")
        content = result.stdout
        content_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
        return {"js_url": js_url, "content": content, "content_hash": content_hash, "size": len(content)}

    @staticmethod
    def local_regex_scan(content: str) -> dict:
        """Cheap local pass before AI ever sees the file — cuts AI cost dramatically."""
        secrets_found = {
            name: pattern.findall(content) for name, pattern in SECRET_PATTERNS.items() if pattern.search(content)
        }
        endpoints_found = sorted(set(ENDPOINT_PATTERN.findall(content)))
        return {"secrets": secrets_found, "endpoints": endpoints_found}
