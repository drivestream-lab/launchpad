# Exit criteria — platform bootstrap

Use when closing the **first factory bootstrap** epic for a new tenant (repos, teams, gitflow, board, wiki).

---

## Factory (`<client>-meta`)

- [ ] `launchpad status --meta` — all checks green
- [ ] Engineering project board live with custom fields
- [ ] Bootstrap work manifest seeded (if used)
- [ ] Wiki published from `wiki/` (optional)
- [ ] Teams populated: `pm-team`, `backend-devs`, `release-managers`, …

---

## Pilot app harness (`example-api` or first app repo)

- [ ] `launchpad apply-harness --repo <name> --apply` merged
- [ ] `launchpad status --repo <name>` passes
- [ ] Rules submodule + prayog-skills pin documented in harness config
- [ ] `/pre-implement` and Pass-1/closeout audition pass — [skills audition](../../playbook/harness/skills-audition.md)

---

## Not required for bootstrap exit

- Every app repo on the board
- First product PRD / product INIT
- Full CI gate on `main` (enable workflow required checks after policy workflow PRs land)

---

## Related

- [bootstrap-prerequisites.md](bootstrap-prerequisites.md)
- [tenant-meta.md](tenant-meta.md)
- [docs/README.md](../README.md)
