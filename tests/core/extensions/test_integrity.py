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

import pytest

from pygpt_net.core.extensions.integrity import (
    AddonIntegrityError,
    compute_addon_sha256,
    is_valid_sha256,
    normalize_sha256,
    validate_sha256,
    write_manifest_sha256,
)


def _manifest(**updates):
    data = {
        "manifest_version": 1,
        "id": "integrity_test",
        "name": "Integrity Test",
        "description": "Integrity test add-on",
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


def _addon(tmp_path: Path, name: str = "addon") -> Path:
    root = tmp_path / name
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps(_manifest(), indent=2), encoding="utf-8")
    (root / "plugin.py").write_text("class Plugin:\n    pass\n", encoding="utf-8")
    return root


def _make_symlink(link: Path, target: Path, directory: bool = False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable on this platform: {exc}")


def test_sha256_value_validation_and_normalization():
    upper = "AB" * 32
    assert normalize_sha256(f"  {upper}  ") == upper.lower()
    assert is_valid_sha256(upper) is True
    assert is_valid_sha256("a" * 63) is False
    assert is_valid_sha256("g" * 64) is False
    assert validate_sha256(upper, required=True) == upper.lower()
    assert validate_sha256(None, required=False) == ""

    with pytest.raises(AddonIntegrityError, match="Missing registry sha256"):
        validate_sha256("", label="registry sha256", required=True)
    with pytest.raises(AddonIntegrityError, match="64 hexadecimal"):
        validate_sha256("not-a-digest", required=True)


def test_compute_requires_existing_directory_and_manifest(tmp_path):
    with pytest.raises(AddonIntegrityError, match="directory not found"):
        compute_addon_sha256(str(tmp_path / "missing"))

    root = tmp_path / "addon"
    root.mkdir()
    with pytest.raises(AddonIntegrityError, match="Missing manifest.json"):
        compute_addon_sha256(str(root))


def test_manifest_is_canonicalized_and_own_sha_field_is_excluded(tmp_path):
    root = _addon(tmp_path)
    original = compute_addon_sha256(str(root))

    manifest_path = root / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Different key order/whitespace and any value in the self-referential field
    # must not alter the tree digest.
    data = {key: data[key] for key in reversed(list(data.keys()))}
    data["sha256"] = "f" * 64
    manifest_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    assert compute_addon_sha256(str(root)) == original


def test_changing_real_manifest_content_changes_digest(tmp_path):
    root = _addon(tmp_path)
    before = compute_addon_sha256(str(root))
    manifest_path = root / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["entrypoint"] = "other.py:Plugin"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    assert compute_addon_sha256(str(root)) != before


def test_changing_regular_file_content_changes_digest(tmp_path):
    root = _addon(tmp_path)
    before = compute_addon_sha256(str(root))
    (root / "plugin.py").write_text("class Plugin:\n    changed = True\n", encoding="utf-8")
    assert compute_addon_sha256(str(root)) != before


def test_git_metadata_is_ignored_but_gitignore_is_hashed(tmp_path):
    root = _addon(tmp_path)
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    before = compute_addon_sha256(str(root))

    git = root / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "index").write_bytes(b"repository metadata")
    assert compute_addon_sha256(str(root)) == before

    (root / ".gitignore").write_text("__pycache__/\n*.tmp\n", encoding="utf-8")
    assert compute_addon_sha256(str(root)) != before


def test_empty_directories_do_not_change_digest(tmp_path):
    root = _addon(tmp_path)
    before = compute_addon_sha256(str(root))
    (root / "empty" / "nested").mkdir(parents=True)
    assert compute_addon_sha256(str(root)) == before


def test_file_order_on_disk_does_not_change_digest(tmp_path):
    one = _addon(tmp_path, "one")
    two = _addon(tmp_path, "two")

    (one / "z.txt").write_text("z", encoding="utf-8")
    (one / "a.txt").write_text("a", encoding="utf-8")
    (two / "a.txt").write_text("a", encoding="utf-8")
    (two / "z.txt").write_text("z", encoding="utf-8")

    assert compute_addon_sha256(str(one)) == compute_addon_sha256(str(two))


def test_symlinked_file_is_rejected(tmp_path):
    root = _addon(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    _make_symlink(root / "link.txt", outside)

    with pytest.raises(AddonIntegrityError, match="may not contain symlinks"):
        compute_addon_sha256(str(root))


def test_symlinked_directory_is_rejected(tmp_path):
    root = _addon(tmp_path)
    outside = tmp_path / "outside-dir"
    outside.mkdir()
    (outside / "payload.txt").write_text("outside", encoding="utf-8")
    _make_symlink(root / "linked-dir", outside, directory=True)

    with pytest.raises(AddonIntegrityError, match="may not contain symlinks"):
        compute_addon_sha256(str(root))


def test_invalid_manifest_json_and_non_object_root_are_rejected(tmp_path):
    root = _addon(tmp_path)
    manifest_path = root / "manifest.json"

    manifest_path.write_text("{broken", encoding="utf-8")
    with pytest.raises(AddonIntegrityError, match="Cannot canonicalize manifest.json"):
        compute_addon_sha256(str(root))

    manifest_path.write_text("[]", encoding="utf-8")
    with pytest.raises(AddonIntegrityError, match="root must be an object"):
        compute_addon_sha256(str(root))


def test_manifest_non_finite_json_value_is_rejected(tmp_path):
    root = _addon(tmp_path)
    manifest_path = root / "manifest.json"
    manifest_path.write_text('{"value": NaN}', encoding="utf-8")

    with pytest.raises(AddonIntegrityError, match="Cannot canonicalize manifest.json"):
        compute_addon_sha256(str(root))


def test_write_manifest_sha256_is_stable_and_persists_digest(tmp_path):
    root = _addon(tmp_path)
    expected = compute_addon_sha256(str(root))

    first = write_manifest_sha256(str(root))
    data = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert first == expected
    assert data["sha256"] == expected
    assert compute_addon_sha256(str(root)) == expected

    second = write_manifest_sha256(str(root))
    assert second == expected
    assert json.loads((root / "manifest.json").read_text(encoding="utf-8"))["sha256"] == expected
