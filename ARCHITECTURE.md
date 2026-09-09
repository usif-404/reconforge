# ReconForge — Architecture

Personal bug-bounty operating system: VPS hunts continuously, you hunt manually,
AI decides what deserves your attention. Built around the methodology in
`Recon_Methodology.txt` — nothing in that file was simplified into
`subfinder -> httpx -> nuclei`. Every tool/technique listed there is a
configurable stage in the pipeline (see `api/app/recon/stages/`).

## Core loop

```
PROGRAM -> SCOPE CHECK -> DISCOVER -> NORMALIZE -> STORE -> COMPARE (change
detection) -> CLASSIFY -> SCORE -> AI TRIAGE -> MANUAL HUNT QUEUE -> YOU
```

The system's job is never "is this vulnerable" — it's "what changed since
yesterday, and does it deserve a human." Vulnerability scanning (nuclei) is one
narrow, explicitly-scoped stage, not the center of the pipeline.

## Components

```
                     Bug Bounty Programs (H1 / Bugcrowd)
                                  |
                          Scope Manager  <-- every active stage asks this first
                                  |
      +---------------------------------------------------+
      |                                                     |
   VPS (24/7)                                        Workstation
   Celery workers                                    Burp + browser
   recon pipeline stages                              manual testing
   change detection                                   AI Burp Assistant
      |                                                     |
      +------------------- PostgreSQL / Redis -------------+
                                  |
                        AI Agents (see below)
                                  |
                         Manual Hunt Queue
                                  |
                            YOU decide
```

## AI agents (Strix-inspired: narrow agent + injected skill docs, not one mega-prompt)

Strix's actual pattern (from `strix/tools/load_skill` + `strix/skills/`) is: a
sub-agent is created for a task and gets 1–5 relevant `SKILL.md` files injected
into its context — not a fixed giant system prompt. We reuse that pattern here:

| Agent | Input | Skills injected | Output |
|---|---|---|---|
| Recon Analyst | `new_hosts.json` | `recon/*` | ranked new-host list with reasons |
| JS Analyst | new/changed JS diffs only | `javascript/*`, `api/*`, `graphql/*` | extracted routes/roles/flags flagged by risk |
| Change Analyst | yesterday vs today diff | `triage/*` | human-readable "what matters" digest |
| Burp Assistant | live request/response + role/account model | `authorization/*`, `authentication/*`, `business_logic/*` | suggested manual tests (IDOR/BOLA matrix etc.) |

None of these agents mark a finding as confirmed. They only ever populate the
`manual_hunt_queue` and `ai_analysis` tables. A human (you) verifies before
`findings` gets a submitted report attached — this is enforced at the DB layer,
not just by prompt instruction (see `Finding.status` state machine in
`api/app/db/models.py`).

## Why not Kubernetes / microservices

Docker Compose: Postgres, Redis, FastAPI, Celery worker(s), Celery beat,
notification worker. Workstation runs its own lightweight worker over
Tailscale and pulls jobs from the same Redis queue — if it's offline, the VPS
queue just keeps growing and the VPS-side jobs keep running.

## Build order (matches the phases you specified)

- **Phase 1** (this scaffold): Scope Manager, subdomain/HTTP/JS monitors,
  Postgres schema, change detection, Discord/Telegram notifications.
- **Phase 2**: AI prioritization + change summaries + endpoint classification
  (agent stubs are scaffolded now, wired to a real LLM call — fill in your
  provider key).
- **Phase 3**: Burp integration, role/account model, manual testing assistant,
  knowledge base (`knowledge_entries` table is scaffolded, ingestion isn't).
- **Phase 4**: distributed workers, program scoring, adaptive automation,
  custom detectors.
