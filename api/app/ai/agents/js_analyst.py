"""
AI #2 — JavaScript Analyst (methodology section 5).

Called ONLY on new/changed JS content (see changes/detector.diff_javascript_version)
— never on the full historical JS corpus every run.
"""
from __future__ import annotations

from app.ai.client import LLMClient
from app.ai.skill_loader import build_skill_context

SYSTEM_PROMPT_TEMPLATE = """You are a JavaScript Analyst for an experienced bug bounty hunter.
You are given the contents of NEW or CHANGED JavaScript files (already
filtered by content hash, so every file here is worth reading closely).
Extract, in priority order:

- API routes (REST, GraphQL operations, WebSocket endpoints)
- role names and role-comparison logic (e.g. checks like role === "ADMIN")
- feature flags
- interesting object IDs / ID patterns used in requests
- upload endpoints
- internal terminology not normally user-facing
- admin functionality references
- authentication/authorization flow logic

You never confirm a vulnerability exists. You flag WHAT was found and WHY it
is worth a human's attention, then suggest concrete manual tests (authorization
boundary checks, ID substitution, role separation checks) — not exploit code.

{skill_context}

Output strict JSON: a list of objects, each with:
  "finding_type": one of api_route|graphql_op|role_check|feature_flag|admin_functionality|upload_endpoint|auth_flow
  "value": the extracted route/name/snippet
  "context_snippet": short surrounding code context (a few lines max)
  "risk_note": why this deserves attention
  "suggested_manual_tests": list of short strings
"""

SKILLS_FOR_THIS_AGENT = [
    "javascript/js_analysis",
    "api/api_discovery",
    "graphql/graphql_testing",
]


def analyze_js_diff(js_url: str, content: str, model: str | None = None) -> list[dict]:
    client = LLMClient(model=model) if model else LLMClient()
    skill_context = build_skill_context(SKILLS_FOR_THIS_AGENT)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(skill_context=skill_context)

    # Truncate defensively — large bundles should be pre-filtered/minified-aware
    # chunked upstream; this is a safety net, not the primary strategy.
    truncated = content[:60_000]

    user_content = f"File: {js_url}\n\n```javascript\n{truncated}\n```"
    result = client.complete_json(system_prompt, user_content)
    return result if isinstance(result, list) else result.get("findings", [])
