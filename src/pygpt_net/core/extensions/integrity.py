#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.10.01 15:10:00                  #
# ================================================== #

"""Deterministic integrity hashing for external PyGPT Add-ons.

The digest is intentionally independent from ZIP/Git metadata and OS path
separators.  ``manifest.json`` participates in the digest, but its own
``sha256`` field is removed before canonical JSON serialization so the digest
can be stored inside the manifest without creating a circular dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
from pathlib import Path
from typing import Iterable, Tuple

MANIFEST_FILENAME = "manifest.json"
HASH_FIELD = "sha256"
HASH_ALGORITHM = "sha256"
HASH_FORMAT_VERSION = 1
_HASH_MAGIC = b"PYGPT-ADDON-SHA256-V1\x00"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_IGNORED_DIRS = {".git"}


class AddonIntegrityError(RuntimeError):
    """Raised when an Add-on tree cannot be hashed safely/deterministically."""


def normalize_sha256(value: object) -> str:
    """Return a normalized lowercase SHA-256 hex digest or an empty string."""
    if value is None:
        return ""
    return str(value).strip().lower()


def is_valid_sha256(value: object) -> bool:
    """Return True only for a full 64-character hexadecimal SHA-256 digest."""
    return bool(_SHA256_RE.fullmatch(str(value or "").strip()))


def validate_sha256(value: object, label: str = HASH_FIELD, required: bool = False) -> str:
    """Validate and normalize a SHA-256 value.

    Empty values are accepted only when ``required`` is False.
    """
    normalized = normalize_sha256(value)
    if not normalized:
        if required:
            raise AddonIntegrityError(f"Missing {label}")
        return ""
    if not is_valid_sha256(normalized):
        raise AddonIntegrityError(f"Invalid {label}; expected 64 hexadecimal characters")
    return normalized


def _manifest_payload(path: Path) -> bytes:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        raise AddonIntegrityError(f"Cannot canonicalize {MANIFEST_FILENAME}: {exc}") from exc
    if not isinstance(data, dict):
        raise AddonIntegrityError(f"{MANIFEST_FILENAME} root must be an object")
    data = dict(data)
    data.pop(HASH_FIELD, None)
    try:
        text = json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise AddonIntegrityError(f"Cannot canonicalize {MANIFEST_FILENAME}: {exc}") from exc
    return text.encode("utf-8")


def _iter_files(root: Path) -> Iterable[Tuple[str, Path]]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        kept_dirs = []
        for name in dirnames:
            path = current / name
            if path.is_symlink():
                raise AddonIntegrityError(f"Add-on packages may not contain symlinks: {path}")
            if name in _IGNORED_DIRS:
                continue
            kept_dirs.append(name)
        dirnames[:] = kept_dirs

        for name in filenames:
            path = current / name
            if path.is_symlink():
                raise AddonIntegrityError(f"Add-on packages may not contain symlinks: {path}")
            if not path.is_file():
                raise AddonIntegrityError(f"Unsupported non-regular Add-on file: {path}")
            relative = path.relative_to(root).as_posix()
            files.append((relative, path))

    files.sort(key=lambda item: item[0].encode("utf-8"))
    return files


def compute_addon_sha256(directory: str) -> str:
    """Compute the PyGPT Add-on tree SHA-256 for ``directory``.

    Hash format v1:

    * starts with a fixed version/domain marker;
    * includes every regular file recursively except ``.git`` metadata;
    * uses UTF-8 POSIX relative paths sorted by their UTF-8 bytes;
    * frames each path and file payload with fixed-width byte lengths;
    * hashes raw bytes for every file except ``manifest.json``;
    * hashes canonical JSON for ``manifest.json`` with the top-level ``sha256``
      field removed.

    Empty directories, timestamps, permissions and archive/Git metadata do not
    affect the digest.
    """
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise AddonIntegrityError(f"Add-on directory not found: {root}")
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise AddonIntegrityError(f"Missing {MANIFEST_FILENAME}: {root}")

    digest = hashlib.sha256()
    digest.update(_HASH_MAGIC)
    for relative, path in _iter_files(root):
        path_bytes = relative.encode("utf-8")
        if relative == MANIFEST_FILENAME:
            payload = _manifest_payload(path)
        else:
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise AddonIntegrityError(f"Cannot read Add-on file: {path}: {exc}") from exc
        digest.update(struct.pack(">I", len(path_bytes)))
        digest.update(path_bytes)
        digest.update(struct.pack(">Q", len(payload)))
        digest.update(payload)
    return digest.hexdigest()


def write_manifest_sha256(directory: str) -> str:
    """Compute the digest and store it as top-level ``manifest.json.sha256``."""
    root = Path(directory).expanduser().resolve()
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise AddonIntegrityError(f"Missing {MANIFEST_FILENAME}: {root}")
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        raise AddonIntegrityError(f"Invalid {MANIFEST_FILENAME}: {exc}") from exc
    if not isinstance(data, dict):
        raise AddonIntegrityError(f"{MANIFEST_FILENAME} root must be an object")

    digest = compute_addon_sha256(str(root))
    data[HASH_FIELD] = digest
    tmp = manifest_path.with_name(manifest_path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, manifest_path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
    return digest


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute the deterministic PyGPT Add-on tree SHA-256.",
    )
    parser.add_argument("directory", nargs="?", default=".", help="Add-on root containing manifest.json")
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the computed digest into manifest.json as the sha256 field",
    )
    args = parser.parse_args(argv)
    try:
        digest = write_manifest_sha256(args.directory) if args.write else compute_addon_sha256(args.directory)
    except AddonIntegrityError as exc:
        parser.error(str(exc))
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
