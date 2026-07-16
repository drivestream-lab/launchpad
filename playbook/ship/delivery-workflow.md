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
| `<client>-meta` PRD PR | PM team | Product clarification, PRD, impact map, Gate 1 |
| App spec PR | Profile developer team | Repo spec, feasibility, optional TDD, plan, Gate 2 |
| App wave PR | Profile developer team | Code, tests, verify evidence, ground report |
| Gate 1 | PE / tech lead | Engineering handoff readiness |
| Gate 2 | PE / engineering gate | Coding readiness |
| Wave checkpoint | Peer/tech lead | Grounded implementation evidence |

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
- Gate 1 labels: `impact-map-pending`, `impact-map-blocked`,
  `impact-map-lgtm`; `impact-map-revised` or `impact-map-stale` closes the gate.
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
- Initial Gate 2 label: **`spec-pending`** (provision with `launchpad apply-gates --repo <name> --apply`)
- PE sets **`spec-lgtm`** only when spec + feasibility + TDD + Accepted ADRs +
  implementation plan §9 are on the current head
- PE also submits GitHub **Approve** with attestation (initiative, head SHA,
  digests, artifact paths) — never infer approval from the label alone
- Mark **Ready for review** before merge (Draft PRs cannot merge while Draft)
- New commits after `spec-lgtm` → add `spec-revised`, remove `spec-lgtm`
- Merge means the repo slice is ready to build; then board-seed from plan §9

#### Gate 2 label transitions (PE)

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
- Applicable live verification runs before grounding.
- Ground Report is committed before human approval.

## Board seed binding

Board seeding uses **`/board-seed`** (development lane, **stack-agnostic**) after
spec PR merge. Preconditions:

1. Merged spec PR head had **`spec-lgtm`**
2. `Implementation-Plan-{initiative}.md` and valid §9 WorkManifest on `develop`
3. Programme board resolved from read-only meta governance (`launchpad board-bind`)
4. Explicit developer authorization before `gh issue create`

The skill reads plan §9 and governance `project_board`, creates **EPIC + wave
sub-issues** on the org Project (`--parent`, `--project`), and groups under the
initiative label. If `gh` is unavailable, it prints exact commands.
`/pre-implement` remains blocked until the epic tree is complete.

Requires `gh auth refresh -s project` and **Project WRITER** on the programme board.

Optional: enable `github/workflows/board-seed-gate.yml` from the launchpad
template to fail CI when a spec PR merges without `spec-lgtm` or without a
plan file on the merge commit.

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
