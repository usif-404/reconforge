"""
Target scoring engine (methodology section 11).

Weights start as your stated defaults. `hunter_feedback` (interesting / noise
/ duplicate verdicts, section 14) can adjust `SIGNAL_WEIGHTS` over time — see
`recompute_weights_from_feedback` below. This is a simple frequency-based
adjustment, not a ML model; swap in something fancier once you have a few
hundred feedback rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_SIGNAL_WEIGHTS: dict[str, int] = {
    "new_asset": 30,
    "authentication": 25,
    "admin_functionality": 25,
    "payment": 20,
    "graphql": 20,
    "upload": 15,
    "api": 15,
    "newly_modified": 15,
    "unusual_technology": 10,
    "staging_or_beta": 10,
    "swagger_or_api_docs": 10,
    # negative signals
    "static_only": -20,
    "marketing": -20,
    "third_party": -30,
    "out_of_scope": -50,
}

# Per your section-14 example: multi-tenant identifiers becoming stronger
# signals once your feedback shows you find bugs there most often.
TENANT_ID_KEYWORDS = ["organizationId", "tenantId", "workspaceId", "teamId", "accountId"]


@dataclass
class ScoredTarget:
    subject: str
    score: int
    signals: list[str] = field(default_factory=list)


def score_target(signals_present: list[str], weights: dict[str, int] | None = None) -> int:
    weights = weights or DEFAULT_SIGNAL_WEIGHTS
    return sum(weights.get(signal, 0) for signal in signals_present)


def detect_signals(text_blob: str, is_new: bool, is_out_of_scope: bool = False) -> list[str]:
    """
    Cheap rule-based signal detection from a URL/endpoint/hostname string.
    This feeds score_target(); the AI Recon Analyst layer adds a second,
    context-aware pass on top of this for the final ranked list.
    """
    blob = text_blob.lower()
    signals = []

    if is_out_of_scope:
        return ["out_of_scope"]
    if is_new:
        signals.append("new_asset")
    if any(k in blob for k in ["login", "auth", "oauth", "sso", "signin"]):
        signals.append("authentication")
    if any(k in blob for k in ["admin", "internal", "impersonate", "manage"]):
        signals.append("admin_functionality")
    if any(k in blob for k in ["payment", "billing", "invoice", "checkout"]):
        signals.append("payment")
    if "graphql" in blob:
        signals.append("graphql")
    if any(k in blob for k in ["upload", "import"]):
        signals.append("upload")
    if "/api/" in blob or "/v1/" in blob or "/v2/" in blob or "/v3/" in blob:
        signals.append("api")
    if any(k in blob for k in ["swagger", "openapi", "api-docs"]):
        signals.append("swagger_or_api_docs")
    if any(k in blob for k in ["staging", "beta", "dev.", "internal."]):
        signals.append("staging_or_beta")
    if any(k in blob for k in ["static.", "cdn.", "assets."]):
        signals.append("static_only")
    if any(k in blob for k in ["marketing", "blog.", "careers."]):
        signals.append("marketing")
    if any(k in blob for k in TENANT_ID_KEYWORDS):
        signals.append("api")  # tenant-identifier presence reinforces API signal; weight bump handled below

    return signals or ["uncategorized"]


def recompute_weights_from_feedback(feedback_rows: list[dict]) -> dict[str, int]:
    """
    feedback_rows: [{"signals": [...], "verdict": "interesting"|"noise"|"duplicate"}, ...]

    Naive approach: bump weight of a signal that co-occurred with
    "interesting" more than baseline, dampen ones that co-occurred with
    "noise". This is meant to be run as a periodic offline job, not on
    every request — write results back into a config table, don't mutate
    DEFAULT_SIGNAL_WEIGHTS at runtime.
    """
    weights = dict(DEFAULT_SIGNAL_WEIGHTS)
    interesting_counts: dict[str, int] = {}
    noise_counts: dict[str, int] = {}

    for row in feedback_rows:
        target = interesting_counts if row["verdict"] == "interesting" else noise_counts
        for signal in row.get("signals", []):
            target[signal] = target.get(signal, 0) + 1

    for signal, count in interesting_counts.items():
        noise = noise_counts.get(signal, 0)
        if count + noise < 5:
            continue  # not enough data yet
        ratio = count / (count + noise)
        if ratio > 0.7:
            weights[signal] = weights.get(signal, 0) + 5
        elif ratio < 0.3:
            weights[signal] = weights.get(signal, 0) - 5

    return weights
