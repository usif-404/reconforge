"""
Queue layout sized for a 2 vCPU / 7.6GB RAM / no-GPU box (AWS t3.large).

Rule: nothing runs with unbounded concurrency. Each queue below maps to a
worker process in docker-compose.yml with its own `-c <concurrency>` cap —
see the recommended concurrency table below. AI calls go through the
Anthropic API, never a local model, so there's no GPU/large-RAM requirement
on the `ai` queue itself — its concurrency limit bounds outbound API
rate/cost, not local resource use.
"""
import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("reconforge", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Prefetch=1 matters more than usual here: a worker with concurrency=2
    # that prefetches 4 tasks can end up holding 4 subprocess-heavy jobs in
    # memory waiting for CPU time. Keep it tight on a memory-constrained box.
    worker_prefetch_multiplier=1,
    task_routes={
        # Passive recon: subfinder/assetfinder/amass -passive/crt.sh — mostly
        # network-IO-bound, cheap on CPU. concurrency=2 is fine.
        "workers.tasks.run_passive_recon": {"queue": "passive_recon"},
        "workers.tasks.infra_discovery": {"queue": "passive_recon"},

        # HTTP probing (httpx): light per-request but many hosts at once —
        # keep concurrency=2, rely on httpx's own internal threading rather
        # than stacking multiple httpx processes.
        "workers.tasks.probe_new_hosts": {"queue": "http_probe"},

        # Crawling (katana/hakrawler/gospider) and JS fetch/analysis: the
        # most CPU/RAM-hungry stage on this box. concurrency=1 — run one
        # crawl at a time, not several in parallel.
        "workers.tasks.crawl_alive_hosts": {"queue": "crawler"},
        "workers.tasks.analyze_javascript": {"queue": "crawler"},

        # nuclei: isolate to its own queue with concurrency=1 and a low
        # internal rate-limit (-rl 5, already set in discovery_extras.py) —
        # this is the stage most likely to spike CPU if run alongside a crawl.
        "workers.tasks.run_active_recon": {"queue": "nuclei"},
        "workers.tasks.run_safe_vuln_checks": {"queue": "nuclei"},

        # AI triage: no local compute cost, just outbound HTTPS to Anthropic.
        # concurrency=2 bounds cost/rate, not CPU.
        "workers.tasks.triage_new_hosts": {"queue": "ai"},
        "workers.tasks.run_ai_triage": {"queue": "ai"},

        # Workstation-only tasks (Burp Assistant, human-supervised browser
        # work) — never scheduled on the VPS at all, consumed only by the
        # worker you run locally over Tailscale.
        "workers.tasks.manual_workstation_task": {"queue": "workstation"},
    },
)

# Beat schedule: none by default — add one entry per program once you've
# decided a polling cadence. Example (uncomment and adjust program name):
#
# from celery.schedules import crontab
# celery_app.conf.beat_schedule = {
#     "passive-recon-example-daily": {
#         "task": "workers.tasks.run_passive_recon",
#         "schedule": crontab(hour=2, minute=0),  # 2am, low-traffic window
#         "args": ("example", ["example.com"]),
#     },
#     "ai-digest-example-daily": {
#         "task": "workers.tasks.run_ai_triage",
#         "schedule": crontab(hour=8, minute=0),  # digest ready when you wake up
#         "args": ("example", 24),
#     },
# }
#
# Keep passive_recon and nuclei/crawler schedules staggered (different
# hours), not simultaneous — on this box you want one heavy stage running
# at a time, which staggered cron times achieve for free without extra code.

# Recommended per-queue concurrency on a 2 vCPU / 7.6GB box (no GPU):
#   passive_recon : 2
#   http_probe    : 2
#   crawler       : 1
#   nuclei        : 1
#   ai            : 2   (API-bound, not local-compute-bound)
#   workstation   : n/a — runs on your workstation, not the VPS
#
# Total VPS-side worker processes at once: 6, matched to docker-compose.yml.
# If you upsize the VPS later, raise these in docker-compose.yml's celery
# `-c` flags — nothing else needs to change.
