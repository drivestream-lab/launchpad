"""board-bind — resolve programme board binding and optionally link repos."""

from __future__ import annotations

import sys
from pathlib import Path

from launchpad.forge.providers.github import GitHubForgeProvider
from launchpad.harness.paths import PM_HARNESS_PROFILE
from launchpad.programme.board_binding import enrich_board_binding, resolve_board_binding
from launchpad.schema import SchemaError
from launchpad.schema.governance import load_governance
from launchpad.schema.programme import load_programme
from launchpad.ui import print_next_box


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def run_board_bind(
    *,
    meta: bool = False,
    repo_name: str = "",
    apply: bool = False,
    config_dir: Path | None = None,
    workspace: Path | None = None,
) -> int:
    if config_dir is None:
        raise RuntimeError(
            "config_dir not resolved — pass --client <id> or run launchpad onboard interview"
        )

    governance_path = _find_config(config_dir, "governance-*.yaml")
    programme_path = config_dir / "programme.yaml"
    if not governance_path or not programme_path.is_file():
        print("ERROR: programme and governance config are required", file=sys.stderr)
        return 1

    try:
        governance = load_governance(governance_path)
        programme = load_programme(programme_path)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    org = governance.org
    binding = resolve_board_binding(org, governance.project_board)

    if apply and binding.configured:
        try:
            from launchpad.github_client import GitHubClient

            with GitHubClient(dry_run=False) as client:
                binding = enrich_board_binding(binding, client)
        except Exception as exc:  # noqa: BLE001 — surface token/API issues clearly
            print(f"WARN: could not enrich board from GitHub API: {exc}", file=sys.stderr)

    print(f"Programme board binding ({org})")
    print(f"  enabled:  {binding.enabled}")
    print(f"  name:     {binding.name or '(not set)'}")
    print(f"  number:   {binding.number if binding.number is not None else '(not set)'}")
    print(f"  url:      {binding.url or '(not set)'}")
    print(f"  source:   {governance_path}")

    if not binding.configured:
        print(
            "\nERROR: project_board.enabled and project_board.name are required in governance",
            file=sys.stderr,
        )
        return 1

    if not apply:
        target_flag = "--meta" if meta else f"--repo {repo_name or programme.meta_repo}"
        print_next_box(
            [
                f"launchpad board-bind {target_flag} --apply  # link repo(s) to board",
                "/create-board-tickets INIT-<id>  # after spec merge (in app repo)",
            ]
        )
        return 0

    if meta:
        targets = [programme.meta_repo]
    elif repo_name:
        if repo_name not in governance.repos:
            print(f"ERROR: repo '{repo_name}' not in governance", file=sys.stderr)
            return 1
        targets = [repo_name]
    else:
        targets = [
            name
            for name, entry in governance.repos.items()
            if entry.stack != PM_HARNESS_PROFILE
        ]

    with GitHubForgeProvider(dry_run=False) as forge:
        from launchpad.github_client import GitHubClient

        with GitHubClient(dry_run=False) as client:
            binding = enrich_board_binding(binding, client)
        board_id = ""
        if binding.number is not None:
            from launchpad.github_ops import _project_meta

            with GitHubClient(dry_run=False) as client:
                board_id = str(_project_meta(client, org, binding.number)["id"])
        if not board_id:
            board_id = forge.ensure_project_board(org, binding.name)

        for target_repo in targets:
            if target_repo not in governance.repos:
                print(f"  WARN: skip {target_repo} — not in governance", file=sys.stderr)
                continue
            print(f"  Linking {org}/{target_repo} → {binding.name}")
            forge.link_repo_to_project(org, target_repo, board_id)

    if binding.number is not None and not governance.project_board.get("number"):
        print(
            f"\nTip: add to governance project_board for offline resolution:\n"
            f"  number: {binding.number}\n"
            f"  url: {binding.url}",
        )

    return 0
