"""GitHub REST + GraphQL helpers for init-client / forge operations.

Idempotent helpers used by GitHubForgeProvider.  Safe to re-run after partial failure.
"""

from __future__ import annotations

import sys
from typing import Any
from urllib.parse import quote

from launchpad.github_client import GitHubClient, GitHubError


# ── Existence probes ──────────────────────────────────────────────────────────


def team_exists(client: GitHubClient, org: str, slug: str) -> bool:
    try:
        client.rest("GET", f"/orgs/{org}/teams/{slug}")
        return True
    except GitHubError:
        return False


def repo_access_state(client: GitHubClient, org: str, repo: str) -> str:
    """Return exists | missing | forbidden."""
    try:
        client.rest("GET", f"/repos/{org}/{repo}")
        return "exists"
    except GitHubError as exc:
        if exc.status == 404:
            return "missing"
        if exc.status == 403:
            return "forbidden"
        raise


def repo_exists(client: GitHubClient, org: str, repo: str) -> bool:
    return repo_access_state(client, org, repo) == "exists"


# ── Teams ─────────────────────────────────────────────────────────────────────


def ensure_team(
    client: GitHubClient,
    org: str,
    name: str,
    *,
    description: str = "",
    privacy: str = "closed",
) -> None:
    if team_exists(client, org, name):
        print(f"  Team exists: {org}/{name}")
        return
    print(f"  Creating team: {org}/{name}")
    client.rest(
        "POST",
        f"/orgs/{org}/teams",
        json_body={
            "name": name,
            "description": description,
            "privacy": privacy,
        },
    )
    print(f"  ✔  team created: {org}/{name}")


# ── Repos ─────────────────────────────────────────────────────────────────────


def ensure_repo(
    client: GitHubClient,
    org: str,
    name: str,
    *,
    description: str = "",
    private: bool = True,
) -> None:
    state = repo_access_state(client, org, name)
    if state == "exists":
        print(f"  Repo exists: {org}/{name}")
        return
    if state == "forbidden":
        raise RuntimeError(
            f"PAT cannot access {org}/{name} (403). "
            "Ensure your fine-grained PAT has access to this org's repositories."
        )
    print(f"  Creating repo: {org}/{name}")
    client.rest(
        "POST",
        f"/orgs/{org}/repos",
        json_body={
            "name": name,
            "private": private,
            "description": description or name,
            "auto_init": True,
        },
    )
    print(f"  ✔  repo created: {org}/{name}")


def add_team_to_repo(
    client: GitHubClient,
    org: str,
    repo: str,
    team_slug: str,
    *,
    permission: str = "push",
) -> None:
    print(f"  Grant team {team_slug} ({permission}) → {org}/{repo}")
    client.rest(
        "PUT",
        f"/orgs/{org}/teams/{team_slug}/repos/{org}/{repo}",
        json_body={"permission": permission},
    )


def team_repo_permission(
    client: GitHubClient,
    org: str,
    repo: str,
    team_slug: str,
) -> str | None:
    """Return the team's repository permission, or None when unavailable."""
    try:
        data = client.rest(
            "GET",
            f"/orgs/{org}/teams/{team_slug}/repos/{org}/{repo}",
        )
    except GitHubError as exc:
        if exc.status == 404:
            return None
        raise
    permission = data.get("permission")
    return str(permission) if permission else "pull"


# ── Delivery labels ───────────────────────────────────────────────────────────


def get_label(
    client: GitHubClient,
    org: str,
    repo: str,
    name: str,
) -> dict[str, Any] | None:
    """Return one label or None when it does not exist."""
    try:
        return client.rest(
            "GET",
            f"/repos/{org}/{repo}/labels/{quote(name, safe='')}",
        )
    except GitHubError as exc:
        if exc.status == 404:
            return None
        raise


def ensure_label(
    client: GitHubClient,
    org: str,
    repo: str,
    name: str,
    *,
    color: str,
    description: str = "",
) -> None:
    """Create or reconcile one repository label."""
    path = f"/repos/{org}/{repo}/labels/{quote(name, safe='')}"
    desired_color = color.lstrip("#").upper()
    current = get_label(client, org, repo, name)
    if current is None:
        print(f"  Creating label: {org}/{repo}#{name}")
        client.rest(
            "POST",
            f"/repos/{org}/{repo}/labels",
            json_body={
                "name": name,
                "color": desired_color,
                "description": description,
            },
        )
        print(f"  ✔  label created: {name}")
        return

    current_color = str(current.get("color") or "").upper()
    current_description = str(current.get("description") or "")
    if current_color == desired_color and current_description == description:
        print(f"  Label OK: {name}")
        return
    print(f"  Updating label: {org}/{repo}#{name}")
    client.rest(
        "PATCH",
        path,
        json_body={
            "new_name": name,
            "color": desired_color,
            "description": description,
        },
    )
    print(f"  ✔  label updated: {name}")


# ── Branch protection ─────────────────────────────────────────────────────────


def branch_exists(client: GitHubClient, org: str, repo: str, branch: str) -> bool:
    try:
        client.rest("GET", f"/repos/{org}/{repo}/branches/{branch}")
        return True
    except GitHubError as exc:
        if exc.status == 404:
            return False
        raise


def ensure_branch(
    client: GitHubClient,
    org: str,
    repo: str,
    branch: str,
    *,
    from_branch: str,
) -> None:
    """Create branch from from_branch if absent. Idempotent."""
    if not repo_exists(client, org, repo):
        print(f"  WARN: cannot create branch — repo missing: {org}/{repo}")
        return
    if branch_exists(client, org, repo, branch):
        print(f"  Branch exists: {org}/{repo}@{branch}")
        return
    if not branch_exists(client, org, repo, from_branch):
        print(
            f"  WARN: cannot create {branch!r} — source branch {from_branch!r} "
            f"not found on {org}/{repo}",
            file=sys.stderr,
        )
        return
    ref = client.rest("GET", f"/repos/{org}/{repo}/git/ref/heads/{from_branch}")
    sha = str((ref.get("object") or {}).get("sha") or "")
    if not sha:
        print(f"  WARN: cannot resolve SHA for {org}/{repo}@{from_branch}", file=sys.stderr)
        return
    print(f"  Creating branch: {org}/{repo}@{branch} from {from_branch}")
    client.rest(
        "POST",
        f"/repos/{org}/{repo}/git/refs",
        json_body={"ref": f"refs/heads/{branch}", "sha": sha},
    )
    print(f"  ✔  branch created: {org}/{repo}@{branch}")


def set_default_branch(client: GitHubClient, org: str, repo: str, branch: str) -> None:
    """Set default branch, creating it from auto_init ``main``/``master`` when needed.

    Org repos created with ``auto_init: true`` start on ``main``. Programmes that
    set ``policy.default_branch: develop`` previously failed with HTTP 422
    ("branch develop was not found"). Seed the target branch from an existing
    tip first, then flip the default.
    """
    if not repo_exists(client, org, repo):
        print(f"  WARN: cannot set default branch — repo missing: {org}/{repo}")
        return
    data = client.rest("GET", f"/repos/{org}/{repo}")
    current = str(data.get("default_branch") or "")
    if current == branch and branch_exists(client, org, repo, branch):
        print(f"  Default branch OK: {org}/{repo}@{branch}")
        return

    if not branch_exists(client, org, repo, branch):
        source = None
        for candidate in (current, "main", "master"):
            if candidate and candidate != branch and branch_exists(client, org, repo, candidate):
                source = candidate
                break
        if source is None:
            print(
                f"  ERROR: cannot set default branch {branch!r} on {org}/{repo} — "
                f"no seed branch (main/master/{current or '∅'}) exists yet",
                file=sys.stderr,
            )
            raise GitHubError(
                f"PATCH /repos/{org}/{repo} aborted: branch {branch!r} missing "
                "and no auto_init tip to fork from",
                status=422,
            )
        ensure_branch(client, org, repo, branch, from_branch=source)

    if current == branch:
        print(f"  Default branch OK: {org}/{repo}@{branch}")
        return
    print(f"  Setting default branch: {org}/{repo} → {branch}")
    client.rest(
        "PATCH",
        f"/repos/{org}/{repo}",
        json_body={"default_branch": branch},
    )
    print(f"  ✔  default branch set: {org}/{repo}@{branch}")


def update_branch_protection(
    client: GitHubClient,
    org: str,
    repo: str,
    branch: str,
    *,
    required_approvals: int = 1,
    dismiss_stale: bool = True,
) -> None:
    if not repo_exists(client, org, repo):
        print(f"  WARN: cannot protect branch — repo missing: {org}/{repo}")
        return
    print(f"  Branch protection: {org}/{repo}@{branch} (reviews={required_approvals})")
    payload: dict[str, Any] = {
        # GitHub requires this key even when no status checks are enforced.
        "required_status_checks": None,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": dismiss_stale,
            "required_approving_review_count": max(0, required_approvals),
        },
        "enforce_admins": False,
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "restrictions": None,
    }
    try:
        client.rest(
            "PUT",
            f"/repos/{org}/{repo}/branches/{branch}/protection",
            json_body=payload,
        )
        print(f"  ✔  branch protection enabled: {org}/{repo}@{branch}")
    except GitHubError as exc:
        if exc.status == 404:
            print(f"  WARN: branch protection skipped (404): branch {branch!r} not found")
            return
        detail = (exc.body or str(exc))[:300]
        print(f"  WARN: branch protection failed ({exc.status}): {detail}")
        return


# ── GitHub Projects v2 ───────────────────────────────────────────────────────


def _org_node_id(client: GitHubClient, org: str) -> str:
    data = client.graphql(
        """
        query($login: String!) {
          organization(login: $login) { id }
        }
        """,
        {"login": org},
    )
    node_id = data.get("organization", {}).get("id")
    if not node_id:
        raise GitHubError(f"organization not found: {org}")
    return str(node_id)


def _project_number_by_title(client: GitHubClient, org: str, title: str) -> int | None:
    data = client.graphql(
        """
        query($login: String!, $title: String!) {
          organization(login: $login) {
            projectsV2(first: 50, query: $title) {
              nodes { number title }
            }
          }
        }
        """,
        {"login": org, "title": title},
    )
    for node in data.get("organization", {}).get("projectsV2", {}).get("nodes") or []:
        if node.get("title") == title:
            return int(node["number"])
    return None


def _project_meta(client: GitHubClient, org: str, number: int) -> dict[str, Any]:
    data = client.graphql(
        """
        query($login: String!, $number: Int!) {
          organization(login: $login) {
            projectV2(number: $number) { id title url }
          }
        }
        """,
        {"login": org, "number": number},
    )
    proj = data.get("organization", {}).get("projectV2")
    if not proj:
        raise GitHubError(f"project #{number} not found in {org}")
    return proj


def _repo_node_id(client: GitHubClient, org: str, repo: str) -> str:
    data = client.graphql(
        """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) { id }
        }
        """,
        {"owner": org, "name": repo},
    )
    node_id = (data.get("repository") or {}).get("id")
    if not node_id:
        raise GitHubError(f"repository not found: {org}/{repo}")
    return str(node_id)


def ensure_org_project(client: GitHubClient, org: str, name: str) -> str:
    """Ensure an org-level Projects v2 board exists.  Returns the project node ID."""
    number = _project_number_by_title(client, org, name)
    if number is None:
        print(f"  Creating project board: {org} / {name!r}")
        org_id = _org_node_id(client, org)
        data = client.graphql(
            """
            mutation($ownerId: ID!, $title: String!) {
              createProjectV2(input: {ownerId: $ownerId, title: $title}) {
                projectV2 { number }
              }
            }
            """,
            {"ownerId": org_id, "title": name},
        )
        number = int(data["createProjectV2"]["projectV2"]["number"])
        print(f"  ✔  project board created: {org} / {name!r} (#{number})")
    else:
        print(f"  Project board exists: {org} / {name!r} (#{number})")

    meta = _project_meta(client, org, number)
    return str(meta["id"])


def link_repo_to_project(
    client: GitHubClient,
    org: str,
    repo: str,
    project_id: str,
) -> None:
    if not repo_exists(client, org, repo):
        print(f"  WARN: cannot link project — repo missing: {org}/{repo}")
        return
    print(f"  Linking {org}/{repo} → project")
    repo_id = _repo_node_id(client, org, repo)
    try:
        client.graphql(
            """
            mutation($projectId: ID!, $repositoryId: ID!) {
              linkProjectV2ToRepository(input: {
                projectId: $projectId
                repositoryId: $repositoryId
              }) {
                repository { name }
              }
            }
            """,
            {"projectId": project_id, "repositoryId": repo_id},
        )
        print(f"  ✔  linked {org}/{repo} → project")
    except GitHubError as exc:
        if "already" in str(exc.body).lower():
            print("  (already linked)")
        else:
            raise
