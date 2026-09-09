"""
Scope Manager.

Rule (non-negotiable, per the methodology doc): no active stage may run
against a target without calling `is_authorized()` first. Discovery of a
domain/IP/CNAME does NOT make it an authorized target — it only gets added
as an asset row; authorization is a separate, explicit check every time.

This module has zero dependency on the rest of the app on purpose, so it can
be unit tested in isolation and imported by every pipeline stage and worker.
"""
from __future__ import annotations

import fnmatch
import ipaddress
from dataclasses import dataclass, field
from enum import Enum


class Action(str, Enum):
    PASSIVE_RECON = "passive_recon"
    CRAWLING = "crawling"
    ACTIVE_DNS = "active_dns"
    DIRECTORY_DISCOVERY = "directory_discovery"
    AUTOMATED_SCANNING = "automated_scanning"


@dataclass
class ScopeDecision:
    allowed: bool
    reason: str


@dataclass
class ProgramScopeConfig:
    """In-memory representation of one program.yaml, loaded by programs/loader.py."""

    name: str
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    include_ip_ranges: list[str] = field(default_factory=list)
    rules: dict[str, bool] = field(default_factory=dict)  # Action.value -> bool
    global_rps: int = 5
    concurrency: int = 10
    prohibited: list[str] = field(default_factory=list)  # dos / social_engineering / destructive_testing


def _host_matches(host: str, pattern: str) -> bool:
    host = host.lower().rstrip(".")
    pattern = pattern.lower().rstrip(".")
    return fnmatch.fnmatch(host, pattern)


def _ip_in_ranges(ip: str, ranges: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for r in ranges:
        try:
            if addr in ipaddress.ip_network(r, strict=False):
                return True
        except ValueError:
            continue
    return False


class ScopeManager:
    def __init__(self, programs: dict[str, ProgramScopeConfig]):
        self._programs = programs

    def is_in_scope(self, program_name: str, target: str) -> ScopeDecision:
        """
        Pure scope-membership check (no action/rate-limit logic).
        `target` may be a hostname or an IP.
        """
        program = self._programs.get(program_name)
        if not program:
            return ScopeDecision(False, f"unknown program '{program_name}'")

        for pattern in program.exclude:
            if _host_matches(target, pattern):
                return ScopeDecision(False, f"matches exclusion pattern '{pattern}'")

        for pattern in program.include:
            if _host_matches(target, pattern):
                return ScopeDecision(True, f"matches inclusion pattern '{pattern}'")

        if program.include_ip_ranges and _ip_in_ranges(target, program.include_ip_ranges):
            return ScopeDecision(True, "matches included IP range")

        return ScopeDecision(False, "does not match any inclusion pattern")

    def is_authorized(self, program_name: str, target: str, action: Action) -> ScopeDecision:
        """
        Full check: in scope AND the specific action type is permitted by the
        program's rules. Call this — not is_in_scope — before running a tool.
        """
        scope_decision = self.is_in_scope(program_name, target)
        if not scope_decision.allowed:
            return scope_decision

        program = self._programs[program_name]
        if not program.rules.get(action.value, False):
            return ScopeDecision(
                False, f"action '{action.value}' disabled for program '{program_name}'"
            )

        return ScopeDecision(True, f"authorized for {action.value}")

    def rate_limit_for(self, program_name: str) -> tuple[int, int]:
        """Returns (global_rps, concurrency) for a program, defaulting conservatively."""
        program = self._programs.get(program_name)
        if not program:
            return (1, 1)
        return (program.global_rps, program.concurrency)


def require_authorization(scope_manager: ScopeManager, program_name: str, target: str, action: Action) -> None:
    """
    Convenience guard for pipeline stages: raises instead of returning a bool,
    so a forgotten `if` doesn't silently let an unauthorized scan through.

    Usage:
        require_authorization(scope, "example", "admin.example.com", Action.ACTIVE_DNS)
        # only reached if authorized
        run_dnsx(...)
    """
    decision = scope_manager.is_authorized(program_name, target, action)
    if not decision.allowed:
        raise PermissionError(
            f"BLOCKED: {target} / {action.value} for program '{program_name}': {decision.reason}"
        )
