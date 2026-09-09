"""
URL classification — pure Python, no network calls, no scope check needed.
This is the rule-based first pass; the AI Recon/JS Analysts do the smarter
pass on top of this output (see ai/agents/).
"""
from __future__ import annotations

import re

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "javascript": [r"\.js(\?|$)", r"\.mjs(\?|$)"],
    "api": [r"/api/", r"/graphql", r"/v[0-9]+/", r"/rest/"],
    "auth": [r"/login", r"/signin", r"/signup", r"/register", r"/oauth", r"/sso", r"/auth"],
    "admin": [r"/admin", r"/manage", r"/internal", r"/dashboard", r"/console"],
    "upload_download": [r"/upload", r"/download", r"/export", r"/import", r"/file"],
    "sensitive_files": [r"\.env", r"\.git/", r"\.sql", r"\.bak", r"\.zip", r"config\.json"],
    "idor_candidate": [r"/\d+(/|$)", r"[?&](id|user_id|account_id|order_id)="],
    "cloud": [r"s3\.amazonaws\.com", r"blob\.core\.windows\.net", r"storage\.googleapis\.com"],
    "backend_files": [r"\.php$", r"\.aspx$", r"\.jsp$", r"\.do$"],
}

COMPILED = {cat: [re.compile(p, re.IGNORECASE) for p in patterns] for cat, patterns in CATEGORY_PATTERNS.items()}


def classify_url(url: str) -> list[str]:
    matched = []
    for category, patterns in COMPILED.items():
        if any(p.search(url) for p in patterns):
            matched.append(category)
    return matched or ["uncategorized"]


def classify_batch(urls: list[str]) -> list[dict]:
    return [{"url": u, "categories": classify_url(u)} for u in urls]
