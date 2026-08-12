"""Materialize harness skill hub and mirror symlinks into agent runtime roots."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path

from launchpad.harness.paths import (
    HARNESS_SKILLS_HUB_REL,
    PRAYOG_SKILLS_SUBMODULE_REL,
)
from launchpad.harness.skills_resolve import find_skill_source_dir, skill_list_key

_PRAYOG_SUBMODULE_NAME = "prayog-skills"
_PRAYOG_REFERENCES_REL = "references"


def _file_hash(path: Path) -> str:
    """Return SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_prayog_references(
    repo: Path,
    submodule_root: Path,
    *,
    apply: bool,
) -> bool:
    """Copy prayog-skills/references/ to project-root/references/.

    SKILL.md files deployed through .harness/skills/ use
    ``../../../references/`` which resolves to the project root.
    The source (prayog-skills/) has ``references/`` at its own root,
    but that path is unreachable once deployed under .harness/skills/.
    Copying the shared references to the project root bridges the gap.

    Uses content-hash comparison: always replaces when any file differs,
    so retagged updates with identical filenames are never silently skipped.
    """
    src = submodule_root / _PRAYOG_REFERENCES_REL
    dest = repo / _PRAYOG_REFERENCES_REL

    if not src.is_dir():
        print(
            f"  -  prayog-skills has no references/ — skipping (safe)",
            file=sys.stderr,
        )
        return False

    if not apply:
        if dest.is_dir():
            # dry-run: check whether content differs
            needs_update = _references_content_differs(src, dest)
            if needs_update:
                print(f"    [dry-run] references  ← prayog-skills/references/  (content differs)")
            else:
                print(f"    [dry-run] references  (up to date)")
        else:
            print(f"    [dry-run] references  ← prayog-skills/references/")
        return True

    # Always replace: remove stale, copy fresh
    if dest.is_dir():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    print(f"  ✔  references  ← prayog-skills/references/")
    return True


def _references_content_differs(src: Path, dest: Path) -> bool:
    """Return True when source and dest file sets or contents differ."""
    source_files = {f.name: _file_hash(f) for f in src.iterdir() if f.is_file()}
    if not source_files:
        return False
    dest_files = {f.name: _file_hash(f) for f in dest.iterdir() if f.is_file()}
    if set(source_files) != set(dest_files):
        return True
    return any(source_files[name] != dest_files[name] for name in source_files)



def _remove_skill_entry(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def _symlink(rel_target: str, dest: Path) -> None:
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            try:
                if dest.resolve() == (dest.parent / rel_target).resolve():
                    return
            except OSError:
                pass
        _remove_skill_entry(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(rel_target)


def materialize_skill_tree(
    repo_path: Path,
    *,
    prayog_submodule_rel: str,
    skill_names: list[str],
    runtime_roots: list[str],
    lane_key: str,
    community_submodule_dirs: list[str],
    apply: bool,
) -> list[str]:
    """Create .harness/skills/<name> hub symlinks and mirror into runtime roots."""
    repo = repo_path.resolve()
    submodule_root = repo / prayog_submodule_rel
    hub_root = repo / HARNESS_SKILLS_HUB_REL
    materialized: list[str] = []

    if not submodule_root.is_dir():
        print(
            f"  WARN: prayog submodule missing at {prayog_submodule_rel} — cannot materialize skills",
            file=sys.stderr,
        )
        return materialized

    # prayog-skills at root has no nested submodule_root path
    if prayog_submodule_rel.endswith("/prayog-skills"):
        submodule_root = repo

    # Copy shared references to project root so ../../../references/ resolves
    # from both source (prayog-skills/skills/) and deployed (.harness/skills/)
    _copy_prayog_references(repo, submodule_root, apply=apply)

    if not apply:
        for name in skill_names:
            src = find_skill_source_dir(submodule_root, name, lane_key=lane_key)
            if src is None:
                print(f"    [dry-run] hub skill: {HARNESS_SKILLS_HUB_REL}/{name}  (source not found)")
                continue
            rel = os.path.relpath(src, hub_root / name)
            print(f"    [dry-run] hub skill: {HARNESS_SKILLS_HUB_REL}/{name}  →  {rel}")
            for runtime in runtime_roots:
                print(
                    f"    [dry-run] runtime skill: {runtime}/{name}  "
                    f"→  {os.path.relpath(hub_root / name, repo / runtime / name)}"
                )
            materialized.append(name)
        _remove_full_pack_runtime_links(repo, runtime_roots, apply=False)
        _print_stale_cleanup(repo, hub_root, runtime_roots, skill_names, community_submodule_dirs, apply=False)
        return materialized

    hub_root.mkdir(parents=True, exist_ok=True)

    for name in skill_names:
        src = find_skill_source_dir(submodule_root, name, lane_key=lane_key)
        if src is None:
            print(f"  ✗  hub skill: {name} not found in {prayog_submodule_rel} "
                  f"(searched skills/{{requirements|development|forge}}/{name}/)",
                  file=sys.stderr)
            continue

        hub_dest = hub_root / name
        hub_rel = os.path.relpath(src, hub_dest.parent)
        _symlink(hub_rel, hub_dest)

        for runtime in runtime_roots:
            runtime_dest = repo / runtime / name
            runtime_rel = os.path.relpath(hub_dest, runtime_dest.parent)
            _symlink(runtime_rel, runtime_dest)

        materialized.append(name)
        print(f"  ✔  hub skill: {HARNESS_SKILLS_HUB_REL}/{name}")
        for runtime in runtime_roots:
            print(f"  ✔  runtime skill: {runtime}/{name}")

    # Never expose the full prayog-skills pack under agent skill roots — only
    # profile-listed skill names (from profiles/*.yaml) are linked above.
    _remove_full_pack_runtime_links(repo, runtime_roots, apply=True)

    _cleanup_stale(
        repo,
        hub_root,
        runtime_roots,
        keep_names=set(skill_names),
        community_submodule_dirs=community_submodule_dirs,
    )
    return materialized


def _remove_full_pack_runtime_links(
    repo: Path,
    runtime_roots: list[str],
    *,
    apply: bool,
) -> None:
    """Drop leftover ``<runtime>/prayog-skills`` so agents cannot discover the full pack."""
    for runtime in runtime_roots:
        pack_link = repo / runtime / _PRAYOG_SUBMODULE_NAME
        if not (pack_link.exists() or pack_link.is_symlink()):
            continue
        if not apply:
            print(f"    [dry-run] remove full-pack runtime link: {runtime}/{_PRAYOG_SUBMODULE_NAME}")
            continue
        _remove_skill_entry(pack_link)
        print(f"  ✔  removed full-pack runtime link: {runtime}/{_PRAYOG_SUBMODULE_NAME}")


def materialize_community_skill_tree(
    repo_path: Path,
    *,
    community_submodule_rel: str,
    skill_name: str,
    runtime_roots: list[str],
    apply: bool,
) -> bool:
    """Hub + runtime symlinks for a community skill under .harness/community/."""
    repo = repo_path.resolve()
    hub_root = repo / HARNESS_SKILLS_HUB_REL
    src = repo / community_submodule_rel / "skills" / skill_name
    hub_dest = hub_root / skill_name
    hub_rel = os.path.relpath(src, hub_dest.parent)

    if not apply:
        if not src.is_dir():
            print(
                f"    [dry-run] community hub: {HARNESS_SKILLS_HUB_REL}/{skill_name}  "
                f"(source not found in {community_submodule_rel})"
            )
            return False
        print(f"    [dry-run] community hub: {HARNESS_SKILLS_HUB_REL}/{skill_name}  →  {hub_rel}")
        for runtime in runtime_roots:
            print(
                f"    [dry-run] community runtime: {runtime}/{skill_name}  "
                f"→  {os.path.relpath(hub_dest, repo / runtime / skill_name)}"
            )
        return True

    if not src.is_dir():
        print(
            f"  ✗  community skill {skill_name} not found in {community_submodule_rel}",
            file=sys.stderr,
        )
        return False

    hub_root.mkdir(parents=True, exist_ok=True)
    _symlink(hub_rel, hub_dest)
    for runtime in runtime_roots:
        runtime_dest = repo / runtime / skill_name
        runtime_rel = os.path.relpath(hub_dest, runtime_dest.parent)
        _symlink(runtime_rel, runtime_dest)

    print(f"  ✔  community hub: {HARNESS_SKILLS_HUB_REL}/{skill_name}")
    for runtime in runtime_roots:
        print(f"  ✔  community runtime: {runtime}/{skill_name}")
    return True


def hub_skill_present(repo_path: Path, skill_name: str) -> bool:
    return (repo_path / HARNESS_SKILLS_HUB_REL / skill_name / "SKILL.md").is_file()


def runtime_skill_present(repo_path: Path, skill_name: str, runtime_root: str) -> bool:
    return (repo_path / runtime_root / skill_name / "SKILL.md").is_file()


def all_runtime_skills_present(
    repo_path: Path,
    skill_names: list[str],
    runtime_roots: list[str],
) -> bool:
    return all(
        runtime_skill_present(repo_path, name, runtime) for name in skill_names for runtime in runtime_roots
    )


def _print_stale_cleanup(
    repo: Path,
    hub_root: Path,
    runtime_roots: list[str],
    keep_names: list[str],
    community_submodule_dirs: list[str],
    *,
    apply: bool,
) -> None:
    for name in _stale_hub_skills(hub_root, keep_names):
        prefix = "    [dry-run] remove stale hub skill:" if not apply else "  ✔  removed stale hub skill:"
        print(f"{prefix} {HARNESS_SKILLS_HUB_REL}/{name}")
    for runtime in runtime_roots:
        runtime_root = repo / runtime
        for name in _stale_runtime_skills(runtime_root, keep_names):
            prefix = "    [dry-run] remove stale runtime skill:" if not apply else "  ✔  removed stale runtime skill:"
            print(f"{prefix} {runtime}/{name}")


def _cleanup_stale(
    repo: Path,
    hub_root: Path,
    runtime_roots: list[str],
    *,
    keep_names: set[str],
    community_submodule_dirs: list[str],
) -> None:
    for name in _stale_hub_skills(hub_root, sorted(keep_names)):
        _remove_skill_entry(hub_root / name)
        print(f"  ✔  removed stale hub skill: {HARNESS_SKILLS_HUB_REL}/{name}")

    for runtime in runtime_roots:
        runtime_root = repo / runtime
        for name in _stale_runtime_skills(runtime_root, sorted(keep_names)):
            _remove_skill_entry(runtime_root / name)
            print(f"  ✔  removed stale runtime skill: {runtime}/{name}")


def _stale_hub_skills(hub_root: Path, keep_names: list[str]) -> list[str]:
    if not hub_root.is_dir():
        return []
    keep = set(keep_names)
    stale: list[str] = []
    for entry in hub_root.iterdir():
        if entry.name in keep or entry.name.startswith("."):
            continue
        stale.append(entry.name)
    return sorted(stale)


def _stale_runtime_skills(runtime_root: Path, keep_names: list[str]) -> list[str]:
    if not runtime_root.is_dir():
        return []
    keep = set(keep_names)
    stale: list[str] = []
    for entry in runtime_root.iterdir():
        if entry.name in keep or entry.name.startswith("."):
            continue
        stale.append(entry.name)
    return sorted(stale)


def lane_key_for_profile(harness_profile_name: str) -> str:
    return skill_list_key(harness_profile_name)
