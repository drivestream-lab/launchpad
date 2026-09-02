"""Unit tests for the greenfield schema layer (WS0)."""

from __future__ import annotations

import pytest
from pathlib import Path

from launchpad.schema import (
    ProgrammeSchema,
    GovernanceSchema,
    HarnessSchema,
    ScaffoldSchema,
    CatalogSchema,
    SchemaError,
    load_programme,
    load_governance,
    load_harness,
    load_scaffold,
    load_catalog,
)

FIXTURES = Path(__file__).parent / "fixtures" / "schema"


# ─── ProgrammeSchema ─────────────────────────────────────────────────────────

class TestProgrammeSchema:
    def test_load_day1_fixture(self):
        prog = load_programme(FIXTURES / "programme-day1.yaml")
        assert prog.programme == "KOLA"
        assert prog.programme_slug == "kola"
        assert prog.org == "apex-common"
        assert prog.meta_repo == "kola-meta"
        assert prog.forge_provider == "github"

    def test_slug_auto_derived_from_programme_name(self):
        prog = ProgrammeSchema({"programme": "My Initiative", "org": "acme"})
        assert prog.programme_slug == "my-initiative"

    def test_missing_programme_raises(self):
        with pytest.raises(SchemaError, match="missing required field 'programme'"):
            ProgrammeSchema({"org": "acme"})

    def test_missing_org_raises(self):
        with pytest.raises(SchemaError, match="missing required field 'org'"):
            ProgrammeSchema({"programme": "Test"})

    def test_gitlab_provider_rejected(self):
        with pytest.raises(SchemaError, match="not yet supported"):
            ProgrammeSchema({"programme": "Test", "org": "acme", "forge": {"provider": "gitlab"}})

    def test_unknown_provider_rejected(self):
        with pytest.raises(SchemaError, match="Unknown forge.provider"):
            ProgrammeSchema({"programme": "Test", "org": "acme", "forge": {"provider": "bitbucket"}})

    def test_invalid_slug_raises(self):
        with pytest.raises(SchemaError, match="invalid"):
            ProgrammeSchema({"programme": "Test", "programme_slug": "UPPER_CASE", "org": "acme"})

    def test_as_dict_round_trip(self):
        prog = ProgrammeSchema({"programme": "KOLA", "org": "apex-common"})
        d = prog.as_dict()
        assert d["kind"] == "Programme"
        assert d["programme"] == "KOLA"
        assert d["forge"]["provider"] == "github"


# ─── GovernanceSchema ────────────────────────────────────────────────────────

class TestGovernanceSchema:
    def test_load_day1_fixture(self):
        gov = load_governance(FIXTURES / "governance-day1.yaml")
        assert gov.org == "apex-common"
        assert "kola-meta" in gov.repos
        assert gov.repos["kola-meta"].stack == "meta-pm"

    def test_load_dayn_fixture(self):
        gov = load_governance(FIXTURES / "governance-dayn.yaml")
        assert "kola-platform-core" in gov.repos
        assert gov.repos["kola-platform-core"].stack == "python-backend"

    def test_stack_profiles_yaml_only(self):
        gov = GovernanceSchema({
            "org": "acme",
            "stack_profiles": {"go-backend": "Go microservice"},
            "teams": [],
            "repos": {},
        })
        assert gov.stack_profiles == {"go-backend": "Go microservice"}
        assert "python-backend" not in gov.stack_profiles

    def test_empty_stack_profiles(self):
        gov = GovernanceSchema({"org": "acme", "teams": [], "repos": {}})
        assert gov.stack_profiles == {}

    def test_missing_org_raises(self):
        with pytest.raises(SchemaError, match="missing required field 'org'"):
            GovernanceSchema({"teams": [], "repos": {}})

    def test_repo_missing_stack_raises(self):
        raw = {
            "org": "acme",
            "teams": [{"name": "team-a"}],
            "repos": {"my-repo": {"teams": ["team-a"]}},
        }
        with pytest.raises(SchemaError, match="missing required field 'stack'"):
            GovernanceSchema(raw)

    def test_repo_missing_teams_raises(self):
        raw = {
            "org": "acme",
            "stack_profiles": {"python-backend": "Python / FastAPI microservice"},
            "teams": [{"name": "team-a"}],
            "repos": {"my-repo": {"stack": "python-backend"}},
        }
        with pytest.raises(SchemaError, match="requires at least one team"):
            GovernanceSchema(raw)

    def test_repo_unknown_stack_raises(self):
        raw = {
            "org": "acme",
            "teams": [{"name": "team-a"}],
            "repos": {"my-repo": {"stack": "cobol-legacy", "teams": ["team-a"]}},
        }
        with pytest.raises(SchemaError, match="not in stack_profiles"):
            GovernanceSchema(raw)

    def test_repo_unknown_team_raises(self):
        raw = {
            "org": "acme",
            "stack_profiles": {"python-backend": "Python / FastAPI microservice"},
            "teams": [{"name": "team-a"}],
            "repos": {"my-repo": {"stack": "python-backend", "teams": ["ghost-team"]}},
        }
        with pytest.raises(SchemaError, match="unknown teams"):
            GovernanceSchema(raw)


# ─── HarnessSchema ───────────────────────────────────────────────────────────

class TestHarnessSchema:
    def test_load_day1_fixture(self):
        h = load_harness(FIXTURES / "harness-day1.yaml")
        assert h.org == "apex-common"
        assert "meta-pm" in h.profiles
        assert list(h.profiles) == ["meta-pm"]
        assert h.delivery_contract == "sdd-delivery/v2"
        assert h.delivery_roles["engineering-gate"] == "pe-team"
        assert h.profiles["meta-pm"].skills[0].repo == "prayog-skills"
        assert h.profiles["meta-pm"].skills[0].ref == "latest"

    def test_template_fields_explicit(self):
        h = load_harness(FIXTURES / "harness-day1.yaml")
        assert h.profiles["meta-pm"].constitution is None  # meta-pm has no rules submodule
        assert h.profiles["meta-pm"].community_skills == []

    def test_template_fields_convention_default(self):
        """If codeowners_template / harness_pin_template are absent, convention applies."""
        raw = {
            "org": "acme",
            "profiles": {
                "nextjs-frontend": {
                    "constitution": {"repo": "nextjs-rules", "ref": "v1.0.0"},
                    "skills": [],
                }
            },
        }
        h = HarnessSchema(raw)
        prof = h.profiles["nextjs-frontend"]
        assert prof.codeowners_template == "CODEOWNERS.nextjs-frontend"
        assert prof.harness_pin_template == "harness-pin.nextjs-frontend.yaml"

    def test_resolve_profile_defaults_to_stack(self):
        h = load_harness(FIXTURES / "harness-day1.yaml")
        assert h.resolve_profile("kola-meta", "meta-pm") == "meta-pm"
        # Unknown stack with no matching profile → None
        assert h.resolve_profile("any-repo", "python-backend") is None

    def test_resolve_profile_uses_override(self):
        raw = {
            "org": "acme",
            "profiles": {
                "python-backend": {
                    "constitution": {"repo": "rules", "ref": "v1"}
                }
            },
            "repos": {"special-repo": "python-backend"},
        }
        h = HarnessSchema(raw)
        assert h.resolve_profile("special-repo", "nextjs-frontend") == "python-backend"

    def test_missing_org_raises(self):
        with pytest.raises(SchemaError, match="missing required field 'org'"):
            HarnessSchema({"profiles": {}})

    def test_constitution_optional(self):
        """Profile without constitution key is valid — meta/config repos."""
        raw = {
            "org": "acme",
            "profiles": {
                "meta-pm": {"skills": []}
            },
        }
        h = HarnessSchema(raw)
        assert h.profiles["meta-pm"].constitution is None

    def test_constitution_repo_accepts_org_prefixed_slug(self):
        raw = {
            "org": "acme",
            "profiles": {
                "python-backend": {
                    "constitution": {
                        "repo": "drivestream-lab/python-services-rules",
                        "ref": "v1",
                    }
                }
            },
        }
        constitution = HarnessSchema(raw).profiles["python-backend"].constitution
        assert constitution.repo == "python-services-rules"
        assert constitution.org == "drivestream-lab"
        assert constitution.submodule_url == (
            "https://github.com/drivestream-lab/python-services-rules"
        )

    def test_constitution_missing_ref_raises(self):
        raw = {
            "org": "acme",
            "profiles": {
                "python-backend": {"constitution": {"repo": "rules"}}
            },
        }
        with pytest.raises(SchemaError, match="missing required field 'ref'"):
            HarnessSchema(raw)

    def test_community_skills_and_runtimes(self):
        raw = {
            "org": "acme",
            "profiles": {
                "meta-pm": {
                    "skills": [{"repo": "prayog-skills", "ref": "v0.4.2"}],
                    "community_skills": [
                        {"source": "github/awesome-copilot", "ref": "v1.0.0", "skill": "prd"}
                    ],
                    "skill_runtimes": [".agents/skills", ".claude/skills"],
                }
            },
        }
        h = HarnessSchema(raw)
        prof = h.profiles["meta-pm"]
        assert prof.name == "meta-pm"
        assert len(prof.community_skills) == 1
        assert prof.community_skills[0].source == "github/awesome-copilot"
        assert prof.community_skills[0].ref == "v1.0.0"
        assert prof.skill_runtimes == [".agents/skills", ".claude/skills"]

    def test_prayog_profile_alias_rejected(self):
        raw = {
            "org": "acme",
            "profiles": {
                "nextjs-frontend": {
                    "prayog_profile": "frontend",
                    "skills": [{"repo": "prayog-skills", "ref": "v0.4.2"}],
                }
            },
        }
        with pytest.raises(SchemaError, match="prayog_profile is not supported"):
            HarnessSchema(raw)

    def test_community_skill_missing_ref_raises(self):
        raw = {
            "org": "acme",
            "profiles": {
                "meta-pm": {
                    "community_skills": [{"source": "github/awesome-copilot", "skill": "prd"}],
                }
            },
        }
        with pytest.raises(SchemaError, match="missing required field 'ref'"):
            HarnessSchema(raw)

    def test_repos_references_unknown_profile_raises(self):
        raw = {
            "org": "acme",
            "profiles": {},
            "repos": {"my-repo": "nonexistent-profile"},
        }
        with pytest.raises(SchemaError, match="unknown profile"):
            HarnessSchema(raw)


# ─── ScaffoldSchema ──────────────────────────────────────────────────────────

class TestScaffoldSchema:
    def test_load_day1_disabled(self):
        s = load_scaffold(FIXTURES / "scaffold-day1.yaml")
        assert s.meta is not None
        assert s.meta.enabled is False

    def test_load_dayn_enabled(self):
        s = load_scaffold(FIXTURES / "scaffold-dayn.yaml")
        assert s.meta is not None
        assert s.meta.enabled is True
        assert s.meta.template == "gh:drivestream-lab/tenant-meta-foundation"
        assert s.meta.ref == "v1.0.0"
        assert s.meta.context["project_name"] == "KOLA"

    def test_dayn_repo_scaffold(self):
        s = load_scaffold(FIXTURES / "scaffold-dayn.yaml")
        repo = s.repos["kola-platform-core"]
        assert repo.enabled is True
        assert repo.context["has_kafka"] is True

    def test_enabled_without_template_raises(self):
        raw = {
            "org": "acme",
            "meta": {"enabled": True, "ref": "v1"},
        }
        with pytest.raises(SchemaError, match="requires 'template'"):
            ScaffoldSchema(raw)

    def test_enabled_without_ref_raises(self):
        raw = {
            "org": "acme",
            "meta": {"enabled": True, "template": "gh:acme/tmpl"},
        }
        with pytest.raises(SchemaError, match="requires 'ref'"):
            ScaffoldSchema(raw)

    def test_gh_shorthand_resolves(self):
        raw = {
            "org": "acme",
            "meta": {
                "enabled": True,
                "template": "gh:drivestream-lab/tenant-meta-foundation",
                "ref": "v1",
                "context": {},
            },
        }
        s = ScaffoldSchema(raw)
        assert s.meta.resolve_template_url() == "https://github.com/drivestream-lab/tenant-meta-foundation"

    def test_missing_org_raises(self):
        with pytest.raises(SchemaError, match="missing required field 'org'"):
            ScaffoldSchema({"meta": {}})


# ─── CatalogSchema ───────────────────────────────────────────────────────────

class TestCatalogSchema:
    def test_load_day1_fixture(self):
        c = load_catalog(FIXTURES / "catalog-day1.yaml")
        assert c.org == "apex-common"
        assert "kola-meta" in c.services
        assert c.services["kola-meta"].status == "live"

    def test_live_services_filter(self):
        c = load_catalog(FIXTURES / "catalog-day1.yaml")
        live = c.live_services
        assert len(live) == 1
        assert live[0].name == "kola-meta"

    def test_missing_org_raises(self):
        with pytest.raises(SchemaError, match="missing required field 'org'"):
            CatalogSchema({"services": {"x": {"stack": "meta-pm"}}})

    def test_empty_services_raises(self):
        with pytest.raises(SchemaError, match="at least one entry"):
            CatalogSchema({"org": "acme", "services": {}})

    def test_service_missing_stack_raises(self):
        with pytest.raises(SchemaError, match="missing required field 'stack'"):
            CatalogSchema({"org": "acme", "services": {"svc": {"description": "no stack"}}})

    def test_invalid_status_raises(self):
        with pytest.raises(SchemaError, match="invalid"):
            CatalogSchema({"org": "acme", "services": {"svc": {"stack": "meta-pm", "status": "unknown"}}})

