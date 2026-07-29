from __future__ import annotations

from typing import Any

from launchpad.github_client import GitHubError
from launchpad.github_ops import ensure_label, team_repo_permission


class FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict | None]] = []

    def rest(self, method: str, path: str, *, json_body: dict | None = None):
        self.calls.append((method, path, json_body))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_ensure_label_creates_missing_label() -> None:
    client = FakeClient([GitHubError("missing", status=404), {}])
    ensure_label(
        client,  # type: ignore[arg-type]
        "org",
        "repo",
        "impact-map-pending",
        color="bfd4f2",
        description="prd-impact-acceptance awaiting PE review",
    )
    assert client.calls[-1] == (
        "POST",
        "/repos/org/repo/labels",
        {
            "name": "impact-map-pending",
            "color": "BFD4F2",
            "description": "prd-impact-acceptance awaiting PE review",
        },
    )


def test_ensure_label_is_idempotent() -> None:
    client = FakeClient(
        [{"color": "bfd4f2", "description": "prd-impact-acceptance awaiting PE review"}]
    )
    ensure_label(
        client,  # type: ignore[arg-type]
        "org",
        "repo",
        "impact-map-pending",
        color="BFD4F2",
        description="prd-impact-acceptance awaiting PE review",
    )
    assert len(client.calls) == 1


def test_ensure_label_updates_drift() -> None:
    client = FakeClient([{"color": "ffffff", "description": "old"}, {}])
    ensure_label(
        client,  # type: ignore[arg-type]
        "org",
        "repo",
        "impact-map-pending",
        color="BFD4F2",
        description="prd-impact-acceptance awaiting PE review",
    )
    assert client.calls[-1][0] == "PATCH"


def test_team_repo_permission_reports_access() -> None:
    client = FakeClient([{"permission": "pull"}])
    assert (
        team_repo_permission(  # type: ignore[arg-type]
            client, "org", "repo", "pe-team"
        )
        == "pull"
    )
