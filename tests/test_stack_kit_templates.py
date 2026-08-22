"""Pin generator, CODEOWNERS families, legacy shim, and pressure fixtures."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from launchpad.commands.apply_harness import _seed_harness_pin
from launchpad.harness.codeowners_render import (
    legacy_codeowners_deprecation_warn,
    resolve_codeowners_content,
)
from launchpad.schema.owners import OwnersConfig, PROFILE_OWNER_DEFAULTS, resolve_owners
from launchpad.harness.pin_render import harness_pin_template_warn, render_harness_pin
from launchpad.schema.errors import SchemaError
from launchpad.schema.harness import HarnessProfile

_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN = _ROOT / "tests" / "fixtures" / "codeowners_golden"
_FAMILIES = _ROOT / "launchpad" / "templates" / "codeowners"


def _profile(name: str, raw: dict | None = None) -> HarnessProfile:
    return HarnessProfile(name, raw or {})


def test_layout_families_present() -> None:
    for family in (
        "app_src",
        "app_edge",
        "app_nextjs",
        "flink",
        "iac",
        "meta",
        "android_kotlin",
        "ios_swift",
    ):
        assert (_FAMILIES / f"family.{family}").is_file()


def test_no_per_stack_kit_templates() -> None:
    templates = _ROOT / "launchpad" / "templates"
    for stack in (
        "python-backend",
        "nextjs-frontend",
        "terraform-iac",
        "flink",
        "edge-agent",
        "meta-pm",
    ):
        assert not (templates / f"CODEOWNERS.{stack}").exists()
        pin = (
            templates / "harness-pin.meta.yaml"
            if stack == "meta-pm"
            else templates / f"harness-pin.{stack}.yaml"
        )
        assert not pin.exists()


@pytest.mark.parametrize(
    "stack,org",
    [
        ("python-backend", "acme"),
        ("nextjs-frontend", "acme"),
        ("flink", "acme"),
        ("terraform-iac", "acme"),
        ("edge-agent", "acme"),
        ("meta-pm", "acme"),
    ],
)
def test_codeowners_golden_parity(stack: str, org: str) -> None:
    """Generated family output matches pre-0.5.36 kit CODEOWNERS (org substituted)."""
    profile = _profile(stack)  # convention template + migration defaults
    got = resolve_codeowners_content(profile, stack, org, warn_stream=io.StringIO())
    assert got is not None
    expected = (_GOLDEN / stack).read_text(encoding="utf-8").replace("example-org", org)
    assert got == expected


def test_legacy_codeowners_name_warns_and_renders() -> None:
    err = io.StringIO()
    profile = HarnessProfile(
        "python-backend",
        {
            "codeowners_template": "CODEOWNERS.python-backend",
            "skills": [{"repo": "prayog-skills", "ref": "v0.5.1"}],
        },
    )
    assert profile.codeowners_template_explicit
    got = resolve_codeowners_content(
        profile, "python-backend", "acme", warn_stream=err
    )
    warn = err.getvalue()
    assert "WARN: codeowners_template 'CODEOWNERS.python-backend' is deprecated" in warn
    assert "kit per-stack CODEOWNERS files were removed in v0.5.36" in warn
    assert "Fix in config/harness-<org>.yaml" in warn
    assert "Remove:" in warn
    assert "codeowners_template: CODEOWNERS.python-backend" in warn
    assert "launchpad reset-harness" in warn
    assert "launchpad apply-harness" in warn
    expected = (_GOLDEN / "python-backend").read_text(encoding="utf-8").replace(
        "example-org", "acme"
    )
    assert got == expected


def test_legacy_warn_helper_matches_plan_shape() -> None:
    text = legacy_codeowners_deprecation_warn(
        tpl_name="CODEOWNERS.python-backend",
        family="app_src",
        profile_name="python-backend",
    )
    assert "layout family 'app_src'" in text


def test_harness_pin_template_warn_on_seed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = HarnessProfile(
        "python-backend",
        {
            "harness_pin_template": "harness-pin.python-backend.yaml",
            "constitution": {"repo": "python-services-rules", "ref": "v0.5.12"},
            "skills": [{"repo": "prayog-skills", "ref": "v0.5.1"}],
        },
    )
    _seed_harness_pin(
        tmp_path,
        profile,
        "python-backend",
        ["ground-spec"],
        "sdd-delivery/v2",
        apply=True,
        agent_skills_ref="v0.5.1",
    )
    err = capsys.readouterr().err
    assert "harness_pin_template" in err
    assert "ignored" in err or "always generated" in err
    assert harness_pin_template_warn("python-backend", profile.harness_pin_template) in err
    pin = (tmp_path / ".harness-pin.yaml").read_text(encoding="utf-8")
    assert "profile: python-backend" in pin
    assert "repo: drivestream-lab/python-services-rules" in pin


def test_constitution_rewrite_is_generalized(tmp_path: Path) -> None:
    profile = HarnessProfile(
        "edge-agent",
        {
            "constitution": {
                "repo": "edge-agent-rules",
                "org": "acme-org",
                "ref": "v0.1.0",
            },
            "skills": [{"repo": "prayog-skills", "ref": "d3bd94e"}],
        },
    )
    _seed_harness_pin(
        tmp_path,
        profile,
        "edge-agent",
        ["ground-spec"],
        "sdd-delivery/v2",
        apply=True,
        agent_skills_ref="d3bd94e",
    )
    pin = (tmp_path / ".harness-pin.yaml").read_text(encoding="utf-8")
    assert "repo: acme-org/edge-agent-rules" in pin
    assert "profile: edge-agent" in pin
    assert "- ground-spec" in pin
    assert "- verify" not in pin


def test_pin_identity_nextjs() -> None:
    profile = HarnessProfile(
        "nextjs-frontend",
        {
            "constitution": {"repo": "nextjs-bff-rules", "ref": "v1.0.0"},
            "skills": [{"repo": "prayog-skills", "ref": "v0.5.1"}],
        },
    )
    text = render_harness_pin(
        profile,
        "nextjs-frontend",
        skill_names=["spec-draft"],
        delivery_contract="sdd-delivery/v2",
        agent_skills_ref="v0.5.1",
    )
    assert "profile: nextjs-frontend" in text
    assert "profile: frontend" not in text


def test_edge_inference_engine_app_src_extra_paths() -> None:
    profile = HarnessProfile(
        "edge-inference-engine",
        {
            "owners": {
                "team": "edge-agent-devs",
                "layout": "app_src",
                "extra_paths": ["/model_checkpoints/"],
            },
            "constitution": {"repo": "edge-inference-engine-rules", "ref": "v0.1.0"},
            "skills": [{"repo": "prayog-skills", "ref": "v0.5.1"}],
        },
    )
    got = resolve_codeowners_content(
        profile, "edge-inference-engine", "lab", warn_stream=io.StringIO()
    )
    assert got is not None
    assert "/src/" in got
    assert "/tests/" in got
    assert "/model_checkpoints/" in got
    assert "@lab/edge-agent-devs" in got


def test_android_kotlin_family() -> None:
    profile = HarnessProfile(
        "android-kotlin",
        {
            "owners": {"team": "mobile-devs", "layout": "android_kotlin"},
        },
    )
    got = resolve_codeowners_content(
        profile, "android-kotlin", "lab", warn_stream=io.StringIO()
    )
    assert got is not None
    assert "/app/src/" in got
    assert "@lab/mobile-devs" in got


def test_ios_swift_family() -> None:
    profile = HarnessProfile(
        "ios-swift",
        {
            "owners": {"team": "mobile-devs", "layout": "ios_swift"},
        },
    )
    got = resolve_codeowners_content(
        profile, "ios-swift", "lab", warn_stream=io.StringIO()
    )
    assert got is not None
    assert "/Sources/" in got
    assert "/Resources/" in got
    assert "@lab/mobile-devs" in got


def test_platform_tooling_none_skips() -> None:
    profile = _profile("platform-tooling")
    assert resolve_owners("platform-tooling", profile.owners).layout == "none"
    got = resolve_codeowners_content(
        profile, "platform-tooling", "lab", warn_stream=io.StringIO()
    )
    assert got is None


def test_embedded_defer_layout_none() -> None:
    profile = HarnessProfile(
        "embedded-c",
        {"owners": {"layout": "none"}},
    )
    got = resolve_codeowners_content(
        profile, "embedded-c", "lab", warn_stream=io.StringIO()
    )
    assert got is None


def test_unknown_stack_without_owners_fails() -> None:
    profile = _profile("brand-new-stack")
    with pytest.raises(SchemaError, match="owners.team and owners.layout"):
        resolve_codeowners_content(
            profile, "brand-new-stack", "lab", warn_stream=io.StringIO()
        )


def test_unknown_missing_template_fails_loud() -> None:
    profile = HarnessProfile(
        "python-backend",
        {"codeowners_template": "CODEOWNERS.does-not-exist"},
    )
    with pytest.raises(SchemaError, match="not found"):
        resolve_codeowners_content(
            profile, "python-backend", "lab", warn_stream=io.StringIO()
        )


def test_meta_templates_override(tmp_path: Path) -> None:
    meta_tpl = tmp_path / "templates"
    meta_tpl.mkdir()
    (meta_tpl / "custom.CODEOWNERS").write_text(
        "* @example-org/custom-team\n", encoding="utf-8"
    )
    profile = HarnessProfile(
        "python-backend",
        {"codeowners_template": "custom.CODEOWNERS"},
    )
    got = resolve_codeowners_content(
        profile,
        "python-backend",
        "acme",
        meta_templates=meta_tpl,
        warn_stream=io.StringIO(),
    )
    assert got == "* @acme/custom-team\n"


def test_migration_defaults_map() -> None:
    assert PROFILE_OWNER_DEFAULTS["python-backend"]["layout"] == "app_src"
    assert resolve_owners("flink", None) == OwnersConfig(
        team="data-platform-devs", layout="flink"
    )
