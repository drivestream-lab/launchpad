"""Tests for AGENTS.md harness-block ownership (Option A)."""

from __future__ import annotations

from launchpad.commands.apply_harness import (
    _HARNESS_BLOCK_END,
    _HARNESS_BLOCK_START,
    _seed_agents_md,
)
from launchpad.schema.harness import HarnessProfile


def _profile(name: str, *, rules_ref: str = "v0.5.10") -> HarnessProfile:
    raw: dict = {"skills": [{"repo": "prayog-skills", "ref": "v0.4.3"}]}
    if name != "meta-pm":
        raw["constitution"] = {"repo": "python-services-rules", "ref": rules_ref}
    return HarnessProfile(name, raw)


def _seed(tmp_path, *, profile: str = "python-backend", adopt: bool = False, skills=None):
    _seed_agents_md(
        tmp_path,
        profile,
        _profile(profile),
        skills or ["spec-draft", "board-seed", "verify"],
        "sdd-delivery/v2",
        target="example-api" if profile != "meta-pm" else "example-meta",
        org="example-org",
        meta_repo="example-meta",
        board_name="Eng Board",
        board_url="https://example.test/board",
        apply=True,
        adopt_agents=adopt,
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


def test_seed_agents_preserves_file_without_markers(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    original = "# Team guide\n\n## Run and verify\n\nmake test\n"
    agents.write_text(original, encoding="utf-8")

    _seed(tmp_path)

    assert agents.read_text(encoding="utf-8") == original


def test_seed_agents_refreshes_only_harness_block(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# Agent guide (example-api)\n\n"
        f"{_HARNESS_BLOCK_START}\n"
        "## Harness (managed by launchpad — do not edit)\n\n"
        "Agent skills: **`prayog-skills/`** (git submodule at root, pinned at **v0.4.2**) — `/verify`.\n"
        f"{_HARNESS_BLOCK_END}\n\n"
        "## Run and verify\n\n"
        "conda activate example-api\n"
        "make verify-all\n",
        encoding="utf-8",
    )

    _seed(tmp_path, skills=["spec-draft", "board-seed", "verify"])

    text = agents.read_text(encoding="utf-8")
    assert "conda activate example-api" in text
    assert "make verify-all" in text
    assert "pinned at **v0.4.3**" in text
    assert "/board-seed" in text
    assert "Eng Board" in text


def test_seed_agents_adopt_inserts_block_keeping_team_content(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# Agent guide (example-api)\n\n"
        "## Run and verify\n\n"
        "make check && make test\n",
        encoding="utf-8",
    )

    _seed(tmp_path, adopt=True)

    text = agents.read_text(encoding="utf-8")
    assert _HARNESS_BLOCK_START in text
    assert _HARNESS_BLOCK_END in text
    assert "## Run and verify" in text
    assert "make check && make test" in text
    assert "pinned at **v0.4.3**" in text
    # second apply without adopt still refreshes block
    _seed(tmp_path, skills=["spec-draft", "initiative-feasibility", "verify"])
    text2 = agents.read_text(encoding="utf-8")
    assert "/initiative-feasibility" in text2
    assert "make check && make test" in text2
