"""Service-mode apply-harness: --no-client + caller config/workspace/token."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from launchpad import clients as clients_mod
from launchpad.cli import main


def _write_minimal_meta(config: Path, *, org: str = "example-org", meta: str = "example-meta") -> None:
    config.mkdir(parents=True, exist_ok=True)
    (config / "programme.yaml").write_text(
        "\n".join(
            [
                "apiVersion: launchpad/v1",
                "kind: Programme",
                "programme: EXAMPLE",
                "programme_slug: example",
                f"org: {org}",
                f"meta_repo: {meta}",
                "forge:",
                "  provider: github",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (config / f"governance-{org}.yaml").write_text(
        "\n".join(
            [
                "apiVersion: launchpad/v1",
                "kind: GovernanceConfig",
                f"org: {org}",
                "stack_profiles:",
                "  python-backend: Python",
                "teams:",
                "  - name: backend-devs",
                "    description: Backend",
                "    privacy: closed",
                "repos:",
                "  example-api:",
                "    description: api",
                "    stack: python-backend",
                "    teams: [backend-devs]",
                "    visibility: private",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (config / f"harness-{org}.yaml").write_text(
        "\n".join(
            [
                "apiVersion: launchpad/v1",
                "kind: HarnessConfig",
                f"org: {org}",
                "profiles:",
                "  python-backend:",
                "    skills:",
                "      - repo: prayog-skills",
                "        ref: dummy",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_apply_harness_no_client_requires_config_dir(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["apply-harness", "--no-client", "--repo", "example-api", "--apply"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--no-client requires --config-dir" in err


def test_apply_harness_no_client_incompatible_with_client_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "meta" / "config"
    _write_minimal_meta(config)
    rc = main(
        [
            "--client",
            "example",
            "apply-harness",
            "--no-client",
            "--config-dir",
            str(config),
            "--repo",
            "example-api",
            "--apply",
        ]
    )
    assert rc == 1
    assert "incompatible with --client" in capsys.readouterr().err


def test_apply_harness_no_client_uses_caller_workspace_not_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Leftover clients.yaml must not steer clone path when --no-client."""
    operator_ws = tmp_path / "operator-ws"
    service_ws = tmp_path / "service-ws"
    meta = service_ws / "example-meta"
    config = meta / "config"
    _write_minimal_meta(config)

    wrong_clone = operator_ws / "example-api"
    wrong_clone.mkdir(parents=True)
    (wrong_clone / ".git").mkdir()

    op_meta = operator_ws / "example-meta"
    op_meta.mkdir(parents=True)
    clients_file = tmp_path / "clients.yaml"
    clients_file.write_text(
        yaml.safe_dump(
            {
                "default": "example",
                "clients": [
                    {
                        "id": "example",
                        "path": str(op_meta),
                        "workspace": str(operator_ws),
                        "forge": "github",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    env_d = tmp_path / "env.d"
    env_d.mkdir()
    (env_d / "example.env").write_text(
        "GITHUB_TOKEN=github_pat_FROM_ENV_D\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", clients_file)
    monkeypatch.setattr(clients_mod, "ENV_D_DIR", env_d)
    monkeypatch.setenv("LAUNCHPAD_CLIENT", "example")
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_FROM_GATEFLOW")

    rc = main(
        [
            "apply-harness",
            "--no-client",
            "--config-dir",
            str(config),
            "--workspace",
            str(service_ws),
            "--repo",
            "example-api",
            "--apply",
        ]
    )
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert str(service_ws / "example-api") in combined
    assert str(wrong_clone) not in combined
    assert os.environ["GITHUB_TOKEN"] == "github_pat_FROM_GATEFLOW"
    assert "LAUNCHPAD_CLIENT" not in os.environ
    assert rc == 1


def test_apply_harness_no_client_skips_env_d_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service_ws = tmp_path / "ws"
    meta = service_ws / "example-meta"
    config = meta / "config"
    _write_minimal_meta(config)

    env_d = tmp_path / "env.d"
    env_d.mkdir()
    (env_d / "example.env").write_text(
        "GITHUB_TOKEN=github_pat_FROM_ENV_D\n",
        encoding="utf-8",
    )
    clients_file = tmp_path / "clients.yaml"
    clients_file.write_text(
        yaml.safe_dump(
            {
                "clients": [
                    {
                        "id": "example",
                        "path": str(meta),
                        "workspace": str(service_ws),
                        "forge": "github",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", clients_file)
    monkeypatch.setattr(clients_mod, "ENV_D_DIR", env_d)
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_CALLER")

    main(
        [
            "apply-harness",
            "--no-client",
            "--config-dir",
            str(config),
            "--workspace",
            str(service_ws),
            "--repo",
            "example-api",
            "--apply",
        ]
    )
    assert os.environ["GITHUB_TOKEN"] == "github_pat_CALLER"


def test_apply_harness_format_json_missing_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    service_ws = tmp_path / "ws"
    meta = service_ws / "example-meta"
    config = meta / "config"
    _write_minimal_meta(config)

    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", tmp_path / "missing-clients.yaml")
    monkeypatch.setattr(clients_mod, "ENV_D_DIR", tmp_path / "no-env-d")
    monkeypatch.delenv("LAUNCHPAD_CLIENT", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_CALLER")

    rc = main(
        [
            "apply-harness",
            "--no-client",
            "--config-dir",
            str(config),
            "--workspace",
            str(service_ws),
            "--repo",
            "example-api",
            "--apply",
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == 1
    assert payload["ok"] is False
    assert payload["command"] == "apply-harness"
    assert payload["repo"] == "example-api"
    assert payload["exit"] == 1
    assert "local clone not found" in (payload["error"] or "")
    assert "apply-harness" not in captured.out.split("{", 1)[0]
    assert "WARN" in captured.err or "clone not found" in captured.err


def test_apply_harness_human_stdout_unchanged_without_format_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    service_ws = tmp_path / "ws"
    meta = service_ws / "example-meta"
    config = meta / "config"
    _write_minimal_meta(config)

    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", tmp_path / "missing-clients.yaml")
    monkeypatch.setattr(clients_mod, "ENV_D_DIR", tmp_path / "no-env-d")
    monkeypatch.delenv("LAUNCHPAD_CLIENT", raising=False)

    rc = main(
        [
            "apply-harness",
            "--no-client",
            "--config-dir",
            str(config),
            "--workspace",
            str(service_ws),
            "--repo",
            "example-api",
            "--apply",
        ]
    )
    out = capsys.readouterr().out
    assert "apply-harness" in out
    assert "WARN" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    assert rc == 1
