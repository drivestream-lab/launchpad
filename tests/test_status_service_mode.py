"""Service-mode status: --no-client + caller config/workspace/token."""

from __future__ import annotations

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


def test_status_no_client_requires_config_dir(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["status", "--no-client", "--repo", "example-api"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--no-client requires --config-dir" in err


def test_status_no_client_incompatible_with_client_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "meta" / "config"
    _write_minimal_meta(config)
    rc = main(
        [
            "--client",
            "example",
            "status",
            "--no-client",
            "--config-dir",
            str(config),
            "--repo",
            "example-api",
        ]
    )
    assert rc == 1
    assert "incompatible with --client" in capsys.readouterr().err


def test_status_no_client_uses_caller_workspace_not_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Leftover clients.yaml must not steer clone path when --no-client."""
    operator_ws = tmp_path / "operator-ws"
    service_ws = tmp_path / "service-ws"
    meta = service_ws / "example-meta"
    config = meta / "config"
    _write_minimal_meta(config)

    # Wrong place (what a leftover laptop registry would point at)
    wrong_clone = operator_ws / "example-api"
    wrong_clone.mkdir(parents=True)
    (wrong_clone / ".git").mkdir()

    # Correct Gateflow clone
    good_clone = service_ws / "example-api"
    good_clone.mkdir(parents=True)
    (good_clone / ".git").mkdir()
    (good_clone / ".harness-pin.yaml").write_text("profile: python-backend\n", encoding="utf-8")

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
            "status",
            "--no-client",
            "--config-dir",
            str(config),
            "--workspace",
            str(service_ws),
            "--repo",
            "example-api",
        ]
    )
    # May be 0 or 1 depending on harness completeness — assert path + token.
    out = capsys.readouterr().out
    assert str(good_clone) in out
    assert str(wrong_clone) not in out
    assert os.environ["GITHUB_TOKEN"] == "github_pat_FROM_GATEFLOW"
    assert "LAUNCHPAD_CLIENT" not in os.environ
    assert rc in (0, 1)


def test_status_no_client_skips_env_d_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service_ws = tmp_path / "ws"
    meta = service_ws / "example-meta"
    config = meta / "config"
    _write_minimal_meta(config)
    clone = service_ws / "example-api"
    clone.mkdir(parents=True)
    (clone / ".git").mkdir()

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
            "status",
            "--no-client",
            "--config-dir",
            str(config),
            "--workspace",
            str(service_ws),
            "--repo",
            "example-api",
        ]
    )
    assert os.environ["GITHUB_TOKEN"] == "github_pat_CALLER"


def test_status_clean_vm_no_clients_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No ~/.config/launchpad at all — service mode still runs."""
    service_ws = tmp_path / "ws"
    meta = service_ws / "example-meta"
    config = meta / "config"
    _write_minimal_meta(config)
    clone = service_ws / "example-api"
    clone.mkdir(parents=True)
    (clone / ".git").mkdir()

    missing = tmp_path / "missing-clients.yaml"
    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", missing)
    monkeypatch.setattr(clients_mod, "ENV_D_DIR", tmp_path / "no-env-d")
    monkeypatch.delenv("LAUNCHPAD_CLIENT", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_CALLER")

    rc = main(
        [
            "status",
            "--no-client",
            "--config-dir",
            str(config),
            "--workspace",
            str(service_ws),
            "--repo",
            "example-api",
        ]
    )
    out = capsys.readouterr().out
    assert str(clone) in out
    assert "Governance declared" in out
    assert rc in (0, 1)
