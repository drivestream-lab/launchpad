"""HarnessConfig schema — governance envelope per stack profile.

File: config/harness-<org>.yaml
Kind: HarnessConfig

A harness = an optional constitution (rules submodule) + optional agent skills +
            CODEOWNERS and harness-pin skeleton templates.

constitution is OPTIONAL — code repos (python-backend, nextjs-frontend) pin a
rules submodule; planning/config repos (meta-pm) typically have no MDC rules and
omit it.  apply-harness skips the submodule step when constitution is absent.

Fields
------
org             Must match programme.yaml org.
delivery_contract Optional expected Prayog delivery contract (e.g. sdd-delivery/v2).
delivery_roles Optional portable delivery role → tenant team slug mapping.
profiles        Map of stack name → HarnessProfile.
  constitution  Optional. Omit for repos that need no .cursor/rules submodule.
    repo        GitHub repo slug for rules (e.g. "python-services-rules").
    org         Optional override org; defaults to drivestream-lab.
    ref         Git ref (branch or tag, e.g. "v1.2.0").
  skills        List of agent skill repos (optional).
    repo        Skill repo slug.
    org         Optional override org.
    ref         Git ref.
  community_skills    Optional. External skill repos (e.g. awesome-copilot /prd on meta).
    source      GitHub org/repo slug.
    ref         Pinned tag or branch.
    skill       Skill directory name under source repo skills/.
  skill_runtimes      Optional. Agent runtime roots for flat skill symlinks.
                      Defaults to .agents/skills and .claude/skills.
  codeowners_template   Filename inside kit templates/ to seed as .github/CODEOWNERS.
                        Defaults to "CODEOWNERS.<profile-name>" (convention).
  harness_pin_template  Filename inside kit templates/ to seed as .harness-pin.yaml.
                        Defaults to "harness-pin.<profile-name>.yaml" (convention).
repos           Map of repo slug → harness_profile (stack override per-repo).
                If absent, harness_profile defaults to repo.stack from governance.

Identity equality: harness profile name == prayog profiles/{name}.yaml ==
pin profile / agent_skills.profile. No prayog_profile aliases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from launchpad.schema.errors import SchemaError

API_VERSION = "launchpad/v1"
KIND = "HarnessConfig"

_PLATFORM_ORG = "drivestream-lab"
_DEFAULT_SKILL_RUNTIMES = (".agents/skills", ".claude/skills")


class CommunitySkillRef:
    def __init__(self, raw: dict[str, Any], *, profile: str, idx: int, path: str = "") -> None:
        source = str(raw.get("source") or "").strip()
        if not source:
            raise SchemaError(
                f"profiles.{profile!r}.community_skills[{idx}] missing required field 'source'",
                path=path,
                hint="Use org/repo form, e.g. source: github/awesome-copilot",
            )
        if "/" not in source:
            raise SchemaError(
                f"profiles.{profile!r}.community_skills[{idx}].source must be org/repo",
                path=path,
            )
        self.source = source
        ref = str(raw.get("ref") or "").strip()
        if not ref:
            raise SchemaError(
                f"profiles.{profile!r}.community_skills[{idx}] missing required field 'ref'",
                path=path,
                hint="Pin to a tag, e.g. ref: v1.0.0",
            )
        self.ref = ref
        skill = str(raw.get("skill") or "").strip()
        if not skill:
            raise SchemaError(
                f"profiles.{profile!r}.community_skills[{idx}] missing required field 'skill'",
                path=path,
            )
        self.skill = skill

    @property
    def url(self) -> str:
        return f"https://github.com/{self.source}"

    @property
    def submodule_dir(self) -> str:
        return self.source.split("/", 1)[-1]

    @property
    def submodule_rel(self) -> str:
        return f".harness/community/{self.submodule_dir}"


class ConstitutionRef:
    def __init__(self, raw: dict[str, Any], *, profile: str, path: str = "") -> None:
        repo = str(raw.get("repo") or "").strip()
        if not repo:
            raise SchemaError(
                f"profiles.{profile!r}.constitution missing required field 'repo'",
                path=path,
            )
        configured_org = str(raw.get("org") or _PLATFORM_ORG).strip()
        if "/" in repo:
            repo_org, repo_name = repo.split("/", 1)
            if repo_org:
                configured_org = repo_org
            repo = repo_name
        self.repo = repo
        self.org = configured_org
        ref = str(raw.get("ref") or "").strip()
        if not ref:
            raise SchemaError(
                f"profiles.{profile!r}.constitution missing required field 'ref'",
                path=path,
                hint="Pin to a tag or branch, e.g. ref: v1.2.0",
            )
        self.ref = ref

    @property
    def submodule_url(self) -> str:
        return f"https://github.com/{self.org}/{self.repo}"


class SkillRef:
    def __init__(self, raw: dict[str, Any], *, profile: str, idx: int, path: str = "") -> None:
        repo = str(raw.get("repo") or "").strip()
        if not repo:
            raise SchemaError(
                f"profiles.{profile!r}.skills[{idx}] missing required field 'repo'",
                path=path,
            )
        self.repo = repo
        self.org = str(raw.get("org") or _PLATFORM_ORG).strip()
        self.ref = str(raw.get("ref") or "").strip()


class HarnessProfile:
    def __init__(self, name: str, raw: dict[str, Any], *, path: str = "") -> None:
        self.name = name

        # constitution is optional — omit for repos that need no .cursor/rules submodule.
        # Code repos (python-backend, nextjs-frontend) set it; meta/config repos typically don't.
        constitution_raw = raw.get("constitution")
        if constitution_raw is not None and not isinstance(constitution_raw, dict):
            raise SchemaError(
                f"profiles.{name!r}.constitution must be a mapping (or omitted entirely)",
                path=path,
            )
        self.constitution: ConstitutionRef | None = (
            ConstitutionRef(constitution_raw, profile=name, path=path)
            if constitution_raw
            else None
        )

        skills_raw = raw.get("skills") or []
        if not isinstance(skills_raw, list):
            raise SchemaError(f"profiles.{name!r}.skills must be a list", path=path)
        self.skills: list[SkillRef] = [
            SkillRef(s, profile=name, idx=i, path=path) for i, s in enumerate(skills_raw)
        ]

        if "prayog_profile" in raw:
            raise SchemaError(
                f"profiles.{name!r}: prayog_profile is not supported — "
                f"use identity equality (profiles/{name}.yaml)",
                path=path,
                hint="Remove prayog_profile and rename the prayog file to match the stack key",
            )

        community_raw = raw.get("community_skills") or []
        if not isinstance(community_raw, list):
            raise SchemaError(f"profiles.{name!r}.community_skills must be a list", path=path)
        self.community_skills: list[CommunitySkillRef] = [
            CommunitySkillRef(c, profile=name, idx=i, path=path) for i, c in enumerate(community_raw)
        ]

        runtimes_raw = raw.get("skill_runtimes")
        if runtimes_raw is None:
            self.skill_runtimes: list[str] = list(_DEFAULT_SKILL_RUNTIMES)
        elif not isinstance(runtimes_raw, list):
            raise SchemaError(f"profiles.{name!r}.skill_runtimes must be a list", path=path)
        else:
            runtimes = [str(r).strip() for r in runtimes_raw if str(r).strip()]
            if not runtimes:
                raise SchemaError(
                    f"profiles.{name!r}.skill_runtimes must not be empty when set",
                    path=path,
                )
            self.skill_runtimes = runtimes

        # Template filenames in kit templates/ — default to convention if not set.
        # Convention: CODEOWNERS.<name>  and  harness-pin.<name>.yaml
        self.codeowners_template: str = (
            str(raw.get("codeowners_template") or "").strip()
            or f"CODEOWNERS.{name}"
        )
        self.harness_pin_template: str = (
            str(raw.get("harness_pin_template") or "").strip()
            or f"harness-pin.{name}.yaml"
        )


class HarnessSchema:
    """Validated, normalised representation of harness-<org>.yaml."""

    def __init__(self, raw: dict[str, Any], *, path: str = "") -> None:
        self._path = path
        self.org: str = ""
        self.delivery_contract: str = ""
        self.delivery_roles: dict[str, str] = {}
        self.profiles: dict[str, HarnessProfile] = {}
        self.repos: dict[str, str] = {}
        self._validate(raw)

    def _validate(self, raw: dict[str, Any]) -> None:
        p = self._path

        org = str(raw.get("org") or "").strip()
        if not org:
            raise SchemaError(
                "harness YAML missing required field 'org'",
                path=p,
                hint="Set org: to match your programme.yaml org",
            )
        self.org = org

        self.delivery_contract = str(raw.get("delivery_contract") or "").strip()
        roles_raw = raw.get("delivery_roles") or {}
        if not isinstance(roles_raw, dict):
            raise SchemaError("delivery_roles must be a mapping", path=p)
        self.delivery_roles = {
            str(role).strip(): str(team).strip()
            for role, team in roles_raw.items()
            if str(role).strip() and str(team).strip()
        }

        profiles_raw = raw.get("profiles") or {}
        if not isinstance(profiles_raw, dict):
            raise SchemaError("'profiles' must be a mapping", path=p)
        for pname, pdata in profiles_raw.items():
            if not isinstance(pdata, dict):
                raise SchemaError(f"profiles.{pname!r} must be a mapping", path=p)
            self.profiles[pname] = HarnessProfile(pname, pdata, path=p)

        repos_raw = raw.get("repos") or {}
        if not isinstance(repos_raw, dict):
            raise SchemaError("'repos' must be a mapping", path=p)
        for repo_name, harness_profile in repos_raw.items():
            if harness_profile and harness_profile not in self.profiles:
                raise SchemaError(
                    f"repos.{repo_name!r} references unknown profile {harness_profile!r}",
                    path=p,
                    hint=f"Add profile {harness_profile!r} to profiles: or use one of: {sorted(self.profiles)}",
                )
            self.repos[repo_name] = str(harness_profile or "")

    def resolve_profile(self, repo_name: str, stack: str) -> str | None:
        """Return the harness profile for a repo, defaulting to its stack."""
        if repo_name in self.repos:
            return self.repos[repo_name] or stack
        return stack if stack in self.profiles else None


def load_harness(path: str | Path) -> HarnessSchema:
    """Load and validate a harness-<org>.yaml from *path*."""
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise SchemaError(f"Harness YAML not found: {p}")
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise SchemaError(f"Harness YAML must be a YAML mapping: {p}")
    return HarnessSchema(raw, path=str(p))

