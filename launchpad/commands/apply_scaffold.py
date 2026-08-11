"""apply-scaffold — run cookiecutter scaffold from scaffold-<org>.yaml.

Reads scaffold-<org>.yaml ONLY.
Context is passed free-form to cookiecutter — no kit-owned key validation.
Template owners can evolve their cookiecutter.json without Launchpad changes.

Usage:
  launchpad apply-scaffold --meta [--apply] [--force]
  launchpad apply-scaffold --repo <name> [--apply] [--force]
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from launchpad.clients import resolve_programme_workspace
from launchpad.schema import SchemaError
from launchpad.schema.scaffold import ScaffoldEntry, ScaffoldSchema, load_scaffold
from launchpad.ui import print_next_box


class ScaffoldTemplateError(Exception):
    """Cookiecutter template or hook failed — operator-facing message only."""

    def __init__(self, message: str, *, hints: list[str] | None = None) -> None:
        super().__init__(message)
        self.hints = hints or []


def _parse_cookiecutter_output(captured: str) -> list[str]:
    """Extract hook/template messages; drop cookiecutter tracebacks."""
    messages: list[str] = []
    for raw in captured.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Traceback (most recent call last):"):
            break
        if line.startswith("File ") and "site-packages" in line:
            break
        if line.startswith("ERROR:"):
            messages.append(line[len("ERROR:") :].strip())
        elif "Stopping generation because" in line:
            messages.append(line)
    return messages


def _print_scaffold_template_error(
    exc: ScaffoldTemplateError,
    *,
    sca_path: Path,
    label: str,
    meta: bool,
    repo_name: str,
) -> None:
    print(f"ERROR: scaffold template failed — {exc}", file=sys.stderr)
    for hint in exc.hints:
        print(f"  {hint}", file=sys.stderr)
    client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
    client_prefix = f"--client {client_id} " if client_id else ""
    target_flag = "--meta" if meta else f"--repo {repo_name}"
    block = sca_path.name if label == "meta" else f"{sca_path.name} → repos.{label}.context"
    print(
        f"\n  Fix template context in config/{block}, then re-run:",
        file=sys.stderr,
    )
    print(
        f"    launchpad {client_prefix}apply-scaffold {target_flag} --apply --force",
        file=sys.stderr,
    )
    print(
        "  Validation rules live in the cookiecutter template (not launchpad).",
        file=sys.stderr,
    )


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def _scaffold_target_dir(
    ws: Path,
    *,
    meta: bool,
    repo_name: str,
    prog: object | None,
    entry: ScaffoldEntry,
) -> Path:
    """Directory cookiecutter will write into (workspace / project folder)."""
    if meta:
        if prog is not None and hasattr(prog, "meta_repo"):
            return ws / str(getattr(prog, "meta_repo"))
        meta_repo = entry.context.get("meta_repo")
        if meta_repo:
            return ws / str(meta_repo)
        return ws
    return ws / repo_name


def _print_exists_hint(
    *,
    target: Path,
    meta: bool,
    repo_name: str,
) -> None:
    client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
    client_prefix = f"--client {client_id} " if client_id else ""
    target_flag = "--meta" if meta else f"--repo {repo_name}"
    print(f"ERROR: output directory already exists: {target}", file=sys.stderr)
    print(
        "  Normal after init-client — the local clone is already there.",
        file=sys.stderr,
    )
    print(
        "  Re-run with --force to overlay the foundation template "
        "(keeps .git; does not delete local-only files):",
        file=sys.stderr,
    )
    print(
        f"  launchpad {client_prefix}apply-scaffold {target_flag} --apply --force",
        file=sys.stderr,
    )


def _resolve_template_url(entry: ScaffoldEntry) -> str:
    """Resolve template shorthand to a clonable URL."""
    t = entry.template
    if t.startswith("gh:"):
        slug = t[3:]
        return f"https://github.com/{slug}"
    return t


def _run_cookiecutter(
    template_url: str,
    ref: str,
    context: dict,
    *,
    output_dir: Path,
    force: bool = False,
) -> None:
    """Invoke cookiecutter against the template."""
    try:
        from cookiecutter.main import cookiecutter
        from cookiecutter.exceptions import FailedHookException
    except ImportError:
        raise RuntimeError("cookiecutter is not installed.  Run: pip install cookiecutter")

    stderr_capture = io.StringIO()
    stdout_capture = io.StringIO()
    try:
        with redirect_stderr(stderr_capture), redirect_stdout(stdout_capture):
            cookiecutter(
                template_url,
                checkout=ref,
                no_input=True,
                extra_context=context,
                output_dir=str(output_dir),
                overwrite_if_exists=force,
            )
    except FailedHookException as exc:
        captured = stderr_capture.getvalue() + stdout_capture.getvalue()
        messages = _parse_cookiecutter_output(captured)
        primary = messages[0] if messages else str(exc).strip() or "template hook failed"
        extra = messages[1:] if len(messages) > 1 else []
        raise ScaffoldTemplateError(primary, hints=extra) from None
    except Exception as exc:
        captured = stderr_capture.getvalue() + stdout_capture.getvalue()
        messages = _parse_cookiecutter_output(captured)
        if messages:
            raise ScaffoldTemplateError(messages[0], hints=messages[1:]) from None
        if not force and "already exists" in str(exc).lower():
            raise
        raise ScaffoldTemplateError(str(exc).strip() or "cookiecutter failed") from None


def run_apply_scaffold(
    *,
    meta: bool = False,
    repo_name: str = "",
    apply: bool = False,
    force: bool = False,
    config_dir: Path | None = None,  # None only in tests — main() always resolves via clients.yaml
    client_id: str | None = None,
) -> int:
    if not meta and not repo_name:
        print("ERROR: pass --meta or --repo <name>", file=sys.stderr)
        return 1

    if config_dir is None:
        # Should not reach here — main() blocks client-less commands early.
        raise RuntimeError("config_dir not resolved — pass --client <id> or run launchpad onboard interview")
    cdir = config_dir

    sca_path = _find_config(cdir, "scaffold-*.yaml")
    if sca_path is None:
        print(f"ERROR: scaffold-<org>.yaml not found in {cdir}", file=sys.stderr)
        print("  Run 'launchpad onboard interview' first", file=sys.stderr)
        return 1

    try:
        sca = load_scaffold(sca_path)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    prog = None
    try:
        prog_path = cdir / "programme.yaml"
        if prog_path.is_file():
            from launchpad.schema.programme import load_programme
            prog = load_programme(prog_path)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        ws = resolve_programme_workspace(client_id=client_id, config_dir=cdir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if meta:
        entry = sca.meta
        if entry is None:
            print("ERROR: scaffold-<org>.yaml has no 'meta' block", file=sys.stderr)
            return 1
        label = "meta"
        output_dir = ws
    else:
        if repo_name not in sca.repos:
            print(f"ERROR: repo '{repo_name}' not in scaffold-<org>.yaml repos", file=sys.stderr)
            print(f"  Known repos: {sorted(sca.repos)}", file=sys.stderr)
            return 1
        entry = sca.repos[repo_name]
        label = repo_name
        output_dir = ws

    if not entry.enabled:
        print(f"  scaffold.{label}.enabled = false — nothing to do.")
        print(f"  Enable it in {sca_path.name} and re-run.")
        return 0

    template_url = _resolve_template_url(entry)
    ref = entry.ref
    context = entry.context

    print(f"apply-scaffold  →  {label}")
    print(f"  template:  {entry.template}")
    print(f"  ref:       {ref}")
    print(f"  context:   {context}")
    print(f"  output:    {output_dir}")
    print()

    if not apply:
        print("  [dry-run] No files written.  Pass --apply to execute.")
        target_flag = "--meta" if meta else f"--repo {repo_name}"
        print_next_box([f"launchpad apply-scaffold {target_flag} --apply"])
        return 0

    target_dir = _scaffold_target_dir(
        ws, meta=meta, repo_name=repo_name, prog=prog, entry=entry
    )
    if target_dir.is_dir() and not force:
        _print_exists_hint(target=target_dir, meta=meta, repo_name=repo_name)
        return 1

    try:
        _run_cookiecutter(template_url, ref, context, output_dir=output_dir, force=force)
    except ScaffoldTemplateError as exc:
        _print_scaffold_template_error(
            exc,
            sca_path=sca_path,
            label=label,
            meta=meta,
            repo_name=repo_name,
        )
        return 1
    except Exception as exc:
        if not force and "already exists" in str(exc).lower():
            _print_exists_hint(target=target_dir, meta=meta, repo_name=repo_name)
            return 1
        print(f"ERROR: cookiecutter failed: {exc}", file=sys.stderr)
        return 1

    # Marker for status — records which foundation was applied
    marker_repo = ws / (prog.meta_repo if meta and prog else repo_name)
    marker_path = marker_repo / ".launchpad-scaffold"
    marker_path.write_text(
        f"template: {entry.template}\nref: {ref}\n",
        encoding="utf-8",
    )
    print(f"  ✔  scaffold applied → {marker_repo}")
    print()

    client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
    client_prefix = f"--client {client_id} " if client_id else ""
    target_flag = "--meta" if meta else f"--repo {repo_name}"
    if meta:
        next_cmd = f"launchpad {client_prefix}apply-harness --meta --apply"
    else:
        next_cmd = f"launchpad {client_prefix}apply-harness --repo {repo_name} --apply"

    print_next_box([next_cmd.strip()])
    return 0
