"""
Every stage subclasses ReconStage. run() is expected to:
  1. Call self.require_scope(target, action) for each target before touching it.
  2. Shell out to the real tool (subprocess) with JSON output where possible.
  3. Return raw results as a list[dict] — normalization happens in stages/normalize.py.

Stages are intentionally dumb single-purpose wrappers. All "is this
interesting" logic lives in scoring/ and ai/, not here.
"""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass

from app.scope.manager import Action, ScopeManager, require_authorization


@dataclass
class StageResult:
    tool: str
    ok: bool
    stdout: str
    stderr: str
    exit_code: int


class ReconStage:
    tool_name: str = "base"
    action: Action = Action.PASSIVE_RECON

    def __init__(self, scope_manager: ScopeManager, program_name: str):
        self.scope_manager = scope_manager
        self.program_name = program_name

    def require_scope(self, target: str) -> None:
        require_authorization(self.scope_manager, self.program_name, target, self.action)

    def run_command(self, command: str, timeout: int = 600) -> StageResult:
        proc = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return StageResult(
            tool=self.tool_name,
            ok=proc.returncode == 0,
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
        )

    def run(self, targets: list[str]) -> list[dict]:  # pragma: no cover - interface
        raise NotImplementedError
