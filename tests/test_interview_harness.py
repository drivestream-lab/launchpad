"""Tests for onboard interview day-1 YAML defaults and skills ref latest."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

import httpx
import pytest
import yaml

from launchpad.harness.skills_ref import SkillsRefResolveError, resolve_skills_ref
from launchpad.onboarding.interview import (
    _render_catalog,
    _render_governance,
    _render_harness,
    run_interview,
)


def test_render_governance_uses_operator_team_slugs() -> None:
    text = _render_governance(
        "acme",
        "acme-meta",
        pm_team="product-owners",
        pe_team="platform-eng",
    )
    raw = yaml.safe_load(text)
    names = {t["name"] for t in raw["teams"]}
    assert names == {"product-owners", "platform-eng"}
    assert raw["repos"]["acme-meta"]["teams"] == ["product-owners", "platform-eng"]
    assert "platform-core" not in text


def test_render_harness_meta_prd_ready() -> None:
    text = _render_harness("acme", pe_team="platform-eng")
    raw = yaml.safe_load(text)
    assert raw["delivery_contract"] == "sdd-delivery/v2"
    assert raw["delivery_roles"]["engineering-gate"] == "platform-eng"
    meta = raw["profiles"]["meta-pm"]
    assert meta["skills"][0]["repo"] == "prayog-skills"
    assert meta["skills"][0]["ref"] == "latest"
    assert "community_skills" not in meta
    assert "python-agent-skills" not in text
    assert list(raw["profiles"]) == ["meta-pm"]


def test_render_catalog_teams() -> None:
    text = _render_catalog(
        "acme", "acme-meta", pm_team="product-owners", pe_team="platform-eng"
    )
    raw = yaml.safe_load(text)
    assert raw["services"]["acme-meta"]["teams"] == ["product-owners", "platform-eng"]


def test_run_interview_writes_parameterized_yaml(tmp_path, monkeypatch) -> None:
    answers = iter(
        [
            "Demo",  # programme
            "demo",  # slug
            "demo-org",  # org
            str(tmp_path / "ws"),  # workspace
            "product-owners",  # pm
            "platform-eng",  # pe
        ]
    )
    out = StringIO()

    def fake_input(prompt: str) -> str:
        return next(answers)

    monkeypatch.setattr(
        "launchpad.onboarding.interview.CLIENTS_FILE",
        tmp_path / "clients.yaml",
    )
    monkeypatch.setattr(
        "launchpad.onboarding.interview.CONFIG_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        "launchpad.onboarding.interview.ENV_D_DIR",
        tmp_path / "env.d",
    )

    run_interview(input_fn=fake_input, out=out)

    harness = yaml.safe_load(
        (tmp_path / "ws" / "demo-meta" / "config" / "harness-demo-org.yaml").read_text()
    )
    gov = yaml.safe_load(
        (tmp_path / "ws" / "demo-meta" / "config" / "governance-demo-org.yaml").read_text()
    )
    assert harness["delivery_roles"]["engineering-gate"] == "platform-eng"
    assert harness["profiles"]["meta-pm"]["skills"][0]["ref"] == "latest"
    assert {t["name"] for t in gov["teams"]} == {"product-owners", "platform-eng"}


def test_resolve_skills_ref_passthrough() -> None:
    assert resolve_skills_ref("drivestream-lab", "prayog-skills", "v0.4.3") == "v0.4.3"


def test_resolve_skills_ref_latest(monkeypatch) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tag_name": "v9.9.9"}

    def fake_get(url, headers=None, timeout=None):
        assert "releases/latest" in url
        return mock_response

    monkeypatch.setattr(httpx, "get", fake_get)
    assert resolve_skills_ref("drivestream-lab", "prayog-skills", "latest") == "v9.9.9"
    assert resolve_skills_ref("drivestream-lab", "prayog-skills", "LATEST") == "v9.9.9"


def test_resolve_skills_ref_latest_http_error(monkeypatch) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404

    monkeypatch.setattr(httpx, "get", lambda *a, **k: mock_response)
    with pytest.raises(SkillsRefResolveError, match="HTTP 404"):
        resolve_skills_ref("drivestream-lab", "prayog-skills", "latest")
