# Kit evolution

How improvements discovered on **any** tenant deployment flow back into the **single** global kit (`drivestream-lab/launchpad`) without customer names, secrets, or tenant config in this repo.

Tenant-specific values live in **`<client>-meta`** (private per programme). This repo stays **generic**.

Release notes: [CHANGELOG.md](../../CHANGELOG.md).

---

## Principles

1. **One kit, many tenants** — operators install a **tagged release**; tenants pin `.launchpad-version` in meta.
2. **No customer names in the kit** — no enterprise org/repo/team names in committed docs, examples, tests, or changelog.
3. **Reusable fixes upstream** — if a second tenant could use it, it belongs here.
4. **Config stays in meta** — org names, team slugs, board titles, issue types, etc.

---

## What belongs where

| Change type | Global launchpad | Tenant `<client>-meta` |
|-------------|------------------|------------------------|
| CLI bug / idempotent factory step | Yes | No |
| New gitflow or project option (generic) | Yes | No |
| Enterprise PAT limitation (documented generically) | Yes | No |
| Org name, repo list, team slugs | No | `config/governance-<org>.yaml` |
| Board title, project # | No | `config/governance-<org>.yaml` |
| Stack profiles, issue types | No | `config/governance-<org>.yaml` |
| PRDs, work manifests, wiki copy | No | `prd/`, `work/`, `wiki/` |
| Playbook **deltas** (enterprise quirks) | No | `<client>-meta/playbook/` |
| PAT, `clients.yaml` paths | No | `~/.config/launchpad/` (never commit) |

**Examples** use fictional programmes only (`example`, `example-org`) — see `examples/tenant-meta/config/`.

---

## Issue intake (any tenant)

### 1. Report

| Channel | Use for |
|---------|---------|
| **GitHub issue** on `drivestream-lab/launchpad` | Kit bugs, feature requests, docs gaps |
| **Tenant meta issue** (private) | Wrong YAML, PRD, wiki, customer-only process |

**Issue template (kit):**

- **Symptom** — command + error (redact org/repo names; use `example-org` / `example-api`)
- **Expected** — generic behaviour
- **Classification** — `kit-bug` \| `kit-feature` \| `tenant-config` \| `tenant-content`

### 2. Triage (maintainers)

| Label | Action |
|-------|--------|
| `tenant-config` | Close with pointer: fix in `<client>-meta` |
| `kit-bug` / `kit-feature` | Schedule; reproduce with fictional org |
| `docs` | `docs/` or `playbook/` only — still no customer names |

### 3. Implement

- Branch from `main` on `drivestream-lab/launchpad`
- Reproduce with `examples/` or unit tests — **not** a customer clone
- PR diff must stay generic
- Add/update tests where behaviour is new

### 4. Release

1. Merge PR to `main`
2. Bump `launchpad/__init__.py` + `pyproject.toml`
3. Update [CHANGELOG.md](../../CHANGELOG.md)
4. Tag: `git tag v0.x.y && git push origin v0.x.y`
5. GitHub Release from changelog section
6. Notify tenant operators: bump `.launchpad-version` and reinstall

### 5. Tenant adoption

```bash
pipx install "launchpad @ git+https://github.com/drivestream-lab/launchpad@<tag>"
launchpad --version    # must match <client>-meta/.launchpad-version
launchpad --client <client> doctor
```

Re-run idempotent factory commands only when [CHANGELOG.md](../../CHANGELOG.md) says so.

---

## Learning propagation

```text
Tenant A finds gap → kit PR (generic) → tag v0.x.y
                                      ↓
Tenant B, C, … upgrade pip package → same fix, no merge from A's meta repo
```

Tenants do **not** fork launchpad. They share **releases**.

---

## Distribution policy (operators)

| Do | Don't |
|----|--------|
| `pipx install` from **git tag** | `pipx install -e .` on a laptop fork for production use |
| Pin `.launchpad-version` in meta | Everyone on random `main` SHA |
| `launchpad doctor` after upgrade | Commit PAT or `clients.yaml` to git |

See [setup/multi-laptop.md](../setup/multi-laptop.md).

**Kit contributors** may use `pipx install -e .` locally; **tenant operators** install **released tags**.

---

## Release checklist (maintainers)

- [ ] CI / tests pass on `main`
- [ ] `pyproject.toml` + `launchpad/__init__.py` version bumped
- [ ] [CHANGELOG.md](../../CHANGELOG.md) updated
- [ ] No customer names in diff — [PUBLICATION_CHECKLIST.md](../PUBLICATION_CHECKLIST.md)
- [ ] If kit tip / prayog pin moved: re-vendor `tests/fixtures/prayog-skills/` from that tip; update the `# Vendored from …@<sha>` header; align `examples/` harness refs; optionally run `scripts/check-fixture-pin.sh`
- [ ] Tag pushed: `v0.x.y`
- [ ] GitHub Release published
- [ ] Tenant operators notified: version + any re-run commands

---

## Related

- [Local development](local-dev.md)
- [CHANGELOG.md](../../CHANGELOG.md)
