# Agent guide ({{SERVICE_NAME}})

## Constitution (how to code)

Shared rules: **`.cursor/rules/*.mdc`** (git submodule, pinned at **{{RULES_PIN}}**).

Agent skills: **`prayog-skills/`** (git submodule at root, pinned at **{{AGENT_SKILLS_REF}}**) — {{AGENT_SKILLS_SLASH_LIST}}.

**Do not edit** `.cursor/rules/`. Skill changes go upstream in prayog-skills.
Pin record: [`.harness-pin.yaml`](.harness-pin.yaml) (`profile: {{PROFILE}}`).

---

## Delivery bootstrap

- Contract: **{{DELIVERY_CONTRACT}}**
- Workflow: `prayog-skills/workflow.yaml`
- Pin record: `.harness-pin.yaml`
- Skill hub: `.harness/skills/`

When asked “what next?”, read the latest persistent handoff and the pinned
workflow, then explain the current stage, blockers, and next candidate. Do not
perform file or GitHub mutations unless the user explicitly authorizes them.

**PRs:** use `.github/pull_request_template.md` — Initiative, Spec path, Verify command.

---

## Programme board

Engineering work is tracked on **[{{BOARD_NAME}}]({{BOARD_URL}})** (org Project).

- SSOT: `{{META_REPO}}/config/governance-*.yaml` → `project_board` (read-only meta clone)
- Resolve binding: `launchpad board-bind --client <id>`
- After spec merge: `/board-seed INIT-<id>` — creates EPIC + wave sub-issues on this board (all app stacks)

---

## Product (what to build)

Start here: [`docs/specification/README.md`](docs/specification/README.md)

| Layer | Entry point | Purpose |
|-------|-------------|---------|
| **Product specs** | [`docs/specification/product/`](docs/specification/product/) | What this service does |
| **As-built** | [`docs/specification/as-built/implementation-status.md`](docs/specification/as-built/implementation-status.md) | Live vs deferred; verification matrix |
| **ADRs** | [`docs/specification/adr/README.md`](docs/specification/adr/README.md) | Architecture decisions |

Active work: board issue **Spec path** → product initiative spec (from PRD handoff).

---

## Run and verify

- Setup/run source: [`README.md`](README.md)
- Canonical build/check/test commands: repository Makefile or package scripts
- Live verification and prerequisites: [`tests/README.md`](tests/README.md)

Use the repository commands exactly as documented; do not invent environment
activation, test, or verify commands.

---

## Before changing behavior

1. Read `.cursor/rules/code-guidelines-index.mdc` (or the profile’s rule index).
2. Read the relevant product spec and accepted ADRs.
3. Read as-built; do not infer live behavior from a spec.
4. Read `tests/README.md` and the repository Makefile/package scripts for exact commands.
5. Resolve the current delivery stage from the pinned Prayog workflow.

Do not edit pinned rules or skill sources. Product truth belongs in
`docs/specification/`; repository-specific commands remain in the repository.
