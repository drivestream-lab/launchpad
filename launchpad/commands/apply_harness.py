"""apply-harness — pin constitution + skills submodules per stack.

Reads harness-<org>.yaml + governance-<org>.yaml.
harness_profile resolves as: repos.<name> override → repo.stack from governance.

Usage:
  launchpad apply-harness --meta [--apply]
  launchpad apply-harness --repo <name> [--apply]
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from launchpad.harness.community_skills import community_skill_names, install_community_skills
from launchpad.harness.paths import (
    HARNESS_PROFILE_REL,
    PM_HARNESS_PROFILE,
    PRAYOG_SKILLS_SUBMODULE_REL,
)
from launchpad.harness.skills_materialize import lane_key_for_profile, materialize_skill_tree
from launchpad.harness.skills_ref import SkillsRefResolveError, resolve_skills_ref
from launchpad.harness.skills_resolve import (
    HarnessResolveError,
    copy_harness_profile,
    resolve_delivery_contract,
    resolve_skill_names,
    slash_list,
)
from launchpad.harness.submodules import pin_submodule
from launchpad.clients import ClientRegistryError, resolve_programme_workspace
from launchpad.programme.board_binding import resolve_board_binding
from launchpad.schema import SchemaError
from launchpad.schema.harness import HarnessProfile, load_harness
from launchpad.schema.governance import load_governance
from launchpad.ui import print_next_box

_TEMPLATE_ORG_PLACEHOLDER = "example-org"


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def _kit_templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def _resolve_kit_template(filename: str) -> Path | None:
    path = _kit_templates_dir() / filename
    return path if path.is_file() else None


def _community_skills_yaml_block(profile: HarnessProfile) -> str:
    if not profile.community_skills:
        return "community_skills: []"
    lines = ["community_skills:"]
    for spec in profile.community_skills:
        lines.append(f"  - source: {spec.source}")
        lines.append(f"    ref: {spec.ref}")
        lines.append(f"    skill: {spec.skill}")
    return "\n".join(lines)


def _seed_codeowners(repo_path: Path, tpl_name: str, org: str, *, apply: bool) -> None:
    tpl_path = _resolve_kit_template(tpl_name)
    if tpl_path is None:
        print(f"  WARN: CODEOWNERS template '{tpl_name}' not found in kit templates/ — skipping")
        return

    dest = repo_path / ".github" / "CODEOWNERS"
    if not apply:
        print(f"    [dry-run] CODEOWNERS  ← {tpl_name}  →  .github/CODEOWNERS")
        print(f"              (replace '{_TEMPLATE_ORG_PLACEHOLDER}' → '{org}')")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    content = tpl_path.read_text(encoding="utf-8").replace(_TEMPLATE_ORG_PLACEHOLDER, org)
    dest.write_text(content, encoding="utf-8")
    print(f"  ✔  CODEOWNERS  ← {tpl_name}  (org: {org})")


def _resolve_profile_skill_refs(
    profile: HarnessProfile,
) -> list[tuple[Any, str]]:
    """Return (skill, concrete_ref) pairs; expands floating ``latest``."""
    resolved: list[tuple[Any, str]] = []
    for skill in profile.skills:
        concrete = resolve_skills_ref(skill.org, skill.repo, skill.ref or "HEAD")
        resolved.append((skill, concrete))
    return resolved


def _seed_harness_pin(
    repo_path: Path,
    tpl_name: str,
    profile: HarnessProfile,
    profile_name: str,
    skill_names: list[str],
    delivery_contract: str,
    *,
    apply: bool,
    agent_skills_ref: str = "",
) -> None:
    tpl_path = _resolve_kit_template(tpl_name)
    if tpl_path is None:
        print(f"  WARN: harness-pin template '{tpl_name}' not found in kit templates/ — skipping")
        return

    if not apply:
        print(f"    [dry-run] harness-pin ← {tpl_name}  →  .harness-pin.yaml")
        return

    dest = repo_path / ".harness-pin.yaml"
    con = profile.constitution
    skill = profile.skills[0] if profile.skills else None
    skills_block = "\n".join(f"    - {name}" for name in skill_names)

    content = tpl_path.read_text(encoding="utf-8")
    content = content.replace("{{DELIVERY_CONTRACT}}", delivery_contract)
    if con:
        content = content.replace("{{RULES_REF}}", con.ref)
        for rules_repo in (
            "python-services-rules",
            "nextjs-bff-rules",
            "terraform-infra-rules",
            "data-platform-rules",
        ):
            content = content.replace(f"repo: drivestream-lab/{rules_repo}", f"repo: {con.org}/{con.repo}")

    if skill:
        pin_ref = agent_skills_ref or skill.ref or "HEAD"
        content = content.replace("{{AGENT_SKILLS_REF}}", pin_ref)
        content = content.replace(
            "repo: drivestream-lab/prayog-skills",
            f"repo: {skill.org}/{skill.repo}",
        )
    content = content.replace("{{AGENT_SKILLS_LIST}}", skills_block)

    community_block = _community_skills_yaml_block(profile)
    if "community_skills:" in content:
        content = re.sub(
            r"community_skills:\n(?:[ \t]+-[^\n]*\n(?:[ \t]+[^\n]*\n)*)*",
            community_block + "\n",
            content,
            count=1,
        )

    dest.write_text(content, encoding="utf-8")
    print(f"  ✔  harness-pin synced ← {tpl_name}  (profile: {profile_name})")


def _fill_agents_placeholders(
    content: str,
    *,
    profile_name: str,
    profile: HarnessProfile,
    skill_names: list[str],
    delivery_contract: str,
    target: str,
    org: str,
    meta_repo: str,
    board_name: str,
    board_url: str,
    agent_skills_ref: str = "",
) -> str:
    con = profile.constitution
    skill = profile.skills[0] if profile.skills else None
    filled = content
    filled = filled.replace("{{DISPLAY_NAME}}", org)
    filled = filled.replace("{{ORG}}", org)
    filled = filled.replace("{{META_REPO}}", meta_repo)
    filled = filled.replace("{{SERVICE_NAME}}", target)
    filled = filled.replace("{{PROFILE}}", profile_name)
    filled = filled.replace("{{RULES_PIN}}", con.ref if con else "")
    skills_ref = agent_skills_ref or (skill.ref if skill else "")
    filled = filled.replace("{{AGENT_SKILLS_REF}}", skills_ref)
    filled = filled.replace("{{DELIVERY_CONTRACT}}", delivery_contract)
    filled = filled.replace("{{BOARD_NAME}}", board_name or "Engineering board")
    filled = filled.replace(
        "{{BOARD_URL}}", board_url or f"https://github.com/orgs/{org}/projects"
    )
    filled = filled.replace("{{AGENT_SKILLS_SLASH_LIST}}", slash_list(skill_names))
    filled = filled.replace("{{CHECK_COMMAND}}", "")
    filled = filled.replace("{{TEST_COMMAND}}", "")
    filled = filled.replace("{{VERIFY_SMOKE}}", "")
    filled = filled.replace("{{SETUP_NOTES}}", "")
    return filled


_HARNESS_BLOCK_START = "<!-- launchpad:harness-start -->"
_HARNESS_BLOCK_END = "<!-- launchpad:harness-end -->"
_HARNESS_BLOCK_RE = re.compile(
    re.escape(_HARNESS_BLOCK_START) + r".*?" + re.escape(_HARNESS_BLOCK_END),
    re.DOTALL,
)


def _harness_block_present(text: str) -> bool:
    return bool(_HARNESS_BLOCK_RE.search(text))


def _extract_harness_block(text: str) -> str | None:
    match = _HARNESS_BLOCK_RE.search(text)
    return match.group(0) if match else None


def _replace_harness_block(text: str, new_block: str) -> str:
    if not _HARNESS_BLOCK_RE.search(text):
        raise ValueError("AGENTS.md has no launchpad harness markers")
    return _HARNESS_BLOCK_RE.sub(new_block.strip(), text, count=1)


def _insert_harness_block(text: str, block: str) -> str:
    """Insert managed harness block after the first H1 (or at file start)."""
    block = block.strip() + "\n\n"
    match = re.search(r"^# .+$", text, re.MULTILINE)
    if match is None:
        return block + text.lstrip()
    insert_at = match.end()
    # skip a single blank line after the title if present
    if insert_at < len(text) and text[insert_at] == "\n":
        insert_at += 1
    return text[:insert_at] + "\n" + block + text[insert_at:].lstrip("\n")


# Unmarked AGENTS.md: strip known factory prose before inserting the managed block
# so legacy kit files do not keep duplicate Shared-rules / Delivery / Board sections.
_FACTORY_SECTION_RES: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^## Harness\b.*?(?=^## |\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"^### Delivery bootstrap\b.*?(?=^#{1,3} |\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"^### Programme board\b.*?(?=^#{1,3} |\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
)

_FACTORY_LINE_RE = re.compile(
    r"^(?:"
    r"Shared rules:"
    r"|Agent skills:"
    r"|Prayog PM bundle"
    r"|Installed under \*\*`"
    r"|Pin record:"
    r"|Re-sync after clone:"
    r"|\*\*Do not edit\*\* `\.\s*cursor/rules"
    r"|Skill changes go upstream"
    r"|Community: `/prd`"
    r")",
    re.IGNORECASE,
)


def _strip_factory_owned_agents_prose(text: str) -> str:
    """Remove unmarked factory-owned chunks; leave team sections intact."""
    updated = text
    for pattern in _FACTORY_SECTION_RES:
        updated = pattern.sub("", updated)

    kept: list[str] = []
    for line in updated.splitlines(keepends=True):
        stripped = line.lstrip()
        if _FACTORY_LINE_RE.match(stripped):
            continue
        if ".agents/skills/prayog-skills/" in line:
            # Stale nested path lines from pre-v0.5.20 kit templates
            continue
        kept.append(line)

    # Collapse runs of blank lines left by stripped sections
    cleaned = "".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + ("\n" if cleaned.strip() else "")


def _prepare_unmarked_agents_for_insert(text: str, block: str) -> str:
    """Insert managed harness block into unmarked AGENTS.md without duplicating factory prose."""
    prepared = _strip_factory_owned_agents_prose(text)
    return _insert_harness_block(prepared, block)


def _render_agents_document(
    tpl_path: Path,
    *,
    profile_name: str,
    profile: HarnessProfile,
    skill_names: list[str],
    delivery_contract: str,
    target: str,
    org: str,
    meta_repo: str,
    board_name: str,
    board_url: str,
    agent_skills_ref: str = "",
) -> str:
    return _fill_agents_placeholders(
        tpl_path.read_text(encoding="utf-8"),
        profile_name=profile_name,
        profile=profile,
        skill_names=skill_names,
        delivery_contract=delivery_contract,
        target=target,
        org=org,
        meta_repo=meta_repo,
        board_name=board_name,
        board_url=board_url,
        agent_skills_ref=agent_skills_ref,
    )


def _render_harness_block(
    tpl_path: Path,
    *,
    profile_name: str,
    profile: HarnessProfile,
    skill_names: list[str],
    delivery_contract: str,
    target: str,
    org: str,
    meta_repo: str,
    board_name: str,
    board_url: str,
    agent_skills_ref: str = "",
) -> str:
    rendered = _render_agents_document(
        tpl_path,
        profile_name=profile_name,
        profile=profile,
        skill_names=skill_names,
        delivery_contract=delivery_contract,
        target=target,
        org=org,
        meta_repo=meta_repo,
        board_name=board_name,
        board_url=board_url,
        agent_skills_ref=agent_skills_ref,
    )
    block = _extract_harness_block(rendered)
    if block is None:
        raise ValueError(
            f"kit template {tpl_path.name} is missing "
            f"{_HARNESS_BLOCK_START} / {_HARNESS_BLOCK_END} markers"
        )
    return block


def _seed_agents_md(
    repo_path: Path,
    profile_name: str,
    profile: HarnessProfile,
    skill_names: list[str],
    delivery_contract: str,
    *,
    target: str,
    org: str,
    meta_repo: str,
    board_name: str,
    board_url: str,
    apply: bool,
    agent_skills_ref: str = "",
) -> None:
    """Seed or refresh AGENTS.md using a launchpad-owned harness marker block.

    Ownership contract:
    - Between ``<!-- launchpad:harness-start -->`` / ``end`` → factory regenerates
    - Outside markers → team-owned; never overwritten by apply-harness
    - Existing file without markers → strip stale factory prose, insert marked block
    """
    is_meta = profile_name == PM_HARNESS_PROFILE
    tpl_name = "AGENTS.meta.md" if is_meta else "AGENTS.md"
    tpl_path = _resolve_kit_template(tpl_name)
    if tpl_path is None:
        return

    dest = repo_path / "AGENTS.md"
    render_kwargs = dict(
        profile_name=profile_name,
        profile=profile,
        skill_names=skill_names,
        delivery_contract=delivery_contract,
        target=target,
        org=org,
        meta_repo=meta_repo,
        board_name=board_name,
        board_url=board_url,
        agent_skills_ref=agent_skills_ref,
    )

    if not apply:
        if not dest.is_file():
            print(f"    [dry-run] AGENTS.md  (seed from {tpl_name})")
        elif _harness_block_present(dest.read_text(encoding="utf-8")):
            print("    [dry-run] AGENTS.md  (refresh launchpad harness block)")
        else:
            print(
                "    [dry-run] AGENTS.md  "
                "(insert launchpad harness block; keep team sections)"
            )
        return

    if not dest.is_file():
        dest.write_text(_render_agents_document(tpl_path, **render_kwargs), encoding="utf-8")
        print(f"  ✔  AGENTS.md  ← {tpl_name}")
        return

    original = dest.read_text(encoding="utf-8")
    try:
        new_block = _render_harness_block(tpl_path, **render_kwargs)
    except ValueError as exc:
        print(f"  WARN: {exc} — leaving AGENTS.md unchanged", file=sys.stderr)
        return

    if _harness_block_present(original):
        updated = _replace_harness_block(original, new_block)
        if updated == original:
            print("  –  AGENTS.md  (harness block already current)")
        else:
            dest.write_text(updated, encoding="utf-8")
            print("  ✔  AGENTS.md  (refreshed launchpad harness block)")
        return

    updated = _prepare_unmarked_agents_for_insert(original, new_block)
    dest.write_text(updated, encoding="utf-8")
    print("  ✔  AGENTS.md  (inserted launchpad harness block — team content kept)")


_HARNESS_GITIGNORE_MARKER = "# launchpad harness — skill symlinks (apply-harness)"
_LEGACY_AGENTS_GITIGNORE = ".agents/skills/*/"
_LEGACY_CLAUDE_GITIGNORE = ".claude/skills/"


def _harness_gitignore_block() -> str | None:
    tpl_path = _resolve_kit_template("gitignore.harness")
    if tpl_path is None:
        return None
    return tpl_path.read_text(encoding="utf-8").rstrip() + "\n"


def _upgrade_harness_gitignore_patterns(text: str) -> str:
    """Fix pre-v0.5.17 trailing-slash patterns that miss symlink entries."""
    updated = text.replace(_LEGACY_AGENTS_GITIGNORE, ".agents/skills/*")
    if ".claude/skills/*" not in updated:
        updated = updated.replace(_LEGACY_CLAUDE_GITIGNORE, ".claude/skills/*")
    return updated


_DELIVERY_WORKFLOW_TEMPLATES: tuple[str, ...] = (
    "github/workflows/ci.yml",
    "github/workflows/policy-branch-name.yml",
    "github/workflows/board-seed-gate.yml",
)


def _seed_delivery_workflows(
    repo_path: Path,
    *,
    delivery_contract: str,
    profile_name: str,
    apply: bool,
) -> None:
    """Seed SDD delivery GitHub workflows into app repos (skip meta-pm)."""
    if profile_name == PM_HARNESS_PROFILE or not delivery_contract:
        return

    for kit_rel in _DELIVERY_WORKFLOW_TEMPLATES:
        tpl_path = _resolve_kit_template(kit_rel)
        workflow_name = Path(kit_rel).name
        dest = repo_path / ".github" / "workflows" / workflow_name

        if tpl_path is None:
            print(
                f"  WARN: workflow template '{kit_rel}' not found in kit — skipping",
                file=sys.stderr,
            )
            continue

        if not apply:
            if dest.is_file():
                print(f"    [dry-run] skip (exists)  .github/workflows/{workflow_name}")
            else:
                print(
                    f"    [dry-run] .github/workflows/{workflow_name}  ← {kit_rel}"
                )
            continue

        if dest.is_file():
            print(f"  –  skip (exists)  .github/workflows/{workflow_name}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tpl_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  ✔  workflow  ← {kit_rel}  →  .github/workflows/{workflow_name}")


def _seed_gitignore_harness(repo_path: Path, *, apply: bool) -> None:
    block = _harness_gitignore_block()
    if block is None:
        print("  WARN: gitignore.harness template not found in kit templates/ — skipping")
        return

    dest = repo_path / ".gitignore"

    if not apply:
        if dest.is_file() and _HARNESS_GITIGNORE_MARKER in dest.read_text(encoding="utf-8"):
            print("    [dry-run] .gitignore  (harness block present)")
        else:
            print("    [dry-run] .gitignore  ← gitignore.harness")
        return

    if dest.is_file():
        text = dest.read_text(encoding="utf-8")
        if _HARNESS_GITIGNORE_MARKER in text:
            upgraded = _upgrade_harness_gitignore_patterns(text)
            if upgraded != text:
                dest.write_text(upgraded, encoding="utf-8")
                print("  ✔  .gitignore  (upgraded harness symlink patterns)")
            return
        if ".harness/skills/" in text and _LEGACY_AGENTS_GITIGNORE in text:
            dest.write_text(_upgrade_harness_gitignore_patterns(text), encoding="utf-8")
            print("  ✔  .gitignore  (upgraded harness symlink patterns)")
            return
        prefix = "" if text.endswith("\n") else "\n"
        dest.write_text(text + prefix + "\n" + block, encoding="utf-8")
        print("  ✔  .gitignore  ← appended harness block")
    else:
        dest.write_text(block, encoding="utf-8")
        print("  ✔  .gitignore  ← gitignore.harness")


def _remove_legacy_cursor_skills(repo_path: Path, *, apply: bool) -> None:
    legacy_rel = ".cursor/skills"
    legacy = repo_path / ".cursor" / "skills"
    gitmodules = repo_path / ".gitmodules"
    in_gitmodules = gitmodules.is_file() and legacy_rel in gitmodules.read_text()

    if not in_gitmodules and not legacy.is_dir():
        return

    if not apply:
        print(f"    [dry-run] remove legacy {legacy_rel} submodule")
        return

    if in_gitmodules:
        subprocess.run(
            ["git", "submodule", "deinit", "-f", legacy_rel],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "rm", "-rf", legacy_rel],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
    if legacy.is_dir():
        shutil.rmtree(legacy, ignore_errors=True)
    print(f"  ✔  removed legacy {legacy_rel}")


def _preview_or_resolve_skills(
    prayog_submodule: Path,
    profile: HarnessProfile,
    profile_name: str,
) -> list[str] | None:
    if not prayog_submodule.is_dir():
        print(
            f"    [dry-run] prayog skills: resolve from profiles/{profile.prayog_profile}.yaml "
            f"after submodule pin"
        )
        return None
    return resolve_skill_names(prayog_submodule, profile, profile_name)


def _verify_delivery_contract(prayog_submodule: Path, expected: str) -> str:
    """Resolve and compare the pinned Prayog workflow contract."""
    if not expected:
        return ""
    actual = resolve_delivery_contract(prayog_submodule)
    if actual != expected:
        raise HarnessResolveError(
            f"delivery contract mismatch: harness expects {expected!r}, "
            f"pinned prayog-skills provides {actual!r}"
        )
    return actual


def _apply_harness_to_repo(
    repo_path: Path,
    profile: HarnessProfile,
    profile_name: str,
    org: str,
    delivery_contract: str,
    *,
    target: str,
    meta_repo: str,
    board_name: str = "",
    board_url: str = "",
    apply: bool = False,
) -> int:
    prayog_submodule = repo_path / PRAYOG_SKILLS_SUBMODULE_REL
    skill_names: list[str] = []
    community_dirs = [spec.submodule_dir for spec in profile.community_skills]
    lane_key = lane_key_for_profile(profile_name)

    try:
        skill_pins = _resolve_profile_skill_refs(profile)
    except SkillsRefResolveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    agent_skills_ref = skill_pins[0][1] if skill_pins else ""

    if not apply:
        con = profile.constitution
        if con:
            print(f"    [dry-run] constitution submodule: {con.submodule_url}@{con.ref}")
        else:
            print("    [dry-run] constitution: (none — no .cursor/rules submodule for this profile)")
        for skill, concrete_ref in skill_pins:
            skill_url = f"https://github.com/{skill.org}/{skill.repo}"
            declared = skill.ref or "HEAD"
            suffix = (
                f"  (latest → {concrete_ref})"
                if declared.lower() == "latest"
                else ""
            )
            print(
                f"    [dry-run] skills submodule: {PRAYOG_SKILLS_SUBMODULE_REL} "
                f"← {skill_url}@{concrete_ref}{suffix}"
            )
        install_community_skills(repo_path, profile, apply=False)
        preview = _preview_or_resolve_skills(prayog_submodule, profile, profile_name)
        if prayog_submodule.is_dir() and delivery_contract:
            try:
                actual_contract = _verify_delivery_contract(
                    prayog_submodule, delivery_contract
                )
                print(f"    [dry-run] delivery contract: {actual_contract}")
            except HarnessResolveError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
        preview_names = (preview or []) + community_skill_names(profile)
        if preview is not None:
            materialize_skill_tree(
                repo_path,
                prayog_submodule_rel=PRAYOG_SKILLS_SUBMODULE_REL,
                skill_names=preview,
                runtime_roots=profile.skill_runtimes,
                lane_key=lane_key,
                community_submodule_dirs=community_dirs,
                apply=False,
            )
        copy_harness_profile(
            prayog_submodule,
            profile,
            repo_path / HARNESS_PROFILE_REL,
            harness_profile_name=profile_name,
            apply=False,
        )
        _seed_codeowners(repo_path, profile.codeowners_template, org, apply=False)
        _seed_harness_pin(
            repo_path,
            profile.harness_pin_template,
            profile,
            profile_name,
            skill_names=preview_names,
            delivery_contract=delivery_contract,
            apply=False,
            agent_skills_ref=agent_skills_ref,
        )
        _seed_agents_md(
            repo_path,
            profile_name,
            profile,
            skill_names=preview_names,
            delivery_contract=delivery_contract,
            target=target,
            org=org,
            meta_repo=meta_repo,
            board_name=board_name,
            board_url=board_url,
            apply=False,
            agent_skills_ref=agent_skills_ref,
        )
        _seed_gitignore_harness(repo_path, apply=False)
        _seed_delivery_workflows(
            repo_path,
            delivery_contract=delivery_contract,
            profile_name=profile_name,
            apply=False,
        )
        return 0

    con = profile.constitution
    if con:
        if pin_submodule(
            repo_path,
            ".cursor/rules",
            con.submodule_url,
            con.ref,
            label="constitution",
        ):
            print(f"  ✔  constitution pinned: {con.repo}@{con.ref}")
        else:
            print(f"  ✗  constitution pin failed: {con.submodule_url}@{con.ref}", file=sys.stderr)
            return 1
    else:
        print("  –  constitution: (none — meta/config repo, no rules submodule)")

    _remove_legacy_cursor_skills(repo_path, apply=True)

    for skill, concrete_ref in skill_pins:
        skill_url = f"https://github.com/{skill.org}/{skill.repo}"
        declared = skill.ref or "HEAD"
        if not pin_submodule(
            repo_path,
            PRAYOG_SKILLS_SUBMODULE_REL,
            skill_url,
            concrete_ref,
            label=f"skills/{skill.repo}",
        ):
            print(f"  ✗  skills pin failed: {skill_url}@{concrete_ref}", file=sys.stderr)
            return 1
        if declared.lower() == "latest":
            print(
                f"  ✔  skills pinned: {skill.org}/{skill.repo}@latest → {concrete_ref}"
            )
        else:
            print(f"  ✔  skills pinned: {skill.org}/{skill.repo}@{concrete_ref}")

    try:
        actual_contract = _verify_delivery_contract(
            prayog_submodule, delivery_contract
        )
        if actual_contract:
            print(f"  ✔  delivery contract: {actual_contract}")
        skill_names = resolve_skill_names(prayog_submodule, profile, profile_name)
    except HarnessResolveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    materialized = materialize_skill_tree(
        repo_path,
        prayog_submodule_rel=PRAYOG_SKILLS_SUBMODULE_REL,
        skill_names=skill_names,
        runtime_roots=profile.skill_runtimes,
        lane_key=lane_key,
        community_submodule_dirs=community_dirs,
        apply=True,
    )
    if len(materialized) < len(skill_names):
        print(
            f"  WARN: materialized {len(materialized)}/{len(skill_names)} prayog skills",
            file=sys.stderr,
        )

    copy_harness_profile(
        prayog_submodule,
        profile,
        repo_path / HARNESS_PROFILE_REL,
        harness_profile_name=profile_name,
        apply=True,
    )

    community_names = install_community_skills(repo_path, profile, apply=True)
    all_skill_names = skill_names + community_names

    _seed_codeowners(repo_path, profile.codeowners_template, org, apply=True)
    _seed_harness_pin(
        repo_path,
        profile.harness_pin_template,
        profile,
        profile_name,
        skill_names=all_skill_names,
        delivery_contract=delivery_contract,
        apply=True,
        agent_skills_ref=agent_skills_ref,
    )
    _seed_agents_md(
        repo_path,
        profile_name,
        profile,
        skill_names=all_skill_names,
        delivery_contract=delivery_contract,
        target=target,
        org=org,
        meta_repo=meta_repo,
        board_name=board_name,
        board_url=board_url,
        apply=True,
        agent_skills_ref=agent_skills_ref,
    )
    _seed_gitignore_harness(repo_path, apply=True)
    _seed_delivery_workflows(
        repo_path,
        delivery_contract=delivery_contract,
        profile_name=profile_name,
        apply=True,
    )
    return 0


def run_apply_harness(
    *,
    meta: bool = False,
    repo_name: str = "",
    apply: bool = False,
    config_dir: Path | None = None,
    workspace: Path | None = None,
) -> int:
    if not meta and not repo_name:
        print("ERROR: pass --meta or --repo <name>", file=sys.stderr)
        return 1

    if config_dir is None:
        raise RuntimeError("config_dir not resolved — pass --client <id> or run launchpad onboard interview")
    cdir = config_dir

    harness_path = _find_config(cdir, "harness-*.yaml")
    if harness_path is None:
        print(f"ERROR: harness-<org>.yaml not found in {cdir}", file=sys.stderr)
        return 1

    gov_path = _find_config(cdir, "governance-*.yaml")
    if gov_path is None:
        print(f"ERROR: governance-<org>.yaml not found in {cdir}", file=sys.stderr)
        return 1

    try:
        h = load_harness(harness_path)
        gov = load_governance(gov_path)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    org = gov.org
    prog = None
    meta_repo = cdir.parent.name
    try:
        prog_path = cdir / "programme.yaml"
        if prog_path.is_file():
            from launchpad.schema.programme import load_programme

            prog = load_programme(prog_path)
            meta_repo = prog.meta_repo
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        ws = resolve_programme_workspace(config_dir=cdir, override=workspace)
    except ClientRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if meta:
        target = meta_repo
        stack = gov.repos[target].stack if target in gov.repos else PM_HARNESS_PROFILE
    else:
        target = repo_name
        if repo_name not in gov.repos:
            print(f"ERROR: repo '{repo_name}' not in governance yaml", file=sys.stderr)
            return 1
        stack = gov.repos[repo_name].stack

    profile_name = h.resolve_profile(target, stack)
    if profile_name is None or profile_name not in h.profiles:
        print(f"  No harness profile found for {target} (stack={stack}) — skipping.")
        print(f"  Add a '{stack}' profile to harness-{h.org}.yaml and re-run.")
        return 0

    profile = h.profiles[profile_name]
    repo_path = Path(ws).expanduser().resolve() / target
    binding = resolve_board_binding(org, gov.project_board)
    board_name = binding.name if binding.configured and profile_name != PM_HARNESS_PROFILE else ""
    board_url = binding.url if binding.configured and profile_name != PM_HARNESS_PROFILE else ""

    print(f"apply-harness  →  {h.org}/{target}  [profile: {profile_name}]")
    if not repo_path.is_dir():
        print(f"  WARN: local clone not found at {repo_path}")
        print("  Clone it first, then re-run apply-harness.")
        if apply:
            return 1

    result = _apply_harness_to_repo(
        repo_path,
        profile,
        profile_name,
        org,
        h.delivery_contract,
        target=target,
        meta_repo=meta_repo,
        board_name=board_name,
        board_url=board_url,
        apply=apply,
    )
    if result != 0:
        return result

    if not apply:
        target_flag = "--meta" if meta else f"--repo {target}"
        print_next_box([f"launchpad apply-harness {target_flag} --apply"])
    else:
        client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
        client_prefix = f"--client {client_id} " if client_id else ""
        target_flag = "--meta" if meta else f"--repo {target}"
        next_steps = [f"launchpad {client_prefix}status {target_flag}".strip()]
        if not meta and h.delivery_contract:
            next_steps.insert(
                0,
                'git add .harness-pin.yaml .github/workflows/ && git commit -m "chore: sync harness and delivery workflows"',
            )
        print_next_box(next_steps)

    return 0
