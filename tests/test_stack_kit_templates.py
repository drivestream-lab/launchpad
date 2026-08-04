"""Kit stack template presence and constitution rewrite."""

from __future__ import annotations

from pathlib import Path

from launchpad.commands.apply_harness import _seed_harness_pin
from launchpad.schema.harness import HarnessProfile

_TEMPLATES = Path(__file__).resolve().parents[1] / "launchpad" / "templates"


def test_stack_kit_templates_present() -> None:
    for stack in (
        "python-backend",
        "nextjs-frontend",
        "terraform-iac",
        "flink",
        "edge-agent",
        "meta-pm",
    ):
        if stack == "meta-pm":
            assert (_TEMPLATES / "harness-pin.meta.yaml").is_file()
            assert (_TEMPLATES / "CODEOWNERS.meta-pm").is_file()
        else:
            assert (_TEMPLATES / f"harness-pin.{stack}.yaml").is_file()
            assert (_TEMPLATES / f"CODEOWNERS.{stack}").is_file()


def test_no_data_platform_stack_kit() -> None:
    assert not (_TEMPLATES / "harness-pin.data-platform.yaml").exists()
    assert not (_TEMPLATES / "CODEOWNERS.data-platform").exists()


def test_nextjs_pin_identity() -> None:
    text = (_TEMPLATES / "harness-pin.nextjs-frontend.yaml").read_text(encoding="utf-8")
    assert "profile: nextjs-frontend" in text
    assert "profile: frontend" not in text


def test_constitution_rewrite_is_generalized(tmp_path: Path) -> None:
    profile = HarnessProfile(
        "edge-agent",
        {
            "constitution": {
                "repo": "edge-agent-rules",
                "org": "acme-org",
                "ref": "v0.1.0",
            },
            "skills": [{"repo": "prayog-skills", "ref": "v0.5.0-rc.2"}],
        },
    )
    _seed_harness_pin(
        tmp_path,
        "harness-pin.edge-agent.yaml",
        profile,
        "edge-agent",
        ["verify"],
        "sdd-delivery/v2",
        apply=True,
        agent_skills_ref="v0.5.0-rc.2",
    )
    pin = (tmp_path / ".harness-pin.yaml").read_text(encoding="utf-8")
    assert "repo: acme-org/edge-agent-rules" in pin
    assert "profile: edge-agent" in pin
