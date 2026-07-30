# Publication checklist

Before pushing public changes to `launchpad`:

- [ ] No `.env` or real tokens in git
- [ ] No client PRDs, planning archives, or live work manifests
- [ ] No private org names in examples (`example-org` only)
- [ ] Harness examples reference public `drivestream-lab/*-rules` (not tenant-specific placeholders)
- [ ] No private repo lists — only `example-api`, `example-platform`, etc.
- [ ] `examples/tenant-meta/config/` uses 5-YAML model
- [ ] `examples/tenant-meta/` contains structure only (no `launchpad/v1` WorkManifest YAML)
- [ ] README states tenant vs kit separation
- [ ] [CHANGELOG.md](../CHANGELOG.md) updated for releases
- [ ] `launchpad --version` and `launchpad --help` work after `pip install .`
- [ ] `pytest` passes (no network required for schema tests)
- [ ] Example config validates against `examples/tenant-meta/config/`
- [ ] `scripts/smoke-local.sh` exits 0 (dry-run only, no PAT required)
- [ ] CI (`ci.yml`) passes on `main` and `develop`
- [ ] No GitLab-specific commands in public CLI (`launchpad --help` output)
- [ ] `.launchpad-version` in `examples/tenant-meta/` matches `pyproject.toml` version
