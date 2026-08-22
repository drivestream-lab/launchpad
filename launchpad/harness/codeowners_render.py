"""Render .github/CODEOWNERS from layout families, overrides, or legacy shim."""

from __future__ import annotations

import sys
from pathlib import Path

from launchpad.schema.owners import (
    EDGE_APP_SRC_FAMILY,
    LEGACY_CODEOWNERS_TEMPLATES,
    family_template_name,
    resolve_owners,
)
from launchpad.schema.errors import SchemaError
from launchpad.schema.harness import HarnessProfile

_TEMPLATE_ORG_PLACEHOLDER = "example-org"


def _kit_templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def _codeowners_families_dir() -> Path:
    return _kit_templates_dir() / "codeowners"


def _resolve_file_template(filename: str, meta_templates: Path | None) -> Path | None:
    """Prefer meta/config/templates/, then kit templates/ root."""
    if meta_templates is not None:
        candidate = meta_templates / filename
        if candidate.is_file():
            return candidate
    kit = _kit_templates_dir() / filename
    return kit if kit.is_file() else None


def _family_path(family: str) -> Path | None:
    if family == "none":
        return None
    path = _codeowners_families_dir() / f"family.{family}"
    return path if path.is_file() else None


def legacy_codeowners_deprecation_warn(
    *,
    tpl_name: str,
    family: str,
    profile_name: str,
) -> str:
    """Mandatory WARN + fix instructions for legacy CODEOWNERS.* names."""
    return (
        f"WARN: codeowners_template '{tpl_name}' is deprecated\n"
        f"      (kit per-stack CODEOWNERS files were removed in v0.5.36).\n"
        f"      Launchpad rendered layout family '{family}' for this remount.\n"
        f"\n"
        f"  Fix in config/harness-<org>.yaml for profile '{profile_name}':\n"
        f"    1. Remove:\n"
        f"         codeowners_template: {tpl_name}\n"
        f"         harness_pin_template: harness-pin.<stack>.yaml\n"
        f"    2. Optional (defaults already apply for known stacks):\n"
        f"         owners:\n"
        f"           team: <team-slug>\n"
        f"           layout: <family>\n"
        f"    3. Custom CODEOWNERS: place file under config/templates/ and keep\n"
        f"         codeowners_template: <filename>\n"
        f"       (resolved from meta config/templates/).\n"
        f"\n"
        f"  Then:\n"
        f"    launchpad reset-harness --repo <name> --apply\n"
        f"    launchpad apply-harness --repo <name> --apply\n"
    )


def _append_extra_paths(content: str, team: str, org: str, extra_paths: tuple[str, ...]) -> str:
    if not extra_paths:
        return content
    owner = f"@{org}/{team}"
    block_lines = [
        "",
        "# ── Extra owned paths (owners.extra_paths) ─────────────────────────────────",
        "",
    ]
    for path in extra_paths:
        p = path if path.startswith("/") else f"/{path}"
        if not p.endswith("/") and "." not in Path(p).name:
            p = p + "/"
        block_lines.append(f"{p:<52} {owner}")
    block = "\n".join(block_lines) + "\n"
    # Insert before the default catch-all `*` line when present.
    lines = content.splitlines(keepends=True)
    insert_at = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("*") and "@" in line:
            insert_at = i
            break
    if insert_at is None:
        return content.rstrip() + "\n" + block
    return "".join(lines[:insert_at]) + block + "".join(lines[insert_at:])


def _render_family_body(
    family: str,
    *,
    org: str,
    team: str,
    extra_paths: tuple[str, ...],
) -> str:
    path = _family_path(family)
    if path is None:
        raise SchemaError(
            f"CODEOWNERS layout family {family!r} has no kit template",
            path="",
            hint="Add templates/codeowners/family.<layout> or use layout: none",
        )
    content = path.read_text(encoding="utf-8")
    content = content.replace("{{DEV_TEAM}}", team)
    content = content.replace(_TEMPLATE_ORG_PLACEHOLDER, org)
    content = _append_extra_paths(content, team, org, extra_paths)
    return content


def resolve_codeowners_content(
    profile: HarnessProfile,
    profile_name: str,
    org: str,
    *,
    meta_templates: Path | None = None,
    warn_stream=None,
) -> str | None:
    """Return CODEOWNERS text, or None when layout is none (skip write).

    Resolution order:
      1. codeowners_template file in meta templates or kit templates/
      2. Known legacy kit name → mapped family (+ WARN)
      3. owners.layout + owners.team (explicit or migration defaults)
      4. layout none → None
      5. Unknown missing template → SchemaError with fix hint
    """
    stream = warn_stream if warn_stream is not None else sys.stderr
    tpl_name = (profile.codeowners_template or "").strip()
    owners = resolve_owners(profile_name, profile.owners)

    if owners.skip_codeowners and not tpl_name:
        return None

    # Explicit empty / unset after schema may still hold convention default.
    # Treat convention default CODEOWNERS.<name> as "no override" when file missing.
    convention = f"CODEOWNERS.{profile_name}"
    explicit_override = bool(profile.codeowners_template_explicit)

    if tpl_name and (explicit_override or tpl_name != convention or _resolve_file_template(tpl_name, meta_templates)):
        file_path = _resolve_file_template(tpl_name, meta_templates)
        if file_path is not None:
            content = file_path.read_text(encoding="utf-8")
            return content.replace(_TEMPLATE_ORG_PLACEHOLDER, org)

        legacy_family = LEGACY_CODEOWNERS_TEMPLATES.get(tpl_name)
        if legacy_family is not None:
            display_family = (
                "app_src" if legacy_family == EDGE_APP_SRC_FAMILY else legacy_family
            )
            print(
                legacy_codeowners_deprecation_warn(
                    tpl_name=tpl_name,
                    family=display_family,
                    profile_name=profile_name,
                ),
                file=stream,
                end="",
            )
            return _render_family_body(
                legacy_family,
                org=org,
                team=owners.team,
                extra_paths=owners.extra_paths,
            )

        # Unknown missing template — fail loud.
        raise SchemaError(
            f"codeowners_template {tpl_name!r} not found for profile {profile_name!r}",
            path="",
            hint=(
                f"Remove codeowners_template and set owners.layout, or place "
                f"{tpl_name} under meta config/templates/. "
                f"Legacy names: {', '.join(sorted(LEGACY_CODEOWNERS_TEMPLATES))}"
            ),
        )

    if owners.skip_codeowners:
        return None

    family = family_template_name(owners.layout, profile_name)
    return _render_family_body(
        family,
        org=org,
        team=owners.team,
        extra_paths=owners.extra_paths,
    )


def seed_codeowners(
    repo_path: Path,
    profile: HarnessProfile,
    profile_name: str,
    org: str,
    *,
    apply: bool,
    meta_templates: Path | None = None,
    warn_stream=None,
) -> None:
    """Write or preview .github/CODEOWNERS."""
    content = resolve_codeowners_content(
        profile,
        profile_name,
        org,
        meta_templates=meta_templates,
        warn_stream=warn_stream,
    )
    if content is None:
        if not apply:
            print("    [dry-run] CODEOWNERS  skipped (owners.layout: none)")
        else:
            print("  ·  CODEOWNERS  skipped (owners.layout: none)")
        return

    dest = repo_path / ".github" / "CODEOWNERS"
    if not apply:
        print(f"    [dry-run] CODEOWNERS  →  .github/CODEOWNERS")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"  ✔  CODEOWNERS  (org: {org})")
