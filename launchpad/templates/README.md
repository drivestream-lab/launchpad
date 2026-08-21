# Templates (launchpad kit)

Reference files seeded by factory commands into each repo clone.

**SSOT:** launchpad kit `templates/` (installed with pipx / editable install).
Optional tenant overrides: `<meta>/config/templates/` (for custom CODEOWNERS files).

---

## Seeded by `apply-harness`

| Artifact | Source | Destination |
|----------|--------|-------------|
| CODEOWNERS | Layout family from `owners.layout` (or legacy/custom `codeowners_template`) | `.github/CODEOWNERS` |
| Harness pin | **Generated** from harness profile (constitution + skills) | `.harness-pin.yaml` |
| AGENTS.md | `AGENTS.md` / `AGENTS.meta.md` | `AGENTS.md` |
| Gitignore (harness) | `gitignore.harness` | `.gitignore` (append or upgrade symlink patterns) |
| Delivery workflows | `github/workflows/*.yml` when `delivery_contract` is set | `.github/workflows/` (app repos only; skip if file exists) |
| Constitution | rules repo URL from harness profile | `.cursor/rules/` submodule |
| Skills | skill repos from harness profile | `.harness/skills/` hub + runtime symlinks |

Substitutes `example-org` → actual GitHub org from `governance-<org>.yaml` in CODEOWNERS.
Substitutes owning team from `owners.team` (or migration defaults for known stacks).

---

## Seeded by `apply-forge-templates`

Contributor-facing forge artifacts (GitHub today; GitLab planned v0.6).

| Artifact | Kit source | Destination (GitHub) |
|----------|------------|----------------------|
| Issue forms (meta) | `issues/*.yml` | `.github/ISSUE_TEMPLATE/*.yml` |
| Issue forms (app) | `issues/*.app.yml` | `.github/ISSUE_TEMPLATE/*.yml` |
| PR template | `pull_request_template.md` | `.github/pull_request_template.md` |

Substitutions from `governance-<org>.yaml` + `programme.yaml`: org, meta repo, board URL, repo list (Codebase dropdown on meta).

```bash
launchpad apply-forge-templates --meta --apply
launchpad apply-forge-templates --repo <name> --apply
```

Use `--force` to overwrite after governance repo list changes.

---

## CODEOWNERS layout families (`templates/codeowners/`)

Kit grows with **layout families**, not per-stack files. Set in harness YAML:

```yaml
owners:
  team: backend-devs
  layout: app_src
  # extra_paths: [/model_checkpoints/]   # optional
```

| `owners.layout` | Family file | Typical stacks |
|-----------------|-------------|----------------|
| `app_src` | `family.app_src` | `python-backend`, `edge-inference-engine` |
| *(edge-agent)* | `family.app_edge` | `edge-agent` (same `app_src` layout key; docker-shaped) |
| `app_nextjs` | `family.app_nextjs` | `nextjs-frontend` |
| `flink` | `family.flink` | `flink` |
| `iac` | `family.iac` | `terraform-iac` |
| `meta` | `family.meta` | `meta-pm` |
| `android_kotlin` | `family.android_kotlin` | `android-kotlin` → team `mobile-devs` |
| `ios_swift` | `family.ios_swift` | `ios-swift` → team `mobile-devs` |
| `none` | *(skip write)* | `platform-tooling`; deferred embedded/RTOS |

**Legacy:** enrolled metas may still set `codeowners_template: CODEOWNERS.python-backend`.
Those names map to families with a **stderr WARN + fix instructions** (v0.5.36+).
Custom files: place under `meta/config/templates/` and keep `codeowners_template: <filename>`.

**Deprecated:** `harness_pin_template` is ignored; pin is always generated (WARN once per apply).

---

## Reference copies (manual deploy when no delivery_contract)

Copy into each repo as needed when not using `delivery_contract` in harness config.
See [playbook/github/github-enforcement.md](../../playbook/github/github-enforcement.md).

### GitHub workflows

When `harness-<org>.yaml` sets `delivery_contract` (e.g. `sdd-delivery/v2`),
`apply-harness --repo <name> --apply` seeds these into `.github/workflows/`
(skip if the file already exists):

| File | Purpose |
|------|---------|
| `github/workflows/ci.yml` | Placeholder CI — job name `ci` for required checks |
| `github/workflows/policy-branch-name.yml` | Branch name validation on PRs to `develop` |

Manual-only workflows (not auto-seeded):

| File | Purpose |
|------|---------|
| `github/workflows/policy-merge-source.yml` | Merge-source validation on PRs to `main` |

### Issue templates

`*.app.yml` variants are for app repos; plain `*.yml` for the meta repo.

| File | Type |
|------|------|
| `issues/feature.yml` / `feature.app.yml` | New capability |
| `issues/bug.yml` / `bug.app.yml` | Defect |
| `issues/chore.yml` / `chore.app.yml` | Non-functional work |
| `issues/config.yml` / `config.app.yml` | Config / infra change |

### Agent guides and PR template

| File | Typical use |
|------|-------------|
| `AGENTS.md` | App repo agent router (customize per repo) |
| `AGENTS.meta.md` | Meta repo agent router |
| `pull_request_template.md` | `.github/pull_request_template.md` |
| `INIT-PRD-outline.md` | PM PRD starter doc |
| `INIT-spec-PR.md` | Spec PR description template |

---

Constitution (`.mdc`) lives in `*-rules` repos pinned as git submodules — not in this folder.
