# Skills matrix (example-org)

Agent skills and factory commands for Example engineering. **PM pipeline skills** install from [drivestream-lab/prayog-skills](https://github.com/drivestream-lab/prayog-skills).

**Audition:** [skills-audition.md](skills-audition.md)  
**Full workflow:** [delivery-workflow.md](../ship/delivery-workflow.md)

Skills CLI installs to **`.agents/skills/`** (project) or **`~/.agents/skills/`** (global).

**Dev + PM skills SSOT:** [prayog-skills](https://github.com/drivestream-lab/prayog-skills) @ harness pin. App repos: [`apply-harness`](harness-pins.md).

---

## Two workspaces

| Who | Open in Cursor | Skills |
|-----|----------------|--------|
| **PM / PO** | `<client>-meta` | `prd` + prayog PM bundle + forge skills via `apply-harness --meta` |
| **Developer** | app repo | prayog dev bundle + forge skills — `/spec-draft` through `/verify`, including `/learning-extract`, plus forge |

**Shared forge skills** (meta + app, from `forge_skills` → `skills/forge/`): `/commit-workspace`, `/open-draft-pr`, `/create-board-tickets`. Not workflow graph nodes — human install surface only. Board seeding is **not** a development-lane skill (retired `/board-seed`). Unrelated to kit forge templates (`apply-forge-templates`).

**Wave sequencing (pinned workflow):** Pass-1 `/pre-implement` → `/loop-spec` → `live-verify` (park). Pass-2 closeout `/learning-extract` → `/ground-spec` → `wave-signoff`. `/verify` is optional/manual.

---

## PM bundle (meta)

Skill names are resolved from the pinned Prayog `meta-pm` profile. The order
and transitions come from the pinned `workflow.yaml`, not this document.

Install:

```bash
launchpad apply-harness --meta --apply
launchpad status --meta
```

Community `/prd` and the Prayog PM bundle are materialized into configured
runtime roots.

---

## Development bundle (app repo)

Skill names are resolved from the pinned Prayog development profile. Agents
route by reading the latest handoff and pinned `workflow.yaml`.

Harness: `launchpad apply-harness --repo <name> --apply` — see [harness-pins.md](harness-pins.md).

---

## Routing

See [delivery-workflow.md](../ship/delivery-workflow.md) for repository/role
bindings and the pinned Prayog workflow for stage transitions.

---

## Related

- [agent-prompt-templates.md](../../examples/agent-prompt-templates.md)
- [github-project.md](../github/github-project.md)
