# Wiki index (required — BOOTSTRAP M4)

**Published wiki:** tenant <client>-meta/wiki  
**Source files:** `wiki/*.md` in this repo  
**Publish:** manual wiki git clone (see [wiki-setup.md](wiki-setup.md))

Wiki pages are **navigation only**. Commands, field tables, and checklists live in **<client>-meta** playbook — link below; do not copy blocks into wiki.

Base URL: `tenant <client>-meta/blob/develop/`

---

## Page 0 — Spec structure (mandatory)

**Wiki title:** Example — Spec structure

| Link | Path |
|------|------|
| Spec layout | `playbook/ship/spec-layout.md` |
| SDD workflow | `playbook/ship/sdd-workflow.md` |

---

## Page 1 — PM workflow

**Wiki title:** Example — PM workflow

| Link | Path |
|------|------|
| PM workflow | `docs/setup/pm-setup.md` |
| Skills matrix (prayog-skills install) | `playbook/harness/skills-matrix.md` |
| Delivery workflow | `playbook/ship/delivery-workflow.md` |

---

## Page 2 — How we ship

**Wiki title:** Example — How we ship

| Link | Path |
|------|------|
| Delivery workflow | `playbook/ship/delivery-workflow.md` |
| Branching policy | `playbook/ship/branching-policy.md` |
| Board columns + fields | `playbook/github/github-project.md` |
| PR template | `templates/pull_request_template.md` |

---

## Page 3 — Python dev (example-api)

**Wiki title:** Example — Python dev

| Link | Path |
|------|------|
| Agent guide | `example-org/example-api` → `AGENTS.md` |
| Integration tests | `example-org/example-api` → `tests/README.md` |
| SDD workflow | `playbook/ship/sdd-workflow.md` |
| Skills matrix | `playbook/harness/skills-matrix.md` |

---

## Page 4 — Platform operator

**Wiki title:** Example — Platform operator

| Link | Path |
|------|------|
| PAT + factory CLI | `docs/onboarding/factory-cli.md` |
| Setup platform | `README.md` (Factory CLI section) |
| Work manifests | Plan §9 + pin contract (board = long-term after seed; may purge at initiative closure) |
| Teams / RBAC | `playbook/ship/teams-and-rbac.md` |

---

## Page 5 — Skills & agents

**Wiki title:** Example — Skills & agents

| Link | Path |
|------|------|
| Skills matrix | `playbook/harness/skills-matrix.md` |
| Skills audition | `playbook/harness/skills-audition.md` |
| Pre-implement (example-api) | `example-org/example-api` → `.agents/skills/pre-implement/SKILL.md` |
| Ground-spec (example-api) | `example-org/example-api` → `.agents/skills/ground-spec/SKILL.md` |

---

## Maintenance

When playbook paths change, update wiki links only — not wiki body content.
