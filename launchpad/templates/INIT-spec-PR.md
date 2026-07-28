# Spec PR (INIT template)

| Artifact | Location |
|----------|----------|
| **Meta PRD** | `<client>-meta/prd/INIT-<id>.md` |
| **Board** | Engineering board — Initiative = `INIT-<id>`, Codebase = `<repo>` |
| **App spec** | `<app>/docs/specification/product/INIT-<id>.md` |

## Opening the spec PR

1. Run `/spec-draft` locally — review the spec slice.
2. Authorize the agent to open a **Draft** spec PR on
   `chore/INIT-<id>-spec-<repo>` targeting `develop`.
3. Initial label: **`spec-pending`** (`launchpad apply-gates --repo <name> --apply`).
4. Stack feasibility, TDD, ADRs, and plan on the **same** Draft PR.
5. PE sets **`spec-lgtm`** + Approve + attestation only when the full package
   is on head — then Ready for review → merge → `/create-board-tickets`.

See `playbook/ship/delivery-workflow.md` and pinned `workflow.yaml`.
