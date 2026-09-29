#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 17:15:00                  #
# ================================================== #

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import types
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from packaging.version import InvalidVersion, Version

from pygpt_net.__init__ import __version__


class ExtensionError(RuntimeError):
    pass


class ExtensionManifestError(ExtensionError):
    pass


class ExtensionAlreadyInstalled(ExtensionError):
    pass


class Extensions:
    """Profile-scoped external extension discovery, installation and runtime loader."""

    MANIFEST_FILENAME = "manifest.json"
    MANIFEST_VERSION = 1
    REGISTRY_FILENAME = ".registry.json"
    REGISTRY_VERSION = 1
    DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/szczyglis-dev/py-gpt-addons/master/addons.json"
    LEGACY_REGISTRY_URLS = {}
    DEFAULT_REGISTRY_REPOSITORY = "https://github.com/szczyglis-dev/py-gpt-addons"
    ROOT_DIRNAME = "addons"
    LEGACY_ROOT_DIRNAME = "extensions"
    MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
    MAX_REGISTRY_BYTES = 4 * 1024 * 1024
    MAX_ARCHIVE_FILES = 10000

    TYPE_DIRS = {
        "plugin": "plugins",
        "llm": "llms",
        "vector_store": "vector_stores",
        "loader": "loaders",
        "audio_input": "audio_input",
        "audio_output": "audio_output",
        "web": "web",
        "tool": "tools",
        "agent": "agents",
        "theme": "themes",
        "locale": "locale",
    }
    TYPE_ALIASES = {
        "plugins": "plugin",
        "provider": "llm",
        "providers": "llm",
        "llm_provider": "llm",
        "llm_providers": "llm",
        "vector_stores": "vector_store",
        "data_loader": "loader",
        "data_loaders": "loader",
        "loaders": "loader",
        "audio_in": "audio_input",
        "input_provider": "audio_input",
        "input_providers": "audio_input",
        "audio_out": "audio_output",
        "output_provider": "audio_output",
        "output_providers": "audio_output",
        "web_provider": "web",
        "web_providers": "web",
        "web_search": "web",
        "tools": "tool",
        "agents": "agent",
        "themes": "theme",
        "translation": "locale",
        "translations": "locale",
        "locales": "locale",
    }
    RUNTIME_TYPES = {
        "plugin": "add_plugin",
        "llm": "add_llm",
        "vector_store": "add_vector_store",
        "loader": "add_loader",
        "audio_input": "add_audio_input",
        "audio_output": "add_audio_output",
        "web": "add_web",
        "tool": "add_tool",
        "agent": "add_agent",
    }
    STATIC_TYPES = {"theme", "locale"}
    _ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

    def __init__(self, window=None):
        self.window = window
        self._loaded_modules: Dict[str, str] = {}
        self._module_cache: Dict[str, types.ModuleType] = {}
        self._loaded_objects: Dict[str, list] = {}

    # PATHS / REGISTRY -------------------------------------------------

    def get_root_dir(self, create: bool = True, profile_dir: Optional[str] = None) -> str:
        base = os.path.abspath(profile_dir or self.window.core.config.get_user_path())
        path = os.path.join(base, self.ROOT_DIRNAME)
        legacy = os.path.join(base, self.LEGACY_ROOT_DIRNAME)

        # 2.8.32 initially used %workdir%/extensions. Move that profile-scoped
        # directory atomically when possible so existing installations keep all
        # installed add-ons after the public folder name changes to ``addons``.
        if not os.path.exists(path) and os.path.isdir(legacy) and not os.path.islink(legacy):
            try:
                os.replace(legacy, path)
            except OSError as exc:
                # Keep the old location usable if migration cannot be completed
                # (for example because of permissions), rather than hiding all
                # previously installed add-ons from the current profile.
                self._warn(f"Could not migrate legacy add-ons directory to '{path}': {exc}")
                path = legacy

        if create:
            os.makedirs(path, exist_ok=True)
        return path

    def get_registry_path(self, profile_dir: Optional[str] = None) -> str:
        return os.path.join(self.get_root_dir(create=False, profile_dir=profile_dir), self.REGISTRY_FILENAME)

    def get_registry_url(self) -> str:
        value = str(self.window.core.config.get("extensions.registry.url", "") or "").strip()
        if value in self.LEGACY_REGISTRY_URLS:
            return self.DEFAULT_REGISTRY_URL
        return value or self.DEFAULT_REGISTRY_URL

    def set_registry_url(self, value: str):
        self.window.core.config.set("extensions.registry.url", str(value or "").strip())
        self.window.core.config.save()

    def _load_registry(self) -> dict:
        path = self.get_registry_path()
        if not os.path.isfile(path):
            return {"version": self.REGISTRY_VERSION, "items": {}}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("Registry root must be an object")
            if not isinstance(data.get("items"), dict):
                data["items"] = {}
            return data
        except Exception as exc:
            self._warn(f"Cannot read add-on registry: {exc}")
            return {"version": self.REGISTRY_VERSION, "items": {}}

    def _save_registry(self, data: dict):
        path = self.get_registry_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data["version"] = self.REGISTRY_VERSION
        if not isinstance(data.get("items"), dict):
            data["items"] = {}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)

    # MANIFEST ---------------------------------------------------------

    @classmethod
    def normalize_type(cls, value: str) -> str:
        value = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        value = cls.TYPE_ALIASES.get(value, value)
        return value if value in cls.TYPE_DIRS else ""

    def read_manifest(self, directory: str, validate: bool = True) -> dict:
        path = os.path.join(directory, self.MANIFEST_FILENAME)
        if not os.path.isfile(path):
            raise ExtensionManifestError(f"Missing {self.MANIFEST_FILENAME}: {directory}")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            raise ExtensionManifestError(f"Invalid {self.MANIFEST_FILENAME}: {exc}") from exc
        if validate:
            return self.validate_manifest(data, directory=directory)
        return data

    def validate_manifest(self, data: dict, directory: str = "") -> dict:
        if not isinstance(data, dict):
            raise ExtensionManifestError("Manifest root must be an object")
        manifest = dict(data)
        required = ("id", "name", "description", "author", "contact", "version", "type", "manifest_version", "min_app_version")
        missing = [key for key in required if manifest.get(key) in (None, "")]
        if missing:
            raise ExtensionManifestError("Missing manifest field(s): " + ", ".join(missing))

        string_fields = ("id", "name", "description", "author", "version", "type", "min_app_version")
        invalid_strings = [key for key in string_fields if not isinstance(manifest.get(key), str) or not manifest[key].strip()]
        if invalid_strings:
            raise ExtensionManifestError("Manifest field(s) must be non-empty strings: " + ", ".join(invalid_strings))

        raw_id = manifest["id"].strip()
        ext_id = raw_id.lower()
        if raw_id != ext_id or not self._ID_RE.fullmatch(ext_id):
            raise ExtensionManifestError("Invalid add-on id; use lowercase letters, digits, '.', '_' or '-'")
        ext_type = self.normalize_type(manifest["type"])
        if not ext_type:
            raise ExtensionManifestError(f"Unsupported add-on type: {manifest.get('type')}")
        manifest_version = manifest["manifest_version"]
        if isinstance(manifest_version, bool) or not isinstance(manifest_version, int):
            raise ExtensionManifestError("manifest_version must be an integer")
        if manifest_version > self.MANIFEST_VERSION or manifest_version < 1:
            raise ExtensionManifestError(
                f"Unsupported manifest_version {manifest_version}; supported: {self.MANIFEST_VERSION}"
            )
        try:
            Version(str(manifest["version"]))
            minimum = Version(str(manifest["min_app_version"]))
        except InvalidVersion as exc:
            raise ExtensionManifestError(f"Invalid version in manifest: {exc}") from exc

        contact = manifest.get("contact")
        if not isinstance(contact, (str, dict, list)):
            raise ExtensionManifestError("contact must be a string, object or array")
        if (isinstance(contact, str) and not contact.strip()) or (isinstance(contact, (dict, list)) and not contact):
            raise ExtensionManifestError("contact may not be empty")

        deps = manifest.get("external_dependencies", [])
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            raise ExtensionManifestError("external_dependencies must be an array")
        for dep in deps:
            if not isinstance(dep, (str, dict)):
                raise ExtensionManifestError("Each external dependency must be a string or object")
            if isinstance(dep, str) and not dep.strip():
                raise ExtensionManifestError("Dependency strings may not be empty")
            if isinstance(dep, dict) and not str(dep.get("name") or "").strip():
                raise ExtensionManifestError("Dependency objects require a name")

        if ext_type in self.RUNTIME_TYPES:
            entrypoint = manifest.get("entrypoint")
            if not isinstance(entrypoint, (str, list)) or not entrypoint:
                raise ExtensionManifestError("Runtime add-ons require an entrypoint")
            entries = [entrypoint] if isinstance(entrypoint, str) else entrypoint
            if not entries:
                raise ExtensionManifestError("Runtime add-ons require at least one entrypoint")
            for item in entries:
                self._validate_entrypoint(item)

        for key in ("name", "description", "author", "version", "min_app_version"):
            manifest[key] = manifest[key].strip()
        manifest["id"] = ext_id
        manifest["type"] = ext_type
        manifest["manifest_version"] = manifest_version
        manifest["external_dependencies"] = deps
        manifest["_compatible"] = minimum <= Version(__version__)
        if directory:
            manifest["_path"] = os.path.abspath(directory)
        return manifest

    # DISCOVERY --------------------------------------------------------

    def list_installed(self) -> List[dict]:
        root = self.get_root_dir(create=False)
        registry = self._load_registry().get("items", {})
        result: List[dict] = []
        if not os.path.isdir(root):
            return result
        for ext_type, dirname in self.TYPE_DIRS.items():
            parent = os.path.join(root, dirname)
            if not os.path.isdir(parent):
                continue
            try:
                names = sorted(os.listdir(parent), key=str.lower)
            except OSError as exc:
                self._warn(f"Cannot scan addons/{dirname}: {exc}")
                continue
            for name in names:
                directory = os.path.join(parent, name)
                if not os.path.isdir(directory) or os.path.islink(directory):
                    continue
                try:
                    manifest = self.read_manifest(directory)
                    if manifest["type"] != ext_type:
                        raise ExtensionManifestError(
                            f"Manifest type '{manifest['type']}' does not match directory '{dirname}'"
                        )
                    if manifest["id"] != name:
                        raise ExtensionManifestError(
                            f"Manifest id '{manifest['id']}' does not match directory '{name}'"
                        )
                    meta = registry.get(manifest["id"], {}) if isinstance(registry, dict) else {}
                    manifest.update({
                        "trusted": bool(meta.get("trusted", False)),
                        "official": bool(meta.get("official", False)),
                        "source": str(meta.get("source") or "local"),
                        "source_url": str(meta.get("source_url") or ""),
                        "github_path": str(meta.get("github_path") or ""),
                        "installed_at": str(meta.get("installed_at") or ""),
                    })
                    result.append(manifest)
                except Exception as exc:
                    self._warn(f"Skipping add-on at {directory}: {exc}")
        return sorted(result, key=lambda item: (item.get("type", ""), item.get("name", "").lower()))

    def get_installed_ids(self) -> set:
        return {item["id"] for item in self.list_installed()}

    def get_installed_versions(self) -> Dict[str, str]:
        return {
            str(item.get("id") or ""): str(item.get("version") or "")
            for item in self.list_installed()
            if item.get("id")
        }

    @staticmethod
    def is_newer_version(candidate: str, installed: str) -> bool:
        try:
            return Version(str(candidate or "")) > Version(str(installed or ""))
        except InvalidVersion:
            return False

    # INSTALL / REMOVE -------------------------------------------------

    def import_directory(
            self,
            source: str,
            overwrite: bool = False,
            source_name: str = "directory",
            source_url: str = "",
            trusted: bool = False,
            official: bool = False,
            github_path: str = "",
    ) -> dict:
        source = os.path.abspath(source)
        if not os.path.isdir(source):
            raise ExtensionError(f"Directory not found: {source}")
        if os.path.islink(source):
            raise ExtensionError("Add-on source directory may not be a symlink")
        self._validate_source_tree(source)
        manifest = self.read_manifest(source)
        if not manifest.get("_compatible", False):
            raise ExtensionManifestError(
                f"Add-on requires PyGPT >= {manifest['min_app_version']} (current: {__version__})"
            )
        existing = next(
            (item for item in self.list_installed() if item.get("id") == manifest["id"]),
            None,
        )
        if existing is not None:
            if not overwrite:
                try:
                    incoming_version = Version(str(manifest.get("version") or ""))
                    installed_version = Version(str(existing.get("version") or ""))
                except InvalidVersion as exc:
                    raise ExtensionManifestError(f"Invalid add-on version: {exc}") from exc
                if incoming_version <= installed_version:
                    raise ExtensionAlreadyInstalled(
                        f"Add-on '{manifest['id']}' version {installed_version} is already installed; "
                        f"incoming version is {incoming_version}"
                    )
            self.uninstall(manifest["id"])

        destination = self.get_extension_dir(manifest["type"], manifest["id"], create_parent=True)
        if os.path.exists(destination):
            if not overwrite:
                raise ExtensionAlreadyInstalled(f"Add-on '{manifest['id']}' is already installed")
            # Clean an invalid/unregistered leftover at the exact destination too.
            shutil.rmtree(destination)
        self._check_static_conflicts(manifest, source)
        deployed = []
        try:
            shutil.copytree(source, destination, symlinks=False)
            installed = self.read_manifest(destination)
            deployed = self._deploy_static(installed)
            registry = self._load_registry()
            registry.setdefault("items", {})[installed["id"]] = {
                "type": installed["type"],
                "source": source_name,
                "source_url": source_url,
                "github_path": github_path,
                "trusted": bool(trusted),
                "official": bool(official),
                "deployed": deployed,
                "installed_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_registry(registry)
        except Exception:
            self._remove_deployed(deployed)
            shutil.rmtree(destination, ignore_errors=True)
            raise
        installed.update({
            "trusted": bool(trusted),
            "official": bool(official),
            "source": source_name,
            "source_url": source_url,
            "github_path": github_path,
        })
        return installed

    def import_zip(self, path: str, overwrite: bool = False, **meta) -> dict:
        if not os.path.isfile(path):
            raise ExtensionError(f"ZIP file not found: {path}")
        temp_root = tempfile.mkdtemp(prefix="pygpt-extension-zip-")
        try:
            with zipfile.ZipFile(path, "r") as archive:
                self._safe_extract_zip(archive, temp_root)
            source = self._find_manifest_root(temp_root)
            return self.import_directory(
                source,
                overwrite=overwrite,
                source_name=meta.pop("source_name", "zip"),
                source_url=meta.pop("source_url", os.path.abspath(path)),
                **meta,
            )
        except zipfile.BadZipFile as exc:
            raise ExtensionError(f"Invalid ZIP archive: {exc}") from exc
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def import_github(
            self,
            url: str,
            github_path: str = "",
            ref: str = "",
            overwrite: bool = False,
            trusted: bool = False,
            official: bool = False,
    ) -> dict:
        owner, repo, parsed_ref, parsed_path = self._parse_github_url(url)
        ref = str(ref or parsed_ref or "").strip()
        if not ref:
            ref = self._github_default_branch(owner, repo)
        subpath = str(github_path or parsed_path or "").strip("/\\")
        while subpath.startswith("./"):
            subpath = subpath[2:]
        archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/{quote(ref, safe='/')}"
        raw = self._download_bytes(archive_url, self.MAX_DOWNLOAD_BYTES)
        temp_root = tempfile.mkdtemp(prefix="pygpt-extension-github-")
        archive_path = os.path.join(temp_root, "repo.zip")
        try:
            with open(archive_path, "wb") as handle:
                handle.write(raw)
            extract_dir = os.path.join(temp_root, "repo")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as archive:
                self._safe_extract_zip(archive, extract_dir)
            roots = [os.path.join(extract_dir, name) for name in os.listdir(extract_dir)]
            roots = [path for path in roots if os.path.isdir(path)]
            if len(roots) != 1:
                raise ExtensionError("Unexpected GitHub archive layout")
            source = roots[0]
            if subpath:
                source = os.path.realpath(os.path.join(source, subpath))
                if not self._is_inside(source, roots[0]):
                    raise ExtensionError("GitHub path escapes repository root")
                if not os.path.isdir(source):
                    raise ExtensionError(f"GitHub add-on path not found: {subpath}")
            else:
                manifest_path = os.path.join(source, self.MANIFEST_FILENAME)
                if not os.path.isfile(manifest_path):
                    raise ExtensionManifestError(
                        f"GitHub repository root must contain {self.MANIFEST_FILENAME}; "
                        "use a tree URL or github_path for monorepos"
                    )
            canonical_url = f"https://github.com/{owner}/{repo}"
            return self.import_directory(
                source,
                overwrite=overwrite,
                source_name="github",
                source_url=canonical_url,
                trusted=trusted,
                official=official,
                github_path=subpath,
            )
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def install_registry_entry(self, entry: dict, overwrite: bool = False) -> dict:
        if not isinstance(entry, dict):
            raise ExtensionError("Invalid registry entry")
        path = str(entry.get("github_path") or entry.get("path") or "").strip()
        url = str(entry.get("github_url") or entry.get("url") or "").strip()
        if not url and path:
            url = self.DEFAULT_REGISTRY_REPOSITORY
        if not url:
            raise ExtensionError("Registry entry requires github_url or a path in the official registry repository")
        installed = self.import_github(
            url,
            github_path=path,
            ref=str(entry.get("ref") or ""),
            overwrite=overwrite,
            trusted=entry.get("trusted") is True,
            official=entry.get("official") is True,
        )
        expected_id = str(entry.get("id") or "").strip().lower()
        expected_type = self.normalize_type(entry.get("type"))
        if expected_id and installed.get("id") != expected_id:
            self.uninstall(installed.get("id", ""))
            raise ExtensionManifestError(
                f"Registry id '{expected_id}' does not match package manifest id '{installed.get('id')}'"
            )
        if expected_type and installed.get("type") != expected_type:
            self.uninstall(installed.get("id", ""))
            raise ExtensionManifestError(
                f"Registry type '{expected_type}' does not match package manifest type '{installed.get('type')}'"
            )
        return installed

    def uninstall(self, extension_id: str, remove_registry: bool = True) -> bool:
        extension_id = str(extension_id or "").strip().lower()
        self._validate_extension_id(extension_id)
        registry = self._load_registry()
        meta = registry.get("items", {}).get(extension_id, {})
        found = False
        self._remove_deployed(meta.get("deployed") or [])
        for ext_type in self.TYPE_DIRS:
            path = self.get_extension_dir(ext_type, extension_id, create_parent=False)
            if os.path.isdir(path):
                shutil.rmtree(path)
                found = True
        if remove_registry:
            registry.setdefault("items", {}).pop(extension_id, None)
            self._save_registry(registry)
        return found

    def get_extension_dir(self, ext_type: str, extension_id: str, create_parent: bool = False) -> str:
        ext_type = self.normalize_type(ext_type)
        if not ext_type:
            raise ExtensionError("Unknown add-on type")
        extension_id = str(extension_id or "").strip().lower()
        self._validate_extension_id(extension_id)
        parent = os.path.join(self.get_root_dir(create=create_parent), self.TYPE_DIRS[ext_type])
        if create_parent:
            os.makedirs(parent, exist_ok=True)
        return os.path.join(parent, extension_id)

    # STATIC EXTENSIONS ------------------------------------------------

    def _check_static_conflicts(self, manifest: dict, source: str):
        ext_type = manifest["type"]
        workdir = self.window.core.config.get_user_path()
        registry = self._load_registry().get("items", {})
        owned = registry.get(manifest["id"], {}).get("deployed", []) if isinstance(registry, dict) else []
        owned_abs = {os.path.realpath(os.path.join(workdir, p)) for p in owned}
        if ext_type == "theme":
            target = os.path.realpath(os.path.join(workdir, "css", manifest["id"]))
            if os.path.exists(target) and target not in owned_abs:
                raise ExtensionError(f"Theme destination already exists: {target}")
        elif ext_type == "locale":
            src = os.path.join(source, "locale") if os.path.isdir(os.path.join(source, "locale")) else source
            for path in Path(src).glob("*.ini"):
                target = os.path.realpath(os.path.join(workdir, "locale", path.name))
                if os.path.exists(target) and target not in owned_abs:
                    raise ExtensionError(f"Locale destination already exists: {target}")

    def _deploy_static(self, manifest: dict) -> List[str]:
        ext_type = manifest["type"]
        if ext_type not in self.STATIC_TYPES:
            return []
        root = manifest["_path"]
        workdir = os.path.abspath(self.window.core.config.get_user_path())
        deployed: List[str] = []
        try:
            if ext_type == "theme":
                source = os.path.join(root, "theme") if os.path.isdir(os.path.join(root, "theme")) else root
                files = [name for name in ("app.css", "app.xml", "chat.css") if os.path.isfile(os.path.join(source, name))]
                if not files:
                    raise ExtensionError("Theme add-on contains no app.css, app.xml or chat.css")
                destination = os.path.join(workdir, "css", manifest["id"])
                rel = os.path.relpath(destination, workdir).replace(os.sep, "/")
                deployed.append(rel)
                os.makedirs(destination, exist_ok=True)
                for name in files:
                    shutil.copy2(os.path.join(source, name), os.path.join(destination, name))
            elif ext_type == "locale":
                source = os.path.join(root, "locale") if os.path.isdir(os.path.join(root, "locale")) else root
                destination = os.path.join(workdir, "locale")
                os.makedirs(destination, exist_ok=True)
                files = list(Path(source).glob("*.ini"))
                if not files:
                    raise ExtensionError("Locale add-on contains no .ini files")
                for src in files:
                    dst = os.path.join(destination, src.name)
                    rel = os.path.relpath(dst, workdir).replace(os.sep, "/")
                    deployed.append(rel)
                    shutil.copy2(str(src), dst)
            return deployed
        except Exception:
            self._remove_deployed(deployed)
            raise

    def _remove_deployed(self, deployed: Iterable[str]):
        workdir = os.path.realpath(self.window.core.config.get_user_path())
        allowed_roots = (
            os.path.realpath(os.path.join(workdir, "css")),
            os.path.realpath(os.path.join(workdir, "locale")),
        )
        for relative in deployed:
            path = os.path.realpath(os.path.join(workdir, str(relative)))
            if not any(self._is_inside(path, root) and path != root for root in allowed_roots):
                self._warn(f"Ignoring unsafe deployed add-on asset path: {relative}")
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
            except OSError as exc:
                self._warn(f"Cannot remove deployed add-on asset {path}: {exc}")

    # RUNTIME LOADING --------------------------------------------------

    def sync_static_extensions(self):
        registry = self._load_registry()
        changed = False
        installed = self.list_installed()
        installed_keys = {(manifest["id"], manifest["type"]) for manifest in installed}

        # Reconcile manually removed static packages. Otherwise their mirrored
        # css/locale files would remain active even though the extension no longer
        # exists under %workdir%/addons.
        items = registry.setdefault("items", {})
        for extension_id, meta in list(items.items()):
            if not isinstance(meta, dict) or meta.get("type") not in self.STATIC_TYPES:
                continue
            if (extension_id, meta.get("type")) in installed_keys:
                continue
            self._remove_deployed(meta.get("deployed") or [])
            items.pop(extension_id, None)
            changed = True

        for manifest in installed:
            if manifest["type"] not in self.STATIC_TYPES or not manifest.get("_compatible", False):
                continue
            try:
                self._check_static_conflicts(manifest, manifest["_path"])
                old = registry.setdefault("items", {}).get(manifest["id"], {})
                self._remove_deployed(old.get("deployed") or [])
                deployed = self._deploy_static(manifest)
                meta = dict(old)
                meta.update({
                    "type": manifest["type"],
                    "source": meta.get("source") or "manual",
                    "trusted": bool(meta.get("trusted", False)),
                    "official": bool(meta.get("official", False)),
                    "deployed": deployed,
                })
                registry["items"][manifest["id"]] = meta
                changed = True
            except Exception as exc:
                self._warn(f"Failed to deploy static add-on '{manifest['id']}': {exc}")
        if changed:
            self._save_registry(registry)

    def load_into_launcher(self, launcher) -> List[dict]:
        # Theme/locale extensions are mirrored into the existing profile CSS/locale
        # locations so they use the normal built-in discovery paths. This also makes
        # manually copied extension directories work without going through the UI.
        self.sync_static_extensions()
        loaded = []
        addon_log_started = False
        for manifest in self.list_installed():
            ext_type = manifest["type"]
            if ext_type not in self.RUNTIME_TYPES:
                continue
            if not manifest.get("_compatible", False):
                self._warn(
                    f"Skipping add-on '{manifest['id']}': requires PyGPT >= {manifest['min_app_version']}"
                )
                continue
            try:
                objects = self._load_entrypoints(manifest)
                self._validate_runtime_objects(ext_type, objects)
                register = getattr(launcher, self.RUNTIME_TYPES[ext_type])
                for obj in objects:
                    register(obj)
                self._loaded_objects[manifest["id"]] = objects
                loaded.append(manifest)
                if not addon_log_started:
                    print()
                    addon_log_started = True
                print(f"[Add-ons] Loaded {ext_type}: {manifest['id']} ({manifest['version']})")
            except Exception as exc:
                self._warn(f"Failed to load add-on '{manifest['id']}': {exc}")
        if addon_log_started:
            print()
        return loaded

    @staticmethod
    def _validate_runtime_objects(ext_type: str, objects: list):
        # Import lazily so discovery/manifest management itself has no dependency
        # on provider/UI modules. At runtime these are the same classes Launcher uses.
        from pygpt_net.plugin.base.plugin import BasePlugin
        from pygpt_net.provider.agents.base import BaseAgent
        from pygpt_net.provider.audio_input.base import BaseProvider as BaseAudioInput
        from pygpt_net.provider.audio_output.base import BaseProvider as BaseAudioOutput
        from pygpt_net.provider.llms.base import BaseLLM
        from pygpt_net.provider.loaders.base import BaseLoader
        from pygpt_net.provider.vector_stores.base import BaseStore
        from pygpt_net.provider.web.base import BaseProvider as BaseWeb
        from pygpt_net.tools import BaseTool

        expected = {
            "plugin": BasePlugin,
            "llm": BaseLLM,
            "vector_store": BaseStore,
            "loader": BaseLoader,
            "audio_input": BaseAudioInput,
            "audio_output": BaseAudioOutput,
            "web": BaseWeb,
            "tool": BaseTool,
            "agent": BaseAgent,
        }[ext_type]
        if not objects:
            raise ExtensionError("Entrypoint returned no add-on objects")
        for obj in objects:
            if not isinstance(obj, expected):
                raise ExtensionError(
                    f"Entrypoint returned {type(obj).__name__}; expected {expected.__module__}.{expected.__name__}"
                )

    def _load_entrypoints(self, manifest: dict) -> list:
        value = manifest["entrypoint"]
        entries = [value] if isinstance(value, str) else list(value)
        objects = []
        for entry in entries:
            module_ref, symbol = entry.rsplit(":", 1)
            module = self._load_external_module(manifest, module_ref.strip())
            target = getattr(module, symbol.strip())
            if isinstance(target, type):
                target = target()
            elif callable(target):
                target = target()
            if isinstance(target, (list, tuple)):
                objects.extend(target)
            else:
                objects.append(target)
        return objects

    def _load_external_module(self, manifest: dict, module_ref: str):
        root = os.path.realpath(manifest["_path"])
        relative = module_ref.replace("\\", "/")
        if relative.endswith(".py"):
            relative = relative[:-3]
        relative = relative.replace(".", "/") if "/" not in relative else relative
        candidate = os.path.realpath(os.path.join(root, relative + ".py"))
        package_init = os.path.realpath(os.path.join(root, relative, "__init__.py"))
        if os.path.isfile(candidate):
            path = candidate
        elif os.path.isfile(package_init):
            path = package_init
        else:
            raise ExtensionError(f"Entrypoint module not found: {module_ref}")
        if not self._is_inside(path, root):
            raise ExtensionError("Entrypoint escapes add-on directory")

        digest = hashlib.sha256(root.encode("utf-8")).hexdigest()[:12]
        package_name = f"pygpt_ext_{self._safe_module_part(manifest['id'])}_{digest}"
        self._ensure_namespace(package_name, root)
        parts = [self._safe_module_part(p) for p in relative.split("/") if p]
        module_name = package_name + ("." + ".".join(parts) if parts else "")
        parent_dir = root
        prefix = package_name
        for raw, safe in zip(relative.split("/")[:-1], parts[:-1]):
            parent_dir = os.path.join(parent_dir, raw)
            prefix += "." + safe
            self._ensure_namespace(prefix, parent_dir)
        cached = self._module_cache.get(module_name)
        if cached is not None:
            return cached
        existing = sys.modules.get(module_name)
        if existing is not None:
            self._module_cache[module_name] = existing
            return existing

        spec = importlib.util.spec_from_file_location(
            module_name,
            path,
            submodule_search_locations=[os.path.dirname(path)] if path.endswith("__init__.py") else None,
        )
        if spec is None or spec.loader is None:
            raise ExtensionError(f"Cannot create import spec for {module_ref}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        self._module_cache[module_name] = module
        self._loaded_modules[manifest["id"]] = module_name
        return module

    @staticmethod
    def _safe_module_part(value: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9_]", "_", str(value))
        if not value or value[0].isdigit():
            value = "_" + value
        return value

    @staticmethod
    def _ensure_namespace(name: str, path: str):
        if name in sys.modules:
            return
        module = types.ModuleType(name)
        module.__path__ = [path]
        module.__package__ = name
        sys.modules[name] = module

    # CATALOG ----------------------------------------------------------

    def fetch_registry(self, url: Optional[str] = None) -> List[dict]:
        target = str(url or self.get_registry_url()).strip()
        if not target:
            target = self.DEFAULT_REGISTRY_URL
        is_official_registry = self._is_official_registry_url(target)
        raw = self._download_bytes(self._normalize_registry_url(target), self.MAX_REGISTRY_BYTES)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ExtensionError(f"Invalid add-ons registry JSON: {exc}") from exc
        entries = data.get("addons") if isinstance(data, dict) else None
        if not isinstance(entries, list) and isinstance(data, dict):
            entries = data.get("extensions")  # legacy catalog schema
        if not isinstance(entries, list):
            raise ExtensionError("Add-ons registry must contain an 'addons' array")
        result = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            item = dict(entry)
            ext_id = str(item.get("id") or "").strip().lower()
            ext_type = self.normalize_type(item.get("type"))
            source_url = str(item.get("github_url") or item.get("url") or "").strip()
            source_path = str(item.get("github_path") or item.get("path") or "").strip()
            if (not ext_id or not self._ID_RE.fullmatch(ext_id) or not ext_type
                    or not str(item.get("name") or "").strip()
                    or not str(item.get("description") or "").strip()
                    or not str(item.get("author") or "").strip()
                    or not str(item.get("version") or "").strip()
                    or (not source_url and not source_path)):
                self._warn(f"Skipping invalid registry entry: {item.get('name') or item.get('id') or '<unnamed>'}")
                continue
            try:
                Version(str(item["version"]))
            except InvalidVersion:
                self._warn(f"Skipping registry entry with invalid version: {item.get('name') or ext_id}")
                continue
            item["id"] = ext_id
            item["type"] = ext_type
            if is_official_registry:
                item["trusted"] = item.get("trusted") is True
                item["official"] = item.get("official") is True
            else:
                # A custom catalog is untrusted by definition. Never allow it to
                # self-assert trust/official status for entries shown in Explore
                # or persisted later during installation.
                item["trusted"] = False
                item["official"] = False
            result.append(item)
        return result

    @classmethod
    def _is_official_registry_url(cls, url: str) -> bool:
        return cls._normalize_registry_url(str(url or "").strip()) == cls._normalize_registry_url(
            cls.DEFAULT_REGISTRY_URL
        )

    @staticmethod
    def _normalize_registry_url(url: str) -> str:
        """Accept the short github.com/owner/repo/file.json form used by PyGPT registries."""
        parsed = urlparse(url)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            return url
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 3 and parts[2].lower().endswith(".json"):
            return f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/main/{parts[2]}"
        if len(parts) >= 5 and parts[2] == "blob":
            return "https://raw.githubusercontent.com/{}/{}/{}/{}".format(
                parts[0], parts[1], parts[3], "/".join(parts[4:])
            )
        return url

    # HELPERS ----------------------------------------------------------

    @classmethod
    def _validate_extension_id(cls, extension_id: str):
        if not extension_id or not cls._ID_RE.fullmatch(extension_id):
            raise ExtensionError("Invalid add-on id")

    @staticmethod
    def _validate_entrypoint(entrypoint: str):
        if not isinstance(entrypoint, str) or entrypoint.count(":") != 1:
            raise ExtensionManifestError("entrypoint must use 'module.py:ClassOrFactory' syntax")
        module_ref, symbol = (part.strip() for part in entrypoint.split(":", 1))
        if not module_ref or not symbol:
            raise ExtensionManifestError("entrypoint module and symbol may not be empty")
        normalized = module_ref.replace("\\", "/")
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            raise ExtensionManifestError("entrypoint module must be relative to the add-on directory")
        parts = [part for part in normalized.split("/") if part]
        if any(part in {".", ".."} for part in parts):
            raise ExtensionManifestError("entrypoint module may not contain '.' or '..' path segments")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", symbol):
            raise ExtensionManifestError("entrypoint symbol must be a valid Python identifier")

    @staticmethod
    def _safe_extract_zip(archive: zipfile.ZipFile, destination: str):
        root = os.path.realpath(destination)
        total = 0
        members = archive.infolist()
        if len(members) > Extensions.MAX_ARCHIVE_FILES:
            raise ExtensionError(f"ZIP archive contains too many entries (limit: {Extensions.MAX_ARCHIVE_FILES})")
        for info in members:
            name = info.filename.replace("\\", "/")
            if not name:
                continue
            if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
                raise ExtensionError(f"Unsafe absolute ZIP entry: {info.filename}")
            target = os.path.realpath(os.path.join(root, name))
            if not Extensions._is_inside(target, root):
                raise ExtensionError(f"Unsafe ZIP entry: {info.filename}")
            # Reject Unix symlink entries and bound uncompressed archive size.
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ExtensionError(f"ZIP symlinks are not allowed: {info.filename}")
            total += int(info.file_size or 0)
            if total > Extensions.MAX_DOWNLOAD_BYTES:
                raise ExtensionError("Unpacked add-on exceeds the 256 MB safety limit")
        archive.extractall(destination)

    @staticmethod
    def _validate_source_tree(source: str):
        root = os.path.realpath(source)
        total = 0
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            for name in list(dirnames) + list(filenames):
                path = os.path.join(dirpath, name)
                if os.path.islink(path):
                    raise ExtensionError(f"Add-on packages may not contain symlinks: {path}")
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    total += os.path.getsize(path)
                except OSError as exc:
                    raise ExtensionError(f"Cannot read add-on file: {path}: {exc}") from exc
                if total > Extensions.MAX_DOWNLOAD_BYTES:
                    raise ExtensionError("Add-on package exceeds the 256 MB safety limit")

    def _find_manifest_root(self, root: str) -> str:
        direct = os.path.join(root, self.MANIFEST_FILENAME)
        if os.path.isfile(direct):
            return root
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # ZIP/GitHub archives commonly add one or more wrapper directories.
            # Accept any depth only when the package contains exactly one manifest;
            # monorepos with multiple extensions must select an explicit GitHub path.
            dirnames[:] = [
                name for name in dirnames
                if not os.path.islink(os.path.join(dirpath, name))
            ]
            if self.MANIFEST_FILENAME in filenames:
                candidates.append(dirpath)
        if len(candidates) != 1:
            raise ExtensionManifestError(
                f"Expected exactly one {self.MANIFEST_FILENAME} in archive/repository; "
                "select an explicit add-on directory for multi-add-on repositories"
            )
        return candidates[0]

    def _download_bytes(self, url: str, limit: int) -> bytes:
        req = Request(url, headers={"User-Agent": f"PyGPT/{__version__}"})
        try:
            with urlopen(req, timeout=30) as response:
                length = response.headers.get("Content-Length")
                if length and int(length) > limit:
                    raise ExtensionError("Download is too large")
                data = response.read(limit + 1)
        except (HTTPError, URLError, OSError) as exc:
            raise ExtensionError(f"Download failed: {exc}") from exc
        if len(data) > limit:
            raise ExtensionError("Download is too large")
        return data

    def _parse_github_url(self, url: str) -> Tuple[str, str, str, str]:
        parsed = urlparse(str(url or "").strip())
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise ExtensionError("Only github.com repository URLs are supported")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ExtensionError("Invalid GitHub URL")
        owner, repo = parts[0], parts[1].removesuffix(".git")
        ref = ""
        subpath = ""
        if len(parts) >= 4 and parts[2] in {"tree", "blob"}:
            ref = parts[3]
            subpath = "/".join(parts[4:])
        elif len(parts) > 2:
            # Also accept a repository URL followed directly by a repository-relative
            # path, e.g. github.com/owner/repo/examples/plugins/example_plugin.
            # In this form the repository default branch is used.
            subpath = "/".join(parts[2:])
        return owner, repo, ref, subpath

    def _github_default_branch(self, owner: str, repo: str) -> str:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            raw = self._download_bytes(url, 1024 * 1024)
            return str(json.loads(raw.decode("utf-8")).get("default_branch") or "main")
        except Exception as exc:
            self._warn(f"Could not resolve GitHub default branch for {owner}/{repo}; using main: {exc}")
            return "main"

    @staticmethod
    def _is_inside(path: str, root: str) -> bool:
        try:
            return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == os.path.realpath(root)
        except (ValueError, OSError):
            return False

    def _warn(self, message: str):
        text = f"[Add-ons] WARNING: {message}"
        print(text)
        try:
            if self.window is not None and getattr(self.window.core, "debug", None) is not None:
                self.window.core.debug.log(text)
        except Exception:
            pass
