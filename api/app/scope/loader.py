"""Load program.yaml files from /programs into ProgramScopeConfig objects."""
from __future__ import annotations

import pathlib

import yaml

from app.scope.manager import ProgramScopeConfig, ScopeManager


def load_program_file(path: pathlib.Path) -> ProgramScopeConfig:
    data = yaml.safe_load(path.read_text())
    program = data["program"]
    scope = data.get("scope", {})
    rules = data.get("rules", {})
    rate_limits = data.get("rate_limits", {})

    return ProgramScopeConfig(
        name=program["name"],
        include=scope.get("include", []),
        exclude=scope.get("exclude", []),
        include_ip_ranges=scope.get("include_ip_ranges", []),
        rules=rules,
        global_rps=rate_limits.get("global_rps", 5),
        concurrency=rate_limits.get("concurrency", 10),
        prohibited=data.get("prohibited", []),
    )


def load_scope_manager(programs_dir: str = "programs") -> ScopeManager:
    programs: dict[str, ProgramScopeConfig] = {}
    for path in pathlib.Path(programs_dir).glob("*.yaml"):
        cfg = load_program_file(path)
        programs[cfg.name] = cfg
    return ScopeManager(programs)
