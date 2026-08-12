"""Tests for prayog skill resolution and harness hub symlink materialization."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from launchpad.commands.apply_harness import _verify_delivery_contract
from launchpad.harness.paths import HARNESS_SKILLS_HUB_REL, PRAYOG_SKILLS_SUBMODULE_REL
from launchpad.harness.skills_materialize import (
    _copy_prayog_references,
    _references_content_differs,
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
            "skills": [{"repo": "prayog-skills", "ref": "v0.4.3-rc.1"}],
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


class TestCopyPrayogReferences:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        repo_path = tmp_path / "demo-repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        submodule_root = repo_path / "prayog-skills"
        submodule_root.mkdir()
        (submodule_root / "delivery-contract.yaml").write_text(
            "id: sdd-delivery\nversion: 2\nworkflow: workflow.yaml\n",
            encoding="utf-8",
        )
        refs = submodule_root / "references"
        refs.mkdir()
        (refs / "checks.md").write_text("# checks", encoding="utf-8")
        (refs / "output-template.md").write_text("# template", encoding="utf-8")
        return repo_path

    def test_skips_when_no_references_dir(self, tmp_path: Path):
        repo = tmp_path / "no-refs"
        repo.mkdir()
        submodule_root = repo / "prayog-skills"
        submodule_root.mkdir()
        assert not _copy_prayog_references(repo, submodule_root, apply=True)

    def test_copies_references_on_apply(self, repo: Path):
        submodule_root = repo / "prayog-skills"
        assert _copy_prayog_references(repo, submodule_root, apply=True)
        assert (repo / "references").is_dir()
        assert (repo / "references" / "checks.md").is_file()
        assert (repo / "references" / "output-template.md").is_file()

    def test_dry_run_reports_new(self, repo: Path):
        submodule_root = repo / "prayog-kills"
        assert (repo / "references").exists() is False
        # dry-run when dest doesn't exist yet
        _copy_prayog_references(repo, submodule_root, apply=False)
        assert (repo / "references").exists() is False  # no apply

    def test_dry_run_reports_up_to_date(self, repo: Path):
        submodule_root = repo / "prayog-skills"
        _copy_prayog_references(repo, submodule_root, apply=True)
        # dry-run when already copied
        _copy_prayog_references(repo, submodule_root, apply=False)
        assert (repo / "references").is_dir()

    def test_content_hash_detects_stale_file(self, repo: Path):
        submodule_root = repo / "prayog-skills"
        _copy_prayog_references(repo, submodule_root, apply=True)
        # Staleness: update source file
        (submodule_root / "references" / "checks.md").write_text(
            "# updated checks", encoding="utf-8",
        )
        assert _references_content_differs(
            submodule_root / "references", repo / "references",
        )
        # Re-apply to fix
        _copy_prayog_references(repo, submodule_root, apply=True)
        assert not _references_content_differs(
            submodule_root / "references", repo / "references",
        )

    def test_content_hash_detects_added_file(self, repo: Path):
        submodule_root = repo / "prayog-skills"
        _copy_prayog_references(repo, submodule_root, apply=True)
        # Staleness: add new file to source
        (submodule_root / "references" / "id-conventions.md").write_text(
            "# conventions", encoding="utf-8",
        )
        assert _references_content_differs(
            submodule_root / "references", repo / "references",
        )

    def test_content_hash_no_diff_when_identical(self, repo: Path):
        submodule_root = repo / "prayog-skills"
        _copy_prayog_references(repo, submodule_root, apply=True)
        assert not _references_content_differs(
            submodule_root / "references", repo / "references",
        )

    def test_content_hash_returns_false_when_source_empty(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "old.md").write_text("old", encoding="utf-8")
        assert not _references_content_differs(src, dest)
