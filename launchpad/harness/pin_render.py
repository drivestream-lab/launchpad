"""Generate .harness-pin.yaml from a harness profile (no per-stack templates)."""

from __future__ import annotations

from launchpad.schema.harness import HarnessProfile


def _community_skills_yaml_block(profile: HarnessProfile) -> str:
    if not profile.community_skills:
        return ""
    lines = ["community_skills:"]
    for spec in profile.community_skills:
        lines.append(f"  - source: {spec.source}")
        lines.append(f"    ref: {spec.ref}")
        lines.append(f"    skill: {spec.skill}")
    return "\n".join(lines)


def render_harness_pin(
    profile: HarnessProfile,
    profile_name: str,
    *,
    skill_names: list[str],
    delivery_contract: str,
    agent_skills_ref: str = "",
) -> str:
    """Return YAML text for ``.harness-pin.yaml``."""
    lines: list[str] = [
        f"profile: {profile_name}",
        f"delivery_contract: {delivery_contract}",
        "",
    ]

    con = profile.constitution
    if con is not None:
        lines.extend(
            [
                "rules:",
                f"  repo: {con.org}/{con.repo}",
                f"  ref: {con.ref}",
                "",
            ]
        )

    skill = profile.skills[0] if profile.skills else None
    if skill is not None:
        pin_ref = agent_skills_ref or skill.ref or "HEAD"
        skills_block = "\n".join(f"    - {name}" for name in skill_names)
        lines.extend(
            [
                "agent_skills:",
                f"  repo: {skill.org}/{skill.repo}",
                f"  ref: {pin_ref}",
                f"  profile: {profile_name}",
                "  skills:",
                skills_block if skills_block else "    []",
                "",
            ]
        )

    community = _community_skills_yaml_block(profile)
    if community:
        lines.append(community)
        lines.append("")

    # Trim trailing blank lines to a single trailing newline.
    text = "\n".join(lines).rstrip() + "\n"
    return text


def harness_pin_template_warn(profile_name: str, tpl_name: str) -> str:
    """Stderr message when harness_pin_template is set (ignored)."""
    return (
        f"WARN: harness_pin_template '{tpl_name}' is ignored "
        f"(pin is always generated from the harness profile).\n"
        f"      Remove harness_pin_template from config/harness-<org>.yaml "
        f"for profile '{profile_name}'."
    )
