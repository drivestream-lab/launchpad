# Tenant meta onboarding

Stand up a **new** programme: local config → GitHub meta repo → harness → app repos.

For joining an **existing** programme, see [PM setup](../setup/pm-setup.md) or [engineer setup](../setup/engineer-setup.md).

Install tag: pick `<tag>` from [CHANGELOG.md](../../CHANGELOG.md).

---

## Architecture

```text
~/Workspace/example/
├── example-meta/          # control-plane (created locally, then on GitHub)
│   └── config/
│       ├── programme.yaml
│       ├── governance-example-org.yaml
│       ├── harness-example-org.yaml
│       ├── scaffold-example-org.yaml
│       └── service-catalog-example-org.yaml
├── example-api/           # app repos (Day N)
└── …
```

| Repo | Role |
|------|------|
| **launchpad** | Factory CLI — not copied into meta |
| **example-meta** | Config SSOT, PRDs, work manifests, wiki |
| **App repos** | Specs, code, harness pin |

---

## Prerequisites

- GitHub org admin access
- Fine-grained factory PAT — [bootstrap prerequisites](bootstrap-prerequisites.md)
- `launchpad` installed — [multi-laptop](../setup/multi-laptop.md)

---

## Step 1 — Local config (pick one path)

### Path A — Interview (interactive)

```bash
launchpad onboard interview
```

Four questions: programme name, slug, GitHub org, workspace path.

Writes:

```text
~/Workspace/example/example-meta/config/     # 5 YAML files
~/.config/launchpad/clients.yaml             # id: example
~/.config/launchpad/env.d/example.env          # PAT stub
```

No GitHub API calls. No PAT required at this stage.

Legacy subcommands (`onboard apply`, `onboard plan`, `onboard show`) are **not** public — only `onboard interview` exists.

### Path B — Copy example skeleton

```bash
cp -r examples/tenant-meta ~/Workspace/example/example-meta
```

Rename `config/*-example-org.yaml` → `config/*-<your-org>.yaml`. Edit `programme.yaml`. Register manually in `clients.yaml` — see [multi-laptop](../setup/multi-laptop.md).

Reference: [examples/tenant-meta](../../examples/tenant-meta/README.md).

---

## Step 2 — Machine registry + doctor

```bash
# Fill PAT in env.d stub (Path A) or create manually (Path B)
chmod 600 ~/.config/launchpad/env.d/example.env

launchpad --client example doctor
```

---

## Step 3 — Meta repo on GitHub

```bash
launchpad --client example init-client --meta --dry-run
launchpad --client example init-client --meta --apply
```

Creates: team(s), `example-meta` repo, gitflow (`main` + `develop`), branch protection, project board.

Clone if not already local:

```bash
gh repo clone example-org/example-meta ~/Workspace/example/example-meta
cd ~/Workspace/example/example-meta && git checkout develop
```

---

## Step 4 — Scaffold meta (optional)

Edit `config/scaffold-<org>.yaml` — set `meta.enabled: true`, `template`, `ref`, `context`.

```bash
launchpad --client example apply-scaffold --meta --apply
```

See [scaffolding.md](../scaffolding.md).

---

## Step 5 — Harness + forge + verify

```bash
launchpad --client example apply-harness --meta --apply
launchpad --client example apply-forge-templates --meta --apply
launchpad --client example status --meta
```

Commit pin file, `AGENTS.md`, submodule gitlinks. Symlinks under `.harness/skills/` are gitignored — every machine re-runs `apply-harness`.

Pin `.launchpad-version` in meta root to match installed `<tag>`.

---

## Step 6 — Day N app repos

For each new application repo:

1. Edit `config/governance-<org>.yaml` — add repo block
2. `launchpad init-client --repo <name> --apply`
3. Edit `config/scaffold-<org>.yaml` if scaffolding
4. `launchpad apply-scaffold --repo <name> --apply`
5. `launchpad apply-harness --repo <name> --apply`
6. `launchpad apply-forge-templates --repo <name> --apply`
7. `launchpad status --repo <name>`
8. Promote in `service-catalog-<org>.yaml`

Full sequence: [greenfield app repo](../../playbook/operator/greenfield-app-repo.md).

---

## GitHub org settings

One-time configuration for your org (e.g. **example-org**).

| Setting | Recommendation |
|---------|----------------|
| Default repository permission | **Read** |
| Two-factor authentication | Required for members |

**Teams** — created by `init-client`. Add members in GitHub UI:

| Team | Role |
|------|------|
| `pm-team` | Meta `develop` merges; spec handoff on app repos |
| `backend-devs` | App repo `develop` merges (`python-backend`) |
| `release-managers` | `main` only |
| `platform-devs` | Factory / Terraform IaC / platform-tooling |
| `frontend-devs` | BFF repos (`nextjs-frontend`) |
| `data-platform-devs` | Data platform domain — owns stack `flink` |
| `edge-agent-devs` | Edge agent repos |
| `qa-team` | QA manifests and deploy verification |
| `pe-team` | Technical review, ADR, harness/rules (CODEOWNERS) |

Details: [teams and RBAC](../../playbook/ship/teams-and-rbac.md).

**Project board** — fields and columns: [github-project.md](../../playbook/github/github-project.md).

**Wiki** — [wiki-setup.md](../../playbook/wiki/wiki-setup.md).

**Branch protection** requires GitHub Team plan — [bootstrap-prerequisites.md](bootstrap-prerequisites.md).

---

## What launchpad automates vs manual

| Step | Launchpad | Manual |
|------|-----------|--------|
| Create GitHub org | | ✓ |
| Generate 5 config YAMLs | ✓ `onboard interview` or copy example | edit to customize |
| Create teams + meta repo | ✓ `init-client --meta` | add members in GitHub UI |
| Gitflow + board | ✓ `init-client` | |
| Scaffold | ✓ `apply-scaffold` | |
| Harness + forge | ✓ `apply-harness`, `apply-forge-templates` | |
| Verify | ✓ `status` | |
| Wave issues | | `/create-board-tickets` after spec merge |

---

## Checklist

```markdown
### Local
- [ ] 5 config YAMLs in example-meta/config/
- [ ] clients.yaml + env.d with PAT
- [ ] launchpad --client example doctor green

### Meta on GitHub
- [ ] init-client --meta --apply
- [ ] apply-scaffold --meta (if enabled)
- [ ] apply-harness --meta --apply
- [ ] apply-forge-templates --meta --apply
- [ ] status --meta green
- [ ] .launchpad-version matches installed tag

### First app (Day N)
- [ ] governance YAML updated
- [ ] init-client --repo <name> --apply
- [ ] apply-scaffold / apply-harness / apply-forge-templates --repo
- [ ] status --repo green
```

---

## Related

- [SCHEMA.md](../SCHEMA.md) — 5 YAML kinds
- [stacks.md](../stacks.md) — stack registry
- [PM setup](../setup/pm-setup.md) — join existing meta later
- [CHANGELOG.md](../../CHANGELOG.md) — release notes
