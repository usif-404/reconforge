# ReconForge

Personal bug-bounty automation platform. Built for authorized programs only —
see `programs/*.yaml` and `api/app/scope/manager.py`: nothing runs against a
target without an explicit scope + rule check.

Read `ARCHITECTURE.md` first — it explains the design and what was adapted
from Strix (usestrix/strix) vs. built fresh for this project.

## What's here (Phase 1 + scaffolding for 2-4)

```
reconforge/
├── ARCHITECTURE.md          # design doc — read this first
├── docker-compose.yml       # postgres, redis, api, vps worker, beat
├── .env.example             # copy to .env, fill in keys
├── api/
│   ├── Dockerfile           # installs the full recon toolchain
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI entrypoint
│       ├── db/models.py               # 30-table canonical schema
│       ├── scope/                     # Scope Manager (first-class citizen)
│       ├── recon/stages/              # one file per tool category from
│       │                              #   your methodology doc
│       ├── changes/detector.py        # the actual core value: diffing
│       ├── scoring/                   # target_scorer.py, program_scorer.py
│       ├── ai/                        # LLM client + skill loader + 4 agents
│       ├── notifications/discord.py
│       ├── workers/                   # celery_app.py + tasks.py
│       │                              #   (event-driven pipeline)
│       └── api_routes/                # programs, assets, queue, feedback
├── skills/                  # SKILL.md files, Strix-style, category-organized
├── programs/example.yaml    # program scope config template
└── scripts/
    ├── setup_wordlists.sh
    └── run_workstation_worker.sh
```

## VPS sizing (t3.large: 2 vCPU / 7.6GB RAM / no GPU)

This scaffold is tuned for exactly that box. Two things matter more than
anything else here:

1. **No local LLM, ever.** All AI calls go through the Anthropic API
   (`api/app/ai/client.py`). Don't add Ollama or a local model container —
   this box has no GPU and 7.6GB total RAM, nowhere near enough for a useful
   local model alongside the recon stack.
2. **Everything runs in resource-bounded queues, never all at once.**
   `docker-compose.yml` splits Celery workers into `passive_recon` (c=2),
   `http_probe` (c=2), `crawler` (c=1), `nuclei` (c=1), `ai` (c=2) — each its
   own container with a `mem_limit`. Total budget is ~5.4GB, leaving ~2.2GB
   headroom. If you resize the VPS later, only the `-c` flags and
   `mem_limit`s in `docker-compose.yml` need to change.

Run the swap setup once before first boot — without it, a heavy `katana`
crawl or several `nuclei` templates at once can trigger the OOM killer:

```bash
./scripts/setup_vps_swap.sh 4   # 4GB swap, safety net not routine memory
```

## Quick start

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY at minimum; DISCORD_WEBHOOK_URL for notifications

./scripts/setup_vps_swap.sh
./scripts/setup_wordlists.sh

docker compose build
docker compose up -d postgres redis
# run migrations once you add Alembic revisions (not scaffolded yet — the
# models.py schema is ready but you still need `alembic init` +
# `alembic revision --autogenerate` for your first migration)

docker compose up -d
```

Edit `programs/example.yaml` (or copy it to `programs/<your-program>.yaml`)
with the real scope for a program you're authorized on before running
anything beyond passive recon.

## Running the workstation side

On your workstation, over Tailscale to the VPS:

```bash
export REDIS_URL="redis://<vps-tailscale-ip>:6379/0"
export DATABASE_URL="postgresql+psycopg2://reconforge:reconforge@<vps-tailscale-ip>:5432/reconforge"
./scripts/run_workstation_worker.sh
```

This worker only consumes the `workstation` Celery queue — Burp Assistant
calls and anything needing your supervision. If you turn your workstation
off, the VPS keeps running Phase 1/2 tasks uninterrupted; workstation tasks
just queue in Redis until you're back.

## Triggering a recon run manually (before you wire up beat scheduling)

```python
from app.workers.tasks import run_passive_recon
run_passive_recon.delay("example", ["example.com"])
```

This kicks off the full event chain: passive subdomain enum → probe new
hosts → crawl alive hosts → analyze JS → AI triage → Discord notification —
each stage only continuing if the previous one found something.

## What's NOT built yet (intentionally left for you to extend)

- **Celery beat schedule** — commented example in `celery_app.py`; uncomment
  and set your real polling cadence per program once you've decided one.
  Deliberately staggered by design: don't schedule `passive_recon` and
  `nuclei` for the same hour on this box.
- **Alembic migrations** — models.py is ready; run `alembic init` and
  generate your first revision.
- **Deduplication against existing DB rows** in `workers/tasks.py` — the
  `# TODO` comments mark exactly where to add the "is this actually new"
  check against `subdomains`/`javascript_versions` before continuing the
  chain. Right now the scaffold treats every run's output as new for
  demonstration purposes.
- **`nuclei` stdin wiring** in `discovery_extras.SafeVulnChecks` — the base
  `run_command` helper doesn't pipe stdin; extend it if you want this stage
  live rather than illustrative.
- **Knowledge base ingestion** (`knowledge_entries` table) — schema's ready,
  no ingestion pipeline from Hacktivity yet (section 15 of the methodology).
- **Telegram notifications** — Discord is wired; Telegram is a stub to fill
  in analogous to `notifications/discord.py`.

## Safety notes

- `ScopeManager.is_authorized()` is enforced at the stage level
  (`recon/stages/base.py`'s `require_scope`), not just documented — every
  stage raises `PermissionError` if called against an unauthorized target.
- No AI agent code path writes `FindingStatus.confirmed` or `.submitted` —
  see `db/models.py`'s `Finding` docstring and `skills/triage/ai_triage.md`.
  You are the only path to those two states.
