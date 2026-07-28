"""Resolve prayog skill names from a pinned submodule checkout."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from launchpad.harness.paths import HARNESS_PROFILE_REL, PM_HARNESS_PROFILE
from launchpad.schema.harness import HarnessProfile

_SKILL_LIST_KEYS = {
    PM_HARNESS_PROFILE: "requirements_skills",
}

FORGE_SKILLS_KEY = "forge_skills"

_FORGE_SKILL_NAMES = (
    "commit-workspace",
    "open-draft-pr",
    "create-board-tickets",
)


class HarnessResolveError(Exception):
    """Prayog profile or skill list could not be resolved at the pinned ref."""


def load_delivery_contract(submodule_root: Path) -> dict:
    """Load and minimally validate the pinned Prayog delivery contract."""
    contract_path = submodule_root / "delivery-contract.yaml"
    workflow_path = submodule_root / "workflow.yaml"
    if not contract_path.is_file():
        raise HarnessResolveError(
            "pinned prayog-skills has no delivery-contract.yaml; "
            "bump skills[].ref to a GitHub release that ships the contract, "
            "or omit delivery_contract for a legacy pin"
        )
    if not workflow_path.is_file():
        raise HarnessResolveError(
            "pinned prayog-skills has no workflow.yaml required by its delivery contract"
        )
    raw = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise HarnessResolveError("delivery-contract.yaml must be a mapping")
    contract_id = str(raw.get("id") or "").strip()
    version = raw.get("version")
    if not contract_id or version in (None, ""):
        raise HarnessResolveError(
            "delivery-contract.yaml must define non-empty id and version"
        )
    declared_workflow = str(raw.get("workflow") or "").strip()
    if declared_workflow and declared_workflow != "workflow.yaml":
        if not (submodule_root / declared_workflow).is_file():
            raise HarnessResolveError(
                f"delivery contract workflow not found: {declared_workflow}"
            )
    return raw


def resolve_delivery_contract(submodule_root: Path) -> str:
    """Return ``id/vN`` from the pinned Prayog delivery contract."""
    raw = load_delivery_contract(submodule_root)
    contract_id = str(raw["id"]).strip()
    version = raw["version"]
    return f"{contract_id}/v{version}"


def _profile_matches(profile_name: str, profiles: list[str]) -> bool:
    """Match harness profile against contract profile list.

    Token ``app`` means any non-meta-pm delivery repo (stack-agnostic).
    """
    if not profiles:
        return True
    if profile_name in profiles:
        return True
    if "app" in profiles and profile_name != PM_HARNESS_PROFILE:
        return True
    return False


def resolve_gate_resources(
    submodule_root: Path,
    profile_name: str,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Return profile-scoped labels and portable review-role requirements."""
    raw = load_delivery_contract(submodule_root)
    github = raw.get("github") or {}
    if not isinstance(github, dict):
        raise HarnessResolveError("delivery contract github section must be a mapping")

    labels: list[dict[str, str]] = []
    for entry in github.get("labels") or []:
        if not isinstance(entry, dict):
            raise HarnessResolveError("delivery contract labels must be mappings")
        profiles = [str(p) for p in (entry.get("profiles") or [])]
        if profiles and not _profile_matches(profile_name, profiles):
            continue
        name = str(entry.get("name") or "").strip()
        color = str(entry.get("color") or "").strip().lstrip("#")
        description = str(entry.get("description") or "").strip()
        if not name or not color:
            raise HarnessResolveError("delivery label requires name and color")
        labels.append(
            {"name": name, "color": color, "description": description}
        )

    roles: dict[str, str] = {}
    for gate, entry in (github.get("review_roles") or {}).items():
        if not isinstance(entry, dict):
            raise HarnessResolveError("review role entries must be mappings")
        profiles = [str(p) for p in (entry.get("profiles") or [])]
        if profiles and not _profile_matches(profile_name, profiles):
            continue
        role = str(entry.get("role") or "").strip()
        if role:
            roles[str(gate)] = role
    return labels, roles


def skill_list_key(harness_profile_name: str) -> str:
    return _SKILL_LIST_KEYS.get(harness_profile_name, "development_skills")


def _parse_skill_list_block(text: str, key: str) -> list[str]:
    pattern = re.compile(rf"^{re.escape(key)}:\s*\n((?:[ \t]*-[ \t]*\S+[ \t]*\n?)+)", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return []
    return re.findall(r"-\s*(\S+)", match.group(1))


def parse_forge_skill_names(profile_path: Path) -> list[str]:
    """Return forge_skills names from a prayog profile YAML path."""
    return _parse_skill_list_block(profile_path.read_text(encoding="utf-8"), FORGE_SKILLS_KEY)


def resolve_skill_names(
    submodule_root: Path,
    profile: HarnessProfile,
    harness_profile_name: str,
) -> list[str]:
    """Return lane + forge skill directory names from prayog profiles/{prayog_profile}.yaml.

    Order is stable: lane skills first, then forge_skills (deduped, first wins).
    ``forge_skills`` must be present and non-empty at the pinned ref.
    """
    profile_file = profile.prayog_profile
    profile_path = submodule_root / "profiles" / f"{profile_file}.yaml"
    if not profile_path.is_file():
        hint = (
            f"Add profiles/{profile_file}.yaml in prayog-skills and bump skills[].ref, "
            f"or set prayog_profile: <existing-profile> in harness YAML "
            f"(e.g. python-backend for IaC until terraform-iac ships)."
        )
        raise HarnessResolveError(
            f"prayog profile not found: profiles/{profile_file}.yaml "
            f"in pinned prayog-skills submodule. {hint}"
        )

    text = profile_path.read_text(encoding="utf-8")
    key = skill_list_key(harness_profile_name)
    lane_names = _parse_skill_list_block(text, key)
    if not lane_names:
        raise HarnessResolveError(
            f"profiles/{profile_file}.yaml has no {key} list at the pinned prayog ref. "
            f"Update prayog-skills or bump the harness skills ref."
        )

    forge_names = _parse_skill_list_block(text, FORGE_SKILLS_KEY)
    if not forge_names:
        raise HarnessResolveError(
            f"profiles/{profile_file}.yaml has no {FORGE_SKILLS_KEY} list at the pinned "
            f"prayog ref. Add a non-empty {FORGE_SKILLS_KEY} block "
            f"(e.g. {', '.join(_FORGE_SKILL_NAMES)}) and bump the harness skills ref."
        )

    seen: set[str] = set()
    names: list[str] = []
    for name in lane_names + forge_names:
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def find_skill_source_dir(submodule_root: Path, skill_name: str, *, lane_key: str) -> Path | None:
    """Locate skills/{requirements|development|forge}/{name} inside prayog-skills.

    Search order: lane bucket (requirements or development from ``lane_key``), then forge.
    """
    bucket = "requirements" if lane_key == "requirements_skills" else "development"
    for area in (bucket, "forge"):
        candidate = submodule_root / "skills" / area / skill_name
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None


def copy_harness_profile(
    submodule_root: Path,
    profile: HarnessProfile,
    dest: Path,
    *,
    harness_profile_name: str,
    apply: bool,
) -> bool:
    """Copy prayog profiles/{profile}.yaml → consumer .harness/profile.yaml (app repos)."""
    if harness_profile_name == PM_HARNESS_PROFILE:
        return False

    profile_file = profile.prayog_profile
    src = submodule_root / "profiles" / f"{profile_file}.yaml"
    if not src.is_file():
        return False

    if not apply:
        print(
            f"    [dry-run] harness profile  ← profiles/{profile_file}.yaml  "
            f"→  {HARNESS_PROFILE_REL}"
        )
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  ✔  harness profile  ← profiles/{profile_file}.yaml")
    return True


def slash_list(skill_names: list[str]) -> str:
    return ", ".join(f"`/{name}`" for name in skill_names)
