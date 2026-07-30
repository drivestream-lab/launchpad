# Delivery model (INIT initiatives)

How implementation work is **declared** (PRD), **detailed** (repo spec), **tracked** (board), and **accepted** (PR merges).

**SSOT chain:**

```text
PRD delivery_model + wave table
  → repo spec (mirror wave IDs; may add PRE* gates)
  → dev: /spec-implementation-plan §9 WorkManifest YAML   ← on spec branch, before spec merge
  → spec PR merge
  → /create-board-tickets (forge; P16 + pin validator preflight)
  → /pre-implement → /loop-spec → wave-pr-action (/open-draft-pr) → live-verify
  → Pass-2: /learning-extract → /ground-spec → wave-signoff (human merge)
  → INIT closure when all units + success criteria pass
```

**Work manifest rule:** SSOT is plan §9 under pinned prayog
`references/workmanifest-contract.md` (`apiVersion: prayog/v1`). PM never
hand-writes Launchpad-owned WorkManifest YAML. Optional meta `work/` copies are
audit-only. See [delivery-workflow.md](delivery-workflow.md).

Related: [delivery-workflow.md](delivery-workflow.md) · [spec-layout.md](spec-layout.md) · [pm-workflow.md](../../docs/setup/pm-setup.md)

---

## Delivery models

Every INIT PRD declares exactly one model:

| Model | When to use | Board shape |
|-------|-------------|-------------|
| **`waves`** | Single-repo or harness INITs with phased delivery; test-quality programs; any PRD with an implementation wave table | Epic + **one issue per wave** (W0…Wn, optional PRE*) |
| **`repo-slice`** | Multi-repo product INIT where each app repo merges one implementation slice | Epic + **one issue per repo** |

**Default for harness / tech-debt INITs:** `waves`.

---

## 1:1 rule (waves model)

| Unit | Artifact |
|------|----------|
| 1 wave ID (e.g. **W2**) | 1 board issue |
| 1 board issue | 1 feature PR |
| 1 feature PR | 1 merge to `develop` |
| Wave **Done** | Per-wave PR gate passed (not whole INIT) |

Manifest task `id` **must equal** PRD/spec wave id (`W0`, `W1`, `PRE1`, …).

---

## Wave naming

| ID | Role |
|----|------|
| **W0** | Structure only — layout, CI, docs skeleton (no domain unit tests beyond health move) |
| **W1–Wn** | Domain — unit tests + verify alignment per wave table |
| **PRE*** | Optional plan/doc gate before a wave (e.g. unit test case matrix before W1) |

**Branch:** `feature/INIT-{COMPONENT}-{NUMBER}-w{N}-{slug}` (e.g. `feature/INIT-KAVACH-001-w1-auth-login`)  
**Issue title:** `[W<N>] <short summary>` or `[PRE1] <gate name>`

Do **not** use legacy labels (`4a`, `Phase 4b`) in new INITs — use **W0–Wn** only.

---

## Acceptance levels

### Per-wave (merge gate)

Blocked until all pass (from PRD/spec):

- Feature-map / as-built rows for touched capabilities updated (same PR)
- `make check && make test` green
- Overlap audit — no full HTTP journey duplicated in pytest
- Verify module headers updated where applicable

### INIT closure

After **all** wave issues are Done:

- Meta PRD success criteria (S1–Sn)
- Live verify / harness verify per PRD (closure gates — not necessarily every wave in CI)
- Board epic closed
- [delivery-workflow.md](delivery-workflow.md) wave checklist complete

---

## Responsibilities

| Step | PM | Dev |
|------|-----|-----|
| Declare `delivery_model` + waves in PRD | ✓ | review |
| Spec PR + `/spec-draft` | — | ✓ |
| `/spec-implementation-plan` §9 | — | ✓ (on spec branch) |
| Board tickets after spec merge | — | ✓ (`/create-board-tickets`) |
| Implement wave PRs | — | ✓ |
| Close epic | ✓ | verify S-criteria |

---

## Board tickets

Dev runs `/spec-implementation-plan` **while spec PR is open**. Plan §9 emits
WorkManifest YAML (`prayog/v1`) validated by P16 + pin
`scripts/workmanifest_contract.py`.

**After spec PR merge**, dev runs forge **`/create-board-tickets`** (preflight + project).

| Role | Action |
|------|--------|
| **Dev** | Owns §9 YAML content on the spec branch |
| **Dev** | `/create-board-tickets` after spec PR merge |
| **PM** | Does **not** author manifest before spec merge; may archive a §9 copy under meta `work/` (non-schema) |

Do not treat Launchpad examples as WorkManifest SSOT.

---

## Agent templates (meta)

| Template | Use |
|----------|-----|
| [templates/INIT-PRD-outline.md](../../launchpad/templates/INIT-PRD-outline.md) | `/prd` — Delivery section stub |
| [templates/INIT-spec-PR.md](../../launchpad/templates/INIT-spec-PR.md) | Spec PR on app repo |

Playbook = policy; templates = agent starting structure.
