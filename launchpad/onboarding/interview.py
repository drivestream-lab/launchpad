"""Greenfield onboard interview — day-1 meta config from operator answers.

Flow:
  1. Programme name / slug / GitHub org / workspace
  2. PM + PE team slugs (defaults: pm-team / pe-team) — written into YAML SSOT
  3. Creates <workspace>/<slug>-meta/config/ with all 5 YAML files
  4. Patches ~/.config/launchpad/clients.yaml with path + workspace
  5. Writes env.d/<slug>.env stub; prints NEXT

Team names and skills ref are not kit hard locks: teams come from answers;
prayog-skills uses floating ``ref: latest`` (resolved at apply-harness).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

import yaml

from launchpad.clients import CLIENTS_FILE, CONFIG_DIR, ENV_D_DIR
from launchpad.ui import format_next_box, shorten_path

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_DEFAULT_PM_TEAM = "pm-team"
_DEFAULT_PE_TEAM = "pe-team"


# ─── Prompt helpers ─────────────────────────────────────────────────────────


def _ask(
    label: str,
    default: str = "",
    *,
    required: bool = True,
    input_fn: Callable[[str], str] | None = None,
    out: TextIO = sys.stdout,
) -> str:
    reader = input_fn or input
    hint = f" [{default}]" if default else ""
    while True:
        value = reader(f"  {label}{hint}: ").strip()
        if not value:
            if default:
                return default
            if required:
                out.write("    (required)\n")
                continue
            return ""
        return value


def _ask_slug(
    label: str,
    default: str = "",
    *,
    input_fn: Callable[[str], str] | None = None,
    out: TextIO = sys.stdout,
) -> str:
    reader = input_fn or input
    while True:
        hint = f" [{default}]" if default else ""
        value = reader(f"  {label}{hint}: ").strip() or default
        if not value:
            out.write("    (required)\n")
            continue
        if not _SLUG_RE.match(value):
            out.write("    Must be lowercase [a-z][a-z0-9-]+\n")
            continue
        return value


def _derive_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ─── 5-YAML renderer ────────────────────────────────────────────────────────


def _render_programme(slug: str, programme: str, org: str, meta_repo: str) -> str:
    return f"""\
apiVersion: launchpad/v1
kind: Programme
programme: {programme}
programme_slug: {slug}
org: {org}
meta_repo: {meta_repo}
forge:
  provider: github
"""


def _render_governance(org: str, meta_repo: str, *, pm_team: str, pe_team: str) -> str:
    return f"""\
apiVersion: launchpad/v1
kind: GovernanceConfig

# Day 1: meta repo only.
# Add app repos incrementally (Day N) by uncommenting / adding repo blocks.
org: {org}

stack_profiles:
  meta-pm: Programme management & ADR meta repo
  # Add a stack for each technology profile you use; each needs a harness profile.
  # python-backend: Python / FastAPI microservice
  # nextjs-frontend: Next.js frontend or BFF
  # terraform-iac: Terraform infrastructure-as-code
  # go-backend: Go microservice

teams:
  - name: {pm_team}
    description: Product — PRD and meta develop merges
    privacy: closed
  - name: {pe_team}
    description: Platform engineering — delivery gates and technical review
    privacy: closed

repos:
  {meta_repo}:
    stack: meta-pm
    teams: [{pm_team}, {pe_team}]
    visibility: private
    description: Control-plane for {org}

policy:
  default_branch: main
  integration_branch: develop
  require_pr_reviews: 1
  dismiss_stale_reviews: true

project_board:
  enabled: true
  name: "{org} Board"
"""


def _render_harness(org: str, *, pe_team: str) -> str:
    return f"""\
apiVersion: launchpad/v1
kind: HarnessConfig
org: {org}

# Day 1: meta is PRD-ready. App profiles below are Day N (uncomment when needed).
# skills[].ref: latest  → apply-harness resolves GitHub releases/latest on each apply.
# Or pin an explicit tag (e.g. v0.5.0-rc.2) to freeze.
delivery_contract: sdd-delivery/v2
delivery_roles:
  engineering-gate: {pe_team}

profiles:
  meta-pm:
    # constitution: omitted — meta repos hold config/planning docs, not code.
    skills:
      - repo: prayog-skills
        ref: latest
    community_skills:
      - source: github/awesome-copilot
        ref: v1.0.0
        skill: prd
    skill_runtimes:
      - .agents/skills
      - .claude/skills
    codeowners_template: CODEOWNERS.meta-pm
    harness_pin_template: harness-pin.meta.yaml

  # ─── Day N — uncomment when you add this stack to governance ─────────────
  # python-backend:
  #   constitution:
  #     repo: python-services-rules
  #     ref: v2.1.0
  #   skills:
  #     - repo: prayog-skills
  #       ref: latest
  #   codeowners_template: CODEOWNERS.python-backend
  #   harness_pin_template: harness-pin.python-backend.yaml

  # nextjs-frontend:
  #   constitution:
  #     repo: nextjs-bff-rules
  #     ref: v0.1.4
  #   skills:
  #     - repo: prayog-skills
  #       ref: latest
  #   codeowners_template: CODEOWNERS.nextjs-frontend
  #   harness_pin_template: harness-pin.nextjs-frontend.yaml

  # terraform-iac:
  #   constitution:
  #     repo: terraform-infra-rules
  #     ref: v0.1.2
  #   skills:
  #     - repo: prayog-skills
  #       ref: latest
  #   codeowners_template: CODEOWNERS.terraform-iac
  #   harness_pin_template: harness-pin.terraform-iac.yaml

repos: {{}}
"""


def _render_scaffold(org: str) -> str:
    return f"""\
apiVersion: launchpad/v1
kind: ScaffoldConfig

# Scaffold is optional and entirely YAML-driven.
# Enable a block and fill in template + ref + context, then run:
#   launchpad apply-scaffold --meta --apply
org: {org}

meta:
  enabled: false
  engine: cookiecutter
  # template: gh:drivestream-lab/tenant-meta-foundation
  # ref: v0.1.0
  # context:
  #   project_name: {org}
  #   programme_slug: <slug>
  #   github_org: {org}

# App repos — add a block for each repo when you are ready to scaffold.
repos: {{}}

  # ── Python / FastAPI microservice ───────────────────────────────────────
  # <repo-name>:
  #   enabled: true
  #   engine: cookiecutter
  #   template: gh:drivestream-lab/python-fastapi-foundation
  #   ref: v0.3.0
  #   context:
  #     project_name: <repo-name>
  #     has_kafka: false
  #     has_postgres: true

  # ── Next.js BFF / frontend ───────────────────────────────────────────────
  # <repo-name>:
  #   enabled: true
  #   engine: cookiecutter
  #   template: gh:drivestream-lab/nextjs-bff-foundation
  #   ref: v0.1.0
  #   context:
  #     project_name: <repo-name>
  #     has_graphql: false
"""


def _render_catalog(org: str, meta_repo: str, *, pm_team: str, pe_team: str) -> str:
    return f"""\
apiVersion: launchpad/v1
kind: ServiceCatalog

# Required — at least one service must be listed.
# Day 1: only the meta repo is live.
# Promote app repos from 'planned' to 'live' once they are scaffolded.
org: {org}

services:
  {meta_repo}:
    stack: meta-pm
    description: Control-plane for {org}
    status: live
    teams: [{pm_team}, {pe_team}]
    links:
      repo: https://github.com/{org}/{meta_repo}

  # ─── Day-N examples (uncomment when the repo is live) ───────────────────
  #
  # <slug>-api:
  #   stack: python-backend
  #   description: Core platform microservice
  #   status: planned
  #   teams: [{pe_team}]
  #
  # <slug>-web:
  #   stack: nextjs-frontend
  #   description: Web UI
  #   status: planned
  #   teams: [{pe_team}]
"""


# ─── Registry helpers ────────────────────────────────────────────────────────


def _patch_clients_yaml(slug: str, meta_path: Path, *, workspace: Path) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CLIENTS_FILE.is_file():
        with CLIENTS_FILE.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    clients: list[dict[str, Any]] = data.get("clients") or []
    if not isinstance(clients, list):
        clients = []

    entry = {
        "id": slug,
        "path": str(meta_path),
        "workspace": str(workspace),
        "forge": "github",
    }
    clients = [c for c in clients if not (isinstance(c, dict) and c.get("id") == slug)]
    clients.append(entry)
    data["clients"] = clients

    with CLIENTS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


def _write_env_stub(slug: str, org: str, meta_path: Path) -> Path:
    ENV_D_DIR.mkdir(parents=True, exist_ok=True)
    path = ENV_D_DIR / f"{slug}.env"
    if path.is_file():
        return path
    path.write_text(
        f"# {slug} factory secrets\n"
        f"# ─────────────────────────────────────────────────────────────────\n"
        f"# 1. Create a GitHub PAT with these scopes:\n"
        f"#      repo, admin:org, project, delete_repo\n"
        f"#    (GitHub → Settings → Developer settings → Personal access tokens → Fine-grained)\n"
        f"# 2. Paste the token below (replace github_pat_REPLACE_ME)\n"
        f"# 3. Save, then run:  chmod 600 {path}\n"
        f"# ─────────────────────────────────────────────────────────────────\n"
        f"GITHUB_TOKEN=github_pat_REPLACE_ME\n"
        f"\n"
        f"# GitHub org:  {org}\n"
        f"# Meta repo:   https://github.com/{org}/{slug}-meta\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


# ─── Public entry point ──────────────────────────────────────────────────────


def run_interview(
    *,
    input_fn: Callable[[str], str] | None = None,
    out: TextIO = sys.stdout,
) -> None:
    """Run the interview, write config files, patch registry, print NEXT."""
    out.write("\n")
    out.write("╔══════════════════════════════════════════╗\n")
    out.write("║   launchpad — onboard interview          ║\n")
    out.write("╚══════════════════════════════════════════╝\n")
    out.write("\n")
    out.write("Day 1 sets up your meta programme locally.\n")
    out.write("Team slugs you enter are written into governance/harness YAML;\n")
    out.write("init-client creates those GitHub teams from the YAML.\n\n")

    programme = _ask("Programme name  (e.g. KOLA)", input_fn=input_fn, out=out)

    derived = _derive_slug(programme)
    out.write(f"\n  Auto-derived slug: {derived}\n")
    slug = _ask_slug(
        "Programme slug  (confirm or override)",
        derived,
        input_fn=input_fn,
        out=out,
    )

    out.write("\n  GitHub org — the exact organisation slug on GitHub.\n")
    out.write("  Example: apex-common, acme-corp, my-startup\n")
    org = _ask("GitHub org", input_fn=input_fn, out=out)

    default_ws = str(Path("~/Workspace").expanduser())
    out.write("\n  Parent directory where your meta repo will live.\n")
    workspace = _ask("Workspace path", default_ws, input_fn=input_fn, out=out)

    out.write("\n  Day-1 teams (created later by init-client from governance YAML).\n")
    pm_team = _ask_slug(
        "PM team slug  (product / PRD / meta)",
        _DEFAULT_PM_TEAM,
        input_fn=input_fn,
        out=out,
    )
    pe_team = _ask_slug(
        "PE team slug  (engineering gates)",
        _DEFAULT_PE_TEAM,
        input_fn=input_fn,
        out=out,
    )

    meta_repo = f"{slug}-meta"
    workspace_path = Path(workspace).expanduser().resolve()
    meta_path = workspace_path / meta_repo
    config_dir = meta_path / "config"

    out.write("\n")
    out.write("─" * 50 + "\n")
    out.write(f"  programme:       {programme}\n")
    out.write(f"  slug:            {slug}\n")
    out.write(f"  org:             {org}\n")
    out.write(f"  meta repo:       {meta_repo}\n")
    out.write(f"  pm team:         {pm_team}\n")
    out.write(f"  pe team:         {pe_team}\n")
    out.write("  prayog skills:   ref: latest  (resolved on apply-harness)\n")
    out.write(f"  workspace:       {workspace_path}\n")
    out.write(f"  local path:      {meta_path}\n")
    out.write("─" * 50 + "\n\n")

    config_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {
        "programme.yaml": _render_programme(slug, programme, org, meta_repo),
        f"governance-{org}.yaml": _render_governance(
            org, meta_repo, pm_team=pm_team, pe_team=pe_team
        ),
        f"harness-{org}.yaml": _render_harness(org, pe_team=pe_team),
        f"scaffold-{org}.yaml": _render_scaffold(org),
        f"service-catalog-{org}.yaml": _render_catalog(
            org, meta_repo, pm_team=pm_team, pe_team=pe_team
        ),
    }

    for filename, content in files.items():
        fpath = config_dir / filename
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")
            out.write(f"  ✔  {fpath.relative_to(meta_path)}\n")
        else:
            out.write(f"  –  {fpath.relative_to(meta_path)}  (already exists, skipped)\n")

    _patch_clients_yaml(slug, meta_path, workspace=workspace_path)
    out.write(f"\n  ✔  ~/.config/launchpad/clients.yaml  (id: {slug})\n")
    out.write(f"       path:      {meta_path}\n")
    out.write(f"       workspace: {workspace_path}\n")

    env_path = _write_env_stub(slug, org, meta_path)
    out.write(f"  ✔  {env_path}  (PAT stub)\n")

    env_display = shorten_path(env_path)
    out.write("\n")
    out.write(
        format_next_box([
            f"1. Open: {env_display}",
            "Replace github_pat_REPLACE_ME with your GitHub PAT",
            "Scopes: repo, admin:org, project",
            f"2. chmod 600 {env_display}",
            f"3. launchpad --client {slug} doctor",
            f"4. launchpad --client {slug} init-client --meta --apply",
            f"5. launchpad --client {slug} apply-harness --meta --apply",
            f"6. launchpad --client {slug} apply-gates --meta --apply",
        ])
    )
    out.write("\n")
