"""apply-forge-templates — seed issue forms and PR template from kit + governance.

Writes contributor-facing forge artifacts into the local repo clone (GitHub today;
GitLab planned v0.6). Does not touch harness pins, skills, or CODEOWNERS.

Usage:
  launchpad apply-forge-templates --meta [--apply]
  launchpad apply-forge-templates --repo <name> [--apply]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from launchpad.clients import resolve_programme_workspace
from launchpad.forge.templates.render import (
    build_render_context,
    get_layout,
    kit_templates_dir,
    render_template,
)
from launchpad.schema import SchemaError
from launchpad.schema.governance import load_governance
from launchpad.schema.programme import load_programme
from launchpad.ui import print_next_box


def _find_config(config_dir: Path, pattern: str) -> Path | None:
    matches = list(config_dir.glob(pattern))
    return matches[0] if matches else None


def _apply_forge_templates_to_repo(
    repo_path: Path,
    *,
    is_meta: bool,
    provider: str,
    context: dict[str, str],
    apply: bool,
    force: bool,
) -> int:
    kit_dir = kit_templates_dir()
    entries = get_layout(provider, is_meta=is_meta)
    errors = 0

    for entry in entries:
        src = kit_dir / entry.kit_name
        dest = repo_path / entry.dest_rel

        if not src.is_file():
            print(f"  WARN: kit template missing: {entry.kit_name} — skipping", file=sys.stderr)
            errors += 1
            continue

        existed = dest.is_file()
        if existed and not force:
            if not apply:
                print(f"    [dry-run] skip (exists)  {entry.dest_rel}")
            else:
                print(f"  –  skip (exists)  {entry.dest_rel}  (use --force to overwrite)")
            continue

        content = render_template(src.read_text(encoding="utf-8"), context)

        if not apply:
            action = "overwrite" if existed and force else "write"
            print(f"    [dry-run] {action}  {entry.kit_name}  →  {entry.dest_rel}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        verb = "overwrote" if existed else "wrote"
        print(f"  ✔  {verb}  {entry.dest_rel}  ← {entry.kit_name}")

    return 1 if errors else 0


def run_apply_forge_templates(
    *,
    meta: bool = False,
    repo_name: str = "",
    apply: bool = False,
    force: bool = False,
    config_dir: Path | None = None,
    workspace: Path | None = None,
    client_id: str | None = None,
) -> int:
    if not meta and not repo_name:
        print("ERROR: pass --meta or --repo <name>", file=sys.stderr)
        return 1

    if config_dir is None:
        raise RuntimeError("config_dir not resolved — pass --client <id> or run launchpad onboard interview")
    cdir = config_dir

    gov_path = _find_config(cdir, "governance-*.yaml")
    if gov_path is None:
        print(f"ERROR: governance-<org>.yaml not found in {cdir}", file=sys.stderr)
        return 1

    prog_path = cdir / "programme.yaml"
    if not prog_path.is_file():
        print(f"ERROR: programme.yaml not found in {cdir}", file=sys.stderr)
        return 1

    try:
        gov = load_governance(gov_path)
        prog = load_programme(prog_path)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    provider = prog.forge_provider
    if provider == "gitlab":
        print(
            "ERROR: forge provider 'gitlab' is not yet supported for apply-forge-templates "
            "(planned v0.6).",
            file=sys.stderr,
        )
        return 1

    ws = resolve_programme_workspace(
        client_id=client_id,
        config_dir=config_dir,
        override=workspace,
    )
    meta_repo = prog.meta_repo
    target = meta_repo if meta else repo_name

    if not meta and repo_name not in gov.repos:
        print(f"ERROR: repo '{repo_name}' not in governance yaml", file=sys.stderr)
        return 1

    repo_path = Path(ws).expanduser().resolve() / target
    context = build_render_context(gov, prog)
    scope = "meta" if meta else "app"

    print(f"apply-forge-templates  →  {gov.org}/{target}  [{scope}, provider: {provider}]")
    if not repo_path.is_dir():
        print(f"  WARN: local clone not found at {repo_path}")
        print("  Clone it first, then re-run apply-forge-templates.")
        if apply:
            return 1

    result = _apply_forge_templates_to_repo(
        repo_path,
        is_meta=meta,
        provider=provider,
        context=context,
        apply=apply,
        force=force,
    )

    if not apply:
        target_flag = "--meta" if meta else f"--repo {target}"
        force_hint = " --force" if force else ""
        print_next_box([f"launchpad apply-forge-templates {target_flag} --apply{force_hint}"])
    else:
        client_id = os.environ.get("LAUNCHPAD_CLIENT", "").strip()
        client_prefix = f"--client {client_id} " if client_id else ""
        target_flag = "--meta" if meta else f"--repo {target}"
        print_next_box([
            'git add .github/ && git commit -m "chore: forge templates"',
            f"launchpad {client_prefix}status {target_flag}".strip(),
        ])

    return result
