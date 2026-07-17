# Changelog

All notable changes to the launchpad kit. Install a release tag:

```bash
pipx install "launchpad @ git+https://github.com/drivestream-lab/launchpad@<tag>"
launchpad --version   # should match <slug>-meta/.launchpad-version
```

Pick `<tag>` from the latest section below or [GitHub Releases](https://github.com/drivestream-lab/launchpad/releases).

---

## [0.5.21] — 2026-07-17

### Changed

- **`AGENTS.md` ownership contract (Option A):** launchpad regenerates only the
  marked harness block between `<!-- launchpad:harness-start -->` and
  `<!-- launchpad:harness-end -->`. Team sections outside the markers
  (Run/verify, Product, local notes) are never overwritten.
- Greenfield seed writes templates that already include the markers.
- Brownfield without markers: **skip** (preserve file). One-shot adopt with
  `apply-harness --adopt-agents` inserts the managed block and keeps the rest.
- AGENTS templates: workflow path is `prayog-skills/workflow.yaml` (root submodule).
- **`status --repo` skills drift** checks `prayog-skills/` at repo root (not the
  pre-v0.5.20 nested `.agents/skills/prayog-skills/` path).
- **`apply-gates`** skips with exit 0 when `delivery_contract` is omitted
  (legacy pin); still requires a contract-compatible prayog pin when declared.
- **`status --meta`** reports prayog-skills declared refs vs GitHub
  `releases/latest` (advisory only — tenants own `skills[].ref` bumps).
- Docs/examples: drop stale `v0.4.3-rc.1`; pin choice is tenant-owned via
  GitHub latest (illustrative examples use `v0.4.3`).

---

## [0.5.20] — 2026-07-15

### Changed

- **`prayog-skills` submodule mounts at repo root** (`prayog-skills/`) instead of
  `.agents/skills/prayog-skills/`, so only hub-selected skills are activated under
  `.agents/skills/` / `.claude/skills/`. Re-run `apply-harness --apply` and commit
  the updated gitlink after upgrading.
- Constitution `repo` accepts `org/repo` slugs (e.g.
  `drivestream-lab/python-services-rules`); org is parsed from the slug when present.

---

## [0.5.19] — 2026-07-14

### Fixed

- **`env.d/<client>.env` is SSOT for factory PATs** — `load_dotenv(..., override=True)`
  so a stale shell `GITHUB_TOKEN` / `GH_TOKEN` no longer shadows the client file
  (avoids private-repo label 404s when ambient env wins).

---

## [0.5.18] — 2026-07-14

### Added

- **`board-bind`** — resolve programme engineering board from governance YAML
  (read-only meta); optional `--apply` links repo(s) to the org Project.
- Delivery-contract / workflow verification against the pinned Prayog checkout;
  contract recorded in harness pins and `status`.
- **`apply-gates`** — dry-run/apply for contract-declared labels and review-role
  access validation.
- Profile token `app` — stack-agnostic Gate 2 labels for any non-meta-pm harness.
- `apply-harness --repo` seeds delivery workflows (`ci.yml`,
  `policy-branch-name.yml`, `board-seed-gate.yml`) when `delivery_contract` is set.
- `AGENTS.md` programme board section (`{{BOARD_NAME}}`, `{{BOARD_URL}}`) for
  app repos with a delivery contract.

### Changed

- **`workspace` lives in `~/.config/launchpad/clients.yaml`** (machine-local).
  Shared `programme.yaml` must not contain `workspace` — schema fails closed.
- Clone layout: `clients[].workspace` or default `path.parent`.
- `onboard interview` writes `path` + `workspace` into clients.yaml only.
- Delivery playbook documents Draft spec PR, Gate 2, PE attestation, and
  merge → `/board-seed` → `/pre-implement` sequencing (pairs with Prayog v0.4.3).
- Existing team-owned `AGENTS.md` preserved in full on re-apply.

### Removed

- **`LAUNCHPAD_TENANT_ROOT`** — unused env override; docs and examples purged.
  Use `--client` / `clients.yaml`, or `--config-dir` for scripts.

---

## [0.5.17] — 2026-07-10

### Added

- **`apply-harness`** seeds `.gitignore` harness block (`gitignore.harness` template) so skill symlink mirrors are ignored
- **`examples/tenant-meta/.gitignore`** — skeleton for Path B onboarding

### Changed

- Upgrades legacy `.agents/skills/*/` patterns to `.agents/skills/*` on re-apply (symlinks vs directories)

---

## [0.5.16] — 2026-07-10

### Added

- **`docs/`** four-pillar layout — setup, onboarding, scaffolding, contributing
- **`playbook/`** subdirs — `ship/`, `harness/`, `github/`, `operator/`, `wiki/`
- **`docs/onboarding/`** — bootstrap prerequisites, factory CLI, exit criteria
- **`examples/agent-prompt-templates.md`** — moved from playbook
- **`CHANGELOG.md`** at repo root as version SSOT for docs (`@<tag>`)

### Changed

- Onboarding docs folded: org setup → `tenant-meta.md`; Cursor ↔ GitHub → `engineer-setup.md`
- **`apply-harness`** preserves existing `AGENTS.md` **Run and verify** section on re-sync
- Harness docs aligned with gitignored skill symlinks + tracked submodules model
- Kit templates and cross-links updated for new paths

### Removed

- Flat `playbook/*.md` files at playbook root (replaced by subdirs + `docs/onboarding/`)
- Obsolete `docs/` files (setup-guide, greenfield, onboarding-wizard, blog, etc.) — no redirects
- **`setup.py`** — unused wheel hook; packaging is `pyproject.toml` only (`launchpad/templates/` via `package-data`)

---

## [0.5.15] — 2026-07-10

### Added

- **`apply-forge-templates`** — seed `.github/ISSUE_TEMPLATE/` and `pull_request_template.md` from kit + governance
- Harness skill **hub** materialization with **community skills** support
- **`print_next_box`** — shared CLI helper for consistent NEXT output across commands
- Forge template staleness checks in **`status`**

### Changed

- **`status`** — forge template drift detection; hub + runtime skill path checks
- Kit issue templates use governance placeholders (`{{REPO_LIST_YAML}}`, `{{BOARD_URL}}`, etc.)

---

## [0.5.14] — 2026-07-09

### Added

- Harness skill **hub** (`.harness/skills/<name>/`) mirrored into `skill_runtimes` (default `.agents/skills`, `.claude/skills`)
- **`community_skills`** and **`skill_runtimes`** on harness profiles; community submodules under `.harness/community/`
- **`prayog_profile`** optional alias when harness stack name differs from prayog profile filename

### Changed

- **`apply-harness`** resolves skill names from prayog `profiles/*.yaml` at pinned ref (no Python fallbacks)
- **`status`** checks hub + all runtime paths; fails if prayog profile missing at pinned ref

---

## [0.5.13] — 2026-06

### Added

- **`CODEOWNERS.terraform-iac`** and **`harness-pin.terraform-iac.yaml`** harness templates
- Terraform-iac stack examples and docs

### Changed

- **`apply-harness`** substitutes `terraform-infra-rules` in harness pin templates
- **`init-client`** creates `develop` from `main` (`policy.integration_branch`) and protects both branches
- **`apply-harness`** pins constitution and prayog-skills as git submodules; improved tag fetch/checkout
- **`status --repo`** skills submodule drift check
- **`apply-scaffold`** helpful `--force` hint when output directory already exists
- Restore **`github_ops.py`** for GitHub forge (teams, repos, branch protection, projects)

---

## [0.5.11] — 2026-05

### Changed

- Align playbook, docs, examples, and templates with the 5-command CLI (remove stale commands)
- **`apply-harness`** seeds agent skills under **`.agents/skills/`** (removes legacy `.cursor/skills` submodule)
- Wiki publish documented as manual git flow (no `publish-wiki` CLI)

---

## [0.5.10] — 2026-04

### Added

- **5-YAML config model** — programme, governance, harness, scaffold, service-catalog
- **5-command CLI** — `onboard interview`, `init-client`, `apply-scaffold`, `apply-harness`, `status`
- **`onboard interview`** — 4 questions → writes config YAMLs + client registry + PAT stub
- GitHub-only forge (GitLab planned)

### Removed

- Legacy commands: `setup-gitflow`, `seed-work`, `bootstrap-project`, public `onboard apply/plan/show`

---

## Earlier releases

See git history and [GitHub Releases](https://github.com/drivestream-lab/launchpad/releases) for pre-0.5.10 tags.
