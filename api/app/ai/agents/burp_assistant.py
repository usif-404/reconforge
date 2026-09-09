"""
AI #3 — Burp Assistant (methodology section 6).

This is the one meant to run WHILE you're manually testing, not on a
schedule. Feed it a request/response and your current account/role model;
it proposes an authorization test matrix. It never executes anything itself
— you still send every request in Burp.
"""
from __future__ import annotations

from app.ai.client import LLMClient
from app.ai.skill_loader import build_skill_context

SYSTEM_PROMPT_TEMPLATE = """You are a Burp testing assistant for an experienced
bug bounty hunter doing manual authorization testing. You are given:
1. A live request/response pair
2. A model of known accounts/roles/organizations the hunter has access to

Your job is only to propose a concrete, prioritized test matrix — token
substitution, header manipulation, org/tenant ID changes, nested resource
boundary checks, export/download equivalents. Never claim a test will
succeed; frame each as a hypothesis to verify. Never write exploit code —
these are manual steps for the hunter to execute in Burp Repeater.

{skill_context}

Output strict JSON:
{{
  "endpoint": string,
  "tests": [
    {{"test_name": string, "how_to_perform": string, "what_a_positive_result_looks_like": string, "vuln_class": string}}
  ]
}}
"""

SKILLS_FOR_THIS_AGENT = [
    "authorization/idor_bola",
    "authentication/auth_testing",
    "business_logic/business_logic",
]


def suggest_tests(request_response: str, account_model: dict, model: str | None = None) -> dict:
    client = LLMClient(model=model) if model else LLMClient()
    skill_context = build_skill_context(SKILLS_FOR_THIS_AGENT)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(skill_context=skill_context)

    user_content = (
        f"Request/response:\n{request_response}\n\n"
        f"Known account/role model:\n{account_model}"
    )
    return client.complete_json(system_prompt, user_content)
