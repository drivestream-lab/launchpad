"""Tests for AGENTS.md seeding and prayog-root migration."""

from __future__ import annotations

from launchpad.commands.apply_harness import _migrate_agents_md_content, _seed_agents_md
from launchpad.schema.harness import HarnessProfile


def _profile(name: str, *, rules_ref: str = "v0.5.10") -> HarnessProfile:
    raw: dict = {"skills": [{"repo": "prayog-skills", "ref": "v0.4.3"}]}
    if name != "meta-pm":
        raw["constitution"] = {"repo": "python-services-rules", "ref": rules_ref}
    return HarnessProfile(name, raw)


def test_seed_agents_creates_initial_meta_guide(tmp_path) -> None:
    _seed_agents_md(
        tmp_path,
        "meta-pm",
        _profile("meta-pm"),
        ["validate-requirements", "prd-impact-map"],
        "sdd-delivery/v2",
        target="example-meta",
        org="example-org",
        meta_repo="example-meta",
        board_name="",
        board_url="",
        apply=True,
    )

    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "sdd-delivery/v2" in text
    assert "prayog-skills/workflow.yaml" in text
    assert ".agents/skills/prayog-skills/" not in text
    assert "what next?" in text


def test_seed_agents_preserves_team_file_without_stale_paths(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    original = "# Team guide\n\nDo not replace this repository-specific context.\n"
    agents.write_text(original, encoding="utf-8")

    _seed_agents_md(
        tmp_path,
        "python-backend",
        _profile("python-backend"),
        ["spec-draft"],
        "sdd-delivery/v2",
        target="example-api",
        org="example-org",
        meta_repo="example-meta",
        board_name="",
        board_url="",
        apply=True,
    )

    assert agents.read_text(encoding="utf-8") == original


def test_seed_agents_migrates_stale_prayog_paths(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# Agent guide (example-api)\n\n"
        "## Constitution (how to code)\n\n"
        "Shared rules: **`.cursor/rules/*.mdc`** (git submodule, pinned at **v0.5.8**).\n\n"
        "Agent skills: **`.agents/skills/prayog-skills/`** (git submodule, pinned at **v0.4.2**) — "
        "`/spec-draft`, `/verify`.\n\n"
        "Team note: keep this.\n",
        encoding="utf-8",
    )

    _seed_agents_md(
        tmp_path,
        "python-backend",
        _profile("python-backend"),
        [
            "spec-draft",
            "initiative-feasibility",
            "board-seed",
            "verify",
        ],
        "sdd-delivery/v2",
        target="example-api",
        org="example-org",
        meta_repo="example-meta",
        board_name="",
        board_url="",
        apply=True,
    )

    text = agents.read_text(encoding="utf-8")
    assert "Team note: keep this." in text
    assert ".agents/skills/prayog-skills/" not in text
    assert "**`prayog-skills/`** (git submodule at root, pinned at **v0.4.3**)" in text
    assert "Shared rules: **`.cursor/rules/*.mdc`** (git submodule, pinned at **v0.5.10**)" in text
    assert "Shared rules: **`.cursor/rules/*.mdc`** (git submodule at root" not in text
    assert "/board-seed" in text


def test_migrate_agents_md_content_meta_pin() -> None:
    text = (
        "Installed under **`.harness/skills/<skill>/`**\n\n"
        "- Prayog PM bundle @ **v0.4.2**: `/prd`, `/validate-requirements`\n"
        "- Workflow: `.agents/skills/prayog-skills/workflow.yaml`\n"
    )
    updated, notes = _migrate_agents_md_content(
        text,
        skills_ref="v0.4.3",
        skill_names=["validate-requirements", "prd-impact-map", "prd"],
    )
    assert "prayog path → root" in notes
    assert "meta skills pin → v0.4.3" in notes
    assert "prayog-skills/workflow.yaml" in updated
    assert ".agents/skills/prayog-skills/" not in updated
    assert "Prayog PM bundle @ **v0.4.3**:" in updated
    assert "/prd-impact-map" in updated
