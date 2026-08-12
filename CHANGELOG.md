# Changelog

All notable changes to the launchpad kit. Install a release tag:

```bash
pipx install "launchpad @ git+https://github.com/drivestream-lab/launchpad@<tag>"
launchpad --version   # should match <slug>-meta/.launchpad-version
```

Pick `<tag>` from the latest section below or [GitHub Releases](https://github.com/drivestream-lab/launchpad/releases).

---

## [0.5.33] — 2026-08-10

### Fixed

- **`--client` workspace resolution:** `reset-harness` no longer treats
  `workspace=""` as an override of cwd. Blank overrides are ignored;
  `clients.yaml` workspace (via `--client` / `LAUNCHPAD_CLIENT`) is used from
  any working directory. CLI now passes `client_id` explicitly into harness /
  status / scaffold / init / gates / forge-template commands.

---

## [0.5.32] — 2026-08-07

### Fixed

- **Origin tip SSOT for harness pins:** `apply-harness` force-updates retargeted
  tip tags and reports `tip moved` when local HEAD ≠ origin tip.
  `status --repo` compares local submodule HEAD to origin tip (same helper);
  prints `[?]` when origin is unreachable instead of false-green remote sync.
- Maintainer fixture tip checklist + optional `scripts/check-fixture-pin.sh`.

---

## [0.5.31] — 2026-08-06

### Breaking

- **Wave-acceptance alignment:** playbooks, AGENTS, examples, and fixtures track
  prayog tip **`d3bd94e`** (`wave-acceptance`; label **`wave-accepted`**; no
  `/verify` skill; no `live-verify` checkpoint). Pass-2: closeout → pin
  `wave-done-action` (board Done) → `wave-signoff` (merge only).
- **Dual initiative-closure signoffs:** consume
  `initiative-closure-signoff-app` / `initiative-closure-signoff-meta` (drop
  single `initiative-closure-signoff`).
- **Drop prayog v0.4.3 floor:** `forge_skills` required again at the pinned
  profile. Remount programmes onto tip `d3bd94e` (or a later retag) before
  following delivery playbooks: fix meta `skills[].ref`, then
  `reset-harness` → `apply-harness`.

### Changed

- Fixtures vendored from `d3bd94e` (scrubbed orch product names from comments).
- Deleted fixture `skills/development/verify/` stub.

---

## [0.5.30] — 2026-08-04

### Changed

- **Compat / prayog floor v0.4.3:** `apply-harness` accepts profiles that omit
  or leave empty `forge_skills` (lane skills only). Newer pins that declare
  `forge_skills` still materialize forge. Tenant chooses `skills[].ref`; Launchpad
  does not require a tip bump to rematerialize.

---

## [0.5.29] — 2026-08-04

### Breaking

- **Stack identity equality:** remove `prayog_profile` aliases (schema rejects the
  field). Harness profile name == prayog `profiles/{name}.yaml` == pin profiles.
- **Remove `data-platform` stack kit** (`harness-pin` / `CODEOWNERS`). Domain/team
  remains `data-platform-devs` owning stack **`flink`**.
- Fix `harness-pin.nextjs-frontend.yaml` to use `nextjs-frontend` (was `frontend`).

### Added

- Stacks **`flink`** and **`edge-agent`**: pin + CODEOWNERS templates, example
  YAML, interview comments, fixtures/tests.
- Docs: stack/team laws (`stacks.md`, `teams-and-rbac.md`); `reset-harness`
  documented with harness apply flow.
- Generalized constitution `rules.repo` rewrite in `apply-harness` (no allowlist).

### Remount

1. Meta: drop `prayog_profile:`; rename `data-platform` stack → `flink`; bump
   `skills[].ref` to **`v0.5.0-rc.2`** (retagged prayog tip).
2. Per clone: `launchpad reset-harness --apply` then `apply-harness --apply`.
3. Commit pin, AGENTS, CODEOWNERS, submodule SHAs.

Pairs with prayog-skills tip under the **same** tag `v0.5.0-rc.2`
(`nextjs-frontend`, `flink`, `edge-agent` profiles).

---

## [0.5.28] — 2026-08-04

### Changed

- **`AGENTS.meta.md`:** add initiative-closure narrative for the meta workspace
  (`/purge-initiative-artifacts-meta` after app purge; automated closure PR;
  human `initiative-closure-signoff`). Slash list was already seeded from the
  profile; this closes the app/meta AGENTS asymmetry from v0.5.27.

---

## [0.5.27] — 2026-08-04

### Changed

- **Remount tip `v0.5.0-rc.2` @ `bb8b1db`:** initiative-closure purge lane fixtures
  and playbooks. Pass-1/Pass-2 unchanged; add closure once after all waves.
- Profiles: `purge-initiative-artifacts-app` (app) /
  `purge-initiative-artifacts-meta` (meta); fixture `frontend.yaml` added.
- `review_roles`: `initiative-closure-signoff` (app + meta-pm).
- Playbooks/AGENTS: no per-wave purge; no required `/open-draft-pr` on
  `initiative-closure-pr-action` when pin `authorization: automated`; Launchpad
  still does not delete files or own WorkManifest.

### Added

- Fixture stubs for both purge skills (`SKILL.md` only).

---

## [0.5.26] — 2026-07-30

### Changed

- **Pass-1 UX:** playbooks/AGENTS no longer require a human `/open-draft-pr` click
  for `spec-pr-action` / `wave-pr-action` when the pin sets `authorization: automated`.
  Sequence stays `/pre-implement` → `/loop-spec` → `wave-pr-action` → `live-verify`.
  Forge trio remains for walkers; Launchpad still does not parse authorization.
- Re-vendor pin `workflow.yaml` + `delivery-contract.yaml` (tip of `v0.5.0-rc.2`
  family); example harness `ref` stays **`v0.5.0-rc.2`**.

---

## [0.5.25] — 2026-07-30

### Changed

- **Remount prayog `v0.5.0-rc.2`** (`b3180b3…`): keep `delivery_contract: sdd-delivery/v2`
  (WorkManifest + `wave-pr-action` on tip without a v3 contract bump).
- **Pass-1 docs:** `/pre-implement` → `/loop-spec` → `wave-pr-action` (`/open-draft-pr`)
  → `live-verify`. Pass-2 unchanged. Content vs Forge wording in AGENTS/playbooks.
- **Retire board-seed gate:** delete `board-seed-gate.yml` from kit and stop seeding it.
- **WorkManifest debt:** remove `launchpad/v1` example YAML; point at prayog contract +
  `tests/fixtures/workmanifest/valid.yaml`; plan §9 SSOT.
- **Audition:** T1–T12, P1–P16, G1–G10 (`GF-*`); C2 excluded.
- Vendored pin `workflow.yaml` + `delivery-contract.yaml` into test fixtures.

### Added

- **`launchpad reset-harness`** — clear skill hub/mirrors, `.harness-pin.yaml`, AGENTS
  harness block; `--include-seeded-workflows` purges allowlisted kit workflows
  (including legacy `board-seed-gate.yml`).

---

## [0.5.24] — 2026-07-29

### Changed

- **Pass-1 / learning-extract alignment:** fixtures and docs match prayog purpose-named
  checkpoints (`prd-impact-acceptance`, `coding-readiness`) and Pass-1 stop at
  `live-verify` with Pass-2 closeout `/learning-extract` → `/ground-spec` →
  `wave-signoff`. `/verify` remains installable as manual.
- Fixture `review_roles` keys retargeted; app profiles add `learning-extract`
  (order mirrors prayog); label descriptions use purpose names (label **names**
  unchanged).
- Playbook, skills audition, agent prompt templates, spec-layout, exit criteria
  updated for the new wave sequencing.

---

## [0.5.23] — 2026-07-28

### Changed

- **Retire `/board-seed` guidance:** human copy, AGENTS, status, board-bind,
  engineer-setup, and delivery-workflow point at forge
  `/create-board-tickets` after spec merge (plan §9 WorkManifest; no separate
  content hop). Pairs with prayog Option B
  (`spec-merge` → `board-tickets-action` → `pre-implement`).
- Fixtures/tests: drop `board-seed` from app `development_skills` expectations;
  keep forge trio including `create-board-tickets`.
- `board-seed-gate.yml`: filename and workflow `name` unchanged; comments/echo
  say `/create-board-tickets`.

---

## [0.5.22] — 2026-07-28

### Added

- **Forge skills install surface:** `apply-harness` resolves required
  `forge_skills` from prayog `profiles/*.yaml` and materializes
  `skills/forge/<name>/` into the hub and configured runtimes (meta + app).
  Shared human skills: `/commit-workspace`, `/open-draft-pr`,
  `/create-board-tickets`. Not workflow graph nodes; distinct from kit forge
  templates (`apply-forge-templates`).

### Changed

- **Fail-closed skill materialize:** missing or empty `forge_skills`, or any
  listed skill without `SKILL.md` under `skills/{requirements|development|forge}/`,
  causes `apply-harness` to exit non-zero (no soft WARN skip).
- Playbook / SCHEMA: document the third install bucket and forge-skills vs
  forge-templates terminology.

---

## [0.5.21] — 2026-07-17

### Changed

- **`AGENTS.md` ownership contract (Option A):** launchpad regenerates only the
  marked harness block between `<!-- launchpad:harness-start -->` and
  `<!-- launchpad:harness-end -->`. Team sections outside the markers
  (Run/verify, Product, local notes) are never overwritten.
- Greenfield seed writes templates that already include the markers.
- Unmarked brownfield: `apply-harness` strips stale factory prose, inserts the
  managed block, and keeps team sections — no extra CLI flags.
- AGENTS templates: workflow path is `prayog-skills/workflow.yaml` (root submodule).
- **`status --repo` skills drift** checks `prayog-skills/` at repo root (not the
  pre-v0.5.20 nested `.agents/skills/prayog-skills/` path).
- **`apply-gates`** skips with exit 0 when `delivery_contract` is omitted
  (legacy pin); still requires a contract-compatible prayog pin when declared.
- **`status --meta`** reports prayog-skills declared refs vs GitHub
  `releases/latest` (advisory only — tenants own `skills[].ref` bumps).
- Docs/examples: drop stale `v0.4.3-rc.1`; pin choice is tenant-owned via
  GitHub latest (illustrative examples use `v0.4.3`).
- **Selective agent skills:** do not symlink the full `prayog-skills` pack into
  `.agents/skills/` / `.claude/skills/`. Only names from the pinned
  `profiles/*.yaml` list are linked; leftover full-pack runtime links are removed
  on apply.
- **`onboard interview` day-1:** asks for PM/PE team slugs (defaults `pm-team` /
  `pe-team`), writes them into governance + `delivery_roles`; seeds meta-pm with
  `prayog-skills` `ref: latest`, community `/prd`, and `delivery_contract`; app
  profiles commented for Day N. Drops `platform-core` / `python-agent-skills`.
- **`ref: latest` for skills:** `apply-harness` resolves GitHub `releases/latest`
  and pins that tag; harness-pin / AGENTS record the concrete resolved ref.

---

## [0.5.20] — 2026-07-15

### Changed

- **`prayog-skills` submodule mounts at repo root** (`prayog-skills/`) instead of
  `.agents/skills/prayog-skills/`, so only hub-selected skills are activated under
  `.agents/skills/` / `.claude/skills/`. Re-run `apply-harness --apply` and commit
  the updated gitlink after upgrading.
- Constitution `repo` accepts `org/repo` slugs (e.g.
  `drivestream-lab/python-services-rules`); org is parsed from the slug when present.

---

## [0.5.19] — 2026-07-14

### Fixed

- **`env.d/<client>.env` is SSOT for factory PATs** — `load_dotenv(..., override=True)`
  so a stale shell `GITHUB_TOKEN` / `GH_TOKEN` no longer shadows the client file
  (avoids private-repo label 404s when ambient env wins).

---

## [0.5.18] — 2026-07-14

### Added

- **`board-bind`** — resolve programme engineering board from governance YAML
  (read-only meta); optional `--apply` links repo(s) to the org Project.
- Delivery-contract / workflow verification against the pinned Prayog checkout;
  contract recorded in harness pins and `status`.
- **`apply-gates`** — dry-run/apply for contract-declared labels and review-role
  access validation.
- Profile token `app` — stack-agnostic Gate 2 labels for any non-meta-pm harness.
- `apply-harness --repo` seeds delivery workflows (`ci.yml`,
  `policy-branch-name.yml`, `board-seed-gate.yml`) when `delivery_contract` is set.
- `AGENTS.md` programme board section (`{{BOARD_NAME}}`, `{{BOARD_URL}}`) for
  app repos with a delivery contract.

### Changed

- **`workspace` lives in `~/.config/launchpad/clients.yaml`** (machine-local).
  Shared `programme.yaml` must not contain `workspace` — schema fails closed.
- Clone layout: `clients[].workspace` or default `path.parent`.
- `onboard interview` writes `path` + `workspace` into clients.yaml only.
- Delivery playbook documents Draft spec PR, Gate 2, PE attestation, and
  merge → `/board-seed` → `/pre-implement` sequencing (pairs with Prayog v0.4.3).
- Existing team-owned `AGENTS.md` preserved in full on re-apply.

### Removed

- **`LAUNCHPAD_TENANT_ROOT`** — unused env override; docs and examples purged.
  Use `--client` / `clients.yaml`, or `--config-dir` for scripts.

---

## [0.5.17] — 2026-07-10

### Added

- **`apply-harness`** seeds `.gitignore` harness block (`gitignore.harness` template) so skill symlink mirrors are ignored
- **`examples/tenant-meta/.gitignore`** — skeleton for Path B onboarding

### Changed

- Upgrades legacy `.agents/skills/*/` patterns to `.agents/skills/*` on re-apply (symlinks vs directories)

---

## [0.5.16] — 2026-07-10

### Added

- **`docs/`** four-pillar layout — setup, onboarding, scaffolding, contributing
- **`playbook/`** subdirs — `ship/`, `harness/`, `github/`, `operator/`, `wiki/`
- **`docs/onboarding/`** — bootstrap prerequisites, factory CLI, exit criteria
- **`examples/agent-prompt-templates.md`** — moved from playbook
- **`CHANGELOG.md`** at repo root as version SSOT for docs (`@<tag>`)

### Changed

- Onboarding docs folded: org setup → `tenant-meta.md`; Cursor ↔ GitHub → `engineer-setup.md`
- **`apply-harness`** preserves existing `AGENTS.md` **Run and verify** section on re-sync
- Harness docs aligned with gitignored skill symlinks + tracked submodules model
- Kit templates and cross-links updated for new paths

### Removed

- Flat `playbook/*.md` files at playbook root (replaced by subdirs + `docs/onboarding/`)
- Obsolete `docs/` files (setup-guide, greenfield, onboarding-wizard, blog, etc.) — no redirects
- **`setup.py`** — unused wheel hook; packaging is `pyproject.toml` only (`launchpad/templates/` via `package-data`)

---

## [0.5.15] — 2026-07-10

### Added

- **`apply-forge-templates`** — seed `.github/ISSUE_TEMPLATE/` and `pull_request_template.md` from kit + governance
- Harness skill **hub** materialization with **community skills** support
- **`print_next_box`** — shared CLI helper for consistent NEXT output across commands
- Forge template staleness checks in **`status`**

### Changed

- **`status`** — forge template drift detection; hub + runtime skill path checks
- Kit issue templates use governance placeholders (`{{REPO_LIST_YAML}}`, `{{BOARD_URL}}`, etc.)

---

## [0.5.14] — 2026-07-09

### Added

- Harness skill **hub** (`.harness/skills/<name>/`) mirrored into `skill_runtimes` (default `.agents/skills`, `.claude/skills`)
- **`community_skills`** and **`skill_runtimes`** on harness profiles; community submodules under `.harness/community/`
- **`prayog_profile`** optional alias when harness stack name differs from prayog profile filename

### Changed

- **`apply-harness`** resolves skill names from prayog `profiles/*.yaml` at pinned ref (no Python fallbacks)
- **`status`** checks hub + all runtime paths; fails if prayog profile missing at pinned ref

---

## [0.5.13] — 2026-06

### Added

- **`CODEOWNERS.terraform-iac`** and **`harness-pin.terraform-iac.yaml`** harness templates
- Terraform-iac stack examples and docs

### Changed

- **`apply-harness`** substitutes `terraform-infra-rules` in harness pin templates
- **`init-client`** creates `develop` from `main` (`policy.integration_branch`) and protects both branches
- **`apply-harness`** pins constitution and prayog-skills as git submodules; improved tag fetch/checkout
- **`status --repo`** skills submodule drift check
- **`apply-scaffold`** helpful `--force` hint when output directory already exists
- Restore **`github_ops.py`** for GitHub forge (teams, repos, branch protection, projects)

---

## [0.5.11] — 2026-05

### Changed

- Align playbook, docs, examples, and templates with the 5-command CLI (remove stale commands)
- **`apply-harness`** seeds agent skills under **`.agents/skills/`** (removes legacy `.cursor/skills` submodule)
- Wiki publish documented as manual git flow (no `publish-wiki` CLI)

---

## [0.5.10] — 2026-04

### Added

- **5-YAML config model** — programme, governance, harness, scaffold, service-catalog
- **5-command CLI** — `onboard interview`, `init-client`, `apply-scaffold`, `apply-harness`, `status`
- **`onboard interview`** — 4 questions → writes config YAMLs + client registry + PAT stub
- GitHub-only forge (GitLab planned)

### Removed

- Legacy commands: `setup-gitflow`, `seed-work`, `bootstrap-project`, public `onboard apply/plan/show`

---

## Earlier releases

See git history and [GitHub Releases](https://github.com/drivestream-lab/launchpad/releases) for pre-0.5.10 tags.
