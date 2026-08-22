"""Owners / CODEOWNERS layout families and migration defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from launchpad.schema.errors import SchemaError

# Layout families shipped in kit templates/codeowners/
LAYOUT_FAMILIES = frozenset(
    {
        "app_src",
        "app_nextjs",
        "flink",
        "iac",
        "meta",
        "android_kotlin",
        "ios_swift",
        "none",
    }
)

# Known stacks: remount without tenant owners: block.
# edge-agent uses app_src in YAML; renderer selects family.app_edge for parity.
PROFILE_OWNER_DEFAULTS: dict[str, dict[str, Any]] = {
    "meta-pm": {"team": "pm-team", "layout": "meta"},
    "python-backend": {"team": "backend-devs", "layout": "app_src"},
    "nextjs-frontend": {"team": "frontend-devs", "layout": "app_nextjs"},
    "edge-agent": {"team": "edge-agent-devs", "layout": "app_src"},
    "flink": {"team": "data-platform-devs", "layout": "flink"},
    "terraform-iac": {"team": "platform-devs", "layout": "iac"},
    "platform-tooling": {"team": "", "layout": "none"},
}

# Legacy kit filenames → layout family (compat shim).
LEGACY_CODEOWNERS_TEMPLATES: dict[str, str] = {
    "CODEOWNERS.python-backend": "app_src",
    "CODEOWNERS.nextjs-frontend": "app_nextjs",
    "CODEOWNERS.flink": "flink",
    "CODEOWNERS.terraform-iac": "iac",
    "CODEOWNERS.meta-pm": "meta",
    "CODEOWNERS.edge-agent": "app_edge",
}

# Internal family file for edge-shaped app_src (docker + feasibility with PM).
EDGE_APP_SRC_FAMILY = "app_edge"


@dataclass(frozen=True)
class OwnersConfig:
    """Resolved owners block for CODEOWNERS rendering."""

    team: str
    layout: str
    extra_paths: tuple[str, ...] = field(default_factory=tuple)

    @property
    def skip_codeowners(self) -> bool:
        return self.layout == "none"


def parse_owners_raw(
    raw: Any,
    *,
    profile: str,
    path: str,
) -> OwnersConfig | None:
    """Parse optional owners: mapping; None if absent."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise SchemaError(
            f"profiles.{profile!r}.owners must be a mapping",
            path=path,
        )
    layout = str(raw.get("layout") or "").strip()
    team = str(raw.get("team") or "").strip()
    extras_raw = raw.get("extra_paths") or []
    if extras_raw and not isinstance(extras_raw, list):
        raise SchemaError(
            f"profiles.{profile!r}.owners.extra_paths must be a list",
            path=path,
        )
    extras = tuple(str(p).strip() for p in extras_raw if str(p).strip())

    if not layout:
        raise SchemaError(
            f"profiles.{profile!r}.owners.layout is required when owners is set",
            path=path,
            hint=f"Use one of: {', '.join(sorted(LAYOUT_FAMILIES))}",
        )
    if layout not in LAYOUT_FAMILIES:
        raise SchemaError(
            f"profiles.{profile!r}.owners.layout {layout!r} is unknown",
            path=path,
            hint=f"Known layouts: {', '.join(sorted(LAYOUT_FAMILIES))}",
        )
    if layout != "none" and not team:
        raise SchemaError(
            f"profiles.{profile!r}.owners.team is required when layout is not 'none'",
            path=path,
            hint="Example: owners: { team: backend-devs, layout: app_src }",
        )
    return OwnersConfig(team=team, layout=layout, extra_paths=extras)


def resolve_owners(profile_name: str, owners: OwnersConfig | None) -> OwnersConfig:
    """Merge explicit owners with migration defaults for known stacks."""
    if owners is not None:
        return owners
    defaults = PROFILE_OWNER_DEFAULTS.get(profile_name)
    if defaults is None:
        raise SchemaError(
            f"profiles.{profile_name!r}: owners.team and owners.layout are required "
            f"for new stacks (no migration default)",
            path="",
            hint=(
                "Add owners: { team: <github-team>, layout: <family> } "
                f"or layout: none. Known layouts: {', '.join(sorted(LAYOUT_FAMILIES))}"
            ),
        )
    return OwnersConfig(
        team=str(defaults.get("team") or ""),
        layout=str(defaults["layout"]),
        extra_paths=tuple(defaults.get("extra_paths") or ()),
    )


def family_template_name(layout: str, profile_name: str) -> str:
    """Map layout (+ known edge profile) to kit family.* filename stem."""
    if layout == "none":
        return "none"
    if layout == "app_src" and profile_name == "edge-agent":
        return EDGE_APP_SRC_FAMILY
    if layout == "app_src":
        return "app_src"
    return layout
