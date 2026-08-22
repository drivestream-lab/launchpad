# Stacks Reference

A **stack** is a named technology profile. It drives **harness** (constitution +
prayog profile + generated pin / CODEOWNERS layout). Scaffold is separate —
opt-in per repo in `scaffold-<org>.yaml`.

## First principles

| Layer | Answers | Examples |
|-------|---------|----------|
| **Domain / team** | Who owns merge + CODEOWNERS? | data-platform → `data-platform-devs` |
| **Stack / profile** | What constitution + layout + pin? | `flink`, `python-backend` |
| **Rules / foundation** | How to code / chassis | Follow **stack**, not domain |
| **Scaffold variant** | Which cookiecutter flavor? | `scaffold-*.yaml` — **not** a new profile |

**Laws**

1. Domain ≠ stack.  
2. **Identity equality** — one string everywhere (stack key == profile == pin).  
3. One team may own many stacks.  
4. New engine ⇒ new stack; same team allowed.  
5. Foundation variant ≠ new stack (unless rules/layout diverge).  
6. One stack per repo (multi-constitution monorepo = anti-pattern today).

```text
stack_key
  == governance.stack_profiles key
  == harness.profiles.{stack_key}
  == .harness-pin.yaml profile: / agent_skills.profile
  == prayog-skills/profiles/{stack_key}.yaml
  == owners.layout family (not a per-stack kit file)
```

Stack keys name the **technology profile**, not the domain/team.

---

## YAML is SSOT

The kit does **not** ship a built-in stack registry. Everything is declared in
your meta repo:

| File | What you declare |
|------|------------------|
| `governance-<org>.yaml` → `stack_profiles` | Stack names your programme uses |
| `governance-<org>.yaml` → `repos.*.stack` | Which stack each repo uses |
| `harness-<org>.yaml` → `profiles` | Constitution + skills + optional `owners` per stack |
| `scaffold-<org>.yaml` → `repos.*` | Cookiecutter source **only if** you scaffold |

**Brownfield:** omit or disable scaffold — run `apply-harness` only.  
**Greenfield:** add a scaffold block with `enabled: true`, `template`, `ref`, and `context`.

Adding a stack requires tenant harness/governance YAML + a prayog
`profiles/<stack_key>.yaml` at the skills pin. **No** new
`harness-pin.<stack>.yaml` or `CODEOWNERS.<stack>` in the kit.
A **new layout family** is needed only when the source/CODEOWNERS tree diverges.

---

## Catalog (first-class stacks)

| `stack_key` | Role | Constitution (pin target) | Foundation (scaffold; optional) | `owners.layout` | Default team |
|-------------|------|---------------------------|----------------------------------|-----------------|--------------|
| `meta-pm` | Programme meta | none | tenant-meta-foundation | `meta` | `pm-team` |
| `python-backend` | FastAPI / Python services | python-services-rules | python-fastapi-foundation | `app_src` | `backend-devs` |
| `nextjs-frontend` | Next.js BFF | nextjs-bff-rules | nextjs-bff-foundation | `app_nextjs` | `frontend-devs` |
| `terraform-iac` | Terraform IaC | terraform-infra-rules | terraform-*-foundation | `iac` | `platform-devs` |
| `flink` | Flink streaming monorepo | data-platform-rules | TBD (brownfield until built) | `flink` | `data-platform-devs` |
| `edge-agent` | Edge agent | edge-agent-rules | edge-agent-triton-foundation (also edge-triton-client under same stack — Law 5) | `app_src` | `edge-agent-devs` |
| `edge-inference-engine` | Edge inference engine | edge-inference-engine-rules | edge-pytorch-inference-foundation | `app_src` (+ optional `extra_paths`) | declare `owners.team` |
| `android-kotlin` | Android / Kotlin | android-kotlin-rules | android-kotlin-foundation | `android_kotlin` | `mobile-devs` |
| `ios-swift` | iOS / Swift | ios-swift-rules | ios-swift-foundation | `ios_swift` | `mobile-devs` |
| `platform-tooling` | Kit/SSOT brownfield | none | none | `none` | ignored |

**Deferred:** `embedded-c` / RTOS until lab rules exist — omit harness profile or use
`owners.layout: none`.

**Anti-pattern:** a dual iOS+Android monorepo with two constitutions under one
stack (e.g. drivestream `mobile-native`). Law 6 — split repos or pick one
constitution; do not enrol as a dual-mount harness profile.

Constitution **repo slug** may differ from stack key; ownership team is domain
(`data-platform-devs` owns `flink`; `mobile-devs` owns android/ios).

---

## When to add a stack

Add a stack **only if** at least one holds:

1. Different constitution (or none vs some)  
2. Different layout contract (`source_roots`, verify paths, CODEOWNERS tree)  
3. Different skill lane (meta vs app)  

**Do not** add for: team alone, language alone, cookiecutter flavor of same rules, tenant/product name.

---

## Adding a stack

1. Add to `stack_profiles` in `config/governance-<org>.yaml`.  
2. Add matching `profiles.<stack_key>` in `config/harness-<org>.yaml` with
   `owners.team` + `owners.layout` (required unless the stack is in the
   migration-defaults map).  
3. Ensure prayog ships `profiles/<stack_key>.yaml` at the pinned skills ref.  
4. If the source tree is new, contribute a `templates/codeowners/family.<layout>`
   upstream — otherwise reuse an existing family.  
5. Optional scaffold block in `scaffold-<org>.yaml`.

No Launchpad allowlist edit is required for new constitution repo slugs
(`apply-harness` rewrites `rules.repo` from harness `constitution`).

### Legacy remount (enrolled programmes)

Metas that still list `codeowners_template: CODEOWNERS.<stack>` keep working via
a shim that renders the mapped family and prints **WARN + fix instructions**.
Remove `*_template` keys when convenient; remount with the usual ritual:

```text
launchpad reset-harness --repo <name> --apply
launchpad apply-harness --repo <name> --apply
```

---

## Stack → Harness Resolution

When you run `apply-harness --repo <name>`:

1. Read `governance-<org>.yaml` for the repo's `stack`  
2. Check `harness-<org>.yaml` for a `repos.<name>` override  
3. Fall back to the stack name as the profile name  
4. If no profile found → hint and exit cleanly  

---

## Scaffold is independent of stack

Scaffold configuration in `scaffold-<org>.yaml` is fully independent.
`stack` drives harness only — not which cookiecutter template runs.
