# Skills audition

Score skills before marking harness or PM pipeline ready. Lab sample prompts: [launchpad/skills-audition](https://github.com/drivestream-lab/launchpad/blob/develop/playbook/harness/skills-audition.md).

**PM skills** install from [skills-matrix.md](skills-matrix.md) (`prayog-skills` + community `prd`) — hub symlinks via `apply-harness --meta`.

**Dev skills** install via `launchpad apply-harness --repo <name> --apply` — commit submodule gitlinks and pin file; skill symlinks are local-only.

---

## Scorecard

| Skill | Sample run date | Pass (Y/N) | Notes |
|-------|-----------------|------------|-------|
| prd | | | Community awesome-copilot |
| validate-requirements | | | prayog-skills |
| review-findings | | | prayog-skills |
| update-documents | | | prayog-skills |
| generate-work-manifest | removed v0.3.1 | — | was prayog-skills backlog skill; superseded by spec-implementation-plan §9 |
| initiative-feasibility | | | prayog-skills dev |
| spec-technical-review | | | prayog-skills dev (PE lane) |
| spec-implementation-plan | | | prayog-skills dev |
| pre-implement | | | prayog-skills dev (gate-only) |
| loop-spec | | | prayog-skills dev |
| open-draft-pr | | | forge walker — optional at wave-pr-action |
| learning-extract | | | prayog-skills dev (Pass-2 closeout) |
| ground-spec | | | prayog-skills dev (G1–G10) |
| verify | | | prayog-skills dev (manual; optional) |
| purge-initiative-artifacts-app | | | prayog-skills dev (closure; app) |
| purge-initiative-artifacts-meta | | | prayog-skills requirements (closure; meta) |
| spec-technical-review | | | T1–T12 when TDD produced |
| spec-implementation-plan | | | P1–P16 |

---

## 1. pre-implement (app repo)

**Workspace:** app repo on `develop` after harness sync

```text
/pre-implement

Slice: one board issue / wave from initiative spec.
```

**Pass if:** checklist lists AGENTS.md, relevant `.mdc`, as-built columns; states
verify vs unit scope; **no product code** and **no branch open** (gate-only).
Publish checklist via Forge `/commit-workspace` when the pin requires it.

---

## 2. verify (app repo — optional / manual)

**Workspace:** app repo — server running, `tests/config.yaml` configured  
**Note:** Not on the Pass-1 auto edge after `/loop-spec`. Human live-verify is the
checkpoint; `/verify` may aid that stop or an optional path toward closeout.

```text
/verify

Run verify for one feature area per tests/README.md.
```

**Pass if:** agent cites `tests/README.md`, uses documented verify command, notes env prerequisites.

---

## 3. Board tickets (forge skill — after spec merge)

```text
/create-board-tickets INIT-<id>
```

**Pass if:** epic + wave issues exist on the board with required project fields populated
(plan §9 WorkManifest; not a development-lane skill).

---

## 4. initiative-feasibility (app repo, spec PR branch)

**Workspace:** example-registry (or pilot repo), branch `chore/INIT-*-spec-<repo>`

```text
/initiative-feasibility

Initiative: INIT-EXAMPLE-003
Spec: docs/specification/product/INIT-EXAMPLE-003.md
```

**Pass if:** report saved; F-checks evidenced; PM questions routed to meta PRD PR; PE questions on spec PR; no `src/` edits.

---

## 5. spec-technical-review (app repo, PE lane — after feasibility)

**When:** Feasibility report has NEW-ADR or Critical engineering findings.

```text
/spec-technical-review

Initiative: INIT-EXAMPLE-003
Feasibility report: docs/specification/reports/Feasibility-Report-INIT-EXAMPLE-003.md
```

**Pass if:** TDD produced; **T1–T12** checks evidenced; draft ADRs for each NEW-ADR finding; PE questions resolved or deferred with defaults; PM questions explicitly routed (not answered by agent).

---

## 6. spec-implementation-plan (app repo, while spec PR open)

```text
/spec-implementation-plan

Initiative: INIT-EXAMPLE-003
Feasibility report path: docs/specification/reports/Initiative-Feasibility-Report-INIT-EXAMPLE-003.md
Technical review path: docs/specification/reports/Technical-Review-INIT-EXAMPLE-003.md (or N/A)
```

**Pass if:** §0 PE sign-off referenced; W0–Wn phases with REQ/TASK/FILE; done-when per task;
**P1–P16** checks (P16 = WorkManifest contract via pin validator); §9 WorkManifest YAML present.
Board tickets (`/create-board-tickets`) happen **after** spec merge.

---

## 7. loop-spec (app repo, Pass-1 — before wave Draft PR)

```text
/loop-spec

Implement W1 for INIT-EXAMPLE-003. Run {check_command} and {test_command} after each task.
Fix failures before moving on. Stop when all tasks green on head_ref.
Do not open the Draft PR, commit/push, or run /learning-extract / /ground-spec in this hop.
```

**Pass if:** agent implements task-by-task; records proof locally; does **not** run git/gh
mutations as skill success; leaves Forge readiness for `/commit-workspace` then
`wave-pr-action` (`open_draft_pr` requires).

---

## 8. open-draft-pr (forge walker — optional at wave-pr-action)

**When:** Walker path after `/loop-spec` + required `/commit-workspace` on the same
`head_ref`. Not required when the pin sets `authorization: automated` on
`wave-pr-action`.

```text
/open-draft-pr
```

Requires `title`, `body_path`, `head_ref`, `base_ref` (`draft: true`). Then human **live-verify**
on that Draft PR.

**Pass if:** Draft wave PR opened; no merge by this skill.

---

## 9. learning-extract (app repo, Pass-2 closeout)

**When:** After human live-verify / tip fixes; park at `wave-awaiting-closeout` cleared.

```text
/learning-extract

Wave: W1 of INIT-EXAMPLE-003
```

**Pass if:** structured learning report produced (L-* taxonomy); handoff toward `/ground-spec`.

---

## 10. ground-spec (app repo, after learning-extract)

```text
/ground-spec

Spec: 01  (or wave W1 of INIT-EXAMPLE-003)
```

**Pass if:** **G1–G10** (`GF-*` findings); ground report local only; handoff toward `wave-signoff`;
no commit/merge by this skill. Human merges at `wave-signoff`.

---

## 11. purge-initiative-artifacts-app (app repo — initiative closure)

**When:** All waves done; human `initiative-closure` judgment. **Not** after each wave.

```text
/purge-initiative-artifacts-app

Initiative: INIT-EXAMPLE-003
```

**Pass if:** allowlisted app working papers processed in app workspace; no KEEP deleted;
handoff toward meta purge. Launchpad does not perform deletes — skill owns semantics.

---

## 12. purge-initiative-artifacts-meta (meta repo — initiative closure)

**When:** After app purge in the closure lane.

```text
/purge-initiative-artifacts-meta

Initiative: INIT-EXAMPLE-003
```

**Pass if:** allowlisted meta working papers processed in meta workspace; handoff toward
`initiative-closure-pr-action`. No required human `/open-draft-pr` when pin
`authorization: automated` on that node; human merges at `initiative-closure-signoff`.

---

## Exit

- [ ] Dev bundle (§1–3, §4–12) scored **Y** on pilot repo
- [ ] Technical review audition cites **T1–T12** when TDD is produced
- [ ] `launchpad status --repo <pilot>` passes after harness migration PR
- [ ] C2 excluded: feasibility probes, security-gate/T13, `parallel_safe`, auto-merge
