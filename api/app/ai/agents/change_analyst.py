"""AI #4 — Change Analyst (methodology section 7). Runs periodically, summarizes
Change rows into a human-readable hunting to-do list. Wire this to your
notification worker to send the digest to Discord/Telegram."""
from __future__ import annotations

from app.ai.client import LLMClient
from app.ai.skill_loader import build_skill_context

SYSTEM_PROMPT_TEMPLATE = """You are a Change Analyst summarizing recon changes
for an experienced bug bounty hunter who does NOT want a full changelog — they
want to know what's worth investigating today and why. Group by program.
Call out counts of routine changes briefly, then give a short prioritized
list of specific standout changes with a one-line reason each.

{skill_context}

Output strict JSON:
{{
  "program": string,
  "routine_summary": {{"dns_changes": int, "new_hosts": int, "modified_js_files": int, "new_urls": int}},
  "highlights": [
    {{"subject": string, "change_type": string, "reason": string, "priority": int}}
  ]
}}
"""

SKILLS_FOR_THIS_AGENT = ["triage/ai_triage"]


def summarize_changes(program_name: str, changes: list[dict], model: str | None = None) -> dict:
    client = LLMClient(model=model) if model else LLMClient()
    skill_context = build_skill_context(SKILLS_FOR_THIS_AGENT)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(skill_context=skill_context)

    lines = [
        f"- [{c.get('change_type')}] {c.get('subject')} at {c.get('detected_at')}: {c.get('detail')}"
        for c in changes
    ]
    user_content = f"Program: {program_name}\nChanges in the last window:\n\n" + "\n".join(lines)

    return client.complete_json(system_prompt, user_content)
