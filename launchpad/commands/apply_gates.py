"""apply-gates — provision delivery labels and validate review-role bindings."""

from __future__ import annotations

import sys
from pathlib import Path

from launchpad.clients import ClientRegistryError, resolve_programme_workspace
from launchpad.forge.providers.github import GitHubForgeProvider
from launchpad.harness.paths import PM_HARNESS_PROFILE, PRAYOG_SKILLS_SUBMODULE_REL
from launchpad.harness.skills_resolve import (
    HarnessResolveError,
    resolve_delivery_contract,
    resolve_gate_resources,
)
from launchpad.schema import SchemaError
from launchpad.schema.governance import load_governance
from launchpad.schema.harness import load_harness
from launchpad.schema.programme import load_programme
from launchpad.ui import print_next_box


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def run_apply_gates(
    *,
    meta: bool = False,
    repo_name: str = "",
    apply: bool = False,
    config_dir: Path | None = None,
    workspace: Path | None = None,
) -> int:
    if not meta and not repo_name:
        print("ERROR: pass --meta or --repo <name>", file=sys.stderr)
        return 1
    if config_dir is None:
        raise RuntimeError(
            "config_dir not resolved — pass --client <id> or run launchpad onboard interview"
        )

    harness_path = _find_config(config_dir, "harness-*.yaml")
    governance_path = _find_config(config_dir, "governance-*.yaml")
    programme_path = config_dir / "programme.yaml"
    if not harness_path or not governance_path or not programme_path.is_file():
        print("ERROR: programme, governance, and harness config are required", file=sys.stderr)
        return 1

    try:
        harness = load_harness(harness_path)
        governance = load_governance(governance_path)
        programme = load_programme(programme_path)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    target = programme.meta_repo if meta else repo_name
    if not meta and target not in governance.repos:
        print(f"ERROR: repo '{target}' not in governance", file=sys.stderr)
        return 1
    stack = (
        governance.repos[target].stack
        if target in governance.repos
        else PM_HARNESS_PROFILE
    )
    profile_name = harness.resolve_profile(target, stack)
    if not profile_name or profile_name not in harness.profiles:
        print(f"ERROR: no harness profile for {target}", file=sys.stderr)
        return 1

    try:
        repo_path = resolve_programme_workspace(
            config_dir=config_dir, override=workspace
        ) / target
    except ClientRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not harness.delivery_contract:
        print(
            f"apply-gates  →  {governance.org}/{target}  [profile: {profile_name}]"
        )
        print("  [–] delivery_contract not declared  (legacy Prayog pin; gate apply skipped)")
        target_flag = "--meta" if meta else f"--repo {target}"
        print_next_box([f"launchpad status {target_flag}"])
        return 0

    prayog_root = repo_path / PRAYOG_SKILLS_SUBMODULE_REL
    if not prayog_root.is_dir():
        print(
            "ERROR: pinned Prayog checkout missing — run apply-harness first",
            file=sys.stderr,
        )
        return 1

    try:
        actual_contract = resolve_delivery_contract(prayog_root)
        if actual_contract != harness.delivery_contract:
            raise HarnessResolveError(
                f"delivery contract mismatch: harness expects "
                f"{harness.delivery_contract!r}, pinned Prayog provides "
                f"{actual_contract!r}"
            )
        labels, review_roles = resolve_gate_resources(prayog_root, profile_name)
    except HarnessResolveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"apply-gates  →  {governance.org}/{target}  [profile: {profile_name}]")
    print(f"  contract: {actual_contract}")

    errors = 0
    with GitHubForgeProvider(dry_run=not apply) as forge:
        for label in labels:
            forge.ensure_label(
                governance.org,
                target,
                label["name"],
                color=label["color"],
                description=label["description"],
            )

        known_teams = {team.name for team in governance.teams}
        for gate, role in review_roles.items():
            team = harness.delivery_roles.get(role, "")
            if not team:
                print(
                    f"  ✗  {gate}: no delivery_roles mapping for {role!r}",
                    file=sys.stderr,
                )
                errors += 1
                continue
            if team not in known_teams:
                print(
                    f"  ✗  {gate}: mapped team {team!r} not declared in governance",
                    file=sys.stderr,
                )
                errors += 1
                continue
            permission = forge.team_repo_permission(
                governance.org,
                target,
                team,
            )
            if permission is None:
                print(
                    f"  ✗  {gate}: team {team!r} has no access to {target}",
                    file=sys.stderr,
                )
                errors += 1
                continue
            print(f"  ✔  {gate}: {role} → {team}  (permission: {permission})")

    if not apply:
        target_flag = "--meta" if meta else f"--repo {target}"
        print_next_box([f"launchpad apply-gates {target_flag} --apply"])
    else:
        target_flag = "--meta" if meta else f"--repo {target}"
        print_next_box([f"launchpad status {target_flag}"])
    return 1 if errors else 0
