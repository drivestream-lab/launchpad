"""Tests for apply-gates legacy skip and status skills path."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from launchpad.commands.apply_gates import run_apply_gates
from launchpad.commands.status import _print_skills_drift
from launchpad.harness.paths import PRAYOG_SKILLS_SUBMODULE_REL
from launchpad.schema.harness import HarnessProfile


def _write_min_configs(config_dir: Path, *, delivery_contract: str = "") -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "programme.yaml").write_text(
        "apiVersion: launchpad/v1\nkind: Programme\n"
        "programme: Example\nprogramme_slug: example\norg: example-org\n"
        "meta_repo: example-meta\n"
        "forge:\n  provider: github\n",
        encoding="utf-8",
    )
    (config_dir / "governance-example-org.yaml").write_text(
        "apiVersion: launchpad/v1\nkind: GovernanceConfig\norg: example-org\n"
        "stack_profiles:\n  meta-pm: Meta\n"
        "teams:\n  - name: pe-team\n    description: PE\n    privacy: closed\n"
        "repos:\n  example-meta:\n    stack: meta-pm\n    teams: [pe-team]\n"
        "policy:\n  default_branch: main\n  integration_branch: develop\n"
        "  require_pr_reviews: 1\n  dismiss_stale_reviews: true\n"
        "project_board:\n  enabled: false\n",
        encoding="utf-8",
    )
    harness: dict = {
        "apiVersion": "launchpad/v1",
        "kind": "HarnessConfig",
        "org": "example-org",
        "profiles": {
            "meta-pm": {
                "skills": [{"repo": "prayog-skills", "ref": "v0.4.3"}],
            }
        },
    }
    if delivery_contract:
        harness["delivery_contract"] = delivery_contract
        harness["delivery_roles"] = {"engineering-gate": "pe-team"}
    (config_dir / "harness-example-org.yaml").write_text(
        yaml.safe_dump(harness),
        encoding="utf-8",
    )


def test_apply_gates_skips_when_delivery_contract_omitted(
    tmp_path: Path, capsys
) -> None:
    config_dir = tmp_path / "config"
    workspace = tmp_path / "ws"
    meta = workspace / "example-meta"
    meta.mkdir(parents=True)
    (meta / PRAYOG_SKILLS_SUBMODULE_REL).mkdir()
    _write_min_configs(config_dir, delivery_contract="")

    rc = run_apply_gates(
        meta=True,
        apply=False,
        config_dir=config_dir,
        workspace=workspace,
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "legacy Prayog pin" in out
    assert "gate apply skipped" in out


def test_apply_gates_requires_contract_file_when_declared(
    tmp_path: Path, capsys
) -> None:
    config_dir = tmp_path / "config"
    workspace = tmp_path / "ws"
    meta = workspace / "example-meta"
    prayog = meta / PRAYOG_SKILLS_SUBMODULE_REL
    prayog.mkdir(parents=True)
    _write_min_configs(config_dir, delivery_contract="sdd-delivery/v2")

    rc = run_apply_gates(
        meta=True,
        apply=False,
        config_dir=config_dir,
        workspace=workspace,
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "delivery-contract.yaml" in err


def test_print_skills_drift_uses_root_submodule(tmp_path: Path) -> None:
    profile = HarnessProfile(
        "meta-pm",
        {"skills": [{"repo": "prayog-skills", "ref": "v0.4.3"}]},
    )
    with patch(
        "launchpad.commands.status._print_submodule_drift",
        return_value=False,
    ) as mock_drift:
        drift = _print_skills_drift(profile, tmp_path)
    assert drift is False
    mock_drift.assert_called_once()
    assert mock_drift.call_args.kwargs["submodule_rel"] == PRAYOG_SKILLS_SUBMODULE_REL
