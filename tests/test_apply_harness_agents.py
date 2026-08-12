"""Tests for AGENTS.md harness-block ownership (Option A)."""

from __future__ import annotations

from launchpad.commands.apply_harness import (
    _HARNESS_BLOCK_END,
    _HARNESS_BLOCK_START,
    _seed_agents_md,
    _strip_factory_owned_agents_prose,
)
from launchpad.schema.harness import HarnessProfile


def _profile(name: str, *, rules_ref: str = "v0.5.10") -> HarnessProfile:
    raw: dict = {"skills": [{"repo": "prayog-skills", "ref": "d3bd94e"}]}
    if name != "meta-pm":
        raw["constitution"] = {"repo": "python-services-rules", "ref": rules_ref}
    return HarnessProfile(name, raw)


def _seed(tmp_path, *, profile: str = "python-backend", skills=None):
    _seed_agents_md(
        tmp_path,
        profile,
        _profile(profile),
        skills or ["spec-draft", "create-board-tickets", "ground-spec"],
        "sdd-delivery/v2",
        target="example-api" if profile != "meta-pm" else "example-meta",
        org="example-org",
        meta_repo="example-meta",
        board_name="Eng Board",
        board_url="https://example.test/board",
        apply=True,
    )


def test_seed_agents_creates_initial_guide_with_markers(tmp_path) -> None:
    _seed(tmp_path, profile="meta-pm", skills=["validate-requirements", "prd-impact-map"])

    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert _HARNESS_BLOCK_START in text
    assert _HARNESS_BLOCK_END in text
    assert "sdd-delivery/v2" in text
    assert "prayog-skills/workflow.yaml" in text
    assert ".agents/skills/prayog-skills/" not in text
    assert "## Repository truth" in text


def test_seed_agents_inserts_block_into_unmarked_team_file(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# Team guide\n\n## Run and verify\n\nmake test\n",
        encoding="utf-8",
    )

    _seed(tmp_path)

    text = agents.read_text(encoding="utf-8")
    assert _HARNESS_BLOCK_START in text
    assert _HARNESS_BLOCK_END in text
    assert "## Run and verify" in text
    assert "make test" in text
    assert "pinned at **d3bd94e**" in text


def test_seed_agents_refreshes_only_harness_block(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# Agent guide (example-api)\n\n"
        f"{_HARNESS_BLOCK_START}\n"
        "## Harness (managed by launchpad — do not edit)\n\n"
        "Agent skills: **`prayog-skills/`** (git submodule at root, pinned at **old**) — `/ground-spec`.\n"
        f"{_HARNESS_BLOCK_END}\n\n"
        "## Run and verify\n\n"
        "conda activate example-api\n"
        "make verify-all\n",
        encoding="utf-8",
    )

    _seed(tmp_path, skills=["spec-draft", "create-board-tickets", "ground-spec"])

    text = agents.read_text(encoding="utf-8")
    assert "conda activate example-api" in text
    assert "make verify-all" in text
    assert "pinned at **d3bd94e**" in text
    assert "/create-board-tickets" in text
    assert "Eng Board" in text
    assert "`/verify`" not in text
    assert "tests/verify" in text  # smoke path, not a skill


def test_seed_agents_legacy_kit_dedupes_factory_prose(tmp_path) -> None:
    """Pre-marker kit AGENTS must not keep duplicate Shared rules after insert."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# Agent guide (example-api)\n\n"
        "Shared rules: **`.cursor/rules/*.mdc`** (git submodule, pinned at **v0.4.0**).\n\n"
        "Agent skills: **`.agents/skills/prayog-skills/`** "
        "(git submodule, pinned at **v0.4.0**) — `/ground-spec`.\n\n"
        "### Delivery bootstrap\n\n"
        "- Contract: **sdd-delivery/v1**\n"
        "- Workflow: `.agents/skills/prayog-skills/workflow.yaml`\n\n"
        "### Programme board\n\n"
        "Engineering work is tracked on **Old Board**.\n\n"
        "## Product (what to build)\n\n"
        "Start here: docs/specification/README.md\n\n"
        "## Run and verify\n\n"
        "make check && make test\n",
        encoding="utf-8",
    )

    _seed(tmp_path, skills=["spec-draft", "create-board-tickets", "ground-spec"])

    text = agents.read_text(encoding="utf-8")
    assert text.count(_HARNESS_BLOCK_START) == 1
    assert text.count("### Delivery bootstrap") == 1
    assert "sdd-delivery/v2" in text
    assert "pinned at **d3bd94e**" in text
    assert ".agents/skills/prayog-skills/" not in text
    assert "## Product (what to build)" in text
    assert "Start here: docs/specification/README.md" in text
    assert "## Run and verify" in text
    assert "make check && make test" in text
    # stale pin / board from unmarked factory prose gone
    assert "v0.4.0" not in text
    assert "Old Board" not in text

    # second apply refreshes block only
    _seed(tmp_path, skills=["spec-draft", "initiative-feasibility", "ground-spec"])
    text2 = agents.read_text(encoding="utf-8")
    assert "/initiative-feasibility" in text2
    assert "make check && make test" in text2


def test_strip_factory_owned_keeps_team_sections() -> None:
    raw = (
        "# Guide\n\n"
        "## Harness (managed by launchpad — do not edit)\n\n"
        "Agent skills: **`prayog-skills/`** pinned at **v0.1** — `/x`.\n\n"
        "## Run and verify\n\n"
        "make test\n"
    )
    cleaned = _strip_factory_owned_agents_prose(raw)
    assert "## Harness" not in cleaned
    assert "Agent skills:" not in cleaned
    assert "## Run and verify" in cleaned
    assert "make test" in cleaned
