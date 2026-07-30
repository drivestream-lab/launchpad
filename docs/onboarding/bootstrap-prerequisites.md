# Bootstrap prerequisites

Before `launchpad init-client --apply` succeeds end-to-end.

Factory PAT setup detail: [factory-cli.md](factory-cli.md#create-a-pat-step-by-step).

---

## 1. Fine-grained PAT (factory)

Create a token scoped to your org. Full steps: [factory-cli.md](factory-cli.md#create-a-pat-step-by-step).

**Required organization permissions:**

| Permission | Access |
|------------|--------|
| Administration | Read and write |
| Issue types | **Read and write** |
| Members | Read and write |
| Projects | Read and write |

**Repository access:** All repositories (recommended). If selecting specific repos, include `<slug>-meta` and all app repos — a PAT that omits them returns 404 on repo API calls.

**Required repository permissions:**

| Permission | Access |
|------------|--------|
| Administration | Read and write |
| Contents | Read and write |
| Issues | Read and write |
| Pull requests | Read and write |
| Workflows | Read and write |

---

## 2. Branch protection requires GitHub Team plan

Branch protection rules require **GitHub Team** plan or higher. On free orgs:

| Option | Action |
|--------|--------|
| **A (recommended)** | Upgrade org to GitHub Team |
| **B (bootstrap only)** | Defer protection; use team push grants + manual merge discipline until upgrade |

---

## 3. Operator sequence

Configure client registry once — [multi-laptop](../setup/multi-laptop.md). Then:

```bash
launchpad doctor
launchpad whoami

launchpad init-client --meta --dry-run
launchpad init-client --meta --apply
launchpad apply-scaffold --meta --apply
launchpad apply-harness --meta --apply
launchpad apply-forge-templates --meta --apply
launchpad status --meta
```

Day N per app repo: see [tenant-meta.md](tenant-meta.md) and [factory-cli.md](factory-cli.md).

Board tickets (after spec merge): `/create-board-tickets` from plan §9 — see [delivery workflow](../../playbook/ship/delivery-workflow.md).

---

## Related

- [factory-cli.md](factory-cli.md)
- [tenant-meta.md](tenant-meta.md)
- [exit-criteria.md](exit-criteria.md)
