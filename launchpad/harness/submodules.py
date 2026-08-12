"""Git submodule helpers shared by apply-harness and status."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)


def run_git(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def local_head_sha(repo_dir: Path) -> str | None:
    """Return HEAD commit SHA, or None if unavailable."""
    if not repo_dir.is_dir():
        return None
    result = run_git(["git", "rev-parse", "HEAD"], cwd=repo_dir)
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def _parse_ls_remote_sha(stdout: str, ref: str) -> str | None:
    """Prefer peeled annotated-tag SHA (refs/tags/x^{}) over the tag object."""
    peeled: str | None = None
    direct: str | None = None
    suffixes = (
        f"refs/tags/{ref}",
        f"refs/heads/{ref}",
        ref,
    )
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        sha, name = parts[0], parts[1]
        for suffix in suffixes:
            if name == f"{suffix}^{{}}":
                peeled = sha
            elif name == suffix or name.endswith(f"/{ref}"):
                if name.endswith("^{}"):
                    peeled = sha
                else:
                    direct = sha
    return peeled or direct


def resolve_origin_tip_sha(repo_dir: Path, ref: str) -> str | None:
    """Return the commit SHA origin currently has for ``ref``, or None if unavailable.

    Origin is SSOT for tip tags and branches. Full/short SHA pins resolve to
    themselves when the object is known (or fetchable) locally after a probe.
    """
    if not repo_dir.is_dir():
        return None
    declared = (ref or "").strip()
    if not declared or declared.upper() == "HEAD":
        return None

    if _SHA_RE.match(declared):
        # Immutable SHA pin — SSOT is the declared commit itself.
        probe = run_git(["git", "rev-parse", "--verify", f"{declared}^{{commit}}"], cwd=repo_dir)
        if probe.returncode == 0:
            return probe.stdout.strip()
        fetch = run_git(["git", "fetch", "--depth", "1", "origin", declared], cwd=repo_dir)
        if fetch.returncode != 0:
            return None
        probe = run_git(["git", "rev-parse", "--verify", f"{declared}^{{commit}}"], cwd=repo_dir)
        return probe.stdout.strip() if probe.returncode == 0 else None

    for args in (
        ["git", "ls-remote", "origin", f"refs/tags/{declared}", f"refs/tags/{declared}^{{}}"],
        ["git", "ls-remote", "origin", f"refs/heads/{declared}"],
        ["git", "ls-remote", "origin", declared],
    ):
        result = run_git(args, cwd=repo_dir)
        if result.returncode != 0:
            continue
        sha = _parse_ls_remote_sha(result.stdout, declared)
        if sha:
            return sha
    return None


@dataclass(frozen=True)
class TipCompare:
    """Local HEAD vs origin tip for a declared pin ref."""

    local_sha: str | None
    origin_sha: str | None
    in_sync: bool
    unavailable: bool


def compare_local_to_origin(repo_dir: Path, ref: str) -> TipCompare:
    """Compare local HEAD to the origin tip for ``ref`` (read-only)."""
    local = local_head_sha(repo_dir)
    origin = resolve_origin_tip_sha(repo_dir, ref)
    if origin is None:
        return TipCompare(
            local_sha=local,
            origin_sha=None,
            in_sync=False,
            unavailable=True,
        )
    return TipCompare(
        local_sha=local,
        origin_sha=origin,
        in_sync=bool(local) and local == origin,
        unavailable=False,
    )


def _short(sha: str | None) -> str:
    if not sha:
        return "?"
    return sha[:7]


def _submodule_gitlink_in_index(repo_path: Path, submodule_rel: str) -> bool:
    result = run_git(["git", "ls-files", "-s", submodule_rel], cwd=repo_path)
    return result.returncode == 0 and result.stdout.strip().startswith("160000")


def _gitmodules_has_path(repo_path: Path, submodule_rel: str) -> bool:
    gitmodules = repo_path / ".gitmodules"
    if not gitmodules.is_file():
        return False
    return f"path = {submodule_rel}" in gitmodules.read_text(encoding="utf-8")


def _remove_broken_submodule(repo_path: Path, submodule_rel: str, *, label: str) -> None:
    """Drop a stale gitlink when .gitmodules or the checkout is missing."""
    print(f"  {label}: removing stale submodule gitlink for {submodule_rel} …")
    run_git(["git", "rm", "-rf", "--cached", submodule_rel], cwd=repo_path)
    dest = repo_path / submodule_rel
    if dest.exists() or dest.is_symlink():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest, ignore_errors=True)
        else:
            dest.unlink(missing_ok=True)
    module_dir = repo_path / ".git" / "modules" / submodule_rel
    if module_dir.is_dir():
        shutil.rmtree(module_dir, ignore_errors=True)


def pin_git_ref(repo_dir: Path, ref: str, *, label: str = "") -> bool:
    """Fetch origin tip for ``ref`` (SSOT) and force-checkout that commit."""
    if not repo_dir.is_dir():
        return False

    prefix = f"  {label}: " if label else "  "
    declared = (ref or "").strip() or "HEAD"
    print(f"{prefix}fetching {declared!r} …")

    local_before = local_head_sha(repo_dir)
    origin_sha = resolve_origin_tip_sha(repo_dir, declared)

    # Force-update local tag so retargeted tips replace stale local tag objects.
    fetch = run_git(
        ["git", "fetch", "origin", f"+refs/tags/{declared}:refs/tags/{declared}"],
        cwd=repo_dir,
    )
    checkout_target = f"refs/tags/{declared}"
    if fetch.returncode != 0:
        fetch = run_git(["git", "fetch", "origin", declared], cwd=repo_dir)
        checkout_target = "FETCH_HEAD"
    if fetch.returncode != 0:
        print(f"  WARN: fetch {declared!r} failed: {fetch.stderr.strip()}", file=sys.stderr)
        return False

    # After fetch, prefer the resolved origin tip; fall back to checkout target.
    if origin_sha is None:
        origin_sha = resolve_origin_tip_sha(repo_dir, declared)
    if origin_sha is None:
        resolved = run_git(["git", "rev-parse", "--verify", checkout_target], cwd=repo_dir)
        if resolved.returncode == 0:
            origin_sha = resolved.stdout.strip()

    if (
        local_before
        and origin_sha
        and local_before != origin_sha
    ):
        print(
            f"{prefix}tip moved: {_short(local_before)} → {_short(origin_sha)} "
            f"(ref {declared})"
        )

    target = origin_sha or checkout_target
    print(f"{prefix}checkout {declared!r} …")
    # Detach at the exact fetched commit. Checking out a same-named local branch
    # can silently leave mutable branch pins behind origin/<ref>.
    checkout = run_git(
        ["git", "checkout", "--detach", "-f", target],
        cwd=repo_dir,
    )
    if checkout.returncode != 0:
        print(f"  WARN: checkout {declared!r} failed: {checkout.stderr.strip()}", file=sys.stderr)
        return False
    return True


def pin_submodule(
    repo_path: Path,
    submodule_rel: str,
    url: str,
    ref: str,
    *,
    label: str = "",
) -> bool:
    """Ensure submodule exists at repo_path/submodule_rel and pin it to ref."""
    if not (repo_path / ".git").is_dir():
        print(f"  WARN: {repo_path} is not a git repo — cannot pin submodule", file=sys.stderr)
        return False

    tag = label or submodule_rel
    submodule_dest = repo_path / submodule_rel
    registered = _gitmodules_has_path(repo_path, submodule_rel)
    gitlink = _submodule_gitlink_in_index(repo_path, submodule_rel)

    if gitlink and not registered:
        _remove_broken_submodule(repo_path, submodule_rel, label=tag)
        gitlink = False

    if registered and not submodule_dest.is_dir():
        print(f"  {tag}: submodule registered — initializing {submodule_rel} …")
        init = run_git(["git", "submodule", "update", "--init", "--force", submodule_rel], cwd=repo_path)
        if init.returncode != 0:
            print(f"  WARN: submodule init failed: {init.stderr.strip()}", file=sys.stderr)
            _remove_broken_submodule(repo_path, submodule_rel, label=tag)
            registered = False

    if not registered and not gitlink:
        print(f"  {tag}: adding submodule {url} → {submodule_rel} …")
        result = run_git(
            ["git", "submodule", "add", "--force", url, submodule_rel],
            cwd=repo_path,
        )
        if result.returncode != 0:
            print(f"  WARN: submodule add failed: {result.stderr.strip()}", file=sys.stderr)
            return False
    else:
        print(f"  {tag}: submodule exists — pinning {ref!r} …")

    if not pin_git_ref(submodule_dest, ref, label=tag):
        return False

    run_git(["git", "add", submodule_rel], cwd=repo_path)
    return True
