"""reset-harness — clear local harness materialization before remount.

Default clears skill hub + runtime mirrors, ``.harness-pin.yaml``, and the
managed AGENTS harness block. Opt-in ``--include-seeded-workflows`` removes
allowlisted kit-seeded workflow files (including legacy board-seed-gate.yml).

Does not delete product code, the full ``.github`` tree, or submodule gitlinks.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from launchpad.clients import ClientRegistryError, resolve_programme_workspace
from launchpad.harness.paths import (
    DEFAULT_SKILL_RUNTIMES,
    HARNESS_PROFILE_REL,
    HARNESS_SKILLS_HUB_REL,
    PM_HARNESS_PROFILE,
)
from launchpad.schema import SchemaError
from launchpad.schema.governance import load_governance
from launchpad.schema.harness import load_harness
from launchpad.ui import print_next_box

_HARNESS_BLOCK_START = "<!-- launchpad:harness-start -->"
_HARNESS_BLOCK_END = "<!-- launchpad:harness-end -->"
_HARNESS_BLOCK_RE = re.compile(
    re.escape(_HARNESS_BLOCK_START) + r".*?" + re.escape(_HARNESS_BLOCK_END),
    re.DOTALL,
)

# Kit-seeded delivery workflows (+ legacy name for purge after retire).
_SEEDED_WORKFLOW_NAMES: tuple[str, ...] = (
    "ci.yml",
    "policy-branch-name.yml",
    "board-seed-gate.yml",
)


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def _remove_path(path: Path, *, apply: bool, label: str) -> bool:
    if not (path.exists() or path.is_symlink()):
        return False
    if not apply:
        print(f"    [dry-run] remove {label}: {path}")
        return True
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    print(f"  ✔  removed {label}: {path}")
    return True


def _clear_skill_trees(
    repo_path: Path,
    runtime_roots: list[str],
    *,
    apply: bool,
) -> None:
    hub = repo_path / HARNESS_SKILLS_HUB_REL
    _remove_path(hub, apply=apply, label="skill hub")
    for runtime in runtime_roots:
        root = repo_path / runtime
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.name.startswith("."):
                continue
            _remove_path(entry, apply=apply, label=f"runtime skill {runtime}/{entry.name}")


def _clear_agents_harness_block(repo_path: Path, *, apply: bool) -> None:
    agents = repo_path / "AGENTS.md"
    if not agents.is_file():
        return
    text = agents.read_text(encoding="utf-8")
    if not _HARNESS_BLOCK_RE.search(text):
        return
    if not apply:
        print(f"    [dry-run] strip AGENTS harness block: {agents}")
        return
    cleaned = _HARNESS_BLOCK_RE.sub("", text, count=1)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"
    agents.write_text(cleaned, encoding="utf-8")
    print(f"  ✔  stripped AGENTS harness block: {agents}")


def _clear_seeded_workflows(repo_path: Path, *, apply: bool) -> None:
    workflows = repo_path / ".github" / "workflows"
    for name in _SEEDED_WORKFLOW_NAMES:
        _remove_path(workflows / name, apply=apply, label=f"seeded workflow {name}")


def reset_harness_repo(
    repo_path: Path,
    *,
    runtime_roots: list[str],
    include_seeded_workflows: bool,
    apply: bool,
) -> None:
    """Clear remountable harness materialization in one repo."""
    _clear_skill_trees(repo_path, runtime_roots, apply=apply)
    _remove_path(repo_path / ".harness-pin.yaml", apply=apply, label="harness pin")
    _remove_path(repo_path / HARNESS_PROFILE_REL, apply=apply, label="harness profile")
    _clear_agents_harness_block(repo_path, apply=apply)
    if include_seeded_workflows:
        _clear_seeded_workflows(repo_path, apply=apply)


def run_reset_harness(
    *,
    meta: bool,
    repo_name: str,
    apply: bool,
    include_seeded_workflows: bool,
    config_dir: Path,
    workspace: str = "",
) -> int:
    cdir = config_dir
    harness_path = _find_config(cdir, "harness-*.yaml")
    if harness_path is None:
        print(f"ERROR: harness-<org>.yaml not found in {cdir}", file=sys.stderr)
        return 1

    gov_path = _find_config(cdir, "governance-*.yaml")
    if gov_path is None:
        print(f"ERROR: governance-<org>.yaml not found in {cdir}", file=sys.stderr)
        return 1

    try:
        h = load_harness(harness_path)
        gov = load_governance(gov_path)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    meta_repo = cdir.parent.name
    try:
        prog_path = cdir / "programme.yaml"
        if prog_path.is_file():
            from launchpad.schema.programme import load_programme

            prog = load_programme(prog_path)
            meta_repo = prog.meta_repo
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        ws = resolve_programme_workspace(config_dir=cdir, override=workspace)
    except ClientRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if meta:
        target = meta_repo
        stack = gov.repos[target].stack if target in gov.repos else PM_HARNESS_PROFILE
    else:
        target = repo_name
        if repo_name not in gov.repos:
            print(f"ERROR: repo '{repo_name}' not in governance yaml", file=sys.stderr)
            return 1
        stack = gov.repos[repo_name].stack

    profile_name = h.resolve_profile(target, stack)
    if profile_name is None or profile_name not in h.profiles:
        print(f"  No harness profile found for {target} (stack={stack}) — skipping.")
        return 0

    profile = h.profiles[profile_name]
    runtime_roots = list(profile.skill_runtimes) or list(DEFAULT_SKILL_RUNTIMES)
    repo_path = Path(ws).expanduser().resolve() / target

    mode = "apply" if apply else "dry-run"
    print(f"reset-harness  →  {h.org}/{target}  [profile: {profile_name}]  ({mode})")
    if include_seeded_workflows:
        print("  include: seeded workflows allowlist (ci, policy-branch-name, legacy board-seed-gate)")
    if not repo_path.is_dir():
        print(f"ERROR: local clone not found at {repo_path}", file=sys.stderr)
        return 1

    reset_harness_repo(
        repo_path,
        runtime_roots=runtime_roots,
        include_seeded_workflows=include_seeded_workflows,
        apply=apply,
    )

    target_flag = "--meta" if meta else f"--repo {target}"
    if not apply:
        print_next_box(
            [
                f"launchpad reset-harness {target_flag} --apply",
                f"launchpad apply-harness {target_flag} --apply",
            ]
        )
    else:
        print_next_box([f"launchpad apply-harness {target_flag} --apply"])
    return 0
