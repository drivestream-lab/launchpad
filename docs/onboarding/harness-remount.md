# Harness remount (Breaking greenfield)

Use this when remounting consumers onto identity-equal stacks (Launchpad
**≥ 0.5.29** + prayog-skills tip tagged **`v0.5.0-rc.2`**).

## What to change in meta first

Edit `<slug>-meta/config/` **before** resetting clones:

1. Remove every `prayog_profile:` key (unsupported).  
2. Rename stack/profile `data-platform` → **`flink`** where used.  
3. Ensure Next harness profile is **`nextjs-frontend`** (not `frontend`).  
4. Add `flink` / `edge-agent` harness profile blocks when those repos exist.  
5. Align `stack_profiles` + teams (`data-platform-devs`, `edge-agent-devs`, …).  
6. Bump all `skills[].ref` to **`v0.5.0-rc.2`** (fetch retagged tip SHA).  
7. Commit meta config.

## Clear old harness materialization

Per app or meta clone:

```bash
launchpad reset-harness --repo <name> --dry-run
launchpad reset-harness --repo <name> --apply

# meta:
launchpad reset-harness --meta --apply
```

**Default clears:** `.harness/skills/`, runtime skill dirs (`.agents/skills/*`,
`.claude/skills/*`), `.harness-pin.yaml`, `.harness/profile.yaml`, managed
`AGENTS.md` harness block.

**Opt-in** (reseeds kit workflows on next apply):

```bash
launchpad reset-harness --repo <name> --apply --include-seeded-workflows
```

**Does not delete:** product code, full `.github/` beyond the allowlist,
submodule gitlinks (`.cursor/rules/`, `prayog-skills/`).

## Re-apply harness

```bash
launchpad apply-harness --repo <name> --apply
# or
launchpad apply-harness --meta --apply

launchpad apply-gates --repo <name> --apply   # if labels/roles need refresh
launchpad status --repo <name>
```

Commit: `.harness-pin.yaml`, `AGENTS.md`, `.github/CODEOWNERS`, `.gitmodules`,
and updated submodule SHAs.

Do **not** hand-edit skill hubs or pins and skip apply — reset + apply is the
remount path.
