# Factory CLI reference

All **org bootstrap** runs through **one CLI**: `launchpad` + `GITHUB_TOKEN`.

Developers use **`gh`** for day-to-day git and PRs — separate from the factory.

Install tag: pick `<tag>` from [CHANGELOG.md](../../CHANGELOG.md).

---

## Quick start

**Per machine:** configure once in `~/.config/launchpad/` — see [multi-laptop](../setup/multi-laptop.md).

```bash
launchpad clients
launchpad doctor
launchpad init-client --meta --dry-run
```

Secrets: `~/.config/launchpad/env.d/<slug>.env` (never commit).

---

## Create a PAT (step by step)

Use a **fine-grained PAT** scoped to your org.

### 1. Open token settings

1. Log in to GitHub as an account that can **administer** your org.
2. Profile → **Settings** → **Developer settings** → **Fine-grained tokens** → **Generate new token**.

### 2. Token basics

| Field | Value |
|-------|--------|
| Token name | `<slug>-meta-factory` |
| Expiration | Per org policy (e.g. 90 days) |

### 3. Resource owner

Set to **your GitHub org** (not your personal account).

### 4. Repository access

**All repositories** in the org, or at minimum `<slug>-meta` and all app repos.

### 5. Repository permissions

| Permission | Access |
|------------|--------|
| Administration | Read and write |
| Contents | Read and write |
| Metadata | Read |
| Issues | Read and write |
| Pull requests | Read and write |
| Workflows | Read and write |

### 6. Organization permissions

| Permission | Access |
|------------|--------|
| Administration | Read and write |
| Issue types | **Read and write** |
| Members | Read and write |
| Projects | Read and write |

### 7. Generate and store

```bash
mkdir -p ~/.config/launchpad/env.d
cp examples/env.d/client.env.example ~/.config/launchpad/env.d/<slug>.env
# Edit — paste GITHUB_TOKEN=github_pat_…
chmod 600 ~/.config/launchpad/env.d/<slug>.env
launchpad whoami
```

Register meta path in `~/.config/launchpad/clients.yaml` — [multi-laptop](../setup/multi-laptop.md).

**Classic PAT fallback:** `repo`, `admin:org`, `project`, `read:org` — prefer fine-grained when possible.

---

## Commands

All apply commands default to **`--dry-run`**. Pass **`--apply`** to execute.

| Command | Purpose | Scope |
|---------|---------|-------|
| `onboard interview` | 4 questions → 5 YAMLs + registry + PAT stub | local only |
| `init-client` | Teams, repo, gitflow, project board | `--meta` or `--repo <name>` |
| `apply-scaffold` | Cookiecutter from scaffold YAML | `--meta` or `--repo <name>` |
| `apply-harness` | Pin rules + prayog submodules, AGENTS.md, symlinks | `--meta` or `--repo <name>` |
| `reset-harness` | Clear local harness materialization (hubs, pin, AGENTS block) | `--meta` or `--repo <name>` |
| `apply-forge-templates` | Issue forms + PR template | `--meta` or `--repo <name>` |
| `status` | Readiness checklist + NEXT | `--meta` or `--repo <name>` |
| `doctor` | Token, config, version pin | — |
| `whoami` | Verify token | — |
| `clients` | List programmes | — |

Harness commands work **without PAT** (local file + git submodule ops):

```bash
launchpad apply-harness --repo example-api --apply
launchpad status --repo example-api
```

See [harness pins](../../playbook/harness/harness-pins.md).

---

## YAML kinds (`config/`)

| File | Used by |
|------|---------|
| `programme.yaml` | All commands |
| `governance-<org>.yaml` | `init-client` |
| `harness-<org>.yaml` | `apply-harness`, `status` |
| `scaffold-<org>.yaml` | `apply-scaffold` |
| `service-catalog-<org>.yaml` | `status` |

Reference: [SCHEMA.md](../SCHEMA.md).

---

## What stays manual

- Add people to teams (GitHub UI)
- Wave issues: `/create-board-tickets` after spec merge
- Wiki publish — [wiki setup](../../playbook/wiki/wiki-setup.md)

---

## Related

- [bootstrap-prerequisites.md](bootstrap-prerequisites.md)
- [tenant-meta.md](tenant-meta.md)
- [factory package layout](../contributing/local-dev.md)
