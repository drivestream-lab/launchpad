# Specification layout (mandatory)

Every Launchpad **application repo** uses this frozen tree under `docs/specification/`. **No optional layers.** PM handoff and dev delivery both comply.

Layout defaults for profiles are documented in **prayog-skills** (`layout-defaults`).

---

## Frozen structure

```text
docs/specification/
  product/          ← what to build (capabilities, contracts, INIT slices)
  as-built/         ← what is live today (implementation + testing ground truth)
  adr/              ← why (accepted decisions)
```

**Forbidden:** `docs/specification/harness/`, duplicate testing trees, or ad-hoc top-level spec folders.

---

## Layer responsibilities

| Layer | Required files | Owner |
|-------|----------------|-------|
| **product/** | `00-service-profile.md`, `02-api-contract.md`, …; `INIT-*.md` per product initiative | **Dev** drafts via pinned Prayog workflow and maintains after merge |
| **as-built/** | `implementation-status.md` (live vs deferred + verification table; optional `## Testing harness` for layout/overlap policy — **Option B**) | **Dev** — update in same PR as code/test changes |
| **adr/** | Accepted ADRs before or with architecture changes | Dev + architecture review |

Outside `docs/specification/` (also mandatory):

| Path | Role |
|------|------|
| `AGENTS.md` | Agent router — constitution pin, playbook links, verify commands |
| `tests/README.md` | Runnable verify/debug commands + feature map (must match as-built) |

**Pre-build narrative docs do not belong in app repos.** Long-form architecture, cost, infra scale, and phased-rollout planning live in **<client>-meta** `planning/{service}/` (see [example planning README](../../examples/tenant-meta/planning/README.md)). App-repo agents and SDD tasks must not treat planning archives as SSOT.

---

## Planning archive (meta)

| Location | Purpose |
|----------|---------|
| `<client>-meta/planning/README.md` | Org policy — planning vs PRD vs product spec |
| `<client>-meta/planning/{service}/` | Pre-implementation narratives archived per service |

When planning content hardens: promote via **PRD** + app-repo **product/** + **ADR** — not by leaving aspirational docs in the app repo.

---

## PM handoff (product INIT)

Process: [delivery-workflow.md](delivery-workflow.md) · [delivery-model.md](delivery-model.md)

1. PRD in **<client>-meta** `prd/INIT-*.md` — declares `delivery_model` + wave table when `waves`
2. Eng opens spec PR per repo: `product/INIT-*.md` + feasibility + TDD + plan — **no `src/`**
3. Spec PR merge to **`develop`**
4. Dev runs `/create-board-tickets` after spec merge (plan §9 WorkManifest)
5. Dev implements from **product** + **as-built** — not from meta PRD alone

### INIT spec (`product/INIT-*.md`) — mandatory sections

Agent starting point: [templates/INIT-spec-PR.md](../../launchpad/templates/INIT-spec-PR.md). Reviewers gate against this list.

| Section | Requirement |
|---------|-------------|
| Metadata | Initiative id, status, **delivery_model** (must match PRD), link to meta PRD on `develop` |
| Goals | Outcomes table (structure, unit, verify, overlap, traceability) |
| Baseline | As-delivered items — do not re-implement |
| **Implementation waves** | Wave IDs **must match PRD** (W0, W1, …); may add **PRE*** gates after feasibility |
| Wave PR gate | Same-PR checklist (tests, feature map, as-built, overlap) |
| Appendix | Optional verify → wave → unit → canon (eng validates) |
| Dev read order | Spec → canon → as-built → tests README → AGENTS (once) |
| Smoke commands | CI (`make check`, `make test`) vs live scripts under `tests/verify/` (wave-acceptance) |
| Constraints | No initiative blocks in `AGENTS.md`; no `src/` in spec PR |

**Wave parity gate:** spec wave table IDs = PRD §4.0 / §4.5 wave IDs (PRE* allowed; scope may refine after `/initiative-feasibility`).

---

## Dev delivery (board issue)

1. `/pre-implement` — gate-only checklist (no product code / no branch open)
2. `/loop-spec` — implement + unit/check on `head_ref`; Forge `/commit-workspace` as required
3. `wave-pr-action` — Draft PR after `/loop-spec` (no required human
   `/open-draft-pr` when pin `authorization: automated`; walkers may still run
   it) → human **`wave-acceptance`** (smoke under `tests/verify` or P15 N/A;
   label **`wave-accepted`**)
4. **Same PR:** update `as-built/implementation-status.md` and `tests/README.md` as needed
5. Pass-2 closeout: `/learning-extract` → `/ground-spec` → pin may `wave-done-action`
   → `wave-signoff` (human merge only)
6. **Closure (all waves done, once):** `initiative-closure` →
   `/purge-initiative-artifacts-app` → `initiative-closure-pr-action-app` →
   `initiative-closure-signoff-app` → `/purge-initiative-artifacts-meta` →
   `initiative-closure-pr-action-meta` → `initiative-closure-signoff-meta`.
   Not per-wave. Launchpad does not delete files.

`tests/verify/` holds smoke **scripts** (not a skill package).

Test-quality retro (**INIT-EXAMPLE-001**): board spec path points to `product/INIT-EXAMPLE-001.md` and capability docs (e.g. `05-roles-and-authz.md`), not bootstrap artifacts.

---

## Repo onboarding checklist

- [ ] `docs/specification/product/` scaffold
- [ ] `docs/specification/as-built/implementation-status.md`
- [ ] `docs/specification/as-built/implementation-status.md` includes `## Testing harness` when repo has verify/pytest (Option B)
- [ ] `docs/specification/adr/README.md`
- [ ] `AGENTS.md`, `tests/README.md`
- [ ] **No** `harness/` folder

---

## Related

- [sdd-workflow.md](sdd-workflow.md)
- [test-quality-program.md](../harness/test-quality-program.md)
- [wiki: Spec structure](spec-layout.md) (this doc)
