# Agent prompt templates

Copy-paste starters for Cursor Agent. **Use the section for your role** — workspace and skills differ.

**Skills:** [skills-matrix.md](../playbook/harness/skills-matrix.md) · **Workflow:** [delivery-workflow.md](../playbook/ship/delivery-workflow.md) · **Audition:** [skills-audition.md](../playbook/harness/skills-audition.md)

---

## Who uses what

| Role | Open in Cursor | Skills | Typical work |
|------|----------------|--------|--------------|
| **Product owner / PM** | `<client>-meta` | `/prd`, `/validate-requirements`, `/review-findings`, `/update-documents`, `/prd-impact-map` | PRD writing, impact mapping, product Q&A on PRD PR |
| **Developer** | App repo (e.g. `example-api`) | `/spec-draft`, `/initiative-feasibility`, `/spec-technical-review`, `/spec-implementation-plan`, `/pre-implement`, `/loop-spec`, `/learning-extract`, `/ground-spec`, `/verify` | Opens spec PR, plan, `/create-board-tickets` after merge; Pass-1 loop → live-verify; Pass-2 `/learning-extract` → `/ground-spec` |

**Board:** cite **GitHub issue #** and **full title** — not manifest ids (`Q1`, `T2`) in conversation.

---

# Product owner / PM prompts

**Workspace:** `<client>-meta` (not example-api).  
**Install once:** [skills-matrix.md](../playbook/harness/skills-matrix.md) — `prd` + `prayog-skills` bundle.

---

## 1 — Draft PRD (new product INIT)

**When:** Phase 1 — new initiative, no merged PRD yet.  
**Branch:** `chore/INIT-<id>-prd` from `develop`

```text
Initiative: INIT-EXAMPLE-002 (proposed)
Branch: chore/INIT-EXAMPLE-002-prd from develop

/prd

Follow templates/INIT-PRD-outline.md and playbook/ship/delivery-model.md.
Declare delivery_model: waves | repo-slice.
If waves: include §4.0 Delivery model + §4.5 Implementation waves (W0, W1, …).

Outline:
- Goal: (one sentence)
- Repos affected: example-api, example-registry, …
- Constraints: (timeline, out of scope)

Output: prd/INIT-EXAMPLE-002.md only. No application code.
```

---

## 2 — Validate PRD

**When:** After draft PRD or outline exists.  
**Output:** `prd/reports/Validation-Report-INIT-*.md`

```text
/validate-requirements

Initiative: INIT-EXAMPLE-002
Primary doc: prd/INIT-EXAMPLE-002-outline.md
Also read:
- example-api docs/specification/product/04-cross-service-contracts.md
- (other affected repo product specs)

Report: prd/reports/Validation-Report-INIT-EXAMPLE-002.md
Read-only unless I ask to apply fixes.
```

---

## 3 — Review validation findings

**When:** Validation report has open items; PM decides accept / defer / fix.

```text
/review-findings

Report: prd/reports/Validation-Report-INIT-EXAMPLE-002.md
Primary doc: prd/INIT-EXAMPLE-002.md

Output: prd/reports/Resolution-INIT-EXAMPLE-002.md with decisions per finding.
Do not edit PRD until I confirm resolution.
```

---

## 4 — Apply PRD fixes

**When:** Resolution report approved; update PRD and spec drafts on PR branch.

```text
/update-documents

Resolution: prd/reports/Resolution-INIT-EXAMPLE-002.md
Update: prd/INIT-EXAMPLE-002.md
Also align: (list spec paths on open PR branches if any)
```

---

## 5 — Impact map (before eng opens spec PRs)

**When:** PRD validated and initiative identity collisions are resolved; before
the PRD PR and before app spec PRs.

```text
/prd-impact-map

Initiative: INIT-EXAMPLE-002
PRD: prd/INIT-EXAMPLE-002.md
Service catalog: config/service-catalog.yaml

Generate prd/reports/Impact-Map-INIT-EXAMPLE-002.md locally.
Present the PR-readiness handoff and stop without GitHub side effects.
After I explicitly authorize PR creation, use gh when configured; otherwise
provide exact commands. Initialize impact-map-pending for PE `prd-impact-acceptance`.
```

---

## 6 — Spec vs PRD conformance (PM only — meta workspace)

**When:** PM validates spec drafts against PRD in meta workspace.

```text
/validate-requirements

Initiative: INIT-EXAMPLE-002
Primary doc: prd/INIT-EXAMPLE-002.md on <client>-meta develop
Spec draft: product/INIT-EXAMPLE-002.md on spec PR branch (or pasted path)
Check: repo spec slice matches PRD.
Report only — list gaps; do not merge spec PR until clean.
```

**Dev on spec PR:** runs `/spec-draft` → `/initiative-feasibility` → `/spec-technical-review` (if NEW-ADR) → `/spec-implementation-plan`. PM does **not** write spec files. Product Q&A on **meta PRD PR**; PE Q&A on **spec PR**.

---

## 7 — Board tickets (dev — after spec PR merges)

**When:** Spec PR merged to `develop` in app repo.  
**Workspace:** app repo (not meta).  
**Skill:** forge `/create-board-tickets` (plan §9 WorkManifest already in the plan)

```text
/create-board-tickets INIT-EXAMPLE-002
```

**Pass if:** EPIC + wave sub-issues on the programme board from plan §9.

---

## 8 — INIT retro — spec closure (chore)

**When:** PRD signed off; retro closure like **INIT-EXAMPLE-001** (implementation already on `develop`).

```text
Initiative: INIT-EXAMPLE-001
Repo: example-api
Branch: chore/INIT-EXAMPLE-001-spec-example-api from develop

Add docs/specification/product/INIT-EXAMPLE-001.md:
- Status Closed / retro; link to <client>-meta prd/INIT-EXAMPLE-001.md
- As-delivered wave table (#27–#32) + dev read order
- Delete superseded product quality spec; update README + tests/README header

No src/. No tests/.

PR title: [INIT-EXAMPLE-001] Spec — example-api (retro)
Label: spec
```

**PRD:** `prd/INIT-EXAMPLE-001.md` (in `<client>-meta/prd/`)

---

# Developer prompts

**Workspace:** app repo root (e.g. **`example-api`**), branch `develop` (or feature branch from develop).  
**Skills:** prayog-skills dev bundle in `.agents/skills/` (seeded by `apply-harness`).  
**Do not** edit `.cursor/rules/` submodule — propose upstream in service-rules. Skill changes → [prayog-skills](https://github.com/drivestream-lab/prayog-skills).

**Read first:** `AGENTS.md` → board issue **Spec path** → `docs/specification/as-built/`.

---

## D1 — Product INIT — implementation slice

**When:** Board issue from seeded INIT epic; spec handoff already on `develop`.  
**One issue = one PR.**

```text
Initiative: INIT-EXAMPLE-002
Issue: #42 — [feature] Short title from GitHub
Repo: example-api (this workspace)

/pre-implement

Read:
- AGENTS.md
- docs/specification/product/INIT-EXAMPLE-002.md
- docs/specification/product/02-api-contract.md (if routes)
- docs/specification/as-built/implementation-status.md

Execute one slice:
1. Implement code + tests (unit vs verify — no overlap)
2. Update product spec status if behavior ships
3. Update as-built/implementation-status.md in same PR
4. Run board Verify command

Branch: feature/INIT-EXMPL-002-w{N}-{slug}  ← see branching-policy.md
Verify: (paste from board — e.g. make check && poetry run python -m tests.verify.verify_all)

Do not edit .cursor/rules/ submodule.
```

---

## D2 — Test maintenance chore (post–INIT-EXAMPLE-001)

**When:** Future test work on example-api after **INIT-EXAMPLE-001** retro closure. Waves W1–W5 are **done** — do not re-run.  
**Handoff SSOT:** `docs/specification/product/INIT-EXAMPLE-001.md`

```text
Initiative: INIT-EXAMPLE-001
Issue: #<n> — [chore] <test area>
Repo: example-api (this workspace)

/pre-implement

Read:
- docs/specification/product/INIT-EXAMPLE-001.md (dev read order)
- docs/specification/product/<relevant capability>.md
- docs/specification/as-built/implementation-status.md (## Testing harness)
- tests/README.md

Deliver per overlap rules: unit and/or verify trim; update feature map + as-built.

Branch: chore/INIT-EXAMPLE-001-<slug>
Verify: make test (or board Verify command)

Do not edit .cursor/rules/ submodule. No new product features unless scoped.
```

### Historical wave reference (complete — do not re-implement)

| Wave | Product spec | Verify |
|------|--------------|--------|
| W1 auth | `05-roles-and-authz.md` | `make test` |
| W2 onboarding | `03-tenant-and-user-lifecycle.md` | `make test` |
| W3 device/OTP | `06-device-traffic-and-mqtt.md` | `make test` |
| W4 bridge | `06-device-traffic-and-mqtt.md` | `make test` |
| W5 close-out | `tests/README.md` | `make check && poetry run python -m tests.verify.verify_all` |

---

## D3 — Spec PR (dev writes spec, reviews, plans)

**When:** Eng opened spec PR after impact map LGTM. May parallel meta PRD PR.  
**Workspace:** app repo, branch `chore/INIT-*-spec-<repo>`.

### D3a — Write spec slice (first)

```text
/spec-draft

Initiative: INIT-EXAMPLE-003
PRD: <client>-meta/prd/INIT-EXAMPLE-003.md  (meta PRD PR branch or develop)
Repo: example-registry (this workspace)

Output: docs/specification/product/INIT-EXAMPLE-003.md
Review and edit before committing — this is a draft.
```

### D3b — Review buildability (after committing spec draft)

```text
/initiative-feasibility

Initiative: INIT-EXAMPLE-003
Spec: docs/specification/product/INIT-EXAMPLE-003.md
PRD: <client>-meta/prd/INIT-EXAMPLE-003.md

Output: docs/specification/reports/Initiative-Feasibility-Report-INIT-EXAMPLE-003.md
Post PM questions on meta PRD PR (plain English).
Post PE questions on this spec PR. Route to /spec-technical-review.
```

### D3c — PE technical review (when feasibility has PE questions / NEW-ADR)

```text
/spec-technical-review

Initiative: INIT-EXAMPLE-003
Feasibility report: docs/specification/reports/Initiative-Feasibility-Report-INIT-EXAMPLE-003.md
Spec: docs/specification/product/INIT-EXAMPLE-003.md

Output: docs/specification/reports/Technical-Review-INIT-EXAMPLE-003.md
Commit TDD to spec branch. PE Approve on the same spec PR.
```

### D3d — Implementation plan (after PE approves TDD if required)

```text
/spec-implementation-plan

Initiative: INIT-EXAMPLE-003
Technical review: docs/specification/reports/Technical-Review-INIT-EXAMPLE-003.md (or N/A)
Feasibility report: docs/specification/reports/Initiative-Feasibility-Report-INIT-EXAMPLE-003.md
Spec: docs/specification/product/INIT-EXAMPLE-003.md

Output: docs/specification/reports/Implementation-Plan-INIT-EXAMPLE-003.md
Includes §WorkManifest YAML. Merge spec PR, then `/create-board-tickets`.
```

---

## D4 — Verify only (optional / manual)

**When:** Human wants a live-verify aid; **not** required on the Pass-1 edge after `/loop-spec`.

```text
/verify

Initiative: INIT-EXAMPLE-001
Issue: #<n>
Verify command: make test

Run the command; report pass/fail and any fixes needed.
```

Live stack example:

```text
/verify

Initiative: INIT-EXAMPLE-002
Issue: #42
Verify command: make check && poetry run python -m tests.verify.verify_all

conda activate example-api required for verify_all.
```

---

## D5 — Cross-service check

**When:** Issue touches HTTP routes, JWT claims, or peer integrations.

```text
Initiative: INIT-EXAMPLE-002
Issue: #42
Repo: example-api (this workspace)

Before implementing:
Read docs/specification/product/04-cross-service-contracts.md
Read example-registry docs/specification/product/ (relevant integration doc)

Confirm example-api changes do not break EMQX auth, device validation, or Kafka bridge contracts.
```

---

## D6 — Wave implementation (Pass-1 → live-verify → Pass-2 closeout)

**When:** Board wave issue is In Progress; pre-implement checklist is done.  
**One wave = one PR.** Pass-1 stops at human live-verify; closeout is separate.

```text
Initiative: INIT-EXAMPLE-002
Issue: #42 — [INIT-EXMPL-002 W1] extraction engine
Repo: example-api (this workspace)
Branch: feature/INIT-EXMPL-002-w1-extraction (already open from /pre-implement)

/loop-spec

Implement W1 tasks in order from plan.
Run {check_command} and {test_command} after each task.
Fix failures before moving on. Stop when all tasks green for human live-verify.
Do not run /learning-extract or /ground-spec in this hop.
Do not implement W2 scope.
```

After human live-verify / tip fixes (Pass-2 closeout):

```text
/learning-extract

Wave: W1 of INIT-EXAMPLE-002
```

Then:

```text
/ground-spec

Spec: 01  (or wave W1 of INIT-EXAMPLE-002)
Commit ground report as last commit on feature/INIT-EXMPL-002-w1-extraction.
Open PR: "[INIT-EXMPL-002 W1] extraction engine — implementation + ground report"
```

---

## D7 — Harness / platform chore (bootstrap — reference)

**When:** BOOTSTRAP-001-style harness work in app repo (historical).

```text
Initiative: BOOTSTRAP-001
Repo: example-api
Task: Harness only — no product features.

/pre-implement

Deliverables: AGENTS.md links to <client>-meta playbook; .agents/skills; PR template; as-built columns.
Verify: make check
```

---

## PR traceability (both roles)

Every PR description should match board fields:

| Field | Example |
|-------|---------|
| Initiative | `INIT-EXAMPLE-001` or `INIT-EXAMPLE-002` |
| Issue | `#<n>` |
| Spec path | `docs/specification/product/INIT-EXAMPLE-001.md` |
| Verify command | `make test` |

Template: app repo `.github/pull_request_template.md`
