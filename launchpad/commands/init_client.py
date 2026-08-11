"""init-client — Day-1 setup for a programme (meta repo) or Day-N repo.

Pipeline (for --meta):
  1. Validate programme.yaml + governance-<org>.yaml
  2. Ensure GitHub team(s) declared for the meta repo
  3. Ensure the meta repo on GitHub
  4. Assign teams to repo
  5. Setup gitflow (default branch + integration branch + branch protection on both)
  6. Ensure project board + link repo
  7. Re-ensure clients.yaml entry from programme.yaml
  8. Local git setup: init + commit config + push, or clone if no local dir
  9. Print NEXT: block

Pipeline (for --repo <name>):
  1. Validate programme.yaml + governance-<org>.yaml
  2. Ensure GitHub team(s) declared for the repo
  3. Ensure the app repo on GitHub
  4. Assign teams to repo
  5. Setup gitflow
  6. Link repo to project board
  7. Clone repo locally (if not already cloned)
  8. Print NEXT: block

All steps are idempotent — re-run after a config fix with the same flags.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from launchpad.schema import SchemaError
from launchpad.schema.catalog import load_catalog
from launchpad.schema.governance import load_governance
from launchpad.schema.programme import load_programme
from launchpad.clients import (
    CLIENTS_FILE,
    CONFIG_DIR,
    resolve_programme_workspace,
)
from launchpad.ui import print_next_box


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def _load_all_schemas(config_dir: Path) -> tuple[Any, Any, Any]:
    prog_path = config_dir / "programme.yaml"
    if not prog_path.is_file():
        raise SchemaError(
            f"programme.yaml not found in {config_dir}",
            hint="Run 'launchpad onboard interview' first",
        )
    prog = load_programme(prog_path)

    gov_path = _find_config(config_dir, f"governance-*.yaml")
    if gov_path is None:
        raise SchemaError(
            f"governance-<org>.yaml not found in {config_dir}",
            hint="Run 'launchpad onboard interview' first",
        )
    gov = load_governance(gov_path)

    cat_path = _find_config(config_dir, f"service-catalog-*.yaml")
    if cat_path is None:
        raise SchemaError(
            f"service-catalog-<org>.yaml not found in {config_dir}",
            hint="Run 'launchpad onboard interview' first",
        )
    cat = load_catalog(cat_path)

    return prog, gov, cat


def _patch_clients_yaml(slug: str, meta_path: Path, *, workspace: Path | None = None) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CLIENTS_FILE.is_file():
        with CLIENTS_FILE.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    clients: list[dict[str, Any]] = data.get("clients") or []
    if not isinstance(clients, list):
        clients = []
    existing = next(
        (c for c in clients if isinstance(c, dict) and c.get("id") == slug),
        None,
    )
    ws = workspace if workspace is not None else meta_path.parent
    if existing and str(existing.get("workspace") or "").strip():
        # Preserve an explicit local workspace if the operator already set one
        ws_value = str(existing["workspace"]).strip()
    else:
        ws_value = str(ws)
    entry = {
        "id": slug,
        "path": str(meta_path),
        "workspace": ws_value,
        "forge": "github",
    }
    clients = [c for c in clients if not (isinstance(c, dict) and c.get("id") == slug)]
    clients.append(entry)
    data["clients"] = clients
    with CLIENTS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


def _setup_local_repo(
    repo_path: Path,
    org: str,
    repo_name: str,
    default_branch: str,
    integration_branch: str,
    *,
    dry_run: bool,
) -> None:
    """Ensure repo_path is a local git clone of org/repo_name.

    Three cases:
      A) repo_path already has .git/  → nothing to do (idempotent)
      B) repo_path is a plain dir     → git init, commit, set remote, push
      C) repo_path does not exist     → git clone from GitHub
    """
    remote_url = f"https://github.com/{org}/{repo_name}.git"

    if (repo_path / ".git").is_dir():
        print(f"  ✔  local repo already exists: {repo_path}")
        return

    if dry_run:
        if repo_path.is_dir():
            print(f"  [dry-run] git init + push config → {remote_url}")
        else:
            print(f"  [dry-run] git clone {remote_url} → {repo_path}")
        return

    def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

    if repo_path.is_dir():
        # Case B: plain dir from onboard interview — init + push config files
        print(f"  Initialising git in existing directory: {repo_path}")
        _run(["git", "init", "-b", default_branch], repo_path)
        _run(["git", "remote", "add", "origin", remote_url], repo_path)

        # Stage everything (config/ files written by interview)
        _run(["git", "add", "."], repo_path)

        # Only commit if there is something staged
        staged = _run(["git", "diff", "--cached", "--name-only"], repo_path)
        if staged.stdout.strip():
            _run(
                ["git", "commit", "-m", "chore: initial config from launchpad onboard interview"],
                repo_path,
            )
            result = _run(["git", "push", "-u", "origin", default_branch], repo_path)
            if result.returncode != 0:
                print(f"  WARN: git push failed: {result.stderr.strip()}")
                print(f"  Push manually: cd {repo_path} && git push -u origin {default_branch}")
            else:
                print(f"  ✔  committed config/ and pushed to {remote_url}")
                if integration_branch != default_branch:
                    _run(["git", "fetch", "origin"], repo_path)
                    co = _run(["git", "checkout", "-B", integration_branch, f"origin/{integration_branch}"], repo_path)
                    if co.returncode == 0:
                        print(f"  ✔  checked out {integration_branch}")
                    else:
                        local = _run(["git", "branch", integration_branch], repo_path)
                        push = _run(["git", "push", "-u", "origin", integration_branch], repo_path)
                        if push.returncode == 0:
                            _run(["git", "checkout", integration_branch], repo_path)
                            print(f"  ✔  pushed and checked out {integration_branch}")
                        elif local.returncode != 0:
                            print(f"  WARN: could not set up {integration_branch}: {co.stderr.strip()}")
        else:
            print(f"  ✔  git init done (nothing to commit yet)")
    else:
        # Case C: directory does not exist — clone the (empty) repo from GitHub
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  Cloning {remote_url} → {repo_path} …")
        result = subprocess.run(
            ["git", "clone", remote_url, str(repo_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  WARN: git clone failed: {result.stderr.strip()}")
            print(f"  Clone manually: git clone {remote_url} {repo_path}")
        else:
            print(f"  ✔  cloned {remote_url} → {repo_path}")
            if integration_branch != default_branch:
                _run(["git", "fetch", "origin"], repo_path)
                co = _run(["git", "checkout", integration_branch], repo_path)
                if co.returncode == 0:
                    print(f"  ✔  checked out {integration_branch}")
                else:
                    print(
                        f"  WARN: remote branch {integration_branch!r} not found locally — "
                        f"re-run init-client --apply to create it on GitHub",
                        file=sys.stderr,
                    )


def run_init_client(
    *,
    meta: bool = False,
    repo_name: str = "",
    apply: bool = False,
    dry_run: bool = True,
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

    try:
        prog, gov, cat = _load_all_schemas(cdir)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    org = prog.org
    slug = prog.programme_slug
    dr = dry_run or not apply
    ws = resolve_programme_workspace(client_id=client_id, config_dir=cdir)

    from launchpad.forge.providers.github import GitHubForgeProvider

    targets: list[str] = []
    if meta:
        targets = [prog.meta_repo]
    else:
        if repo_name not in gov.repos:
            print(f"ERROR: repo '{repo_name}' is not declared in governance-{org}.yaml", file=sys.stderr)
            print(f"  Known repos: {sorted(gov.repos)}", file=sys.stderr)
            return 1
        targets = [repo_name]

    policy = gov.policy
    required_approvals = int(policy.get("require_pr_reviews", 1))
    dismiss_stale = bool(policy.get("dismiss_stale_reviews", True))
    default_branch = str(policy.get("default_branch", "main"))
    integration_branch = str(policy.get("integration_branch", "develop"))

    with GitHubForgeProvider(dry_run=dr) as forge:
        # Ensure project board (for all targets, use a shared board)
        board_id = ""
        if gov.project_board.get("enabled"):
            board_name = str(gov.project_board.get("name", f"{org} Board"))
            if not dr:
                print(f"  Ensuring project board: {board_name}")
            board_id = forge.ensure_project_board(org, board_name)

        for target_repo in targets:
            repo_cfg = gov.repos.get(target_repo)
            if repo_cfg is None:
                print(f"  WARN: {target_repo} not in governance — skipping", file=sys.stderr)
                continue

            print(f"\ninit-client  →  {org}/{target_repo}")

            # 1. Teams
            for team_name in repo_cfg.teams:
                team_entry = next((t for t in gov.teams if t.name == team_name), None)
                desc = team_entry.description if team_entry else ""
                privacy = team_entry.privacy if team_entry else "closed"
                forge.ensure_team(org, team_name, description=desc, privacy=privacy)

            # 2. Repo
            forge.ensure_repo(
                org,
                target_repo,
                description=repo_cfg.description,
                visibility=repo_cfg.visibility,
            )

            # 3. Assign teams
            for team_name in repo_cfg.teams:
                forge.add_team_to_repo(org, target_repo, team_name)

            # 4. Gitflow — default branch, integration branch, protection on both
            forge.ensure_default_branch(org, target_repo, default_branch)
            if integration_branch != default_branch:
                forge.ensure_branch(
                    org,
                    target_repo,
                    integration_branch,
                    from_branch=default_branch,
                )
            forge.ensure_branch_protection(
                org,
                target_repo,
                default_branch,
                required_approvals=required_approvals,
                dismiss_stale=dismiss_stale,
            )
            if integration_branch != default_branch:
                forge.ensure_branch_protection(
                    org,
                    target_repo,
                    integration_branch,
                    required_approvals=required_approvals,
                    dismiss_stale=dismiss_stale,
                )

            # 5. Link to board
            if board_id:
                forge.link_repo_to_project(org, target_repo, board_id)

    # 6. Re-ensure clients.yaml + local git setup (meta only)
    if meta:
        meta_path = ws / prog.meta_repo
        _patch_clients_yaml(slug, meta_path, workspace=ws)
        if dr:
            print(f"  [dry-run] ensure clients.yaml entry: id={slug}")
        else:
            print(f"  ✔  ~/.config/launchpad/clients.yaml  (id={slug})")

        # Step 8: local git clone / init
        _setup_local_repo(
            meta_path,
            org,
            prog.meta_repo,
            default_branch,
            integration_branch,
            dry_run=dr,
        )
    else:
        # For app repos: clone locally if the workspace directory doesn't exist
        repo_path = ws / repo_name
        _setup_local_repo(
            repo_path,
            org,
            repo_name,
            default_branch,
            integration_branch,
            dry_run=dr,
        )

    # NEXT step
    if meta:
        sca_path = _find_config(cdir, "scaffold-*.yaml")
        scaffold_enabled = False
        if sca_path and sca_path.is_file():
            try:
                from launchpad.schema.scaffold import load_scaffold
                sca = load_scaffold(sca_path)
                scaffold_enabled = sca.meta is not None and sca.meta.enabled
            except SchemaError:
                pass

        if scaffold_enabled:
            print_next_box(["launchpad apply-scaffold --meta --apply"])
        else:
            print_next_box([
                "Option A — skip scaffold (no foundation template):",
                "launchpad apply-harness --meta --apply",
                "",
                "Option B — scaffold from a cookiecutter template first:",
                f"Edit config/scaffold-{org}.yaml",
                "Set meta.enabled: true, template, ref, context",
                "launchpad apply-scaffold --meta --apply",
            ])
    else:
        print_next_box([f"launchpad apply-scaffold --repo {repo_name} --apply --force"])

    return 0
