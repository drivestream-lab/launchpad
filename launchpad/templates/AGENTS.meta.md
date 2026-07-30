# Agent guide ({{DISPLAY_NAME}} meta)

PM workspace for **{{ORG}}** (`{{META_REPO}}`).

<!-- launchpad:harness-start -->
## Harness (managed by launchpad — do not edit)

Installed under **`.harness/skills/<skill>/`** (hub) mirrored to **`.agents/skills/`** and **`.claude/skills/`**:

- Community: `/prd` @ awesome-copilot
- Prayog PM bundle @ **{{AGENT_SKILLS_REF}}**: {{AGENT_SKILLS_SLASH_LIST}}

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

Development content skills only change the local workspace and record Forge
readiness. Branch/commit/push/PR/issue/label/merge happen only via forge skills.
<!-- launchpad:harness-end -->

## Repository truth

- PRDs: `prd/`
- Reports and impact maps: `prd/reports/`
- Service ownership: `config/service-catalog*.yaml`
- Programme/harness configuration: `config/`

Product decisions must be committed into PRD artifacts. Engineering decisions
are routed to engineering. Check existing branches and PRs before proposing a
new initiative PR.
