"""
AI #1 — Recon Analyst (methodology section 5).

Input: new_hosts (list of dicts from change detection: hostname, tech,
endpoints observed at discovery time). Output: ranked list with reasons.

This agent NEVER writes to `findings` or sets FindingStatus.confirmed/
submitted — it only ever produces AIAnalysis rows and ManualHuntQueueItem
rows. Enforce that at the call site (workers/tasks.py), not just here.
"""
from __future__ import annotations

from app.ai.client import LLMClient
from app.ai.skill_loader import build_skill_context

SYSTEM_PROMPT_TEMPLATE = """You are a Recon Analyst for an experienced bug bounty hunter.
You are shown newly-discovered hosts from continuous recon monitoring. Your
job is ONLY to prioritize which ones deserve human attention today — you
never claim a vulnerability exists, and you never say something is "safe" or
"clean". You reason from the same signals a skilled hunter would: new
authentication surface, admin/internal terminology, API documentation
exposure, unusual or beta technology, multi-tenant identifiers.

{skill_context}

Output strict JSON: a list of objects, each with:
  "hostname": string
  "priority": integer 0-100
  "reason": short string explaining the priority (signals observed, not guesses)
  "suggested_manual_tests": list of short strings
"""

SKILLS_FOR_THIS_AGENT = [
    "recon/asset_discovery",
    "recon/url_discovery",
    "triage/ai_triage",
]


def analyze_new_hosts(new_hosts: list[dict], model: str | None = None) -> list[dict]:
    client = LLMClient(model=model) if model else LLMClient()
    skill_context = build_skill_context(SKILLS_FOR_THIS_AGENT)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(skill_context=skill_context)

    user_content = "New hosts discovered this run:\n\n" + "\n".join(
        f"- {h.get('hostname')} | tech: {h.get('technology', 'unknown')} | "
        f"first_seen: {h.get('first_seen')}" for h in new_hosts
    )

    result = client.complete_json(system_prompt, user_content)
    if isinstance(result, dict) and "hosts" in result:
        return result["hosts"]
    return result if isinstance(result, list) else []
