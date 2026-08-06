# Spec-driven development workflow (example-org)

How agents and engineers use the **truth hierarchy** in Launchpad repos. Constitution rules live in submodules; product truth lives in each service repo.

**Delivery workflow:** [delivery-workflow.md](delivery-workflow.md)

## Hierarchy (read in this order)

| Priority | Location | Answers |
|----------|----------|---------|
| 1 | `.cursor/rules/*.mdc` (submodule) | **How** to build |
| 2 | `AGENTS.md` | Router — rules boundary, smoke / verify_command |
| 3 | `docs/specification/product/` | **What** to build |
| 4 | `docs/specification/adr/` | **Why** (accepted decisions) |
| 5 | `docs/specification/as-built/` | **What is live today** — `implementation-status.md`  |

**Mandatory layout:** [spec-layout.md](spec-layout.md) — **no** `docs/specification/harness/`.

## Constitution vs router vs skills

| Layer | Location | Role |
|-------|----------|------|
| `.cursor/rules/*.mdc` | Rules submodule | **Constitution** — how to build (never list prayog skills here) |
| `AGENTS.md` | App or meta repo root | **Router** — pins, smoke / verify_command, skill names |
| `.harness/skills/<skill>/` | Hub + mirrors (gitignored symlinks) | **Procedures** — prayog slash-command workflows |
| `prayog-skills/` | Git submodule (root) | Skill **source** tree @ pinned ref |

See [harness-pins.md](../harness/harness-pins.md) for the full boundary table.

## Before changing behavior

1. Read `AGENTS.md`
2. Read relevant **product** spec (and **ADR** if architecture/contracts change)
3. Read **as-built** — do not assume a feature exists because the spec mentions it
4. If the change touches another service, read **04-cross-service-contracts.md** (example-api) or equivalent in peer repos

## Implementation discipline

When code changes, update together:

- product spec (if contract or capability changes)
- **unit tests** — logic and edges (see repo `tests/README.md` for layout)
- **smoke scripts** (`tests/verify/`) — live happy path per product feature (not a skill package)
- **as-built** — distinguish implemented / unit-tested / tip-accepted (wave-accepted)

## PR traceability (required)

Every PR uses the template block:

- Initiative (e.g. `BOOTSTRAP-001`, later `INIT-…`)
- Issue #
- Spec paths touched
- Smoke command / tip evidence (`tests/verify` script, `verify_command`, or N/A)

## Example reading order (backend app)

| Step | Path |
|------|------|
| 1 | `AGENTS.md` |
| 2 | `product/00-service-profile.md` → `02-api-contract.md` |
| 3 | `05-roles-and-authz.md` / `03-tenant-and-user-lifecycle.md` as needed |
| 4 | Relevant `adr/` |
| 5 | `as-built/implementation-status.md` |

Integration tests: [`example-api/tests/README.md`](https://github.com/example-org/example-api/blob/develop/tests/README.md)

## Meta references

- Active INIT PRD: `prd/INIT-EXAMPLE-001.md` (in `<client>-meta/prd/`)
- Skills: [skills-matrix.md](../harness/skills-matrix.md)
- Agent prompts: [agent-prompt-templates.md](../../examples/agent-prompt-templates.md)
