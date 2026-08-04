# Stacks Reference

A **stack** is a named technology profile. It drives **harness** (constitution +
prayog profile + pin/CODEOWNERS). Scaffold is separate — opt-in per repo in
`scaffold-<org>.yaml`.

## First principles

| Layer | Answers | Examples |
|-------|---------|----------|
| **Domain / team** | Who owns merge + CODEOWNERS? | data-platform → `data-platform-devs` |
| **Stack / profile** | What constitution + layout + pin? | `flink`, `python-backend` |
| **Rules / foundation** | How to code / chassis | Follow **stack**, not domain |
| **Scaffold variant** | Which cookiecutter flavor? | `scaffold-*.yaml` — **not** a new profile |

**Laws**

1. Domain ≠ stack.  
2. **Identity equality** — one string everywhere (no `prayog_profile` aliases).  
3. One team may own many stacks.  
4. New engine ⇒ new stack; same team allowed.  
5. Foundation variant ≠ new stack (unless rules/layout diverge).  
6. One stack per repo (multi-constitution monorepo = future).

```text
stack_key
  == governance.stack_profiles key
  == harness.profiles.{stack_key}
  == .harness-pin.yaml profile: / agent_skills.profile
  == prayog-skills/profiles/{stack_key}.yaml
  == templates/harness-pin.{stack_key}.yaml
  == templates/CODEOWNERS.{stack_key}
```

**Forbidden as stack keys:** `data-platform`, `frontend`, umbrella “analytics”.

---

## YAML is SSOT

The kit does **not** ship a built-in stack registry. Everything is declared in
your meta repo:

| File | What you declare |
|------|------------------|
| `governance-<org>.yaml` → `stack_profiles` | Stack names your programme uses |
| `governance-<org>.yaml` → `repos.*.stack` | Which stack each repo uses |
| `harness-<org>.yaml` → `profiles` | Constitution + skills per stack |
| `scaffold-<org>.yaml` → `repos.*` | Cookiecutter source **only if** you scaffold |

**Brownfield:** omit or disable scaffold — run `apply-harness` only.  
**Greenfield:** add a scaffold block with `enabled: true`, `template`, `ref`, and `context`.

---

## Catalog (first-class stacks)

| `stack_key` | Role | Constitution (pin target) | Foundation (scaffold; optional) |
|-------------|------|---------------------------|----------------------------------|
| `meta-pm` | Programme meta | none | tenant-meta-foundation |
| `python-backend` | FastAPI / Python services | python-services-rules | python-fastapi-foundation |
| `nextjs-frontend` | Next.js BFF | nextjs-bff-rules | nextjs-bff-foundation |
| `terraform-iac` | Terraform IaC | terraform-infra-rules | terraform-*-foundation |
| `flink` | Flink streaming monorepo | current Flink rules repo slug* | TBD (brownfield until built) |
| `edge-agent` | Edge agent | edge-agent-rules | edge-agent-triton-foundation |
| `platform-tooling` | Kit/SSOT brownfield | none | none |

\*Until a rules-rename workstream lands, Flink pins may still reference today’s
constitution repo name (e.g. `data-platform-rules`); **Launchpad stack key is
`flink`**. Team ownership is `data-platform-devs` (domain), not a stack named
`data-platform`.

**Add later:** `spark`, `edge-triton-client`, …

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
2. Add matching `profiles.<stack_key>` in `config/harness-<org>.yaml`.  
3. Ensure prayog ships `profiles/<stack_key>.yaml` at the pinned skills ref.  
4. Kit templates `harness-pin.<stack_key>.yaml` + `CODEOWNERS.<stack_key>` (or contribute upstream).  
5. Optional scaffold block in `scaffold-<org>.yaml`.

No Launchpad allowlist edit is required for new constitution repo slugs
(`apply-harness` rewrites `rules.repo` from harness `constitution`).

---

## Stack → Harness Resolution

When you run `apply-harness --repo <name>`:

1. Read `governance-<org>.yaml` for the repo's `stack`  
2. Check `harness-<org>.yaml` for a `repos.<name>` override  
3. Fall back to the stack name as the profile name  
4. If no profile found → hint and exit cleanly  

---

## Remount (Breaking greenfield)

See [harness-pins.md](../playbook/harness/harness-pins.md#remount-clean-local-materialization)
and [harness-remount.md](onboarding/harness-remount.md).

```text
1. Fix meta YAML (identity equality; bump skills[].ref to v0.5.0-rc.2 tip)
2. launchpad reset-harness --repo|--meta --apply
3. launchpad apply-harness --repo|--meta --apply
4. Commit pin, AGENTS, CODEOWNERS, submodule SHAs
```

---

## Scaffold is independent of stack

Scaffold configuration in `scaffold-<org>.yaml` is fully independent.
`stack` drives harness only — not which cookiecutter template runs.
