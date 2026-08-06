# Delivery workflow integration

Launchpad supplies repository, role, GitHub, pinning, and factory bindings for
the delivery workflow installed from Prayog.

## Workflow source of truth

The normative stage graph is the pinned Prayog file:

```text
prayog-skills/workflow.yaml
```

Its contract is recorded in:

```text
.harness-pin.yaml
prayog-skills/delivery-contract.yaml
```

Do not copy skill transitions, checks, or output schemas into this playbook.
When asked “what next?”, agents read the latest persistent handoff and the
pinned workflow.

## Repository and role bindings

| Surface | Owner | Purpose |
|---------|-------|---------|
| `<client>-meta` PRD PR | PM team | Product clarification, PRD, impact map, `prd-impact-acceptance` |
| App spec PR | Profile developer team | Repo spec, feasibility, optional TDD, plan, `coding-readiness` |
| App wave PR | Profile developer team | Code, tests, smoke under `tests/verify`, learning + ground |
| `prd-impact-acceptance` | PE / tech lead | Engineering handoff readiness (`review_roles` key; labels `impact-map-*`) |
| `coding-readiness` | PE / engineering gate | Coding readiness (`review_roles` key; labels `spec-*`) |
| `wave-acceptance` | Peer/tech lead | Tip human-approved (`wave-accepted` label; smoke or P15 N/A) |
| `wave-signoff` | Peer/tech lead | Human merge/publish only after Pass-2 (not a second approve) |
| `initiative-closure` | Eng / PE | Human judgment that all waves are done (start purge lane) |
| `initiative-closure-signoff-app` | Peer/tech lead | Human merge of app closure Draft PR |
| `initiative-closure-signoff-meta` | Peer/tech lead | Human merge of meta closure Draft PR |

PM owns product decisions and PRD artifacts. Developers own app specs and code.
PE owns engineering decisions; PE does not choose product behavior.

## GitHub surfaces

### PRD PR

- Branch: `chore/INIT-{COMPONENT}-{NUMBER}-prd`
- Target: `develop`
- Initial impact map is generated locally before the PR exists.
- PR creation/update requires explicit user authorization.
- Product/domain clarification happens on this PR.
- Decisions are committed into PRD/map artifacts before threads resolve.
- `prd-impact-acceptance` labels: `impact-map-pending`, `impact-map-blocked`,
  `impact-map-lgtm`; `impact-map-revised` or `impact-map-stale` closes the checkpoint.
- Labels are projections; matching review/head/artifact evidence remains
  authoritative.
- Pilot default: merge this PR before opening app spec PRs.

### App spec PR

- Branch: `chore/INIT-{COMPONENT}-{NUMBER}-spec-<repo>`
- Target: `develop`
- Type: **Draft PR** for the entire spec lifecycle
- Contains no product domain code (docs/specification only; light verify stubs optional)
- Engineering clarification happens on this PR
- Product questions link back to a PRD amendment surface
- Initial `coding-readiness` label: **`spec-pending`** (provision with `launchpad apply-gates --repo <name> --apply`)
- PE sets **`spec-lgtm`** only when spec + feasibility + TDD + Accepted ADRs +
  implementation plan §9 are on the current head
- PE also submits GitHub **Approve** with attestation (initiative, head SHA,
  digests, artifact paths) — never infer approval from the label alone
- Mark **Ready for review** before merge (Draft PRs cannot merge while Draft)
- New commits after `spec-lgtm` → add `spec-revised`, remove `spec-lgtm`
- Merge means the repo slice is ready to build; then `/create-board-tickets` from plan §9

#### `coding-readiness` label transitions (PE)

| Action | Remove | Add |
|--------|--------|-----|
| Draft opened / new revision | `spec-lgtm`, `spec-blocked` | `spec-pending` |
| Request changes | `spec-pending`, `spec-lgtm` | `spec-blocked` |
| Full package approved | `spec-pending`, `spec-blocked`, `spec-revised`, `spec-stale` | `spec-lgtm` |

#### Approve attestation (spec package)

```text
Spec package approved
initiative: INIT-{id}
spec_pr_head_sha: {SHA}
meta_pr_head_sha: {SHA}
impact_map_revision: {N}
prd_digest: sha256:{hex}
scope_digest: sha256:{hex}
plan_digest: sha256:{hex}
artifacts:
  - docs/specification/product/INIT-{id}.md
  - docs/specification/reports/Initiative-Feasibility-Report-{INIT-id}.md
  - docs/specification/reports/Technical-Review-{INIT-id}.md
  - docs/specification/reports/Implementation-Plan-{INIT-id}.md
```

### Wave PR

- Branch: `feature/INIT-{COMPONENT}-{NUMBER}-w{N}-{slug}`
- Target: `develop`
- One issue maps to one wave PR.
- **Pass-1:** `/pre-implement` → `/loop-spec` → **`wave-pr-action`** → human
  **`wave-acceptance`** → park at `wave-awaiting-closeout`.
  Checklist then code land on the same `head_ref` via Forge `commit_workspace`
  readiness + `/commit-workspace`; Draft PR opens **after** `/loop-spec` (no
  mid-coding Draft PR). When the pin sets `authorization: automated` on
  `wave-pr-action` / `spec-pr-action` / closure PR nodes, do **not** require a
  human `/open-draft-pr` click — walkers may still use that forge skill.
- At **`wave-acceptance`:** run co-shipped smoke (`verify_command` /
  `live_verify_dir` → `tests/verify` scripts) or accept P15 N/A; signal with
  GitHub label **`wave-accepted`** on the Draft PR tip. That label is the **only**
  approval signal Launchpad documents for the tip — not merge. Provision the
  label with `launchpad apply-gates --repo <name> --apply`; humans apply it.
  Content skills must **not** apply `wave-accepted` or mutate GitHub.
- **Pass-2 closeout** closes the wave: `/learning-extract` → `/ground-spec` →
  pin may run **`wave-done-action`** (board ticket → Done; not a slash skill) →
  human **`wave-signoff`** (**manual merge** / publish only — not a second
  approve; record merge SHA).
- Development content skills only change the local workspace and record Forge
  readiness. Branch/commit/push/PR/issue/label/merge happen only via forge skills
  or human GitHub. Wave merge is human-only at `wave-signoff`.

### Initiative closure (after all waves)

Purge **once** when every wave is done — **not** after each `wave-signoff`.

```text
initiative-closure (human judgment)
  → /purge-initiative-artifacts-app      # app workspace
  → initiative-closure-pr-action-app     # pin authorization: automated
  → initiative-closure-signoff-app       # human merge app → develop
  → /purge-initiative-artifacts-meta     # meta workspace
  → initiative-closure-pr-action-meta
  → initiative-closure-signoff-meta      # human merge meta → develop
```

- App and meta are **two checkouts**: run the matching purge skill in each.
- KEEP/PURGE semantics live in pin `references/artifact-write-contract.md` —
  Launchpad does **not** delete files or implement the allowlist.
- No merge Forge skill — closure merges are human-only at the split signoff nodes.
- Walkers may still run `/purge-initiative-artifacts-*` and `/open-draft-pr`.
- After board seed, the programme board is the long-term WorkManifest home; the
  plan file may be purged at closure.

## Board tickets

Board tickets use forge **`/create-board-tickets`** (**stack-agnostic**; not a
development-lane skill) after spec PR merge. WorkManifest SSOT is plan §9 under
the pinned prayog contract (`references/workmanifest-contract.md`). Validate with
P16 + `python prayog-skills/scripts/workmanifest_contract.py <plan.md>` — not
Launchpad kit CI. Preconditions:

1. Merged spec PR head had **`spec-lgtm`**
2. `Implementation-Plan-{initiative}.md` and valid §9 WorkManifest on `develop`
3. Programme board resolved from read-only meta governance (`launchpad board-bind`)
4. Explicit developer authorization before create

Sequencing: **spec merge → `/create-board-tickets` → `/pre-implement` → …**

The skill preflights §9 and projects epic/wave/task summaries to the org Project.
`/pre-implement` remains blocked until the epic tree is complete.

Requires `gh auth refresh -s project` and **Project WRITER** on the programme board.

## Q&A routing

| Lane | GitHub surface | Owner |
|------|----------------|-------|
| Product scope, UX, priority | PRD PR | PM |
| Engineering, ADR, interfaces, test policy | Spec PR | PE / senior engineer |
| Domain source of truth | PRD PR or linked issue | Domain SME |
| Auto-fixable naming/reference drift | Current artifact branch | Agent/developer |

## Launchpad responsibility

Launchpad:

- creates repositories/teams/project bindings,
- applies configured GitHub protection,
- scaffolds repositories,
- pins constitutions and Prayog,
- materializes runtime skill symlinks,
- provisions contract-declared labels and validates review-role bindings with
  `apply-gates`,
- writes the initial `AGENTS.md` when absent,
- verifies refs, contract, workflow, and runtime paths.

Launchpad does not redefine Prayog skill behavior or automatically cross human
and external-write gates.

## Related

- [Delivery model](delivery-model.md)
- [Branching policy](branching-policy.md)
- [Teams and RBAC](teams-and-rbac.md)
- [Harness pins](../harness/harness-pins.md)
- [Skills matrix](../harness/skills-matrix.md)
