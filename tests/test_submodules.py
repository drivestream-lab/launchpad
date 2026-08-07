from __future__ import annotations

import subprocess
from pathlib import Path

from launchpad.harness.submodules import compare_local_to_origin, pin_git_ref


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_identity(repo: Path) -> None:
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")


def test_pin_git_ref_advances_mutable_remote_branch(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    checkout = tmp_path / "checkout"

    _git(tmp_path, "init", "--bare", str(remote))
    source.mkdir()
    _git(source, "init")
    _init_identity(source)
    _git(source, "switch", "-c", "pilot")
    (source / "value.txt").write_text("one\n", encoding="utf-8")
    _git(source, "add", "value.txt")
    _git(source, "commit", "-m", "one")
    _git(source, "remote", "add", "origin", str(remote))
    _git(source, "push", "-u", "origin", "pilot")
    first = _git(source, "rev-parse", "HEAD")

    _git(tmp_path, "clone", str(remote), str(checkout))
    assert pin_git_ref(checkout, "pilot")
    assert _git(checkout, "rev-parse", "HEAD") == first

    (source / "value.txt").write_text("two\n", encoding="utf-8")
    _git(source, "add", "value.txt")
    _git(source, "commit", "-m", "two")
    _git(source, "push")
    second = _git(source, "rev-parse", "HEAD")

    assert pin_git_ref(checkout, "pilot")
    assert _git(checkout, "rev-parse", "HEAD") == second
    assert _git(checkout, "branch", "--show-current") == ""


def test_pin_git_ref_advances_retargeted_tag(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    checkout = tmp_path / "checkout"

    _git(tmp_path, "init", "--bare", str(remote))
    source.mkdir()
    _git(source, "init")
    _init_identity(source)
    _git(source, "switch", "-c", "main")
    (source / "value.txt").write_text("one\n", encoding="utf-8")
    _git(source, "add", "value.txt")
    _git(source, "commit", "-m", "one")
    _git(source, "tag", "v0.x.y-rc1")
    _git(source, "remote", "add", "origin", str(remote))
    _git(source, "push", "-u", "origin", "main")
    _git(source, "push", "origin", "v0.x.y-rc1")
    first = _git(source, "rev-parse", "HEAD")

    _git(tmp_path, "clone", str(remote), str(checkout))
    assert pin_git_ref(checkout, "v0.x.y-rc1")
    assert _git(checkout, "rev-parse", "HEAD") == first

    (source / "value.txt").write_text("two\n", encoding="utf-8")
    _git(source, "add", "value.txt")
    _git(source, "commit", "-m", "two")
    _git(source, "tag", "-f", "v0.x.y-rc1")
    _git(source, "push", "--force", "origin", "v0.x.y-rc1")
    second = _git(source, "rev-parse", "HEAD")

    # Stale local tag still points at first until apply force-fetches.
    assert _git(checkout, "rev-parse", "v0.x.y-rc1") == first
    tip = compare_local_to_origin(checkout, "v0.x.y-rc1")
    assert tip.unavailable is False
    assert tip.in_sync is False
    assert tip.origin_sha == second

    assert pin_git_ref(checkout, "v0.x.y-rc1")
    assert _git(checkout, "rev-parse", "HEAD") == second
    assert _git(checkout, "rev-parse", "v0.x.y-rc1") == second

    tip_after = compare_local_to_origin(checkout, "v0.x.y-rc1")
    assert tip_after.in_sync is True
