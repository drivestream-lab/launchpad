# Scaffolding

Generate repository foundation code from **cookiecutter** templates declared in `config/scaffold-<org>.yaml`.

Config is SSOT — launchpad reads YAML; no CLI flags override template choice.

---

## When to scaffold

| Target | Command | Typical template |
|--------|---------|------------------|
| Meta repo foundation | `apply-scaffold --meta` | `tenant-meta-foundation` |
| App repo foundation | `apply-scaffold --repo <name>` | `python-fastapi-foundation`, etc. |

Scaffolding is **optional**. Disable per repo with `enabled: false` or omit the block.

Prerequisite: repo exists locally or `init-client --repo` has created it on GitHub.

---

## Config shape

See [SCHEMA.md](SCHEMA.md) ScaffoldConfig. Example app block:

```yaml
# config/scaffold-example-org.yaml
repos:
  example-api:
    enabled: true
    engine: cookiecutter
    template: gh:drivestream-lab/python-fastapi-foundation
    ref: <foundation-tag>
    context:
      service_name: example-api
      has_postgres: "yes"
```

**Template shorthand:**

- `gh:<org>/<repo>` → `https://github.com/<org>/<repo>`
- `git+https://...` → arbitrary git URL
- `/absolute/path` → local template directory

All `context` keys pass through to cookiecutter — launchpad does not validate them.

---

## Meta scaffold

Edit `scaffold-<org>.yaml`:

```yaml
meta:
  enabled: true
  engine: cookiecutter
  template: gh:drivestream-lab/tenant-meta-foundation
  ref: <tag>
  context:
    project_name: EXAMPLE
    programme_slug: example
    github_org: example-org
```

```bash
launchpad --client example apply-scaffold --meta --dry-run
launchpad --client example apply-scaffold --meta --apply
```

Review and commit scaffold output in meta.

---

## App scaffold

Register repo in governance YAML first. Then:

```bash
launchpad --client example apply-scaffold --repo example-api --dry-run
launchpad --client example apply-scaffold --repo example-api --apply
```

Commit in the app repo:

```bash
cd ~/Workspace/example/example-api
git add -A
git commit -m "chore: scaffold example-api from foundation template"
git push -u origin develop
```

### Overlay existing code

```bash
launchpad --client example apply-scaffold --repo example-api --apply --force
```

`--force` merges template files into the existing directory; it does not delete local-only files.

---

## Verify

```bash
launchpad --client example status --repo example-api
```

Scaffold applied when `.launchpad-scaffold` marker exists in the repo (written by `apply-scaffold`).

---

## Stacks

Stack name in `governance-<org>.yaml` drives harness profile; scaffold `template` is independent — see [stacks.md](stacks.md).

| Stack | Typical foundation |
|-------|-------------------|
| `python-backend` | `python-fastapi-foundation` |
| `nextjs-frontend` | `nextjs-bff-foundation` |
| `terraform-iac` | `terraform-azure-foundation` (when published) |
| `edge-agent` | `edge-agent-triton-foundation` (`v0.1.0`) |
| `flink` | **None yet** — brownfield / `apply-harness` only |
| `meta-pm` | `tenant-meta-foundation` |

---

## Full Day-N sequence

Scaffolding is step 2 of app repo onboarding:

```text
init-client --repo  →  apply-scaffold  →  apply-harness  →  apply-forge-templates  →  status
```

Details: [greenfield app repo](../playbook/operator/greenfield-app-repo.md).

---

## Related

- [Tenant meta onboarding](onboarding/tenant-meta.md)
- [SCHEMA.md](SCHEMA.md)
- [stacks.md](stacks.md)
