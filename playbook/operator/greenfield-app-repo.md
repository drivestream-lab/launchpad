# Greenfield app repo onboarding (v0.5.10)

Repeatable sequence for adding a **new application repository** to an existing programme:
GitHub repo → scaffold → harness envelope → SDD handoff → wave PRs.

Config is the SSOT — edit YAML in `<slug>-meta/config/`, then run commands.
All commands default to `--dry-run`; pass `--apply` to execute.

---

## Mental model

Three layers — do not skip or reorder:

```text
┌──────────────────────────────────────────────────────────────┐
│ Config (SSOT)   governance + harness + scaffold YAML describe │
│                 the repo before it exists on disk             │
├──────────────────────────────────────────────────────────────┤
│ 1. init-client --repo   GitHub repo + team + gitflow + board  │
│ 2. apply-scaffold       cookiecutter foundation code          │
│ 3. apply-harness        rules submodule + AGENTS.md + skills  │
│ 4. apply-forge-templates  issue forms + PR template           │
│ 5. status        verify pins + forge templates match config   │
├──────────────────────────────────────────────────────────────┤
│ 5. spec handoff PR      docs/specification/product/INIT-*     │
│ 6. wave PRs (W0…)       business logic on top of foundation   │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- [ ] `launchpad` installed and on PATH (`launchpad --version`)
- [ ] Client registry + token: `~/.config/launchpad/clients.yaml`, `env.d/<slug>.env`
- [ ] `launchpad doctor` clean
- [ ] Day-1 meta repo already exists on GitHub (`init-client --meta --apply` was run)

---

## Step 0 — Register repo in config YAML

### 1. governance YAML

Edit `config/governance-<org>.yaml` — add the repo block:

```yaml
repos:
  example-api:
    stack: python-backend
    teams:
      - example-platform   # must exist in teams: section
      - example-dev
    description: "Example API service"
```

### 2. scaffold YAML (optional but recommended)

Edit `config/scaffold-<org>.yaml` — add the repo block with `enabled: true`:

```yaml
repos:
  example-api:
    enabled: true
    template: https://github.com/drivestream-lab/python-fastapi-foundation
    ref: v0.3.0
    context:                        # free-form cookiecutter context
      service_name: example-api
      service_description: Example API service
      has_postgres: "yes"
      has_redis: "yes"
      has_kafka: "no"
      has_internal_api: "no"
```

All context keys pass directly to cookiecutter. Only `enabled`, `template`, and `ref` are read by Launchpad; `context` is yours.

### 3. harness YAML

Edit `config/harness-<org>.yaml` — the `python-backend` profile should already be defined at Day 1. If you need a custom profile for this repo, add one under `profiles:`.

### Commit meta changes

```bash
cd ~/Workspace/<slug>/<slug>-meta
git add config/
git commit -m "chore(config): register example-api for Day-N setup"
git push
```

---

## Step 1 — Create GitHub repo + gitflow + board

```bash
launchpad init-client --repo example-api --dry-run   # preview
launchpad init-client --repo example-api --apply     # execute
```

Creates: GitHub repo, assigns teams, seeds `main` + `develop` branches, applies branch protection on both, links to project board.

Clone locally (checked out on `develop` automatically):

```bash
# init-client clones into clients.yaml workspace/<repo> when the directory is missing
launchpad init-client --repo example-api --apply
cd ~/Workspace/<slug>/example-api   # already on develop
```

---

## Step 2 — Scaffold foundation code

Preview what will be generated:

```bash
launchpad apply-scaffold --repo example-api --dry-run
```

Apply (overlays into existing clone with `--force`, or generates fresh):

```bash
launchpad apply-scaffold --repo example-api --apply
```

Review and commit in the app repo:

```bash
cd ~/Workspace/<slug>/example-api
git status
git add -A
git commit -m "chore: scaffold example-api from python-fastapi-foundation"
git push -u origin develop
```

If the repo already has code and you want to overlay:

```bash
launchpad apply-scaffold --repo example-api --apply --force
```

`--force` merges template files into the existing directory; it does **not** delete local-only files.

---

## Step 3 — Pin harness

```bash
launchpad apply-harness --repo example-api --dry-run
launchpad apply-harness --repo example-api --apply
```

Writes `.harness-pin.yaml`, `AGENTS.md`, syncs rules submodule, seeds skills.

Commit harness artifacts in the app repo:

```bash
cd ~/Workspace/<slug>/example-api
git add .
git commit -m "chore: sync harness pins"
git push
```

---

## Step 3b — Forge contributor templates

```bash
launchpad apply-forge-templates --repo example-api --dry-run
launchpad apply-forge-templates --repo example-api --apply
```

Writes `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md` from kit + governance (repo list, board URL).

Commit in the app repo:

```bash
cd ~/Workspace/<slug>/example-api
git add .github/
git commit -m "chore: seed forge issue templates"
git push
```

---

## Step 4 — Verify harness

```bash
launchpad status --repo example-api
```

Reports any mismatches between `.harness-pin.yaml` and `harness-<org>.yaml`. Fix config then re-run `apply-harness --repo example-api --apply`.

---

## Step 5 — Day-1 quality gate (app repo)

```bash
cd ~/Workspace/<slug>/example-api
cp .env.example .env    # fill local secrets
make setup
make check
make test
```

---

## Step 6 — Product lane

| Step | Owner | Action |
|------|-------|--------|
| Spec PR | **Dev** | Branch `chore/INIT-*-spec-example-api`; follow the pinned Prayog `workflow.yaml` |
| Wave issues | **Dev** | `/create-board-tickets` after spec merge |
| W0+ | Dev | Feature PRs on foundation |

See [delivery-workflow.md](../ship/delivery-workflow.md).

---

## Full cheat sheet (python-backend)

Replace `example-api`, `<org>`, and `<slug>` for each new repo.

```bash
# 0. Edit config YAMLs (governance + scaffold + harness) in <slug>-meta/config/
git add config/ && git commit -m "chore(config): register example-api" && git push

# 1. GitHub repo + gitflow
launchpad init-client --repo example-api --dry-run
launchpad init-client --repo example-api --apply
gh repo clone <org>/example-api ~/Workspace/<slug>/example-api

# 2. Scaffold foundation
launchpad apply-scaffold --repo example-api --apply
cd ../example-api
git add -A && git commit -m "chore: scaffold example-api" && git push -u origin develop

# 3. Harness
cd ../<slug>-meta
launchpad apply-harness --repo example-api --apply
launchpad status --repo example-api

# 4. Harness commit in app repo
cd ../example-api
git add . && git commit -m "chore: sync harness pins" && git push

# 5. Dev setup
cp .env.example .env && make setup && make check && make test
```

---

## Onboarding checklist (copy per repo)

```markdown
- [ ] `governance-<org>.yaml` — repo block added (stack + teams)
- [ ] `scaffold-<org>.yaml` — repo block added (enabled: true, template, ref, context)
- [ ] Config committed and pushed to meta
- [ ] `init-client --repo <name> --apply` — GitHub repo + gitflow + board
- [ ] `apply-scaffold --repo <name> --apply` — foundation code in place
- [ ] Foundation committed and pushed to `develop`
- [ ] `apply-harness --repo <name> --apply` — pins + AGENTS.md
- [ ] `status --repo <name>` green
- [ ] Harness committed and pushed
- [ ] `make setup && make check && make test` green
- [ ] `service-catalog-<org>.yaml` — repo promoted from `planned` to `live`
- [ ] Spec handoff PR merged
- [ ] W0 wave PR opened
```

---

## Stack profiles

| Stack | Foundation template | Status |
|-------|---------------------|--------|
| `python-backend` | `python-fastapi-foundation` | Implemented |
| `nextjs-frontend` | `nextjs-bff-foundation` | Implemented |
| `terraform-iac` | `terraform-azure-foundation` or `terraform-aws-foundation` | IaC repos |
| `flink` | TBD | Brownfield / apply-harness only |
| `edge-agent` | `edge-agent-triton-foundation` | `v0.1.0` |
| `meta-pm` | `tenant-meta-foundation` | Meta repos only |

---

## Related

- [harness-pins.md](../harness/harness-pins.md) — harness pin file details
- [docs/SCHEMA.md](../../docs/SCHEMA.md) — 5-YAML config reference
- [docs/stacks.md](../../docs/stacks.md) — stack registry + custom stacks
- [docs/onboarding/tenant-meta.md](../../docs/onboarding/tenant-meta.md) — new programme onboarding
