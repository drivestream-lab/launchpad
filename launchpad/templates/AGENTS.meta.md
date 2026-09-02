# Agent guide ({{DISPLAY_NAME}} meta)

PM workspace for **{{ORG}}** (`{{META_REPO}}`).

<!-- launchpad:harness-start -->
## Harness (managed by launchpad — do not edit)

Installed under **`.harness/skills/<skill>/`** (hub) mirrored to **`.agents/skills/`** and **`.claude/skills/`**:

- Prayog PM bundle @ **{{AGENT_SKILLS_REF}}**: {{AGENT_SKILLS_SLASH_LIST}}
- Authoring (human): `/prd-think` → `/prd-quality` → promote → validate chain

Pin record: [`.harness-pin.yaml`](.harness-pin.yaml) (`profile: meta-pm`).

Re-sync after clone: `launchpad apply-harness --meta --apply`

### Delivery bootstrap

- Contract: **{{DELIVERY_CONTRACT}}**
- Workflow: `prayog-skills/workflow.yaml`
- Pin record: `.harness-pin.yaml`
- Skill hub: `.harness/skills/`

When asked “what next?”, read the latest persistent handoff and the pinned
workflow, then explain the current stage, blockers, and next candidate. Do not
perform file or GitHub mutations unless the user explicitly authorizes them.

PM content skills only change the local workspace and record Forge readiness.
Branch/commit/push/PR/issue/label/merge happen only via forge skills
(`/commit-workspace`, `/open-draft-pr`, `/create-board-tickets`).

**Closure (all waves done, once — not per wave):** eng loop then PM loop.
After `/purge-initiative-artifacts-app` and `initiative-closure-pr-action-app` /
`initiative-closure-signoff-app` (human merge app), run
`/purge-initiative-artifacts-meta` **in this meta workspace**, then
`initiative-closure-pr-action-meta` → `initiative-closure-signoff-meta`
(human merge meta). Do not require a human `/open-draft-pr` when the pin sets
`authorization: automated` on those PR nodes — walkers may still run them.
Launchpad does not delete files (KEEP/PURGE is pin semantics).
<!-- launchpad:harness-end -->

## Repository truth

- PRDs: `prd/`
- Reports and impact maps: `prd/reports/`
- Service ownership: `config/service-catalog*.yaml`
- Programme/harness configuration: `config/`

Product decisions must be committed into PRD artifacts. Engineering decisions
are routed to engineering. Check existing branches and PRs before proposing a
new initiative PR.
