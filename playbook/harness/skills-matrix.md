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
| **PM / PO** | `<client>-meta` | prayog PM bundle (incl. `/prd-think`, `/prd-quality`, validate chain, `/purge-initiative-artifacts-meta`) + forge via `apply-harness --meta` |
| **Developer** | app repo | prayog dev bundle + forge — `/spec-draft` … `/ground-spec`, `/purge-initiative-artifacts-app`, plus forge |

**Shared forge skills** (meta + app, required `forge_skills` → `skills/forge/`):
`/commit-workspace`, `/open-draft-pr`, `/create-board-tickets`. Not workflow graph
nodes — human install surface only (walkers). Board tickets use
`/create-board-tickets` (not a development-lane skill). Unrelated to kit forge
templates (`apply-forge-templates`).

**Wave sequencing (pinned workflow):** Pass-1 `/pre-implement` → `/loop-spec` →
`wave-pr-action` → `wave-acceptance` (label `wave-accepted`). Do not require a
human `/open-draft-pr` when the pin sets `authorization: automated` on that node.
Pass-2 `/learning-extract` → `/ground-spec` → `wave-done-action` (board Done) →
`wave-signoff` (human merge only). Smoke scripts live under `tests/verify/` — not
a `/verify` skill.

**Closure (all waves done, once):** `initiative-closure` →
`/purge-initiative-artifacts-app` → `initiative-closure-pr-action-app` →
`initiative-closure-signoff-app` → `/purge-initiative-artifacts-meta` →
`initiative-closure-pr-action-meta` → `initiative-closure-signoff-meta`.
No per-wave purge; Launchpad does not implement deletes.

---

## PM bundle (meta)

Skill names are resolved from the pinned Prayog `meta-pm` profile. The order
and transitions come from the pinned `workflow.yaml`, not this document.

Install:

```bash
launchpad apply-harness --meta --apply
launchpad status --meta
```

Prayog PM bundle skills are materialized into configured runtime roots
(`prd-think`, `prd-quality`, validate chain, forge skills, …).

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
