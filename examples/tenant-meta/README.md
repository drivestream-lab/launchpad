# Example tenant meta (smoke fixture)

This directory is the canonical example of a `<slug>-meta` control-plane repo.
It is also used for local smoke tests (`./scripts/smoke-local.sh` via `--config-dir`).

---

## Config files

All five YAML kinds live in `config/`:

| File | Kind | Purpose |
|------|------|---------|
| `programme.yaml` | Programme | Identity spine: name, slug, org, workspace, forge |
| `governance-example-org.yaml` | GovernanceConfig | Teams, repos (stack + teams required), gitflow policy, board |
| `harness-example-org.yaml` | HarnessConfig | Constitution (rules submodule) + agent skills per stack profile |
| `scaffold-example-org.yaml` | ScaffoldConfig | Cookiecutter sources per repo (free-form context pass-through) |
| `service-catalog-example-org.yaml` | ServiceCatalog | Service map (required; meta live + app examples commented) |

Rename `*-example-org.yaml` → `*-<your-org>.yaml` in your real meta repo.

---

## Setup paths

**Path A — interview:**

```bash
launchpad onboard interview
```

**Path B — copy this directory** and edit config.

Full operator guide: [docs/onboarding/tenant-meta.md](../../docs/onboarding/tenant-meta.md).

Then:

```bash
launchpad init-client --meta --apply
launchpad apply-scaffold --meta --apply      # optional
launchpad apply-harness --meta --apply
launchpad apply-forge-templates --meta --apply
launchpad status --meta
```

Day N app repos: [playbook/operator/greenfield-app-repo.md](../../playbook/operator/greenfield-app-repo.md).

---

## Directory layout

| Path | Purpose |
|------|---------|
| `config/` | All five factory YAMLs |
| `prd/` | Product requirements (`INIT-*.md`) after PM sign-off |
| `planning/` | Pre-build narratives — not app-repo SSOT |
| `programs/` | Programme overviews |
| `work/` | Optional human archive of plan §9 copies (not schema SSOT) |
| `wiki/` | Published to GitHub Wiki — see [wiki-setup.md](../../playbook/wiki/wiki-setup.md) |
| `playbook/` | Client-specific playbook deltas (kit playbook is SSOT) |

**No `.env` in meta** — factory secrets live in `~/.config/launchpad/env.d/<slug>.env` only.

---

## Further reading

- [docs/README.md](../../docs/README.md) — documentation index
- [docs/SCHEMA.md](../../docs/SCHEMA.md) — 5 YAML kinds reference
- [docs/stacks.md](../../docs/stacks.md) — Stack registry
- [CHANGELOG.md](../../CHANGELOG.md) — release notes
