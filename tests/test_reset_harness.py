"""Tests for reset-harness local materialization cleanup."""

from __future__ import annotations

from pathlib import Path

from launchpad.commands.apply_harness import _HARNESS_BLOCK_END, _HARNESS_BLOCK_START
from launchpad.commands.reset_harness import reset_harness_repo
from launchpad.harness.paths import HARNESS_PROFILE_REL, HARNESS_SKILLS_HUB_REL


def test_reset_harness_clears_default_surfaces(tmp_path: Path) -> None:
    hub = tmp_path / HARNESS_SKILLS_HUB_REL / "pre-implement"
    hub.mkdir(parents=True)
    (hub / "SKILL.md").write_text("# pre-implement", encoding="utf-8")
    runtime = tmp_path / ".agents" / "skills" / "pre-implement"
    runtime.mkdir(parents=True)
    (runtime / "SKILL.md").write_text("# pre-implement", encoding="utf-8")
    (tmp_path / ".harness-pin.yaml").write_text("profile: python-backend\n", encoding="utf-8")
    profile = tmp_path / HARNESS_PROFILE_REL
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text("profile: python-backend\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "# Guide\n\n"
        f"{_HARNESS_BLOCK_START}\n## Harness\n{_HARNESS_BLOCK_END}\n\n"
        "## Product\n\nStay.\n",
        encoding="utf-8",
    )
    legacy = tmp_path / ".github" / "workflows" / "board-seed-gate.yml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("name: board-seed-gate\n", encoding="utf-8")
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    ci.write_text("name: ci\n", encoding="utf-8")

    reset_harness_repo(
        tmp_path,
        runtime_roots=[".agents/skills"],
        include_seeded_workflows=False,
        apply=True,
    )

    assert not (tmp_path / HARNESS_SKILLS_HUB_REL).exists()
    assert not runtime.exists()
    assert not (tmp_path / ".harness-pin.yaml").exists()
    assert not profile.exists()
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert _HARNESS_BLOCK_START not in agents
    assert "## Product" in agents
    assert legacy.is_file()  # workflows untouched without flag
    assert ci.is_file()


def test_reset_harness_include_seeded_workflows(tmp_path: Path) -> None:
    legacy = tmp_path / ".github" / "workflows" / "board-seed-gate.yml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("name: board-seed-gate\n", encoding="utf-8")
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    ci.write_text("name: ci\n", encoding="utf-8")
    other = tmp_path / ".github" / "workflows" / "custom.yml"
    other.write_text("name: custom\n", encoding="utf-8")

    reset_harness_repo(
        tmp_path,
        runtime_roots=[],
        include_seeded_workflows=True,
        apply=True,
    )

    assert not legacy.exists()
    assert not ci.exists()
    assert other.is_file()
