"""Tests for delivery workflow seeding during apply-harness."""

from __future__ import annotations

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


def test_seed_delivery_workflows_skips_meta_pm(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name=PM_HARNESS_PROFILE,
        apply=True,
    )
    assert not (tmp_path / ".github").exists()


def test_seed_delivery_workflows_skips_without_contract(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="",
        profile_name="python-backend",
        apply=True,
    )
    assert not (tmp_path / ".github").exists()


def test_seed_delivery_workflows_idempotent(tmp_path) -> None:
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    workflows = tmp_path / ".github" / "workflows"
    first_ci = (workflows / "ci.yml").read_text(encoding="utf-8")
    _seed_delivery_workflows(
        tmp_path,
        delivery_contract="sdd-delivery/v2",
        profile_name="python-backend",
        apply=True,
    )
    assert (workflows / "ci.yml").read_text(encoding="utf-8") == first_ci


def test_seeded_ci_yml_is_pr_only_no_feature_push(tmp_path) -> None:
    """Minutes-safe default: PR gate only; no feature/** push double-runs."""
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
