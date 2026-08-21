# Teams and RBAC (example-org)

Config: [`governance-example-org.yaml`](../../examples/tenant-meta/config/governance-example-org.yaml)

**Delivery workflow:** [delivery-workflow.md](delivery-workflow.md)  
**Stacks:** [stacks.md](../../docs/stacks.md) — domain/team ≠ stack.

## Cross-cutting teams

| Team slug | Role |
|-----------|------|
| `pm-team` | Product / meta merges; product specs & feasibility |
| `pe-team` | Platform engineering; ADR, Technical-Review, harness paths |
| `release-managers` | Only group allowed to merge/push to `main` |

## Delivery teams ↔ stacks

| Team | Domain | Owns stacks |
|------|--------|-------------|
| `pm-team` | Programme | `meta-pm` |
| `backend-devs` | Python services | `python-backend` |
| `frontend-devs` | Web BFF / portals | `nextjs-frontend` |
| `platform-devs` | Platform tooling + Terraform IaC | `platform-tooling`, `terraform-iac` |
| `data-platform-devs` | Data platform | `flink` (now); `spark` / batch later |
| `edge-agent-devs` | Edge runtime | `edge-agent`, `edge-inference-engine` |
| `mobile-devs` | Mobile apps | `android-kotlin`, `ios-swift` |
| `qa-team` | QA | (read/push; not a develop-merge owner) |

## Stack → primary CODEOWNERS team

| Stack | Primary team |
|-------|----------------|
| `meta-pm` | `pm-team` |
| `python-backend` | `backend-devs` |
| `nextjs-frontend` | `frontend-devs` |
| `terraform-iac` | `platform-devs` |
| `flink` | `data-platform-devs` |
| `edge-agent` | `edge-agent-devs` |
| `edge-inference-engine` | declare `owners.team` (often `edge-agent-devs`) |
| `android-kotlin` | `mobile-devs` |
| `ios-swift` | `mobile-devs` |
| `platform-tooling` | `platform-devs` (CODEOWNERS skipped: `layout: none`) |

App stacks keep `pe-team` / `pm-team` on report/spec paths (existing pattern).  
Kit placeholders: `@example-org/{team}`.

## Access matrix (example-org v0)

| Repo | `pm-team` | Dev teams | `develop` merge |
|------|-----------|-------------|-----------------|
| **<client>-meta** | **Write** | **Read** (pull) | **`pm-team`** |
| **example-api** | Write (handoff branches) | `backend-devs` Write | `backend-devs` |
| **all — `main`** | — | — | **`release-managers` only** |

## Branch rules (summary)

| Branch | PR required | Reviews | Who can merge to branch |
|--------|-------------|---------|-------------------------|
| `chore/*`, `feature/*` | → `develop` via PR | ≥1 | Profile team (app) or `pm-team` (meta) |
| `develop` | Yes | ≥1 | Profile team / `pm-team` (per repo) |
| `main` | Yes, from `develop` only | ≥1 | **`release-managers` only** |

See [github-enforcement.md](../github/github-enforcement.md) and [branching-policy.md](branching-policy.md).

## Automation

```bash
launchpad init-client --meta --dry-run
launchpad init-client --meta --apply
launchpad init-client --repo example-api --apply
```

Add members to teams in GitHub UI after team creation.
