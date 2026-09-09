"""
Event-driven pipeline (methodology section 13):

    new subdomain -> httpx -> alive -> crawl -> JS discovered -> extract
    endpoints -> new API endpoint -> AI classification -> interesting?
    -> manual queue. Something boring ends automatically.

Each task below does ONE stage and enqueues the next stage only if there's
something worth continuing with — this is what keeps VPS cost/noise down
instead of "scan everything every 6 hours."
"""
from __future__ import annotations

from app.workers.celery_app import celery_app
from app.scope.loader import load_scope_manager
from app.recon.stages.passive_subdomains import PassiveSubdomainEnum
from app.recon.stages.live_hosts import LiveHostDiscovery
from app.recon.stages.url_discovery import ArchiveURLDiscovery, ActiveCrawl
from app.recon.stages.javascript_analysis import JavaScriptDiscovery
from app.ai.agents.recon_analyst import analyze_new_hosts
from app.ai.agents.js_analyst import analyze_js_diff
from app.notifications.discord import send_discord_notification

_scope_manager = None


def get_scope_manager():
    global _scope_manager
    if _scope_manager is None:
        _scope_manager = load_scope_manager()
    return _scope_manager


@celery_app.task(name="workers.tasks.run_passive_recon")
def run_passive_recon(program_name: str, root_domains: list[str]) -> list[str]:
    stage = PassiveSubdomainEnum(get_scope_manager(), program_name)
    raw = stage.run(root_domains)
    hostnames = sorted({r["hostname"] for r in raw})

    # TODO: diff against `subdomains` table; only genuinely-new hostnames
    # should proceed to the next stage. This is the "something boring ends
    # automatically" behavior — placeholder assumes all are new for now.
    new_hostnames = hostnames
    if new_hostnames:
        probe_new_hosts.delay(program_name, new_hostnames)
    return new_hostnames


@celery_app.task(name="workers.tasks.probe_new_hosts")
def probe_new_hosts(program_name: str, hostnames: list[str]) -> list[dict]:
    stage = LiveHostDiscovery(get_scope_manager(), program_name)
    alive = stage.run(hostnames)

    if alive:
        crawl_alive_hosts.delay(program_name, [h["url"] for h in alive if "url" in h])
        triage_new_hosts.delay(program_name, alive)

    return alive


@celery_app.task(name="workers.tasks.crawl_alive_hosts")
def crawl_alive_hosts(program_name: str, urls: list[str]) -> list[dict]:
    archive = ArchiveURLDiscovery(get_scope_manager(), program_name)
    active = ActiveCrawl(get_scope_manager(), program_name)

    all_urls = archive.run(urls) + active.run(urls)
    js_urls = [u["url"] for u in all_urls if u.get("url", "").endswith(".js")]

    if js_urls:
        analyze_javascript.delay(program_name, js_urls)

    return all_urls


@celery_app.task(name="workers.tasks.analyze_javascript")
def analyze_javascript(program_name: str, js_urls: list[str]) -> None:
    discovery = JavaScriptDiscovery(get_scope_manager(), program_name)
    for js_url in js_urls:
        fetched = discovery.fetch_and_hash(js_url)
        # TODO: compare fetched["content_hash"] against javascript_versions
        # table via changes.detector.diff_javascript_version; only call the
        # AI JS Analyst if it's genuinely new/changed.
        findings = analyze_js_diff(js_url, fetched["content"])
        high_value = [f for f in findings if f.get("finding_type") in {"role_check", "admin_functionality"}]
        if high_value:
            send_discord_notification(
                title=f"JS finding: {js_url}",
                body="\n".join(f"- {f['finding_type']}: {f['value']} — {f['risk_note']}" for f in high_value),
            )


@celery_app.task(name="workers.tasks.triage_new_hosts")
def triage_new_hosts(program_name: str, alive_hosts: list[dict]) -> None:
    ranked = analyze_new_hosts(alive_hosts)
    interesting = [h for h in ranked if h.get("priority", 0) >= 70]
    if interesting:
        lines = [f"{h['priority']:>3} {h['hostname']} — {h['reason']}" for h in interesting]
        send_discord_notification(
            title=f"[{program_name}] {len(interesting)} new host(s) worth a look",
            body="\n".join(lines),
        )


@celery_app.task(name="workers.tasks.run_active_recon")
def run_active_recon(program_name: str, root_domains: list[str]) -> None:
    """Gated separately from passive — only run against programs where
    active_dns/automated_scanning rules are explicitly enabled."""
    from app.recon.stages.active_subdomains import ActiveSubdomainEnum

    stage = ActiveSubdomainEnum(get_scope_manager(), program_name)
    stage.run(root_domains)


@celery_app.task(name="workers.tasks.infra_discovery")
def infra_discovery(program_name: str, root_domains: list[str]) -> list[str]:
    """crt.sh + whois/ASN pivoting — cheap, IO-bound, same queue as passive recon."""
    from app.recon.stages.infra_discovery import InfraDiscovery

    stage = InfraDiscovery(get_scope_manager(), program_name)
    all_names: list[str] = []
    for domain in root_domains:
        all_names.extend(stage.crtsh_lookup(domain))
    return stage.normalize_merge(all_names)


@celery_app.task(name="workers.tasks.run_safe_vuln_checks")
def run_safe_vuln_checks(program_name: str, urls: list[str]) -> list[dict]:
    """
    Nuclei on the change-detected subset only — never the full inventory.
    concurrency=1 + -rl 5 (set in discovery_extras.py) keeps this from
    competing with the crawler queue for CPU on a 2 vCPU box.
    """
    from app.recon.stages.discovery_extras import SafeVulnChecks

    stage = SafeVulnChecks(get_scope_manager(), program_name)
    return stage.run(urls, rate_limit=5)


@celery_app.task(name="workers.tasks.run_ai_triage")
def run_ai_triage(program_name: str, hours: int = 24) -> dict:
    """Periodic Change Analyst summary — see celery_app.py beat schedule to wire this on a cron."""
    from app.ai.agents.change_analyst import summarize_changes
    from app.changes.detector import changes_since
    from app.db.models import Program
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        program = db.query(Program).filter(Program.name == program_name).first()
        if not program:
            return {"error": "program not found"}
        changes = changes_since(db, program.id, hours=hours)
        change_dicts = [
            {
                "change_type": c.change_type.value,
                "subject": c.subject,
                "detail": c.detail,
                "detected_at": c.detected_at.isoformat(),
            }
            for c in changes
        ]
    finally:
        db.close()

    if not change_dicts:
        return {"program": program_name, "highlights": []}

    summary = summarize_changes(program_name, change_dicts)
    highlights = summary.get("highlights", [])
    if highlights:
        lines = [f"{h.get('priority', 0):>3} {h['subject']} — {h['reason']}" for h in highlights]
        send_discord_notification(title=f"[{program_name}] Daily change digest", body="\n".join(lines))
    return summary


@celery_app.task(name="workers.tasks.manual_workstation_task")
def manual_workstation_task(payload: dict) -> dict:
    """
    Placeholder for workstation-side work (Burp Assistant calls, browser
    automation requiring human supervision). Routed to the `workstation`
    queue so only your workstation worker consumes it — see celery_app.py
    task_routes. If the workstation is offline, this just queues in Redis
    until it comes back, per the architecture doc.
    """
    return {"received": payload}
