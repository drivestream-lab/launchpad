# Test quality program (backend apps)

Guidance for **unit vs verify** discipline in Python (or similar) app repos after harness sync.

**Example initiative:** `INIT-EXAMPLE-001` — WorkManifest SSOT is plan §9 + pinned
prayog `references/workmanifest-contract.md` (not Launchpad examples).

**Prerequisite:** `launchpad status --repo <app>` passes.

---

## Goals

| Goal | Outcome |
|------|---------|
| **Structure** | `tests/unit/` + test runner config pointing at unit tree |
| **Unit coverage** | Business logic, branches, edges in `tests/unit/` |
| **Verify alignment** | `tests/verify/` — one live happy path per product feature |
| **No overlap** | Same behavior not fully asserted in unit and verify |
| **Traceability** | `tests/README.md` feature map + `as-built/implementation-status.md` |

---

## Wave delivery (when PRD uses `delivery_model: waves`)

| Wave | Typical focus |
|------|----------------|
| **W0** | Repo structure, CI skeleton, harness |
| **W1+** | Domain slices — one board issue = one feature PR |

### Per-wave PR checklist

- [ ] Spec / capability row touched (if behavior changes)
- [ ] `tests/unit/` added or extended for logic edges
- [ ] Matching `tests/verify/` script — representative happy path only
- [ ] `tests/README.md` feature map updated
- [ ] `as-built/implementation-status.md` verification rows updated

---

## Board usage

Set **Initiative** and **Codebase** project fields on each issue. Move to **Verify** when PR includes the live verify command in the description.

---

## Related

- [sdd-workflow.md](../ship/sdd-workflow.md)
- [harness-pins.md](harness-pins.md)
- [delivery-workflow.md](../ship/delivery-workflow.md)
