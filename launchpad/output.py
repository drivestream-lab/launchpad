"""Human TTY vs machine JSON for the same command result.

Default ``text`` keeps stdout unchanged. ``json`` sends the human TTY to
stderr and writes one JSON document to stdout. Command behaviour is identical.
"""

from __future__ import annotations

import json
import sys
from types import TracebackType
from typing import Any, TextIO


def normalize_format(value: str | None) -> str:
    fmt = (value or "text").strip().lower() or "text"
    if fmt not in {"text", "json"}:
        raise ValueError(f"unsupported --format {value!r} (use text or json)")
    return fmt


class CommandReport:
    """Collect the same pass/fail facts humans see; emit JSON when requested."""

    def __init__(
        self,
        command: str,
        *,
        output_format: str = "text",
        repo: str = "",
    ) -> None:
        self.command = command
        self.output_format = normalize_format(output_format)
        self.repo = repo
        self.checks: list[dict[str, Any]] = []
        self.error: str | None = None
        self._real_stdout: TextIO | None = None

    @property
    def is_json(self) -> bool:
        return self.output_format == "json"

    def __enter__(self) -> CommandReport:
        if self.is_json:
            self._real_stdout = sys.stdout
            sys.stdout = sys.stderr
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._restore_stdout()

    def _restore_stdout(self) -> None:
        if self._real_stdout is not None:
            sys.stdout = self._real_stdout
            self._real_stdout = None

    def add_check(self, check_id: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"id": check_id, "ok": bool(ok), "detail": detail or ""})

    def finish(self, exit_code: int) -> int:
        if not self.is_json:
            return exit_code
        self._restore_stdout()
        emit_result_json(
            command=self.command,
            repo=self.repo,
            exit_code=exit_code,
            error=self.error,
            checks=self.checks,
        )
        return exit_code


def emit_result_json(
    *,
    command: str,
    repo: str = "",
    exit_code: int,
    error: str | None = None,
    checks: list[dict[str, Any]] | None = None,
) -> None:
    payload = {
        "ok": exit_code == 0,
        "command": command,
        "repo": repo,
        "exit": exit_code,
        "error": error,
        "checks": checks or [],
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


def emit_failure_json(command: str, error: str, *, repo: str = "") -> None:
    emit_result_json(command=command, repo=repo, exit_code=1, error=error)
