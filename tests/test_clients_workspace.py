"""Tests for clients.yaml workspace resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from launchpad import clients as clients_mod
from launchpad.clients import (
    ClientRegistryError,
    resolve_programme_workspace,
    resolve_workspace,
    workspace_from_config_dir,
)
from launchpad.schema import SchemaError
from launchpad.schema.programme import ProgrammeSchema


def test_workspace_from_config_dir(tmp_path: Path) -> None:
    meta = tmp_path / "example-meta"
    config = meta / "config"
    config.mkdir(parents=True)
    assert workspace_from_config_dir(config) == tmp_path


def test_resolve_workspace_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    meta = tmp_path / "mobbot-meta"
    meta.mkdir()
    ws = tmp_path
    clients_file = tmp_path / "clients.yaml"
    clients_file.write_text(
        yaml.safe_dump(
            {
                "clients": [
                    {
                        "id": "mobbot",
                        "path": str(meta),
                        "workspace": str(ws),
                        "forge": "github",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", clients_file)
    assert resolve_workspace("mobbot") == ws.resolve()


def test_resolve_workspace_defaults_to_path_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    meta = tmp_path / "mobbot-meta"
    meta.mkdir()
    clients_file = tmp_path / "clients.yaml"
    clients_file.write_text(
        yaml.safe_dump(
            {
                "clients": [
                    {"id": "mobbot", "path": str(meta), "forge": "github"}
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", clients_file)
    assert resolve_workspace("mobbot") == tmp_path.resolve()


def test_resolve_programme_workspace_override(tmp_path: Path) -> None:
    assert resolve_programme_workspace(override=tmp_path) == tmp_path.resolve()


def test_resolve_programme_workspace_blank_override_uses_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty-string override must not resolve to cwd (reset-harness trap)."""
    meta = tmp_path / "example-meta"
    meta.mkdir()
    ws = tmp_path / "programme-ws"
    ws.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    clients_file = tmp_path / "clients.yaml"
    clients_file.write_text(
        yaml.safe_dump(
            {
                "clients": [
                    {
                        "id": "example",
                        "path": str(meta),
                        "workspace": str(ws),
                        "forge": "github",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(clients_mod, "CLIENTS_FILE", clients_file)
    monkeypatch.chdir(elsewhere)
    assert resolve_programme_workspace(client_id="example", override="") == ws.resolve()
    assert resolve_programme_workspace(client_id="example", override=None) == ws.resolve()


def test_resolve_programme_workspace_from_config_dir(tmp_path: Path) -> None:
    meta = tmp_path / "kola-meta"
    config = meta / "config"
    config.mkdir(parents=True)
    assert resolve_programme_workspace(config_dir=config) == tmp_path.resolve()


def test_resolve_programme_workspace_missing_raises() -> None:
    with pytest.raises(ClientRegistryError, match="cannot resolve workspace"):
        resolve_programme_workspace()


def test_programme_rejects_workspace_field() -> None:
    with pytest.raises(SchemaError, match="must not contain 'workspace'"):
        ProgrammeSchema(
            {
                "programme": "MOBBOT",
                "org": "autrio10x",
                "workspace": "~/Workspace/handson/botmob",
            }
        )
