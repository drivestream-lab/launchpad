"""status — programme readiness checklist + kit health.

Two views depending on flag:

  --meta   (PM / Operator view)
    Kit version check (installed vs latest on drivestream-lab)
    Meta repo phase checklist: governance, clone, scaffold, harness
    Constitution pins declared across all harness profiles
    Skills pins declared across all harness profiles
    Foundation freshness: new tags available on scaffold template repos

  --repo <name>   (Engineer / Repo-owner view)
    Kit version check
    Repo phase checklist: governance, clone, scaffold, harness
    Constitution: declared ref vs locally pinned ref (drift check)
    Skills: declared ref vs locally pinned ref (drift check)
    Exit code 1 if drift detected — safe for CI pipelines

check-harness is removed — status --repo covers its functionality.

Usage:
  launchpad status --meta
  launchpad status --repo <name>
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version

from launchpad import __version__
from launchpad import github_ops
from launchpad.forge.templates.render import (
    build_render_context,
    forge_templates_present,
    get_layout,
    kit_templates_dir,
    render_template,
)
from launchpad.harness.community_skills import community_skill_names
from launchpad.clients import resolve_programme_workspace
from launchpad.programme.board_binding import resolve_board_binding
from launchpad.harness.paths import HARNESS_PROFILE_REL, PM_HARNESS_PROFILE, PRAYOG_SKILLS_SUBMODULE_REL
from launchpad.harness.skills_materialize import all_runtime_skills_present, hub_skill_present, runtime_skill_present
from launchpad.harness.skills_resolve import (
    HarnessResolveError,
    resolve_delivery_contract,
    resolve_gate_resources,
    resolve_skill_names,
)
from launchpad.github_client import GitHubClient, GitHubError
from launchpad.schema import SchemaError
from launchpad.ui import print_next_box

_KIT_REPO = "drivestream-lab/launchpad"
_API_TIMEOUT = 4.0


# ── Helpers ──────────────────────────────────────────────────────────────────


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def _mark(ok: bool | None, *, neutral: bool = False) -> str:
    """
    ok=True   → [✔]  done / healthy
    ok=False  → [✗]  expected but missing (action required)
    ok=None   → [?]  unknown / prereq not met
    neutral   → [–]  intentionally off (no action needed)
    """
    if neutral:
        return "–"
    if ok is None:
        return "?"
    return "✔" if ok else "✗"


def _section(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, 54 - len(title))}")


# ── Kit version ──────────────────────────────────────────────────────────────


def _fetch_latest_kit_version() -> str | None:
    """Return latest release tag from drivestream-lab/launchpad, or None on failure."""
    try:
        r = httpx.get(
            f"https://api.github.com/repos/{_KIT_REPO}/releases/latest",
            timeout=_API_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 200:
            return r.json().get("tag_name", "").lstrip("v") or None
        # Fall back to tags if no release published
        r2 = httpx.get(
            f"https://api.github.com/repos/{_KIT_REPO}/tags",
            timeout=_API_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r2.status_code == 200:
            tags = r2.json()
            if tags:
                return tags[0]["name"].lstrip("v")
    except Exception:
        pass
    return None


def _semver(v: str) -> Version:
    """Parse stable and prerelease versions for comparison."""
    try:
        return Version(v.replace("-rc.", "rc"))
    except InvalidVersion:
        return Version("0")


def _print_kit_section() -> bool:
    """Print kit version block. Returns True if upgrade needed."""
    _section("Kit")
    installed = __version__
    latest = _fetch_latest_kit_version()
    if latest is None:
        print(f"  [?] launchpad v{installed}  (version check unavailable — offline?)")
        return False
    if _semver(latest) <= _semver(installed):
        print(f"  [✔] launchpad v{installed}  (up to date)")
        return False
    print(f"  [!] launchpad v{installed} installed — v{latest} available")
    print(f'      Upgrade: pipx install "launchpad @ git+https://github.com/{_KIT_REPO}@v{latest}"')
    return True


# ── Foundation freshness (PM view) ───────────────────────────────────────────


def _latest_tag(org: str, repo: str) -> str | None:
    """Return latest tag name without leading ``v``, or None on failure."""
    try:
        r = httpx.get(
            f"https://api.github.com/repos/{org}/{repo}/tags",
            timeout=_API_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 200:
            tags = r.json()
            if tags:
                return tags[0]["name"].lstrip("v")
    except Exception:
        pass
    return None


def _latest_release_tag(org: str, repo: str) -> str | None:
    """Prefer GitHub ``releases/latest``; fall back to newest tag."""
    try:
        r = httpx.get(
            f"https://api.github.com/repos/{org}/{repo}/releases/latest",
            timeout=_API_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 200:
            tag = str(r.json().get("tag_name") or "").lstrip("v")
            if tag:
                return tag
    except Exception:
        pass
    return _latest_tag(org, repo)


def _print_foundation_section(sca: Any) -> None:
    """Print foundation freshness for all scaffold entries that have template + ref set."""
    entries: list[tuple[str, str, str]] = []  # (label, org/repo, declared_ref)

    def _collect(label: str, entry: Any) -> None:
        if entry is None:
            return
        t = getattr(entry, "template", "") or ""
        ref = getattr(entry, "ref", "") or ""
        if not t or not ref:
            return
        if t.startswith("gh:"):
            slug = t[3:]  # e.g. drivestream-lab/python-fastapi-foundation
            parts = slug.split("/", 1)
            if len(parts) == 2:
                entries.append((label, slug, ref.lstrip("v")))

    _collect("meta", sca.meta)
    for rname, rentry in (sca.repos or {}).items():
        _collect(rname, rentry)

    if not entries:
        return

    _section("Foundation updates")
    api_unavailable = False
    for label, slug, declared_ref in entries:
        parts = slug.split("/", 1)
        org_slug, repo_slug = parts[0], parts[1]
        latest = _latest_tag(org_slug, repo_slug)
        if latest is None:
            api_unavailable = True
            print(f"  [?] {repo_slug:<38}  v{declared_ref}  (check unavailable)")
        elif latest == declared_ref:
            print(f"  [✔] {repo_slug:<38}  v{declared_ref}  (up to date)")
        else:
            print(f"  [!] {repo_slug:<38}  v{declared_ref} declared — v{latest} available")

    if api_unavailable:
        print("  (some checks skipped — offline?)")


# ── Governance pins (PM view) ─────────────────────────────────────────────────


def _print_governance_pins(h: Any) -> None:
    _section("Governance pins  (declared in harness YAML)")
    for pname, profile in h.profiles.items():
        if profile.constitution is None:
            print(f"  –   {pname:<20}  no constitution (by design)")
        else:
            con = profile.constitution
            print(f"  [→] {pname:<20}  {con.repo:<34}  @ {con.ref}")
        if not profile.skills:
            print(f"  –   {pname:<20}  no skills (by design)")
        else:
            for skill in profile.skills:
                label = f"{skill.org}/{skill.repo}"
                print(f"  [→] {pname:<20}  {label:<34}  @ {skill.ref or 'HEAD'}")


def _print_prayog_freshness(h: Any) -> None:
    """Advisory: declared prayog-skills refs vs GitHub releases/latest."""
    pins: dict[tuple[str, str], set[str]] = {}
    for profile in h.profiles.values():
        for skill in profile.skills:
            repo_name = skill.repo.split("/")[-1] if skill.repo else ""
            if repo_name != "prayog-skills":
                continue
            ref = (skill.ref or "").strip()
            if not ref:
                continue
            pins.setdefault((skill.org, "prayog-skills"), set()).add(ref)

    if not pins:
        return

    _section("Prayog skills freshness")
    for (org, repo), refs in sorted(pins.items()):
        latest = _latest_release_tag(org, repo)
        for declared in sorted(refs):
            declared_n = declared.lstrip("v")
            if declared.lower() == "latest":
                if latest is None:
                    print(f"  [?] {org}/{repo}  @latest  (check unavailable)")
                else:
                    print(f"  [✔] {org}/{repo}  @latest → v{latest}  (floating)")
                continue
            if latest is None:
                print(f"  [?] {org}/{repo}  @{declared}  (check unavailable)")
            elif latest == declared_n:
                print(f"  [✔] {org}/{repo}  @{declared}  (up to date)")
            else:
                print(
                    f"  [!] {org}/{repo}  @{declared} declared — "
                    f"v{latest} available on GitHub"
                )
                print(
                    "      Bump skills[].ref in harness YAML when ready "
                    "(or use ref: latest for floating pins)"
                )


# ── Submodule drift (Engineer view) ───────────────────────────────────────────


def _get_local_submodule_ref(repo_path: Path, submodule_rel: str) -> str | None:
    """Return the current HEAD ref of a submodule, or None if not present."""
    sub_path = repo_path / submodule_rel
    if not sub_path.is_dir():
        return None
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=sub_path,
        capture_output=True,
        text=True,
    )
    sha = result.stdout.strip()
    # Try to resolve the SHA to a tag name
    tag_result = subprocess.run(
        ["git", "describe", "--tags", "--exact-match", sha],
        cwd=sub_path,
        capture_output=True,
        text=True,
    )
    if tag_result.returncode == 0:
        return tag_result.stdout.strip()
    return sha[:7] if sha else None


def _print_submodule_drift(
    *,
    section: str,
    repo_label: str,
    declared_ref: str,
    submodule_rel: str,
    repo_path: Path,
) -> bool:
    """Print declared vs local submodule state. Returns True if drift detected."""
    _section(section)
    print(f"  [→] declared:  {repo_label} @ {declared_ref}")

    local_ref = _get_local_submodule_ref(repo_path, submodule_rel)
    if local_ref is None:
        print("  [✗] local:     not pinned yet")
        return True

    sub_path = repo_path / submodule_rel
    head_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=sub_path,
        capture_output=True,
        text=True,
    )
    local_sha = head_result.stdout.strip()
    declared_sha = ""
    for candidate in (f"origin/{declared_ref}", declared_ref):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", candidate],
            cwd=sub_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            declared_sha = result.stdout.strip()
            break

    if local_ref == declared_ref or (local_sha and local_sha == declared_sha):
        print(f"  [✔] local:     {repo_label} @ {local_ref}  (in sync)")
        return False

    print(f"  [!] local:     {repo_label} @ {local_ref}  ← behind declared {declared_ref}")
    return True


def _print_constitution_drift(profile: Any, repo_path: Path) -> bool:
    """Print declared vs local constitution state. Returns True if drift detected."""
    con = profile.constitution
    if con is None:
        _section("Constitution")
        print("  –   no constitution for this profile (by design)")
        return False

    return _print_submodule_drift(
        section="Constitution",
        repo_label=con.repo,
        declared_ref=con.ref,
        submodule_rel=".cursor/rules",
        repo_path=repo_path,
    )


def _print_skills_drift(profile: Any, repo_path: Path) -> bool:
    """Print declared vs local skills submodule state. Returns True if any drift."""
    if not profile.skills:
        _section("Skills")
        print("  –   no skills for this profile (by design)")
        return False

    drift = False
    legacy_nested = repo_path / ".agents" / "skills" / "prayog-skills"
    if legacy_nested.is_dir() and not (repo_path / PRAYOG_SKILLS_SUBMODULE_REL).is_dir():
        _section("Skills bundle  (prayog-skills)")
        print(
            "  [✗] local:     nested .agents/skills/prayog-skills/ "
            f"(expected {PRAYOG_SKILLS_SUBMODULE_REL}/ at repo root — re-run apply-harness)"
        )
        drift = True

    for skill in profile.skills:
        declared = skill.ref or "HEAD"
        label = f"{skill.org}/{skill.repo}"
        rel = PRAYOG_SKILLS_SUBMODULE_REL
        if _print_submodule_drift(
            section=f"Skills bundle  ({skill.repo})",
            repo_label=label,
            declared_ref=declared,
            submodule_rel=rel,
            repo_path=repo_path,
        ):
            drift = True
    return drift


def _expected_skill_names(repo_path: Path, profile: Any, profile_name: str) -> list[str]:
    """Skill names that should exist in the harness hub and runtime roots."""
    submodule_root = repo_path / PRAYOG_SKILLS_SUBMODULE_REL
    names: list[str] = []
    if submodule_root.is_dir():
        try:
            names = resolve_skill_names(submodule_root, profile, profile_name)
        except HarnessResolveError:
            return community_skill_names(profile)
    return names + community_skill_names(profile)


def _harness_materialized_ok(repo_path: Path, profile_name: str, profile: Any) -> bool:
    if not profile.skills:
        return True

    if not (repo_path / PRAYOG_SKILLS_SUBMODULE_REL).is_dir():
        return False

    expected = _expected_skill_names(repo_path, profile, profile_name)
    if not expected:
        return False

    if not (repo_path / ".harness-pin.yaml").is_file():
        return False

    return all_runtime_skills_present(repo_path, expected, profile.skill_runtimes)


def _forge_templates_ok(repo_path: Path, *, is_meta: bool, provider: str = "github") -> bool:
    if provider != "github":
        return True
    try:
        entries = get_layout(provider, is_meta=is_meta)
    except (NotImplementedError, ValueError):
        return True
    return forge_templates_present(repo_path, entries)


def _forge_templates_stale(
    repo_path: Path,
    *,
    is_meta: bool,
    gov: Any,
    prog: Any,
    provider: str = "github",
) -> bool:
    """True when on-disk forge templates differ from kit + governance render."""
    if provider != "github" or not forge_templates_present(
        repo_path, get_layout(provider, is_meta=is_meta)
    ):
        return False
    context = build_render_context(gov, prog)
    for entry in get_layout(provider, is_meta=is_meta):
        dest = repo_path / entry.dest_rel
        src = kit_templates_dir() / entry.kit_name
        if not src.is_file() or not dest.is_file():
            continue
        expected = render_template(src.read_text(encoding="utf-8"), context)
        if dest.read_text(encoding="utf-8") != expected:
            return True
    return False


def _print_materialized_skills_check(profile_name: str, repo_path: Path, profile: Any) -> bool:
    """Print hub + runtime skill path health. Returns True if any missing."""
    if not profile.skills:
        return False

    expected = _expected_skill_names(repo_path, profile, profile_name)
    if not expected:
        return False

    _section("Agent skills  (hub + runtime paths)")
    drift = False
    for name in expected:
        hub_ok = hub_skill_present(repo_path, name)
        if hub_ok:
            print(f"  [✔] .harness/skills/{name}/")
        else:
            print(f"  [✗] .harness/skills/{name}/  (missing — run apply-harness --apply)")
            drift = True
        for runtime in profile.skill_runtimes:
            if runtime_skill_present(repo_path, name, runtime):
                print(f"  [✔] {runtime}/{name}/")
            else:
                print(f"  [✗] {runtime}/{name}/  (missing — run apply-harness --apply)")
                drift = True
    return drift


def _print_delivery_contract_check(repo_path: Path, expected: str) -> bool:
    """Print expected vs pinned Prayog delivery contract. Returns drift."""
    if not expected:
        return False
    _section("Delivery contract")
    submodule_root = repo_path / PRAYOG_SKILLS_SUBMODULE_REL
    try:
        actual = resolve_delivery_contract(submodule_root)
    except HarnessResolveError as exc:
        print(f"  [✗] {exc}")
        print(
            "      Bump skills[].ref to a GitHub release that ships "
            "delivery-contract.yaml, or omit delivery_contract for a legacy pin"
        )
        return True
    if actual == expected:
        print(f"  [✔] {actual}  (matches harness)")
        return False
    print(f"  [✗] declared: {expected}  pinned: {actual}")
    print(
        "      Align harness delivery_contract with the pin, or bump skills[].ref "
        "to a release that provides the expected contract"
    )
    return True


def _print_delivery_gates_check(
    repo_path: Path,
    profile_name: str,
    delivery_roles: dict[str, str],
    org: str,
    repo: str,
) -> bool:
    """Print contract label and review-role readiness. Returns drift."""
    submodule_root = repo_path / PRAYOG_SKILLS_SUBMODULE_REL
    try:
        labels, review_roles = resolve_gate_resources(submodule_root, profile_name)
    except HarnessResolveError as exc:
        _section("Delivery gates")
        print(f"  [✗] {exc}")
        return True
    if not labels and not review_roles:
        return False

    _section("Delivery gates")
    drift = False
    try:
        with GitHubClient(dry_run=False) as client:
            for expected in labels:
                actual = github_ops.get_label(client, org, repo, expected["name"])
                if actual is None:
                    print(f"  [✗] label missing: {expected['name']}")
                    drift = True
                    continue
                color_ok = str(actual.get("color") or "").upper() == expected["color"].upper()
                description_ok = str(actual.get("description") or "") == expected["description"]
                ok = color_ok and description_ok
                print(f"  [{'✔' if ok else '✗'}] label: {expected['name']}")
                drift = drift or not ok

            for gate, role in review_roles.items():
                team = delivery_roles.get(role, "")
                if not team:
                    print(f"  [✗] {gate}: no team mapped for role {role!r}")
                    drift = True
                    continue
                permission = github_ops.team_repo_permission(client, org, repo, team)
                if permission is None:
                    print(f"  [✗] {gate}: {role} → {team} has no repository access")
                    drift = True
                    continue
                print(f"  [✔] {gate}: {role} → {team}  (permission: {permission})")
    except GitHubError as exc:
        print(f"  [?] gate check unavailable: {exc}")
    return drift


# ── Main ─────────────────────────────────────────────────────────────────────


def run_status(
    *,
    meta: bool = False,
    repo_name: str = "",
    config_dir: Path | None = None,  # None only in tests — main() always resolves via clients.yaml
    workspace: Path | None = None,
) -> int:
    if not meta and not repo_name:
        print("ERROR: pass --meta or --repo <name>", file=sys.stderr)
        return 1

    if config_dir is None:
        # Should not reach here — main() blocks client-less commands early.
        raise RuntimeError("config_dir not resolved — pass --client <id> or run launchpad onboard interview")
    cdir = config_dir

    # Load schemas (best-effort)
    prog, gov, sca, h = None, None, None, None

    prog_path = cdir / "programme.yaml"
    if prog_path.is_file():
        try:
            from launchpad.schema.programme import load_programme
            prog = load_programme(prog_path)
        except SchemaError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    gov_path = _find_config(cdir, "governance-*.yaml")
    if gov_path:
        try:
            from launchpad.schema.governance import load_governance
            gov = load_governance(gov_path)
        except SchemaError:
            pass

    sca_path = _find_config(cdir, "scaffold-*.yaml")
    if sca_path:
        try:
            from launchpad.schema.scaffold import load_scaffold
            sca = load_scaffold(sca_path)
        except SchemaError:
            pass

    h_path = _find_config(cdir, "harness-*.yaml")
    if h_path:
        try:
            from launchpad.schema.harness import load_harness
            h = load_harness(h_path)
        except SchemaError:
            pass

    try:
        ws = resolve_programme_workspace(config_dir=cdir, override=workspace)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    meta_repo = prog.meta_repo if prog else (
        cdir.parent.name if cdir.parent.name.endswith("-meta") else "unknown-meta"
    )
    org = prog.org if prog else "unknown"

    if meta:
        target = meta_repo
        stack = (gov.repos[target].stack if gov and target in gov.repos else "meta-pm")
    else:
        target = repo_name
        stack = gov.repos[repo_name].stack if gov and repo_name in gov.repos else ""

    print(f"\nstatus  →  {org}/{target}")

    # ── Kit version ──────────────────────────────────────────────────────────
    kit_upgrade_needed = _print_kit_section()

    # ── Repo phase checklist ─────────────────────────────────────────────────
    _section("Repo")

    gov_ok = gov is not None and target in gov.repos
    stack_label = f"stack: {stack}" if gov_ok and stack else f"add '{target}' to governance repos:"
    print(f"  [{_mark(gov_ok)}] Governance declared       ({stack_label})")

    board_detail = "not configured"
    board_neutral = True
    board_ok = False
    if gov and gov.project_board:
        binding = resolve_board_binding(org, gov.project_board)
        if binding.configured:
            board_neutral = False
            board_ok = bool(binding.url or binding.number is not None)
            board_detail = binding.name
            if binding.number is not None:
                board_detail += f" (#{binding.number})"
            if binding.url:
                board_detail += f" — {binding.url}"
            if not meta and stack != PM_HARNESS_PROFILE:
                board_detail += " — run /board-seed after spec merge"
        else:
            board_detail = "project_board disabled in governance"
    print(f"  [{_mark(board_ok if not board_neutral else None, neutral=board_neutral)}] Programme board          ({board_detail})")

    repo_path = Path(ws).expanduser().resolve() / target
    clone_ok = (repo_path / ".git").is_dir()
    clone_detail = str(repo_path) if clone_ok else (
        f"not a git repo: {repo_path}  (run init-client --apply)"
        if repo_path.is_dir() else f"not found: {repo_path}"
    )
    print(f"  [{_mark(clone_ok)}] Local clone (git repo)    ({clone_detail})")

    # Scaffold — [✔] applied, [–] off (intentional), [✗] enabled but not run
    sca_applied = False
    sca_pending = False
    if meta:
        sca_configured = sca is not None and sca.meta is not None
        sca_enabled = sca_configured and sca.meta.enabled  # type: ignore[union-attr]
    else:
        sca_configured = sca is not None and repo_name in sca.repos
        sca_enabled = sca_configured and sca.repos[repo_name].enabled  # type: ignore[index]

    if not sca_configured or not sca_enabled:
        # Scaffold is intentionally off — neutral, not a failure
        print(f"  [{_mark(None, neutral=True)}] Scaffold                  (off — enable in scaffold YAML to opt in)")
    else:
        # Scaffold is enabled — check marker written by apply-scaffold
        sca_applied = clone_ok and (repo_path / ".launchpad-scaffold").is_file()
        sca_pending = clone_ok and not sca_applied
        print(f"  [{_mark(sca_applied)}] Scaffold                  "
              f"({'applied' if sca_applied else 'enabled but not applied — run apply-scaffold --apply --force'})")

    # Harness — [✔] pinned, [–] no profile (opt-out), [✗] profile defined but not applied, [?] prereq missing
    harness_ok = False
    harness_neutral = False
    harness_detail = ""
    profile = None
    if not clone_ok:
        harness_detail = "clone required first"
    elif not h:
        harness_neutral = True
        harness_detail = "no harness config found"
    else:
        profile_name = h.resolve_profile(target, stack)
        if not profile_name or profile_name not in h.profiles:
            harness_neutral = True
            harness_detail = f"no profile defined for stack '{stack}' — add one to harness YAML to opt in"
        else:
            profile = h.profiles[profile_name]
            con = profile.constitution
            if con is None:
                harness_pin_path = repo_path / ".harness-pin.yaml"
                harness_ok = harness_pin_path.is_file() and _harness_materialized_ok(
                    repo_path, profile_name, profile
                )
                harness_detail = (
                    f"profile: {profile_name}"
                    if harness_ok
                    else f"not applied  (profile: {profile_name}) — run apply-harness --apply"
                )
            else:
                rules_path = repo_path / ".cursor" / "rules"
                harness_ok = rules_path.is_dir() and _harness_materialized_ok(
                    repo_path, profile_name, profile
                )
                harness_detail = (
                    f"profile: {profile_name}"
                    if harness_ok
                    else f"not applied  (profile: {profile_name}) — run apply-harness --apply"
                )

    if not clone_ok:
        print(f"  [{_mark(None)}] Harness                   ({harness_detail})")
    elif harness_neutral:
        print(f"  [{_mark(None, neutral=True)}] Harness                   ({harness_detail})")
    else:
        print(f"  [{_mark(harness_ok)}] Harness                   ({harness_detail})")

    # Forge contributor templates (issue forms + PR template)
    forge_provider = prog.forge_provider if prog else "github"
    forge_ok = False
    forge_stale = False
    forge_detail = ""
    if not clone_ok:
        forge_detail = "clone required first"
    elif forge_provider == "gitlab":
        forge_detail = "gitlab layout not yet supported (planned v0.6)"
        forge_ok = True
    else:
        is_meta_repo = meta
        forge_ok = _forge_templates_ok(repo_path, is_meta=is_meta_repo, provider=forge_provider)
        if forge_ok and gov and prog:
            forge_stale = _forge_templates_stale(
                repo_path,
                is_meta=is_meta_repo,
                gov=gov,
                prog=prog,
                provider=forge_provider,
            )
        if not forge_ok:
            forge_detail = "missing — run apply-forge-templates --apply"
        elif forge_stale:
            forge_detail = "stale — run apply-forge-templates --apply --force"
        else:
            forge_detail = "present"

    if not clone_ok:
        print(f"  [{_mark(None)}] Forge templates           ({forge_detail})")
    elif forge_provider == "gitlab":
        print(f"  [{_mark(None, neutral=True)}] Forge templates           ({forge_detail})")
    else:
        mark_ok = forge_ok and not forge_stale
        print(f"  [{_mark(mark_ok)}] Forge templates           ({forge_detail})")

    # ── PM view: constitution pins + foundation freshness ────────────────────
    drift_detected = False
    gate_drift = False
    if profile and clone_ok and h:
        if not h.delivery_contract:
            _section("Delivery contract")
            print("  [–] not declared  (legacy Prayog pin; gate checks skipped)")
        else:
            if _print_delivery_contract_check(repo_path, h.delivery_contract):
                drift_detected = True
            if _print_delivery_gates_check(
                repo_path,
                profile_name,
                h.delivery_roles,
                org,
                target,
            ):
                drift_detected = True
                gate_drift = True
    if meta:
        if h:
            _print_governance_pins(h)
            _print_prayog_freshness(h)
        if sca:
            _print_foundation_section(sca)
        if profile and clone_ok and profile.skills:
            if _print_materialized_skills_check(profile_name, repo_path, profile):
                drift_detected = True
                client = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
                prefix = f"--client {client} " if client else ""
                print(f"      Fix: launchpad {prefix}apply-harness --meta --apply")

    # ── Engineer view: constitution + skills drift ────────────────────────────
    else:
        if profile and clone_ok:
            drift_detected = _print_constitution_drift(profile, repo_path)
            if _print_skills_drift(profile, repo_path):
                drift_detected = True
            if _print_materialized_skills_check(profile_name, repo_path, profile):
                drift_detected = True
            if drift_detected:
                client = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
                prefix = f"--client {client} " if client else ""
                print(f"      Fix: launchpad {prefix}apply-harness --repo {target} --apply")

    # ── NEXT ─────────────────────────────────────────────────────────────────
    print()
    client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
    client_prefix = f"--client {client_id} " if client_id else ""
    flag = "--meta" if meta else f"--repo {target}"
    if kit_upgrade_needed:
        next_cmd = "upgrade launchpad kit (see Kit section above)"
    elif not gov_ok:
        next_cmd = f"add '{target}' to governance-{org}.yaml repos"
    elif not clone_ok:
        next_cmd = f"launchpad {client_prefix}init-client {flag} --apply"
    elif sca_pending:
        next_cmd = f"launchpad {client_prefix}apply-scaffold {flag} --apply --force"
    elif not harness_neutral and not harness_ok and clone_ok:
        next_cmd = f"launchpad {client_prefix}apply-harness {flag} --apply"
    elif clone_ok and forge_provider == "github" and (not forge_ok or forge_stale):
        force = " --force" if forge_stale else ""
        next_cmd = f"launchpad {client_prefix}apply-forge-templates {flag} --apply{force}"
    elif gate_drift:
        next_cmd = f"launchpad {client_prefix}apply-gates {flag} --apply"
    elif drift_detected:
        next_cmd = f"launchpad {client_prefix}apply-harness --repo {target} --apply"
    else:
        next_cmd = f"launchpad {client_prefix}status {flag}  (all checks pass)"

    print_next_box([next_cmd.strip()])

    # Exit 1 for actionable failures — neutral states (scaffold off, no profile) are not failures
    has_failure = (
        not gov_ok
        or not clone_ok
        or sca_pending
        or (not harness_neutral and not harness_ok and clone_ok)
        or (clone_ok and forge_provider == "github" and (not forge_ok or forge_stale))
        or drift_detected
    )
    return 1 if has_failure else 0
