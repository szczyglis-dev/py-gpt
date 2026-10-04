"""Application-wide Add-ons storage migration for 2.8.36."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple


REGISTRY_FILENAME = ".registry.json"
ADDON_TYPE_DIRS = (
    "plugins",
    "llms",
    "vector_stores",
    "loaders",
    "audio_input",
    "audio_output",
    "web",
    "tools",
    "agents",
    "themes",
    "locale",
)


def _same_filesystem(source: str, destination_parent: str) -> bool:
    try:
        return os.stat(source).st_dev == os.stat(destination_parent).st_dev
    except OSError:
        if os.name == "nt":
            source_drive = os.path.splitdrive(os.path.abspath(source))[0].lower()
            target_drive = os.path.splitdrive(os.path.abspath(destination_parent))[0].lower()
            return bool(source_drive) and source_drive == target_drive
        return False


def _path_size(path: str) -> int:
    if os.path.islink(path):
        try:
            return os.lstat(path).st_size
        except OSError:
            return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        dirnames[:] = [
            name for name in dirnames
            if not os.path.islink(os.path.join(dirpath, name))
        ]
        for name in filenames:
            item = os.path.join(dirpath, name)
            try:
                total += os.lstat(item).st_size
            except OSError:
                continue
    return total


def _format_bytes(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{int(value)} B"


def _profile_key_for_workdir(window, workdir: str) -> str:
    target = os.path.normcase(os.path.realpath(workdir))
    profile = getattr(window.core.config, "profile", None)
    if profile is not None:
        for profile_id, data in profile.get_all().items():
            if not isinstance(data, dict):
                continue
            raw = str(data.get("workdir") or "").replace("%HOME%", str(Path.home()))
            if not raw:
                continue
            try:
                candidate = os.path.normcase(os.path.realpath(os.path.expanduser(raw)))
            except OSError:
                continue
            if candidate == target:
                return f"profile:{profile_id}"
    return f"workdir:{os.path.realpath(workdir)}"


def _load_registry(path: str) -> dict:
    if not os.path.isfile(path):
        return {"version": 1, "items": {}}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("registry root must be an object")
    except Exception as exc:
        print(f"WARNING: Unable to read Add-ons registry during migration: {path}: {exc}")
        return {"version": 1, "items": {}}
    if not isinstance(data.get("items"), dict):
        data["items"] = {}
    return data


def _save_registry(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data["version"] = 1
    if not isinstance(data.get("items"), dict):
        data["items"] = {}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def _normalize_registry_deployments(data: dict, profile_key: str) -> bool:
    changed = False
    items = data.get("items")
    if not isinstance(items, dict):
        return False
    for meta in items.values():
        if not isinstance(meta, dict) or "deployed" not in meta:
            continue
        deployed = meta.pop("deployed", [])
        profiles = meta.get("deployed_profiles")
        if not isinstance(profiles, dict):
            profiles = {}
        if isinstance(deployed, list):
            profiles.setdefault(profile_key, list(deployed))
        meta["deployed_profiles"] = profiles
        changed = True
    return changed


def _merge_deployment_maps(destination: dict, source: dict):
    src_profiles = source.get("deployed_profiles") if isinstance(source, dict) else None
    if not isinstance(src_profiles, dict):
        return
    dst_profiles = destination.get("deployed_profiles")
    if not isinstance(dst_profiles, dict):
        dst_profiles = {}
    for key, value in src_profiles.items():
        if isinstance(value, list) and key not in dst_profiles:
            dst_profiles[key] = list(value)
    destination["deployed_profiles"] = dst_profiles


def _merge_registry(
        destination_path: str,
        source_path: str,
        destination_profile_key: str,
        source_profile_key: str,
        moved_ids: Set[str],
        duplicate_ids: Set[str],
        conflict_ids: Set[str],
):
    destination = _load_registry(destination_path)
    source = _load_registry(source_path)
    changed = _normalize_registry_deployments(destination, destination_profile_key)
    _normalize_registry_deployments(source, source_profile_key)

    dst_items = destination.setdefault("items", {})
    src_items = source.get("items", {}) if isinstance(source.get("items"), dict) else {}
    for extension_id, src_meta in src_items.items():
        if not isinstance(src_meta, dict):
            continue
        dst_meta = dst_items.get(extension_id)
        if extension_id in moved_ids:
            if isinstance(dst_meta, dict):
                merged = dict(dst_meta)
                merged.update(src_meta)
                _merge_deployment_maps(merged, dst_meta)
                _merge_deployment_maps(merged, src_meta)
                dst_items[extension_id] = merged
            else:
                dst_items[extension_id] = dict(src_meta)
            changed = True
        elif extension_id in duplicate_ids or extension_id in conflict_ids:
            if isinstance(dst_meta, dict):
                before = json.dumps(dst_meta.get("deployed_profiles", {}), sort_keys=True)
                _merge_deployment_maps(dst_meta, src_meta)
                after = json.dumps(dst_meta.get("deployed_profiles", {}), sort_keys=True)
                changed = changed or before != after
            elif extension_id in duplicate_ids or extension_id in conflict_ids:
                # The package may have been copied manually into the destination
                # without registry metadata. Preserve the source metadata as the
                # best available record, while the destination package itself
                # remains authoritative for a content conflict.
                dst_items[extension_id] = dict(src_meta)
                changed = True

    if changed or not os.path.isfile(destination_path):
        _save_registry(destination_path, destination)


def _file_digest(path: str) -> bytes:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def _trees_equal(left: str, right: str) -> bool:
    def entries(root: str) -> Dict[str, Tuple[str, int]]:
        result = {}
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(
                name for name in dirnames
                if name != "__pycache__"
                and not os.path.islink(os.path.join(dirpath, name))
            )
            rel_dir = os.path.relpath(dirpath, root)
            for name in sorted(filenames):
                if name.endswith((".pyc", ".pyo")):
                    continue
                path = os.path.join(dirpath, name)
                if os.path.islink(path):
                    result[os.path.join(rel_dir, name)] = ("link", 0)
                    continue
                try:
                    result[os.path.join(rel_dir, name)] = ("file", os.path.getsize(path))
                except OSError:
                    return {}
        return result

    left_entries = entries(left)
    right_entries = entries(right)
    if left_entries != right_entries:
        return False
    for relative, (kind, _size) in left_entries.items():
        if kind != "file":
            return False
        try:
            if _file_digest(os.path.join(left, relative)) != _file_digest(os.path.join(right, relative)):
                return False
        except OSError:
            return False
    return True


def _collect_merge_candidates(source: str, destination: str):
    moves = []
    duplicates = []
    conflicts = []
    for dirname in ADDON_TYPE_DIRS:
        source_type = os.path.join(source, dirname)
        if not os.path.isdir(source_type) or os.path.islink(source_type):
            continue
        destination_type = os.path.join(destination, dirname)
        try:
            names = sorted(os.listdir(source_type))
        except OSError:
            continue
        for name in names:
            source_item = os.path.join(source_type, name)
            if not os.path.isdir(source_item) or os.path.islink(source_item):
                continue
            destination_item = os.path.join(destination_type, name)
            if not os.path.lexists(destination_item):
                moves.append((dirname, name, source_item, destination_item))
            elif os.path.isdir(destination_item) and not os.path.islink(destination_item) \
                    and _trees_equal(source_item, destination_item):
                duplicates.append((dirname, name, source_item, destination_item))
            else:
                conflicts.append((dirname, name, source_item, destination_item))
    return moves, duplicates, conflicts


def _remove_empty_tree(path: str):
    if not os.path.isdir(path) or os.path.islink(path):
        return
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        if filenames:
            continue
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
        except OSError:
            pass


def migrate_addons_to_application_base(window) -> bool:
    """Move/merge the active profile's legacy Add-ons into the app base workdir."""
    config = window.core.config
    workdir = os.path.realpath(config.get_user_path())
    base_workdir = os.path.realpath(config.get_base_workdir())
    source = os.path.join(workdir, "addons")
    legacy_source = os.path.join(workdir, "extensions")
    if (not os.path.isdir(source) or os.path.islink(source)) \
            and os.path.isdir(legacy_source) and not os.path.islink(legacy_source):
        # Early 2.8.32 builds used ``extensions`` before the public directory
        # name was finalized as ``addons``. Migrate that legacy tree too.
        source = legacy_source
    destination = os.path.join(base_workdir, "addons")
    source_profile_key = _profile_key_for_workdir(window, workdir)
    destination_profile_key = _profile_key_for_workdir(window, base_workdir)

    # The default profile already stored Add-ons in the application base path.
    # Preserve the old deployment list only as per-profile legacy-cleanup
    # metadata, so files mirrored by older static loaders can be retired safely.
    if os.path.normcase(source) == os.path.normcase(destination):
        registry_path = os.path.join(destination, REGISTRY_FILENAME)
        if os.path.isfile(registry_path):
            data = _load_registry(registry_path)
            if _normalize_registry_deployments(data, source_profile_key):
                _save_registry(registry_path, data)
                return True
        return False

    if not os.path.isdir(source) or os.path.islink(source):
        return False
    os.makedirs(base_workdir, exist_ok=True)

    # Fast path: first migrated profile owns the complete tree. This mirrors the
    # sandbox migration behavior and preserves all package/registry metadata.
    if not os.path.lexists(destination):
        if not _same_filesystem(source, base_workdir):
            required = _path_size(source)
            try:
                free = shutil.disk_usage(base_workdir).free
            except OSError as exc:
                print(f"WARNING: Unable to check free disk space for Add-ons migration: {exc}")
                return False
            if free < required:
                print(
                    "WARNING: Not enough free disk space to migrate Add-ons to "
                    f"{destination}. Required: {_format_bytes(required)}, free: {_format_bytes(free)}."
                )
                return False
        print(f"Migration addons directory to application base workdir: {destination}. Please wait...")
        try:
            shutil.move(source, destination)
            registry_path = os.path.join(destination, REGISTRY_FILENAME)
            if os.path.isfile(registry_path):
                data = _load_registry(registry_path)
                if _normalize_registry_deployments(data, source_profile_key):
                    _save_registry(registry_path, data)
        except Exception as exc:
            print(f"WARNING: Unable to migrate Add-ons to application base workdir: {exc}")
            return False
        print(f"Migration addons directory finished: {destination}")
        return True

    if not os.path.isdir(destination) or os.path.islink(destination):
        print(
            "WARNING: Add-ons migration destination is not a normal directory: "
            f"{destination}. Migration skipped."
        )
        return False

    moves, duplicates, conflicts = _collect_merge_candidates(source, destination)
    required = sum(_path_size(item[2]) for item in moves)
    if required and not _same_filesystem(source, base_workdir):
        try:
            free = shutil.disk_usage(base_workdir).free
        except OSError as exc:
            print(f"WARNING: Unable to check free disk space for Add-ons migration: {exc}")
            return False
        if free < required:
            print(
                "WARNING: Not enough free disk space to merge Add-ons into "
                f"{destination}. Required: {_format_bytes(required)}, free: {_format_bytes(free)}."
            )
            return False

    moved_ids: Set[str] = set()
    duplicate_ids: Set[str] = set()
    conflict_ids: Set[str] = set()
    changed = False
    print(f"Migration addons directory to application base workdir: {destination}. Please wait...")
    try:
        for dirname, extension_id, source_item, destination_item in moves:
            os.makedirs(os.path.dirname(destination_item), exist_ok=True)
            shutil.move(source_item, destination_item)
            moved_ids.add(extension_id)
            changed = True
        for _dirname, extension_id, source_item, _destination_item in duplicates:
            shutil.rmtree(source_item)
            duplicate_ids.add(extension_id)
            changed = True
        for dirname, extension_id, source_item, destination_item in conflicts:
            conflict_ids.add(extension_id)
            print(
                "WARNING: Add-ons migration conflict for "
                f"{dirname}/{extension_id}. Keeping application-wide copy at "
                f"{destination_item}; legacy profile copy remains at {source_item}."
            )

        source_registry = os.path.join(source, REGISTRY_FILENAME)
        destination_registry = os.path.join(destination, REGISTRY_FILENAME)
        _merge_registry(
            destination_registry,
            source_registry,
            destination_profile_key,
            source_profile_key,
            moved_ids,
            duplicate_ids,
            conflict_ids,
        )

        # All non-conflicting packages have been moved or deduplicated. Remove
        # the old registry/root only when no conflicting package remains, so a
        # differing legacy package is never deleted silently.
        if not conflicts:
            try:
                if os.path.isfile(source_registry):
                    os.remove(source_registry)
            except OSError:
                pass
        _remove_empty_tree(source)
    except Exception as exc:
        print(f"WARNING: Unable to merge profile Add-ons into application base workdir: {exc}")
        return changed

    print(f"Migration addons directory finished: {destination}")
    return changed or bool(conflicts)
