"""Program-selection scoring (methodology section 10) — don't hunt everything equally."""
from __future__ import annotations

from dataclasses import dataclass

WEIGHTS = {
    "scope_size": 0.20,
    "reward_quality": 0.15,
    "response_quality": 0.10,
    "technology_match": 0.15,
    "interesting_apis": 0.15,
    "deployment_frequency": 0.15,
    "competition": 0.10,  # lower competition -> higher input score; invert before scoring
}


@dataclass
class ProgramInputs:
    scope_size: float          # 0-100, e.g. normalized subdomain/asset count
    reward_quality: float       # 0-100, your own read of avg bounty vs effort
    response_quality: float     # 0-100, triage speed / history
    technology_match: float     # 0-100, how well it matches your strongest skills
    interesting_apis: float     # 0-100, GraphQL/modern API surface present
    deployment_frequency: float # 0-100, how often you see change events
    competition: float          # 0-100 where 100 = least competition (already inverted)


def score_program(inputs: ProgramInputs) -> float:
    total = 0.0
    for field_name, weight in WEIGHTS.items():
        total += getattr(inputs, field_name) * weight
    return round(total, 1)


def rank_programs(programs: dict[str, ProgramInputs]) -> list[tuple[str, float]]:
    scored = [(name, score_program(inp)) for name, inp in programs.items()]
    return sorted(scored, key=lambda x: x[1], reverse=True)
