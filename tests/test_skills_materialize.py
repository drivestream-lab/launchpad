"""Tests for prayog skill resolution and harness hub symlink materialization."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from launchpad.commands.apply_harness import _verify_delivery_contract
from launchpad.harness.paths import HARNESS_SKILLS_HUB_REL, PRAYOG_SKILLS_SUBMODULE_REL
from launchpad.harness.skills_materialize import (
    all_runtime_skills_present,
    hub_skill_present,
    materialize_community_skill_tree,
    materialize_skill_tree,
    runtime_skill_present,
)
from launchpad.harness.skills_resolve import (
    HarnessResolveError,
    find_skill_source_dir,
    resolve_delivery_contract,
    resolve_gate_resources,
    resolve_skill_names,
    slash_list,
)
from launchpad.schema.harness import HarnessProfile

FIXTURES = Path(__file__).parent / "fixtures" / "prayog-skills"
RUNTIMES = [".agents/skills", ".claude/skills"]


def _meta_profile() -> HarnessProfile:
    return HarnessProfile(
        "meta-pm",
        {
            "skills": [{"repo": "prayog-skills", "ref": "v0.4.2"}],
            "community_skills": [
                {"source": "github/awesome-copilot", "ref": "v1.0.0", "skill": "prd"}
            ],
            "skill_runtimes": RUNTIMES,
        },
    )


def _python_profile() -> HarnessProfile:
    return HarnessProfile(
        "python-backend",
        {
            "skills": [{"repo": "prayog-skills", "ref": "v0.4.2"}],
            "skill_runtimes": RUNTIMES,
        },
    )


def _terraform_profile() -> HarnessProfile:
    return HarnessProfile(
        "terraform-iac",
        {
            "skills": [{"repo": "prayog-skills", "ref": "v0.4.3"}],
            "skill_runtimes": RUNTIMES,
        },
    )


class TestResolveSkillNames:
    def test_meta_pm_from_profile_yaml(self):
        names = resolve_skill_names(FIXTURES, _meta_profile(), "meta-pm")
        assert names == [
            "validate-requirements",
            "review-findings",
            "update-documents",
            "prd-impact-map",
        ]

    def test_python_backend_from_profile_yaml(self):
        names = resolve_skill_names(FIXTURES, _python_profile(), "python-backend")
        assert names == [
            "spec-draft",
            "initiative-feasibility",
            "spec-technical-review",
            "spec-implementation-plan",
            "board-seed",
            "pre-implement",
            "loop-spec",
            "ground-spec",
            "verify",
        ]

    def test_delivery_contract_from_pinned_fixture(self):
        assert resolve_delivery_contract(FIXTURES) == "sdd-delivery/v2"

    def test_delivery_contract_requires_workflow(self, tmp_path: Path):
        (tmp_path / "delivery-contract.yaml").write_text(
            "id: sdd-delivery\nversion: 2\nworkflow: workflow.yaml\n",
            encoding="utf-8",
        )
        with pytest.raises(HarnessResolveError, match="workflow.yaml"):
            resolve_delivery_contract(tmp_path)

    def test_delivery_contract_mismatch_fails_before_materialization(self):
        with pytest.raises(HarnessResolveError, match="mismatch"):
            _verify_delivery_contract(FIXTURES, "sdd-delivery/v1")

    def test_gate_resources_are_profile_scoped(self):
        labels, roles = resolve_gate_resources(FIXTURES, "meta-pm")
        assert [label["name"] for label in labels] == ["impact-map-pending"]
        assert roles == {"gate-1": "engineering-gate"}

        app_labels, app_roles = resolve_gate_resources(FIXTURES, "python-backend")
        assert [label["name"] for label in app_labels] == ["spec-pending", "spec-lgtm"]
        assert app_roles == {"gate-2": "engineering-gate"}

    def test_terraform_iac_from_profile_yaml(self):
        names = resolve_skill_names(FIXTURES, _terraform_profile(), "terraform-iac")
        assert names == [
            "spec-draft",
            "initiative-feasibility",
            "spec-technical-review",
            "spec-implementation-plan",
            "board-seed",
            "pre-implement",
            "loop-spec",
            "ground-spec",
            "verify",
        ]

    def test_missing_profile_suggests_prayog_profile(self, tmp_path: Path):
        with pytest.raises(HarnessResolveError, match="prayog_profile"):
            resolve_skill_names(tmp_path, _meta_profile(), "meta-pm")

    def test_missing_profile_raises(self, tmp_path: Path):
        with pytest.raises(HarnessResolveError, match="profiles/meta-pm.yaml"):
            resolve_skill_names(tmp_path, _meta_profile(), "meta-pm")


class TestFindSkillSourceDir:
    def test_finds_requirements_skill(self):
        src = find_skill_source_dir(FIXTURES, "validate-requirements", lane_key="requirements_skills")
        assert src == FIXTURES / "skills" / "requirements" / "validate-requirements"

    def test_finds_development_skill(self):
        src = find_skill_source_dir(FIXTURES, "pre-implement", lane_key="development_skills")
        assert src == FIXTURES / "skills" / "development" / "pre-implement"


class TestMaterializeSkillTree:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        repo_path = tmp_path / "demo-meta"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        submodule_dest = repo_path / PRAYOG_SKILLS_SUBMODULE_REL
        submodule_dest.parent.mkdir(parents=True, exist_ok=True)

        def _copy_tree(src: Path, dest: Path) -> None:
            dest.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                target = dest / item.name
                if item.is_dir():
                    _copy_tree(item, target)
                else:
                    target.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")

        _copy_tree(FIXTURES, submodule_dest)
        return repo_path

    def test_materialize_hub_and_runtimes_for_meta_pm(self, repo: Path):
        profile = _meta_profile()
        names = resolve_skill_names(repo / PRAYOG_SKILLS_SUBMODULE_REL, profile, "meta-pm")
        materialized = materialize_skill_tree(
            repo,
            prayog_submodule_rel=PRAYOG_SKILLS_SUBMODULE_REL,
            skill_names=names,
            runtime_roots=profile.skill_runtimes,
            lane_key="requirements_skills",
            community_submodule_dirs=[],
            apply=True,
        )
        assert materialized == names
        for name in names:
            assert hub_skill_present(repo, name)
            assert runtime_skill_present(repo, name, ".agents/skills")
            assert runtime_skill_present(repo, name, ".claude/skills")
        assert all_runtime_skills_present(repo, names, profile.skill_runtimes)

    def test_materialize_removes_stale_runtime_skill(self, repo: Path):
        stale = repo / ".agents" / "skills" / "pre-implement"
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("stale", encoding="utf-8")

        profile = _meta_profile()
        names = resolve_skill_names(repo / PRAYOG_SKILLS_SUBMODULE_REL, profile, "meta-pm")
        materialize_skill_tree(
            repo,
            prayog_submodule_rel=PRAYOG_SKILLS_SUBMODULE_REL,
            skill_names=names,
            runtime_roots=profile.skill_runtimes,
            lane_key="requirements_skills",
            community_submodule_dirs=[],
            apply=True,
        )
        assert not stale.exists()


class TestCommunitySkillTree:
    def test_community_hub_and_runtime_symlinks(self, tmp_path: Path):
        repo = tmp_path / "meta"
        community_root = repo / ".harness" / "community" / "awesome-copilot" / "skills" / "prd"
        community_root.mkdir(parents=True)
        (community_root / "SKILL.md").write_text("# prd", encoding="utf-8")

        assert materialize_community_skill_tree(
            repo,
            community_submodule_rel=".harness/community/awesome-copilot",
            skill_name="prd",
            runtime_roots=RUNTIMES,
            apply=True,
        )
        assert hub_skill_present(repo, "prd")
        assert runtime_skill_present(repo, "prd", ".agents/skills")
        assert (repo / HARNESS_SKILLS_HUB_REL / "prd").is_symlink()


class TestSlashList:
    def test_formats_slash_commands(self):
        assert slash_list(["verify", "pre-implement"]) == "`/verify`, `/pre-implement`"
