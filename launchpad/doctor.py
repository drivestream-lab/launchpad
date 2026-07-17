"""Preflight checks for launchpad (v0.5.10).

Checks:
  • clients.yaml exists and active client is resolvable
  • programme.yaml exists and is valid
  • programme_slug matches the active client id
  • env.d/<id>.env exists with a real GITHUB_TOKEN (not placeholder)
  • GitHub API is reachable with the token
  • .launchpad-version pin at meta root matches installed version
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from launchpad import __version__
from launchpad.clients import (
    ClientRegistryError,
    ENV_D_DIR,
    CLIENTS_FILE,
    config_dir_for_client,
    resolve_client_id,
    resolve_client_path,
)
from launchpad.github_client import GitHubClient, GitHubError


_TOKEN_PLACEHOLDER = "github_pat_REPLACE_ME"


def run(*, verbose: bool = False) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    print(f"launchpad {__version__}")
    print()

    # ── Client / clients.yaml ────────────────────────────────────────────────
    client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
    if not client_id:
        # Try resolving without an explicit arg (picks up default: or sole client)
        try:
            client_id = resolve_client_id("") or ""
        except ClientRegistryError:
            client_id = ""

    if not client_id:
        errors.append(
            f"no active client — pass --client <id> or set 'default:' in {CLIENTS_FILE}\n"
            "  First time? Run: launchpad onboard interview"
        )
    else:
        print(f"client:  {client_id}")
        env_file = ENV_D_DIR / f"{client_id}.env"
        if env_file.is_file():
            print(f"secrets: {env_file}")
        else:
            warnings.append(
                f"env file not found: {env_file}\n"
                f"  Create it with your GITHUB_TOKEN — run: launchpad onboard interview"
            )

    # ── Meta repo path / programme.yaml ─────────────────────────────────────
    meta_path: Path | None = None
    if client_id:
        try:
            meta_path = resolve_client_path(client_id)
            print(f"meta:    {meta_path}")
        except ClientRegistryError as exc:
            errors.append(str(exc))

    programme_slug_from_yaml: str = ""
    if meta_path:
        prog_path = meta_path / "config" / "programme.yaml"
        if prog_path.is_file():
            try:
                from launchpad.schema.programme import load_programme
                prog = load_programme(prog_path)
                programme_slug_from_yaml = prog.programme_slug
                print(f"programme: {prog.programme}  (slug: {prog.programme_slug}  org: {prog.org})")

                if client_id and programme_slug_from_yaml and client_id != programme_slug_from_yaml:
                    warnings.append(
                        f"client id '{client_id}' does not match "
                        f"programme_slug '{programme_slug_from_yaml}' in programme.yaml\n"
                        f"  Tip: the client id in clients.yaml should equal the programme_slug."
                    )
            except Exception as exc:
                warnings.append(f"programme.yaml invalid: {exc}")
        elif verbose:
            print("programme.yaml: not found  (run: launchpad onboard interview)")

        pin_path = meta_path / ".launchpad-version"
        if pin_path.is_file():
            pin = pin_path.read_text().strip()
            print(f"pinned:  {pin}")
            if pin != __version__:
                warnings.append(
                    f"installed v{__version__} != .launchpad-version pin '{pin}'\n"
                    f"  Update the pin or reinstall the matching version."
                )
        elif verbose:
            print(".launchpad-version: not pinned  (optional — add it to lock kit version)")

        harness_matches = list((meta_path / "config").glob("harness-*.yaml"))
        if harness_matches:
            try:
                from launchpad.schema.harness import load_harness

                harness = load_harness(harness_matches[0])
                if harness.delivery_contract:
                    print(f"delivery_contract: {harness.delivery_contract}")
                    print(
                        "  Tip: run `launchpad status --meta` to verify the "
                        "pinned prayog-skills contract and GitHub freshness"
                    )
                else:
                    print(
                        "delivery_contract: (not declared — legacy pin; "
                        "apply-gates skips)"
                    )
            except Exception as exc:
                warnings.append(f"harness YAML invalid: {exc}")

    # ── GitHub token ─────────────────────────────────────────────────────────
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not token:
        env_hint = ENV_D_DIR / f"{client_id or '<slug>'}.env"
        errors.append(
            f"GITHUB_TOKEN not set\n"
            f"  Add it to {env_hint} and make sure the env file is loaded.\n"
            f"  The token is loaded automatically when you pass --client <id>."
        )
    elif token == _TOKEN_PLACEHOLDER:
        env_file_path = ENV_D_DIR / f"{client_id or 'unknown'}.env"
        errors.append(
            f"GITHUB_TOKEN is still the placeholder value\n"
            f"  Replace it with a real PAT in {env_file_path}"
        )
    else:
        print("GITHUB_TOKEN: set")
        try:
            with GitHubClient(dry_run=False) as client:
                login = client.whoami()
            print(f"github user: {login}")
        except GitHubError as exc:
            errors.append(f"GitHub API error: {exc}")

    print()
    for w in warnings:
        print(f"WARN:  {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if errors:
        return 1

    print("doctor: OK")
    return 0
