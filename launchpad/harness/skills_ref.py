"""Resolve harness skills[].ref tokens (e.g. floating ``latest``)."""

from __future__ import annotations

import httpx

_API_TIMEOUT = 8.0
_PLATFORM_ORG = "drivestream-lab"


class SkillsRefResolveError(Exception):
    """Could not resolve a floating skills ref against GitHub."""


def resolve_skills_ref(
    org: str,
    repo: str,
    ref: str,
    *,
    client: httpx.Client | None = None,
) -> str:
    """Return a concrete git ref for pinning.

    ``latest`` (any case) resolves to GitHub ``releases/latest`` ``tag_name``.
    Any other non-empty ref is returned unchanged.
    """
    declared = (ref or "").strip() or "HEAD"
    if declared.lower() != "latest":
        return declared

    owner = (org or _PLATFORM_ORG).strip() or _PLATFORM_ORG
    name = (repo or "").strip()
    if not name:
        raise SkillsRefResolveError("skills repo is empty — cannot resolve latest")

    url = f"https://api.github.com/repos/{owner}/{name}/releases/latest"
    headers = {"Accept": "application/vnd.github+json"}

    try:
        if client is not None:
            response = client.get(url, headers=headers, timeout=_API_TIMEOUT)
        else:
            response = httpx.get(url, headers=headers, timeout=_API_TIMEOUT)
    except Exception as exc:
        raise SkillsRefResolveError(
            f"could not resolve latest release for {owner}/{name}: {exc}"
        ) from exc

    if response.status_code != 200:
        raise SkillsRefResolveError(
            f"could not resolve latest release for {owner}/{name}: "
            f"HTTP {response.status_code}"
        )

    tag = str(response.json().get("tag_name") or "").strip()
    if not tag:
        raise SkillsRefResolveError(
            f"latest release for {owner}/{name} has no tag_name"
        )
    return tag
