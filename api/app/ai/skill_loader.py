"""
Skill loader — directly inspired by Strix's `strix/tools/load_skill` +
`strix/skills/` pattern: skills are plain Markdown files with YAML
frontmatter, and an agent gets a handful of relevant ones injected into its
system prompt rather than one giant static prompt.

Strix's own convention (per its skills/README.md): an agent loads up to 5
skills per task. We follow the same cap here.
"""
from __future__ import annotations

import pathlib

import yaml

SKILLS_DIR = pathlib.Path(__file__).resolve().parents[3] / "skills"
MAX_SKILLS_PER_AGENT = 5


def _parse_skill_file(path: pathlib.Path) -> dict:
    text = path.read_text()
    if text.startswith("---"):
        _, frontmatter, body = text.split("---", 2)
        meta = yaml.safe_load(frontmatter)
    else:
        meta, body = {}, text
    return {"name": meta.get("name", path.stem), "description": meta.get("description", ""), "body": body.strip()}


def load_skill(skill_id: str) -> dict:
    """skill_id is 'category/filename' e.g. 'recon/asset_discovery'."""
    path = SKILLS_DIR / f"{skill_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"skill not found: {skill_id}")
    return _parse_skill_file(path)


def list_skills(category: str | None = None) -> list[dict]:
    base = SKILLS_DIR / category if category else SKILLS_DIR
    out = []
    for path in base.rglob("*.md"):
        if path.name == "README.md":
            continue
        rel = path.relative_to(SKILLS_DIR).with_suffix("")
        out.append({"id": str(rel), **_parse_skill_file(path)})
    return out


def build_skill_context(skill_ids: list[str]) -> str:
    """Concatenates skill bodies into a block to append to an agent's system prompt."""
    if len(skill_ids) > MAX_SKILLS_PER_AGENT:
        skill_ids = skill_ids[:MAX_SKILLS_PER_AGENT]
    blocks = []
    for skill_id in skill_ids:
        skill = load_skill(skill_id)
        blocks.append(f"## Skill: {skill['name']}\n\n{skill['body']}")
    return "\n\n---\n\n".join(blocks)
