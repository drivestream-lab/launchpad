"""Tests for delivery workflow seeding during apply-harness."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
import yaml

from launchpad.commands.apply_harness import (
    _DELIVERY_WORKFLOW_TEMPLATES,
    _seed_delivery_workflows,
)
from launchpad.harness.paths import PM_HARNESS_PROFILE


def test_seed_delivery_workflows_creates_files(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    workflows = tmp_path / ".github" / "workflows"
    for kit_rel in _DELIVERY_WORKFLOW_TEMPLATES:
        assert (workflows / kit_rel.split("/")[-1]).is_file()

    # BaseLoader preserves the YAML key "on" as a string.
    ci = yaml.load((workflows / "ci.yml").read_text(), Loader=yaml.BaseLoader)
    assert ci["on"] == {"pull_request": {"branches": ["main"]}}
    policy = yaml.load(
        (workflows / "policy-branch-name.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert policy["on"] == {"pull_request": {"branches": ["develop"]}}
    assert not (workflows / "board-seed-gate.yml").exists()


def test_seed_delivery_workflows_skips_meta_pm(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name=PM_HARNESS_PROFILE,
        apply=True,
    )
    assert not (tmp_path / ".github").exists()
    assert not (tmp_path / ".pre-commit-config.yaml").exists()


def test_seed_delivery_workflows_skips_without_contract(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="",
        profile_name="python-backend",
        apply=True,
    )
    assert not (tmp_path / ".github").exists()
    assert not (tmp_path / ".pre-commit-config.yaml").exists()


def test_seed_delivery_workflows_idempotent(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    workflows = tmp_path / ".github" / "workflows"
    first_ci = "# Team CI\n"
    (workflows / "ci.yml").write_text(first_ci)
    hook_config = tmp_path / ".pre-commit-config.yaml"
    hook_config.write_text("# Team hooks\n")
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    assert (workflows / "ci.yml").read_text(encoding="utf-8") == first_ci
    assert hook_config.read_text() == "# Team hooks\n"


def test_seed_delivery_dry_run(tmp_path, capsys) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=False,
    )
    assert list(tmp_path.iterdir()) == []
    assert ".pre-commit-config.yaml" in capsys.readouterr().out


def test_ci_uses_local_checks(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    config = yaml.safe_load((tmp_path / ".pre-commit-config.yaml").read_text())
    assert config["default_install_hook_types"] == ["pre-commit"]
    assert config["default_stages"] == ["pre-commit"]
    hooks = config["repos"][0]["hooks"]
    assert [hook["entry"] for hook in hooks] == [
        "make format-check",
        "make lint",
        "make test",
        "make build",
        "make docker-build",
    ]
    assert all(hook["always_run"] and not hook["pass_filenames"] for hook in hooks)
    assert all(hook["language"] == "system" for hook in hooks)
    ci = yaml.load(
        (tmp_path / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert ci["jobs"]["ci"]["steps"][-1]["run"] == "pre-commit run --all-files"


@pytest.mark.parametrize(
    "failed_target", ["", "format-check", "lint", "test", "build", "docker-build"]
)
def test_commit_runs_all_checks(tmp_path, failed_target) -> None:
    pytest.importorskip("pre_commit")
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    targets = ["format-check", "lint", "test", "build", "docker-build"]
    (tmp_path / "Makefile").write_text(
        ".PHONY: "
        + " ".join(targets)
        + "\n"
        + " ".join(targets)
        + ":\n\t@echo $@ >> .git/checks.log\n"
        + '\t@test "$$FAIL_TARGET" != "$@"\n'
    )
    env = {
        **os.environ,
        "FAIL_TARGET": failed_target,
        "PRE_COMMIT_HOME": str(tmp_path / ".cache"),
    }

    def run(*args):
        return subprocess.run(
            args, cwd=tmp_path, env=env, capture_output=True, text=True, check=False
        )

    assert run("git", "init").returncode == 0
    assert run("git", "config", "user.name", "Test").returncode == 0
    assert run("git", "config", "user.email", "test@example.com").returncode == 0
    assert run("git", "add", ".").returncode == 0
    assert run(sys.executable, "-m", "pre_commit", "install").returncode == 0
    result = run("git", "commit", "-m", "test: verify hooks")
    assert (result.returncode != 0) == bool(failed_target), (
        result.stdout + result.stderr
    )
    checked = (tmp_path / ".git/checks.log").read_text().splitlines()
    assert checked == targets
    if not failed_target:
        result = run("git", "commit", "--allow-empty", "-m", "test: empty commit")
        assert result.returncode == 0, result.stdout + result.stderr
        assert (tmp_path / ".git/checks.log").read_text().splitlines() == targets * 2

        (tmp_path / "Makefile").unlink()
        assert run("git", "add", "Makefile").returncode == 0
        result = run("git", "commit", "-m", "test: missing checks")
        assert result.returncode != 0
        assert "No rule to make target" in result.stdout + result.stderr


def test_seeded_ci_yml_is_pr_only_no_feature_push(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    ci = (tmp_path / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pull_request:" in ci
    assert "\n  ci:\n" in ci or "\n  ci:\r\n" in ci
    assert "feature/**" not in ci
    assert "branches: [develop, main, 'feature/**']" not in ci
    assert 'branches: [develop, main, "feature/**"]' not in ci
    # Tip push may appear only as a commented example, not as an active trigger.
    active_push = [
        line
        for line in ci.splitlines()
        if line.strip().startswith("push:") and not line.lstrip().startswith("#")
    ]
    assert active_push == []
