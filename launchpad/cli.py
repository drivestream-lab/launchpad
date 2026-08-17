"""CLI entry point for launchpad.

Public commands:
  onboard interview   4-question setup → writes 5 config YAMLs locally
  init-client         Day-1 / Day-N GitHub setup (teams, repos, gitflow, board)
  apply-scaffold      Cookiecutter scaffold from scaffold-<org>.yaml
  apply-harness       Pin constitution + seed agent skills from harness-<org>.yaml
  reset-harness       Clear local harness materialization before remount
  apply-gates         Provision delivery labels + validate review-role bindings
  board-bind          Resolve programme engineering board from governance config
  apply-forge-templates  Seed issue forms + PR template from kit + governance
  status              Readiness checklist + kit version + constitution drift check
                      (service-mode: --no-client --config-dir --workspace)
                      (--format json: same checks, machine-readable stdout)
  doctor              Preflight: token, config, version checks
  clients             List registered clients (~/.config/launchpad/clients.yaml)
  whoami              Verify GITHUB_TOKEN and print login

All apply commands are dry-run by default — pass --apply to execute.
All commands require --meta OR --repo <name> (no --all flag).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from launchpad import __version__
from launchpad.clients import (
    ClientRegistryError,
    apply_client_context,
    config_dir_for_client,
    format_clients_table,
)
from launchpad.doctor import run as run_doctor
from launchpad.github_client import GitHubClient, GitHubError
from launchpad.onboarding.cli import add_onboard_parser
from launchpad.onboarding.errors import OnboardingError
from launchpad.schema.errors import SchemaError


def _add_apply_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True, help="print actions only (default)")
    group.add_argument("--apply", action="store_true", help="execute against GitHub API")


def _add_scope_flags(parser: argparse.ArgumentParser) -> None:
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--meta", action="store_true", help="target the meta repo")
    scope.add_argument("--repo", default="", metavar="NAME", help="target a specific app repo")


_SERVICE_MODE_COMMANDS = frozenset({"status", "apply-harness"})


def _add_service_mode_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace",
        default="",
        metavar="PATH",
        help=(
            "Clone workspace root (parent of <repo>); required for reliable "
            "service-mode with --no-client. Same meaning as clients.yaml workspace."
        ),
    )
    parser.add_argument(
        "--no-client",
        action="store_true",
        help=(
            "Service mode: do not use ~/.config/launchpad clients.yaml or env.d. "
            "Requires --config-dir. Honours process GITHUB_TOKEN/GH_TOKEN only."
        ),
    )


def _add_format_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help=(
            "text (default): current TTY on stdout. "
            "json: one JSON document on stdout; TTY on stderr. Same checks/exit."
        ),
    )


def _workspace_from_args(args: argparse.Namespace) -> Path | None:
    raw_ws = getattr(args, "workspace", "") or ""
    return Path(raw_ws).expanduser() if raw_ws.strip() else None


def _emit_json_failure_if_requested(args: argparse.Namespace, message: str) -> None:
    if getattr(args, "command", "") not in _SERVICE_MODE_COMMANDS:
        return
    from launchpad.output import emit_failure_json, normalize_format

    if normalize_format(getattr(args, "format", "text")) != "json":
        return
    emit_failure_json(
        getattr(args, "command", "") or "",
        message,
        repo=getattr(args, "repo", "") or "",
    )


def _dry_run_from_args(args: argparse.Namespace) -> bool:
    return not getattr(args, "apply", False)


def _active_client_id() -> str | None:
    cid = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
    return cid or None


def _config_dir(args: argparse.Namespace) -> Path:
    """Resolve config/ directory — always derived from clients.yaml.

    Priority:
      1. Explicit --config-dir flag  (escape hatch for scripts/testing)
      2. Active client from LAUNCHPAD_CLIENT env (set by apply_client_context)
         → reads path from clients.yaml, appends /config

    Raises ClientRegistryError if no client can be resolved.
    """
    raw = getattr(args, "config_dir", "") or ""
    if raw:
        return Path(raw).expanduser().resolve()

    client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
    if not client_id:
        raise ClientRegistryError(
            "no client active — pass --client <id> or set a default in "
            f"~/.config/launchpad/clients.yaml\n"
            "  Run 'launchpad clients' to see registered programmes.\n"
            "  First time? Run 'launchpad onboard interview'."
        )
    return config_dir_for_client(client_id)


# ── Command handlers ──────────────────────────────────────────────────────────


def cmd_doctor(args: argparse.Namespace) -> int:
    return run_doctor(verbose=args.verbose)


def cmd_clients(args: argparse.Namespace) -> int:
    print(format_clients_table())
    return 0


def cmd_whoami(args: argparse.Namespace) -> int:
    with GitHubClient(dry_run=False) as client:
        print(client.whoami())
    return 0


def cmd_init_client(args: argparse.Namespace) -> int:
    from launchpad.commands.init_client import run_init_client

    return run_init_client(
        meta=args.meta,
        repo_name=args.repo or "",
        apply=getattr(args, "apply", False),
        dry_run=_dry_run_from_args(args),
        config_dir=_config_dir(args),
        client_id=_active_client_id(),
    )


def cmd_apply_scaffold(args: argparse.Namespace) -> int:
    from launchpad.commands.apply_scaffold import run_apply_scaffold

    return run_apply_scaffold(
        meta=args.meta,
        repo_name=args.repo or "",
        apply=getattr(args, "apply", False),
        force=getattr(args, "force", False),
        config_dir=_config_dir(args),
        client_id=_active_client_id(),
    )


def cmd_apply_harness(args: argparse.Namespace) -> int:
    from launchpad.commands.apply_harness import run_apply_harness

    no_client = bool(getattr(args, "no_client", False))
    return run_apply_harness(
        meta=args.meta,
        repo_name=args.repo or "",
        apply=getattr(args, "apply", False),
        config_dir=_config_dir(args),
        workspace=_workspace_from_args(args),
        client_id=None if no_client else _active_client_id(),
        output_format=getattr(args, "format", "text"),
    )


def cmd_reset_harness(args: argparse.Namespace) -> int:
    from launchpad.commands.reset_harness import run_reset_harness

    return run_reset_harness(
        meta=args.meta,
        repo_name=args.repo or "",
        apply=getattr(args, "apply", False),
        include_seeded_workflows=getattr(args, "include_seeded_workflows", False),
        config_dir=_config_dir(args),
        client_id=_active_client_id(),
    )


def cmd_apply_forge_templates(args: argparse.Namespace) -> int:
    from launchpad.commands.apply_forge_templates import run_apply_forge_templates

    return run_apply_forge_templates(
        meta=args.meta,
        repo_name=args.repo or "",
        apply=getattr(args, "apply", False),
        force=getattr(args, "force", False),
        config_dir=_config_dir(args),
        client_id=_active_client_id(),
    )


def cmd_apply_gates(args: argparse.Namespace) -> int:
    from launchpad.commands.apply_gates import run_apply_gates

    return run_apply_gates(
        meta=args.meta,
        repo_name=args.repo or "",
        apply=getattr(args, "apply", False),
        config_dir=_config_dir(args),
        client_id=_active_client_id(),
    )


def cmd_board_bind(args: argparse.Namespace) -> int:
    from launchpad.commands.board_bind import run_board_bind

    return run_board_bind(
        meta=args.meta,
        repo_name=args.repo or "",
        apply=getattr(args, "apply", False),
        config_dir=_config_dir(args),
    )


def cmd_status(args: argparse.Namespace) -> int:
    from launchpad.commands.status import run_status

    no_client = bool(getattr(args, "no_client", False))
    return run_status(
        meta=args.meta,
        repo_name=args.repo or "",
        config_dir=_config_dir(args),
        workspace=_workspace_from_args(args),
        client_id=None if no_client else _active_client_id(),
        output_format=getattr(args, "format", "text"),
    )


# ── Parser ────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launchpad",
        description=(
            f"Launchpad factory automation (v{__version__} · GitHub only).\n"
            "Pass --client <id> to select your programme (see: launchpad clients).\n"
            "All commands are dry-run by default — pass --apply to execute."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--client",
        default=os.environ.get("LAUNCHPAD_CLIENT", ""),
        metavar="ID",
        help="client id from ~/.config/launchpad/clients.yaml (or LAUNCHPAD_CLIENT env)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── doctor ────────────────────────────────────────────────────────────────
    p = sub.add_parser("doctor", help="Preflight: token, config discovery, version pin")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_doctor)

    # ── clients ───────────────────────────────────────────────────────────────
    p = sub.add_parser("clients", help="List registered clients (clients.yaml + env.d)")
    p.set_defaults(func=cmd_clients)

    # ── whoami ────────────────────────────────────────────────────────────────
    p = sub.add_parser("whoami", help="Verify GITHUB_TOKEN and print GitHub login")
    p.set_defaults(func=cmd_whoami)

    # ── onboard ───────────────────────────────────────────────────────────────
    add_onboard_parser(sub)

    # ── init-client ───────────────────────────────────────────────────────────
    p = sub.add_parser(
        "init-client",
        help="Day-1/Day-N: ensure teams, repo, gitflow, board on GitHub",
    )
    _add_scope_flags(p)
    _add_apply_flags(p)
    p.add_argument("--config-dir", default="", help="Override config/ dir (default: derived from clients.yaml)")
    p.set_defaults(func=cmd_init_client)

    # ── apply-scaffold ────────────────────────────────────────────────────────
    p = sub.add_parser(
        "apply-scaffold",
        help="Run cookiecutter scaffold from scaffold-<org>.yaml",
    )
    _add_scope_flags(p)
    _add_apply_flags(p)
    p.add_argument("--force", action="store_true", help="Overwrite existing scaffold output")
    p.add_argument("--config-dir", default="", help="Override config/ dir (default: derived from clients.yaml)")
    p.set_defaults(func=cmd_apply_scaffold)

    # ── apply-harness ─────────────────────────────────────────────────────────
    p = sub.add_parser(
        "apply-harness",
        help="Pin constitution submodule + seed agent skills from harness-<org>.yaml",
    )
    _add_scope_flags(p)
    _add_apply_flags(p)
    p.add_argument("--config-dir", default="", help="Override config/ dir (default: derived from clients.yaml)")
    _add_service_mode_flags(p)
    _add_format_flag(p)
    p.set_defaults(func=cmd_apply_harness)

    # ── reset-harness ─────────────────────────────────────────────────────────
    p = sub.add_parser(
        "reset-harness",
        help="Clear local harness materialization (hub, pin, AGENTS block) before remount",
    )
    _add_scope_flags(p)
    _add_apply_flags(p)
    p.add_argument(
        "--include-seeded-workflows",
        action="store_true",
        help=(
            "Also remove kit-seeded workflow files (ci, policy-branch-name, "
            "and legacy board-seed-gate.yml if present)"
        ),
    )
    p.add_argument("--config-dir", default="", help="Override config/ dir (default: derived from clients.yaml)")
    p.set_defaults(func=cmd_reset_harness)

    # ── apply-forge-templates ─────────────────────────────────────────────────
    p = sub.add_parser(
        "apply-forge-templates",
        help="Seed issue forms + PR template from kit and governance config",
    )
    _add_scope_flags(p)
    _add_apply_flags(p)
    p.add_argument("--force", action="store_true", help="Overwrite existing forge template files")
    p.add_argument("--config-dir", default="", help="Override config/ dir (default: derived from clients.yaml)")
    p.set_defaults(func=cmd_apply_forge_templates)

    # ── apply-gates ──────────────────────────────────────────────────────────
    p = sub.add_parser(
        "apply-gates",
        help="Provision delivery labels and validate review-role bindings",
    )
    _add_scope_flags(p)
    _add_apply_flags(p)
    p.add_argument(
        "--config-dir",
        default="",
        help="Override config/ dir (default: derived from clients.yaml)",
    )
    p.set_defaults(func=cmd_apply_gates)

    # ── board-bind ────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "board-bind",
        help="Resolve programme engineering board; optionally link repo(s) to the project",
    )
    p.add_argument("--meta", action="store_true", help="link meta repo only (with --apply)")
    p.add_argument("--repo", default="", metavar="NAME", help="link one app repo (with --apply)")
    _add_apply_flags(p)
    p.add_argument(
        "--config-dir",
        default="",
        help="Override config/ dir (default: derived from clients.yaml)",
    )
    p.set_defaults(func=cmd_board_bind)

    # ── status ────────────────────────────────────────────────────────────────
    p = sub.add_parser(
        "status",
        help="Programme readiness checklist + single best NEXT: command",
    )
    _add_scope_flags(p)
    p.add_argument(
        "--config-dir",
        default="",
        help="Override config/ dir (default: derived from clients.yaml)",
    )
    _add_service_mode_flags(p)
    _add_format_flag(p)
    p.set_defaults(func=cmd_status)

    return parser


# Commands that work before clients.yaml exists (bootstrap / utility)
_CLIENT_EXEMPT_COMMANDS = {"doctor", "clients", "whoami", "onboard"}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(argv)
    command = getattr(args, "command", "") or ""
    no_client = bool(getattr(args, "no_client", False))
    client_flag_on_argv = any(
        a == "--client" or a.startswith("--client=") for a in raw_argv
    )

    # Service mode: caller-supplied config/workspace/token — skip registry.
    if no_client:
        if command not in _SERVICE_MODE_COMMANDS:
            msg = "--no-client is only valid with 'status' or 'apply-harness'"
            print(f"ERROR: {msg}", file=sys.stderr)
            _emit_json_failure_if_requested(args, msg)
            return 1
        if client_flag_on_argv:
            msg = (
                "--no-client is incompatible with --client "
                "(omit --client for service mode)"
            )
            print(f"ERROR: {msg}", file=sys.stderr)
            _emit_json_failure_if_requested(args, msg)
            return 1
        if not (getattr(args, "config_dir", "") or "").strip():
            msg = "--no-client requires --config-dir (path to synced meta config/)"
            print(f"ERROR: {msg}", file=sys.stderr)
            _emit_json_failure_if_requested(args, msg)
            return 1
        # Ignore leftover LAUNCHPAD_CLIENT from the parent environment.
        os.environ.pop("LAUNCHPAD_CLIENT", None)
        try:
            return args.func(args)
        except GitHubError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            body = getattr(exc, "body", "")
            if body:
                print(body, file=sys.stderr)
            _emit_json_failure_if_requested(args, str(exc))
            return 1
        except (
            RuntimeError,
            ValueError,
            FileNotFoundError,
            SchemaError,
            ClientRegistryError,
            OnboardingError,
        ) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            _emit_json_failure_if_requested(args, str(exc))
            return 1

    try:
        client_id = apply_client_context(getattr(args, "client", "") or "")
    except ClientRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _emit_json_failure_if_requested(args, str(exc))
        return 1

    # Commands that need a client error at _config_dir() time — but give a
    # better message here upfront so the user doesn't see a stack trace.
    if client_id is None and command not in _CLIENT_EXEMPT_COMMANDS:
        from launchpad.clients import CLIENTS_FILE
        msg = (
            f"no client active — pass --client <id> or set 'default:' in {CLIENTS_FILE}\n"
            f"  Run 'launchpad clients' to see registered programmes.\n"
            f"  First time? Run 'launchpad onboard interview'.\n"
            f"  Service/VM: launchpad status|apply-harness --no-client "
            f"--config-dir <meta>/config --workspace <root> --repo <name>"
        )
        print(f"ERROR: {msg}", file=sys.stderr)
        _emit_json_failure_if_requested(args, msg)
        return 1

    try:
        return args.func(args)
    except GitHubError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        body = getattr(exc, "body", "")
        if body:
            print(body, file=sys.stderr)
        _emit_json_failure_if_requested(args, str(exc))
        return 1
    except (
        RuntimeError,
        ValueError,
        FileNotFoundError,
        SchemaError,
        ClientRegistryError,
        OnboardingError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _emit_json_failure_if_requested(args, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
