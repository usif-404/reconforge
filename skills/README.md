# ReconForge Skills

Pattern borrowed from Strix (`strix/skills/`): a skill is a Markdown file with
YAML frontmatter (`name`, `description`), organized by category. An AI agent
loads at most 5 relevant skills per task via `api/app/ai/skill_loader.py`,
which concatenates their bodies into that agent's system prompt. Skills are
knowledge, not code — they never execute anything themselves.

## Categories

| Category | Used by |
|---|---|
| `recon/` | Recon Analyst |
| `javascript/` | JS Analyst |
| `api/` | JS Analyst, Recon Analyst |
| `graphql/` | JS Analyst, Burp Assistant |
| `authentication/` | Burp Assistant |
| `authorization/` | Burp Assistant |
| `business_logic/` | Burp Assistant |
| `triage/` | Recon Analyst, Change Analyst |
| `reporting/` | you, manually, before submitting |
| `tooling/` | reference command playbooks for the recon stages |

## Writing a new skill

Follow this shape (same as Strix's convention):

```markdown
---
name: skill-name
description: one sentence, used for retrieval/selection
---

# Title

Short framing paragraph — what this skill covers and when NOT to use it.

## Signals to look for
## Methodology
## Validation
## False Positives
## Summary
```

Keep skills to knowledge and judgment calls — "how to tell an IDOR is real
vs a false positive" — not tool command reference (that's `tooling/`).
