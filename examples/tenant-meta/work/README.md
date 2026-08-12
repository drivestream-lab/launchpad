# Work / optional archive (`work/`)

**SSOT for WorkManifest is not Launchpad.** Canonical machine-readable intent lives in:

1. Plan **§9** inside `Implementation-Plan-{INIT}.md` (approved on the spec PR)
2. The pinned prayog contract: `prayog-skills/references/workmanifest-contract.md`
3. Example YAML on the pin: `prayog-skills/tests/fixtures/workmanifest/valid.yaml`

Identity: `apiVersion: prayog/v1` + `kind: WorkManifest` only. Do **not** use `launchpad/v1`.

Validate with the pin (not Launchpad kit CI):

```bash
python prayog-skills/scripts/workmanifest_contract.py <plan.md|manifest.yaml>
```

After spec merge, humans run forge **`/create-board-tickets`** (preflight + project). Launchpad only materializes that skill.

## Optional meta archive

A copy under `work/INIT-*.yaml` may exist for human audit. It is **not** a second
schema and must not drift from plan §9. Prefer plan §9 only. After board seed,
the programme board is the long-term WorkManifest home; plan / working papers may
be purged at **initiative closure** (prayog purge skills — not Launchpad).
