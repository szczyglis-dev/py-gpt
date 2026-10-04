#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.10.01 15:45:00                  #
# ================================================== #

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import pygpt_net.core.extensions.extensions as extensions_module
from pygpt_net.core.extensions import ExtensionManifestError, Extensions
from pygpt_net.core.extensions.integrity import compute_addon_sha256, write_manifest_sha256


class _Config:
    def __init__(self, root: Path):
        self.root = root
        self.values = {}

    def get_base_workdir(self):
        return str(self.root)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def save(self):
        pass


@pytest.fixture
def manager(tmp_path, monkeypatch):
    config = _Config(tmp_path / "workdir")
    packages = SimpleNamespace(ensure_dependencies=MagicMock())
    window = SimpleNamespace(core=SimpleNamespace(config=config, packages=packages))
    result = Extensions(window)
    result._test_warnings = []
    monkeypatch.setattr(result, "_warn", result._test_warnings.append)
    return result


def _manifest(**updates):
    data = {
        "manifest_version": 1,
        "id": "sha_test",
        "name": "SHA Test",
        "description": "SHA integrity test",
        "version": "1.0.0",
        "min_app_version": "1.0.0",
        "author": "PyGPT Tests",
        "contact": "tests@example.org",
        "type": "plugin",
        "entrypoint": "plugin.py:Plugin",
        "external_dependencies": [],
    }
    data.update(updates)
    return data


def _source(tmp_path: Path, **manifest_updates) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / "plugin.py").write_text("class Plugin:\n    pass\n", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps(_manifest(**manifest_updates), indent=2),
        encoding="utf-8",
    )
    return root


def _registry_entry(**updates):
    entry = {
        "id": "sha_test",
        "name": "SHA Test",
        "description": "SHA integrity test",
        "author": "PyGPT Tests",
        "version": "1.0.0",
        "type": "plugin",
        "github_url": "https://github.com/example/sha-test",
        "trusted": False,
    }
    entry.update(updates)
    return entry


def test_manifest_sha256_is_validated_and_normalized(manager):
    digest = "AB" * 32
    normalized = manager.validate_manifest(_manifest(sha256=digest))
    assert normalized["sha256"] == digest.lower()

    with pytest.raises(ExtensionManifestError, match="Invalid manifest sha256"):
        manager.validate_manifest(_manifest(sha256="broken"))
    with pytest.raises(ExtensionManifestError, match="Missing manifest sha256"):
        manager.validate_manifest(_manifest(sha256=""))


def test_untrusted_package_without_any_sha_remains_installable(manager, tmp_path):
    source = _source(tmp_path)
    assert manager._verify_package_integrity(str(source), manager.read_manifest(str(source))) == ""


def test_trusted_package_requires_registry_sha_before_hashing(manager, tmp_path, monkeypatch):
    source = _source(tmp_path)
    manifest = manager.read_manifest(str(source))
    compute = MagicMock()
    monkeypatch.setattr(manager, "compute_sha256", compute)

    with pytest.raises(ExtensionManifestError, match="Missing registry sha256"):
        manager._verify_package_integrity(str(source), manifest, trusted=True)
    compute.assert_not_called()


def test_trusted_package_requires_manifest_sha_before_hashing(manager, tmp_path, monkeypatch):
    source = _source(tmp_path)
    manifest = manager.read_manifest(str(source))
    compute = MagicMock()
    monkeypatch.setattr(manager, "compute_sha256", compute)

    with pytest.raises(ExtensionManifestError, match="Missing manifest sha256"):
        manager._verify_package_integrity(
            str(source), manifest, expected_sha256="a" * 64, trusted=True,
        )
    compute.assert_not_called()


def test_registry_and_manifest_digest_must_match_before_hashing(manager, tmp_path, monkeypatch):
    source = _source(tmp_path, sha256="a" * 64)
    manifest = manager.read_manifest(str(source))
    compute = MagicMock()
    monkeypatch.setattr(manager, "compute_sha256", compute)

    with pytest.raises(ExtensionManifestError, match="registry and manifest declare different digests"):
        manager._verify_package_integrity(
            str(source), manifest, expected_sha256="b" * 64, trusted=True,
        )
    compute.assert_not_called()


def test_manifest_only_pin_is_verified_for_untrusted_package(manager, tmp_path):
    source = _source(tmp_path)
    digest = write_manifest_sha256(str(source))
    manifest = manager.read_manifest(str(source))
    assert manager._verify_package_integrity(str(source), manifest) == digest

    (source / "plugin.py").write_text("class Plugin:\n    tampered = True\n", encoding="utf-8")
    with pytest.raises(ExtensionManifestError, match="manifest expects"):
        manager._verify_package_integrity(str(source), manifest)


def test_registry_only_pin_is_verified_for_untrusted_package(manager, tmp_path):
    source = _source(tmp_path)
    manifest = manager.read_manifest(str(source))
    digest = compute_addon_sha256(str(source))
    assert manager._verify_package_integrity(
        str(source), manifest, expected_sha256=digest, trusted=False,
    ) == digest

    (source / "plugin.py").write_text("changed\n", encoding="utf-8")
    with pytest.raises(ExtensionManifestError, match="registry expects"):
        manager._verify_package_integrity(
            str(source), manifest, expected_sha256=digest, trusted=False,
        )


def test_valid_trusted_package_requires_three_way_match(manager, tmp_path):
    source = _source(tmp_path)
    digest = write_manifest_sha256(str(source))
    manifest = manager.read_manifest(str(source))
    assert manager._verify_package_integrity(
        str(source), manifest, expected_sha256=digest.upper(), trusted=True,
    ) == digest


def test_tampered_trusted_package_fails_before_dependency_install(manager, tmp_path):
    source = _source(tmp_path, external_dependencies=["demo>=1"])
    digest = write_manifest_sha256(str(source))
    (source / "plugin.py").write_text("class Plugin:\n    malicious = True\n", encoding="utf-8")

    with pytest.raises(ExtensionManifestError, match="verification failed"):
        manager.import_directory(
            str(source), trusted=True, official=True, expected_sha256=digest,
        )
    manager.window.core.packages.ensure_dependencies.assert_not_called()
    assert not Path(manager.get_extension_dir("plugin", "sha_test", create_parent=False)).exists()


def test_dependencies_run_only_after_successful_trusted_verification(manager, tmp_path):
    source = _source(tmp_path, external_dependencies=["demo>=1"])
    digest = write_manifest_sha256(str(source))

    installed = manager.import_directory(
        str(source), trusted=True, official=True, expected_sha256=digest,
    )

    assert installed["_registry_sha256"] == digest
    assert installed["trusted"] is True
    manager.window.core.packages.ensure_dependencies.assert_called_once_with(["demo>=1"])


def test_post_copy_integrity_check_detects_copy_time_tampering(manager, tmp_path, monkeypatch):
    source = _source(tmp_path)
    digest = write_manifest_sha256(str(source))
    real_copytree = extensions_module.shutil.copytree

    def tampering_copytree(src, dst, *args, **kwargs):
        result = real_copytree(src, dst, *args, **kwargs)
        Path(dst, "plugin.py").write_text("class Plugin:\n    tampered_after_verify = True\n", encoding="utf-8")
        return result

    monkeypatch.setattr(extensions_module.shutil, "copytree", tampering_copytree)

    with pytest.raises(ExtensionManifestError, match="verification failed"):
        manager.import_directory(
            str(source), trusted=True, official=True, expected_sha256=digest,
        )

    destination = Path(manager.get_extension_dir("plugin", "sha_test", create_parent=False))
    assert not destination.exists()
    assert manager._load_registry().get("items", {}).get("sha_test") is None


def test_successful_install_persists_verified_digest_in_local_registry(manager, tmp_path):
    source = _source(tmp_path)
    digest = write_manifest_sha256(str(source))
    manager.import_directory(
        str(source), trusted=True, official=True, expected_sha256=digest,
    )

    meta = manager._load_registry()["items"]["sha_test"]
    assert meta["sha256"] == digest
    assert meta["trusted"] is True
    assert meta["official"] is True


def test_install_registry_entry_rejects_missing_or_invalid_trusted_sha(manager, monkeypatch):
    import_github = MagicMock()
    monkeypatch.setattr(manager, "import_github", import_github)

    with pytest.raises(ExtensionManifestError, match="Missing registry sha256"):
        manager.install_registry_entry(_registry_entry(trusted=True))
    with pytest.raises(ExtensionManifestError, match="Invalid registry sha256"):
        manager.install_registry_entry(_registry_entry(trusted=True, sha256="bad"))
    import_github.assert_not_called()


def test_install_registry_entry_passes_normalized_sha_to_github_import(manager, monkeypatch):
    digest = "AB" * 32
    import_github = MagicMock(return_value={"id": "sha_test", "type": "plugin"})
    monkeypatch.setattr(manager, "import_github", import_github)

    manager.install_registry_entry(_registry_entry(trusted=True, sha256=digest))

    kwargs = import_github.call_args.kwargs
    assert kwargs["trusted"] is True
    assert kwargs["expected_sha256"] == digest.lower()


def test_official_registry_requires_sha_for_every_published_entry(manager, monkeypatch):
    valid = "1" * 64
    data = {
        "addons": [
            _registry_entry(id="missing", name="missing", trusted=False),
            _registry_entry(id="invalid", name="invalid", trusted=False, sha256="bad"),
            _registry_entry(id="valid", trusted=False, sha256=valid.upper()),
            _registry_entry(id="trusted", trusted=True, sha256="2" * 64),
        ]
    }
    monkeypatch.setattr(manager, "_download_bytes", lambda *args: json.dumps(data).encode("utf-8"))

    result = manager.fetch_registry(manager.DEFAULT_REGISTRY_URL)

    assert [item["id"] for item in result] == ["valid", "trusted"]
    assert result[0]["sha256"] == valid
    assert result[0]["trusted"] is False
    assert result[1]["trusted"] is True
    assert any("missing" in warning and "Missing registry sha256" in warning for warning in manager._test_warnings)
    assert any("invalid" in warning and "Invalid registry sha256" in warning for warning in manager._test_warnings)


def test_custom_registry_does_not_gain_trust_and_sha_is_optional(manager, monkeypatch):
    data = {
        "addons": [
            _registry_entry(id="plain", trusted=True, official=True),
            _registry_entry(id="pinned", trusted=True, official=True, sha256="A" * 64),
            _registry_entry(id="broken", name="broken", trusted=False, sha256="bad"),
        ]
    }
    monkeypatch.setattr(manager, "_download_bytes", lambda *args: json.dumps(data).encode("utf-8"))

    result = manager.fetch_registry("https://example.org/addons.json")

    assert [item["id"] for item in result] == ["plain", "pinned"]
    assert result[0].get("sha256", "") == ""
    assert all(item["trusted"] is False and item["official"] is False for item in result)
    assert result[1]["sha256"] == "a" * 64
    assert any("broken" in warning and "Invalid registry sha256" in warning for warning in manager._test_warnings)


def test_installed_trusted_addon_is_not_rehashed_during_runtime_load(manager, tmp_path, monkeypatch):
    source = _source(tmp_path)
    digest = write_manifest_sha256(str(source))
    manager.import_directory(
        str(source), trusted=True, official=True, expected_sha256=digest,
    )
    destination = Path(manager.get_extension_dir("plugin", "sha_test", create_parent=False))
    (destination / "runtime-state.dat").write_text("created after install\n", encoding="utf-8")
    (destination / "__pycache__").mkdir()
    (destination / "__pycache__" / "plugin.cache").write_bytes(b"runtime-cache")

    verify = MagicMock(side_effect=AssertionError("installed add-on must not be re-hashed"))
    monkeypatch.setattr(manager, "_verify_package_integrity", verify)
    runtime_object = object()
    monkeypatch.setattr(manager, "_load_entrypoints", MagicMock(return_value=[runtime_object]))
    monkeypatch.setattr(manager, "_validate_runtime_objects", MagicMock())
    monkeypatch.setattr(manager, "_configure_runtime_locale", MagicMock())
    launcher = SimpleNamespace(add_plugin=MagicMock())

    loaded = manager.load_into_launcher(launcher)

    assert [item["id"] for item in loaded] == ["sha_test"]
    launcher.add_plugin.assert_called_once_with(runtime_object)
    verify.assert_not_called()


def test_installed_trusted_static_addon_is_not_rehashed_during_sync(manager, tmp_path, monkeypatch):
    source = tmp_path / "theme-source"
    (source / "theme").mkdir(parents=True)
    (source / "theme" / "app.css").write_text("QWidget { border: 0; }\n", encoding="utf-8")
    manifest = _manifest(
        id="sha_theme",
        name="SHA Theme",
        type="theme",
    )
    manifest.pop("entrypoint", None)
    (source / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    digest = write_manifest_sha256(str(source))

    manager.import_directory(
        str(source), trusted=True, official=True, expected_sha256=digest,
    )
    destination = Path(manager.get_extension_dir("theme", "sha_theme", create_parent=False))
    (destination / "runtime-state.dat").write_text("created after install\n", encoding="utf-8")
    (destination / "__pycache__").mkdir()
    (destination / "__pycache__" / "theme.cache").write_bytes(b"runtime-cache")

    verify = MagicMock(side_effect=AssertionError("installed add-on must not be re-hashed"))
    monkeypatch.setattr(manager, "_verify_package_integrity", verify)

    manager.sync_static_extensions()

    verify.assert_not_called()
    assert not any("Invalid static add-on 'sha_theme'" in warning for warning in manager._test_warnings)
