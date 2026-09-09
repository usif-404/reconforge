"""
Change detection: "what appeared or changed since the last run?"

This is intentionally simple SQL-shaped logic, not a clever diffing library —
the methodology doc's own example query is:

    SELECT * FROM endpoints WHERE first_seen > NOW() - INTERVAL '24 hours';

We implement the equivalent in the ORM plus a few change types that need
comparing an old value to a new one (DNS records, JS content hash, endpoint
sets on a JS file).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Change,
    ChangeType,
    HTTPService,
    JavaScriptVersion,
    Program,
    Subdomain,
)


def new_subdomains_since(session: Session, program_id, since: datetime) -> list[Subdomain]:
    stmt = select(Subdomain).where(Subdomain.program_id == program_id, Subdomain.first_seen >= since)
    return list(session.scalars(stmt))


def new_or_modified_http_services(session: Session, program_id, since: datetime) -> tuple[list, list]:
    """Returns (new_services, services_whose_body_hash_changed_this_run)."""
    new_stmt = select(HTTPService).join(Subdomain).where(
        Subdomain.program_id == program_id, HTTPService.first_seen >= since
    )
    new_services = list(session.scalars(new_stmt))

    # "Modified" requires comparing the current body_hash against the previous
    # recorded one — in a real run this is done at ingest time (the ingestion
    # worker fetches the row, compares hash, writes a Change row immediately,
    # then updates last_seen/body_hash). This helper is for ad-hoc querying.
    modified_stmt = select(HTTPService).join(Subdomain).where(
        Subdomain.program_id == program_id, HTTPService.last_seen >= since, HTTPService.first_seen < since
    )
    modified_candidates = list(session.scalars(modified_stmt))
    return new_services, modified_candidates


def record_change(
    session: Session,
    program_id,
    recon_run_id,
    change_type: ChangeType,
    subject: str,
    detail: dict,
) -> Change:
    change = Change(
        program_id=program_id,
        recon_run_id=recon_run_id,
        change_type=change_type,
        subject=subject,
        detail=detail,
    )
    session.add(change)
    return change


def diff_and_record_http_service(
    session: Session,
    program_id,
    recon_run_id,
    subdomain_id,
    url: str,
    new_body_hash: str,
    existing: HTTPService | None,
) -> HTTPService:
    """
    Call this at ingest time for every httpx result. Handles both "new host"
    and "body changed" change types in one place so the logic isn't
    duplicated between the live pipeline and any backfill/reprocessing script.
    """
    now = datetime.utcnow()

    if existing is None:
        service = HTTPService(
            subdomain_id=subdomain_id,
            url=url,
            body_hash=new_body_hash,
            first_seen=now,
            last_seen=now,
            first_run_id=recon_run_id,
            last_run_id=recon_run_id,
        )
        session.add(service)
        session.flush()
        record_change(
            session, program_id, recon_run_id, ChangeType.new_host, url, {"body_hash": new_body_hash}
        )
        return service

    existing.last_seen = now
    existing.last_run_id = recon_run_id
    if existing.body_hash != new_body_hash:
        record_change(
            session,
            program_id,
            recon_run_id,
            ChangeType.modified_js if url.endswith(".js") else ChangeType.new_technology,
            url,
            {"old_hash": existing.body_hash, "new_hash": new_body_hash},
        )
        existing.body_hash = new_body_hash

    return existing


def diff_javascript_version(
    session: Session,
    javascript_file_id,
    new_content_hash: str,
    new_size: int,
    storage_path: str,
) -> tuple[JavaScriptVersion, bool]:
    """Returns (version_row, is_new_or_changed). Only True results should go to the AI JS Analyst."""
    latest_stmt = (
        select(JavaScriptVersion)
        .where(JavaScriptVersion.javascript_file_id == javascript_file_id)
        .order_by(JavaScriptVersion.fetched_at.desc())
        .limit(1)
    )
    latest = session.scalars(latest_stmt).first()

    if latest is not None and latest.content_hash == new_content_hash:
        return latest, False

    version = JavaScriptVersion(
        javascript_file_id=javascript_file_id,
        content_hash=new_content_hash,
        size_bytes=new_size,
        storage_path=storage_path,
    )
    session.add(version)
    return version, True


def changes_since(session: Session, program_id, hours: int = 24) -> list[Change]:
    since = datetime.utcnow() - timedelta(hours=hours)
    stmt = select(Change).where(Change.program_id == program_id, Change.detected_at >= since).order_by(
        Change.detected_at.desc()
    )
    return list(session.scalars(stmt))
