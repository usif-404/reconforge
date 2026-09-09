"""
Canonical knowledge-base schema.

Design rule: everything that can appear/disappear/change gets first_seen,
last_seen, first_run_id, last_run_id. That's what makes change detection
(the whole point of this system) a SQL query instead of a diff script.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def uuid_pk() -> Column:
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# --------------------------------------------------------------------------- #
# Programs / scope
# --------------------------------------------------------------------------- #


class Program(Base):
    __tablename__ = "programs"

    id = uuid_pk()
    name = Column(String, unique=True, nullable=False)
    platform = Column(String)  # hackerone / bugcrowd / intigriti / private
    active = Column(Boolean, default=True)
    score = Column(Integer, default=0)  # program_scorer output, see scoring/
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    scopes = relationship("ProgramScope", back_populates="program")
    rules = relationship("ProgramRule", back_populates="program", uselist=False)


class ProgramScope(Base):
    __tablename__ = "program_scopes"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    pattern = Column(String, nullable=False)  # "*.example.com"
    included = Column(Boolean, default=True)  # False = explicit exclusion

    program = relationship("Program", back_populates="scopes")


class ProgramRule(Base):
    __tablename__ = "program_rules"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), unique=True)
    passive_recon = Column(Boolean, default=True)
    crawling = Column(Boolean, default=True)
    active_dns = Column(Boolean, default=True)
    directory_discovery = Column(Boolean, default=False)
    automated_scanning = Column(Boolean, default=False)
    global_rps = Column(Integer, default=5)
    concurrency = Column(Integer, default=10)
    no_dos = Column(Boolean, default=True)
    no_social_engineering = Column(Boolean, default=True)
    no_destructive_testing = Column(Boolean, default=True)

    program = relationship("Program", back_populates="rules")


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #


class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (UniqueConstraint("program_id", "name"),)

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    first_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))
    last_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))


class Subdomain(Base):
    __tablename__ = "subdomains"
    __table_args__ = (UniqueConstraint("program_id", "hostname"),)

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    hostname = Column(String, nullable=False, index=True)
    source = Column(String)  # subfinder / amass / crtsh / github-subdomains ...
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    first_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))
    last_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))


class DNSRecord(Base):
    __tablename__ = "dns_records"

    id = uuid_pk()
    subdomain_id = Column(UUID(as_uuid=True), ForeignKey("subdomains.id"), nullable=False)
    record_type = Column(String)  # A / AAAA / CNAME / MX / TXT / NS
    value = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class IPAddress(Base):
    __tablename__ = "ip_addresses"
    __table_args__ = (UniqueConstraint("program_id", "ip"),)

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    ip = Column(String, nullable=False, index=True)
    asn = Column(String)
    asn_org = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class Service(Base):
    """Open port / non-HTTP service, from naabu/nmap."""

    __tablename__ = "services"

    id = uuid_pk()
    ip_address_id = Column(UUID(as_uuid=True), ForeignKey("ip_addresses.id"), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String, default="tcp")
    banner = Column(Text)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class HTTPService(Base):
    """httpx probe result for a subdomain."""

    __tablename__ = "http_services"

    id = uuid_pk()
    subdomain_id = Column(UUID(as_uuid=True), ForeignKey("subdomains.id"), nullable=False)
    url = Column(String, nullable=False)
    status_code = Column(Integer)
    title = Column(String)
    content_length = Column(Integer)
    body_hash = Column(String, index=True)  # for change detection
    favicon_hash = Column(String)
    server_header = Column(String)
    cname = Column(String)
    tls_cert_fingerprint = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    first_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))
    last_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))


class Technology(Base):
    """Fingerprinted tech (wappalyzer-style) for an http_service."""

    __tablename__ = "technologies"

    id = uuid_pk()
    http_service_id = Column(UUID(as_uuid=True), ForeignKey("http_services.id"), nullable=False)
    name = Column(String, nullable=False)
    version = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


# --------------------------------------------------------------------------- #
# URLs / endpoints / params
# --------------------------------------------------------------------------- #


class URLRecord(Base):
    __tablename__ = "urls"
    __table_args__ = (UniqueConstraint("program_id", "url", "method"),)

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    url = Column(Text, nullable=False)
    method = Column(String, default="GET")
    source = Column(String)  # katana / gau / waymore / hakrawler / js-extracted
    status_code = Column(Integer)
    content_type = Column(String)
    requires_auth = Column(Boolean, default=False)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    first_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))
    last_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))


class Endpoint(Base):
    """Normalized API-shaped endpoint (path template, not raw URL)."""

    __tablename__ = "endpoints"
    __table_args__ = (UniqueConstraint("program_id", "path_template", "method"),)

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    path_template = Column(String, nullable=False)  # /api/orders/{id}
    method = Column(String, default="GET")
    category = Column(String)  # admin / auth / upload / payment / graphql / internal
    score = Column(Integer, default=0)  # target_scorer output
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class Parameter(Base):
    __tablename__ = "parameters"

    id = uuid_pk()
    endpoint_id = Column(UUID(as_uuid=True), ForeignKey("endpoints.id"), nullable=False)
    name = Column(String, nullable=False)
    source = Column(String)  # arjun / paraminer / js-extracted / manual
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


# --------------------------------------------------------------------------- #
# JavaScript
# --------------------------------------------------------------------------- #


class JavaScriptFile(Base):
    __tablename__ = "javascript_files"
    __table_args__ = (UniqueConstraint("program_id", "url"),)

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    url = Column(Text, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class JavaScriptVersion(Base):
    """A specific fetched revision of a JS file — this is what change detection diffs."""

    __tablename__ = "javascript_versions"

    id = uuid_pk()
    javascript_file_id = Column(UUID(as_uuid=True), ForeignKey("javascript_files.id"), nullable=False)
    content_hash = Column(String, nullable=False, index=True)
    size_bytes = Column(Integer)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    storage_path = Column(String)  # raw file kept on disk/object storage, not in DB


class JavaScriptFinding(Base):
    """Output of the JS Analyst AI agent — routes, secrets, role checks, etc."""

    __tablename__ = "javascript_findings"

    id = uuid_pk()
    javascript_version_id = Column(UUID(as_uuid=True), ForeignKey("javascript_versions.id"), nullable=False)
    finding_type = Column(String)  # api_route / graphql_op / role_check / secret / feature_flag
    value = Column(Text, nullable=False)
    context_snippet = Column(Text)
    risk_note = Column(Text)  # AI's reasoning, human-readable
    created_at = Column(DateTime, default=datetime.utcnow)


# --------------------------------------------------------------------------- #
# API surface
# --------------------------------------------------------------------------- #


class APIEndpoint(Base):
    __tablename__ = "api_endpoints"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    base_url = Column(String)
    spec_source = Column(String)  # swagger / openapi / kiterunner / manual
    path = Column(String, nullable=False)
    method = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class GraphQLOperation(Base):
    __tablename__ = "graphql_operations"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    endpoint_url = Column(String, nullable=False)
    operation_name = Column(String, nullable=False)
    operation_type = Column(String)  # query / mutation / subscription
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


# --------------------------------------------------------------------------- #
# Runs / changes / findings
# --------------------------------------------------------------------------- #


class ReconRun(Base):
    __tablename__ = "recon_runs"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String, default="running")  # running / completed / failed


class ToolRun(Base):
    __tablename__ = "tool_runs"

    id = uuid_pk()
    recon_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"), nullable=False)
    tool_name = Column(String, nullable=False)  # subfinder / httpx / katana ...
    command = Column(Text)
    exit_code = Column(Integer)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)


class Artifact(Base):
    """Raw tool output kept on disk; DB just indexes it."""

    __tablename__ = "artifacts"

    id = uuid_pk()
    tool_run_id = Column(UUID(as_uuid=True), ForeignKey("tool_runs.id"), nullable=False)
    path = Column(String, nullable=False)
    kind = Column(String)  # jsonl / txt / har


class ChangeType(str, enum.Enum):
    new_host = "new_host"
    new_ip = "new_ip"
    dns_changed = "dns_changed"
    new_technology = "new_technology"
    new_port = "new_port"
    new_endpoint = "new_endpoint"
    new_parameter = "new_parameter"
    new_js = "new_js"
    modified_js = "modified_js"
    new_graphql_op = "new_graphql_op"
    new_api_version = "new_api_version"
    new_swagger = "new_swagger"
    new_admin_functionality = "new_admin_functionality"
    new_auth_flow = "new_auth_flow"
    new_upload_functionality = "new_upload_functionality"
    new_payment_functionality = "new_payment_functionality"
    new_staging_asset = "new_staging_asset"


class Change(Base):
    __tablename__ = "changes"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    recon_run_id = Column(UUID(as_uuid=True), ForeignKey("recon_runs.id"))
    change_type = Column(Enum(ChangeType), nullable=False)
    subject = Column(String, nullable=False)  # hostname / url / js file, human readable
    detail = Column(JSON)  # old value / new value / diff
    detected_at = Column(DateTime, default=datetime.utcnow)


class FindingStatus(str, enum.Enum):
    ai_suggested = "ai_suggested"      # AI raised it — nothing confirmed
    investigating = "investigating"    # you're looking at it
    rejected = "rejected"              # you decided it's noise
    confirmed = "confirmed"            # you personally verified impact
    submitted = "submitted"            # report filed to the platform


class Finding(Base):
    """
    State machine is intentional: only a human transition can move a row to
    `confirmed` or `submitted`. No AI agent code path in this project writes
    those two values — see ai/agents/*.py docstrings.
    """

    __tablename__ = "findings"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    endpoint_id = Column(UUID(as_uuid=True), ForeignKey("endpoints.id"))
    title = Column(String, nullable=False)
    vuln_class = Column(String)  # idor / bola / auth_bypass / business_logic ...
    status = Column(Enum(FindingStatus), default=FindingStatus.ai_suggested)
    severity_estimate = Column(String)  # your own estimate, not AI's
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id = uuid_pk()
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id"), nullable=False)
    kind = Column(String)  # request / response / screenshot / note
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# --------------------------------------------------------------------------- #
# AI layer
# --------------------------------------------------------------------------- #


class AITask(Base):
    __tablename__ = "ai_tasks"

    id = uuid_pk()
    agent_name = Column(String, nullable=False)  # recon_analyst / js_analyst / ...
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"))
    input_ref = Column(String)  # path or DB ref to what was fed in
    status = Column(String, default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = uuid_pk()
    ai_task_id = Column(UUID(as_uuid=True), ForeignKey("ai_tasks.id"), nullable=False)
    subject = Column(String)  # hostname / endpoint / js file this is about
    score = Column(Integer)
    reasoning = Column(Text)
    raw_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class ManualHuntQueueItem(Base):
    __tablename__ = "manual_hunt_queue"

    id = uuid_pk()
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    subject = Column(String, nullable=False)
    score = Column(Integer, default=0)
    reason = Column(Text)
    source_ai_analysis_id = Column(UUID(as_uuid=True), ForeignKey("ai_analysis.id"))
    dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = uuid_pk()
    channel = Column(String)  # discord / telegram
    subject = Column(String)
    body = Column(Text)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class HunterFeedback(Base):
    """
    Your Interesting/Noise/Duplicate verdicts on AI suggestions. This table
    is the training signal described in the methodology doc (section 14) —
    consumed by scoring/target_scorer.py to personalize weights over time.
    """

    __tablename__ = "hunter_feedback"

    id = uuid_pk()
    manual_hunt_queue_item_id = Column(UUID(as_uuid=True), ForeignKey("manual_hunt_queue.id"))
    verdict = Column(String)  # interesting / noise / duplicate
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeEntry(Base):
    """Your personal vulnerability-pattern knowledge base (section 15)."""

    __tablename__ = "knowledge_entries"

    id = uuid_pk()
    vulnerability = Column(String, nullable=False)
    root_cause = Column(Text)
    endpoint_pattern = Column(String)
    technology = Column(String)
    required_conditions = Column(Text)
    discovery_method = Column(Text)
    impact = Column(Text)
    keywords = Column(JSON)  # list[str], used for retrieval
    source_url = Column(String)  # e.g. a Hacktivity report you studied
    created_at = Column(DateTime, default=datetime.utcnow)
