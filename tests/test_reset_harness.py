"""Tests for reset-harness local materialization cleanup."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from launchpad import clients as clients_mod
from launchpad.commands.apply_harness import _HARNESS_BLOCK_END, _HARNESS_BLOCK_START
from launchpad.commands.reset_harness import reset_harness_repo, run_reset_harness
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


def test_run_reset_harness_uses_client_workspace_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Regression: blank workspace override must not pin reset to cwd."""
    ws = tmp_path / "programme-ws"
    meta = ws / "example-meta"
    config = meta / "config"
    config.mkdir(parents=True)
    app = ws / "example-api"
    app.mkdir()
    pin = app / ".harness-pin.yaml"
    pin.write_text("profile: python-backend\n", encoding="utf-8")

    (config / "programme.yaml").write_text(
        "\n".join(
            [
                "apiVersion: launchpad/v1",
                "kind: Programme",
                "programme: EXAMPLE",
                "programme_slug: example",
                "org: example-org",
                "meta_repo: example-meta",
                "forge:",
                "  provider: github",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (config / "governance-example-org.yaml").write_text(
        "\n".join(
            [
                "apiVersion: launchpad/v1",
                "kind: GovernanceConfig",
                "org: example-org",
                "stack_profiles:",
                "  python-backend: Python",
                "teams:",
                "  - name: backend-devs",
                "    description: Backend",
                "    privacy: closed",
                "repos:",
                "  example-api:",
                "    description: api",
                "    stack: python-backend",
                "    teams: [backend-devs]",
                "    visibility: private",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (config / "harness-example-org.yaml").write_text(
        "\n".join(
            [
                "apiVersion: launchpad/v1",
                "kind: HarnessConfig",
                "org: example-org",
                "profiles:",
                "  python-backend:",
                "    skills:",
                "      - repo: prayog-skills",
                "        ref: d3bd94e",
                "",
            ]
        ),
        encoding="utf-8",
    )

    clients_file = tmp_path / "clients.yaml"
    clients_file.write_text(
        yaml.safe_dump(
            {
                "clients": [
                    {
                        "id": "example",
                        "path": str(meta),
                        "workspace": str(ws),
                        "forge": "github",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", clients_file)

    elsewhere = tmp_path / "not-the-workspace" / "nested"
    elsewhere.mkdir(parents=True)
    monkeypatch.chdir(elsewhere)

    rc = run_reset_harness(
        meta=False,
        repo_name="example-api",
        apply=True,
        include_seeded_workflows=False,
        config_dir=config,
        workspace="",  # historical CLI default — must not win over client workspace
        client_id="example",
    )
    assert rc == 0
    assert not pin.exists()
    out = capsys.readouterr().out
    assert "example-org/example-api" in out
