# Multi-laptop setup

Install launchpad once per machine. Pick `<tag>` from [CHANGELOG.md](../../CHANGELOG.md) or [GitHub Releases](https://github.com/drivestream-lab/launchpad/releases).

---

## Install

**Tenant operators and engineers** — install a **released tag**:

```bash
pipx install "launchpad @ git+https://github.com/drivestream-lab/launchpad@<tag>"
launchpad --version
```

Match the tag in your tenant `<slug>-meta/.launchpad-version`.

**Upgrade:**

```bash
pipx install --force "launchpad @ git+https://github.com/drivestream-lab/launchpad@<tag>"
launchpad --client <slug> doctor    # operators only (needs PAT)
```

**Kit contributors** — see [contributing/local-dev.md](../contributing/local-dev.md).

---

## Client registry

One-time setup under `~/.config/launchpad/`:

```text
~/.config/launchpad/
├── clients.yaml          # programme registry
└── env.d/
    └── example.env       # GITHUB_TOKEN — operators / PM only
```

The `id` must match `programme_slug` in `config/programme.yaml`.

### Manual `clients.yaml`

```yaml
# ~/.config/launchpad/clients.yaml
clients:
  - id: example
    path: ~/Workspace/example/example-meta
    workspace: ~/Workspace/example    # optional; defaults to parent of path
    forge: github
```

With `--client <id>`, factory commands resolve sibling repo clones from this
`workspace` (cwd-independent). You do not need to `cd` to the workspace root
before `reset-harness` / `apply-harness` / `status`.

### Service-mode `status` (VM / headless — no `~/.config/launchpad`)

Orchestrators (e.g. Gateflow) that already own synced meta + clones + a programme
PAT must **not** synthesize `clients.yaml` / `env.d` on the VM.

```bash
# Child process only — never put the PAT on argv
export GITHUB_TOKEN="<programme-pat-from-db>"

launchpad status \
  --no-client \
  --repo example-api \
  --config-dir /var/gateflow/workspaces/org/example-meta/config \
  --workspace /var/gateflow/workspaces/org
```

| Flag / env | Meaning |
|------------|---------|
| `--no-client` | Skip `clients.yaml` and `env.d`; ignore leftover `LAUNCHPAD_CLIENT` |
| `--config-dir` | Synced meta `config/` (required with `--no-client`) |
| `--workspace` | Parent of `<repo>` (same as `clients.yaml` workspace) |
| `GITHUB_TOKEN` / `GH_TOKEN` | Programme PAT for this process only — **not** overridden by `env.d` |

Operator path is unchanged: `launchpad --client <id> status --repo …` still uses
the registry and `env.d` (file wins over ambient token on laptops).

`--config-dir` alone (without `--no-client`) still requires an active client and
does **not** override workspace/secrets — use service-mode flags on a VM.

### Secrets file (operators / PM only)

Engineers do **not** need `env.d` — see [engineer-setup.md](engineer-setup.md).

```bash
mkdir -p ~/.config/launchpad/env.d
cat > ~/.config/launchpad/env.d/example.env << 'EOF'
# example factory secrets — chmod 600
GITHUB_TOKEN=github_pat_REPLACE_ME
EOF
chmod 600 ~/.config/launchpad/env.d/example.env
```

**Secrets SSOT:** `~/.config/launchpad/env.d/<slug>.env` — never commit.
When you run `launchpad --client <slug> …`, values in that file **override** any
ambient `GITHUB_TOKEN` / `GH_TOKEN` in the shell. Each operator uses their own
PAT in their own `env.d` file — do not share tokens. `gh auth` / `hosts.yml` is
separate and is **not** read by launchpad.

---

## Run from anywhere

```bash
launchpad clients
launchpad --client example status --meta    # or --repo <name>
```

Or set a shell default:

```bash
export LAUNCHPAD_CLIENT=example
launchpad status --repo example-api
```

---

## Resolution order

Launchpad picks the tenant config directory in this order:

1. `--client` / `LAUNCHPAD_CLIENT` → lookup in `clients.yaml` → `<path>/config`
2. `default:` in `clients.yaml`
3. Sole client in `clients.yaml`

Workspace for sibling clones:

1. `clients[].workspace` if set
2. Else parent of `clients[].path`
3. With `--config-dir` only (scripts/tests): parent of the meta repo (`config_dir/../..`)

Secrets load automatically from `env.d/<id>.env` when a client is active.

---

## Role setup

| Role | Doc |
|------|-----|
| PM joining existing programme | [pm-setup.md](pm-setup.md) |
| Engineer joining existing programme | [engineer-setup.md](engineer-setup.md) |
| New programme (platform operator) | [tenant-meta onboarding](../onboarding/tenant-meta.md) |

---

## Version pin

Tenant `<slug>-meta/.launchpad-version` should match the installed tag:

```bash
cat ~/Workspace/example/example-meta/.launchpad-version
launchpad --version
```

Re-run idempotent factory commands only when [CHANGELOG.md](../../CHANGELOG.md) says so.
