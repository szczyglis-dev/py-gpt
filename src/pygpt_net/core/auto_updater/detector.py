#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 20:00:00                  #
# ================================================== #

from __future__ import annotations

import importlib.metadata as importlib_metadata
import os
import site
import sysconfig
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from pygpt_net.core.auto_updater import AUTO_UPDATER_PACKAGE_DIR, AUTO_UPDATER_PYPI_PACKAGE
from pygpt_net.core.auto_updater.helpers import find_git_root


@dataclass(frozen=True)
class DistributionInfo:
    kind: str
    label: str
    source_root: Optional[str] = None


class DistributionDetector:
    """Detect how the running PyGPT instance is distributed."""

    PYPI_DISTRIBUTION = AUTO_UPDATER_PYPI_PACKAGE
    PACKAGE_DIR = AUTO_UPDATER_PACKAGE_DIR

    def __init__(self, window, log_cb: Optional[Callable[[str], None]] = None):
        self.window = window
        self._log_cb = log_cb

    def _log(self, message: str):
        try:
            if self._log_cb is not None:
                self._log_cb(f"[detector] {message}")
        except Exception:
            pass

    def detect(self) -> DistributionInfo:
        platforms = self.window.core.platforms
        config = self.window.core.config
        self._log("Starting installation-type detection.")

        if platforms.is_ms_store():
            self._log("Detected Microsoft Store environment.")
            return DistributionInfo("ms_store", "Microsoft Store")
        self._log("Microsoft Store: no.")

        if platforms.is_snap():
            self._log("Detected Snap environment.")
            return DistributionInfo("snap", "Snap")
        self._log("Snap: no.")

        appimage_env = os.environ.get("APPIMAGE")
        if platforms.is_appimage() or bool(appimage_env):
            self._log(f"Detected AppImage environment; APPIMAGE={appimage_env!r}.")
            return DistributionInfo("appimage", "AppImage")
        self._log("AppImage: no.")

        if platforms.is_flatpak():
            self._log("Detected Flatpak environment.")
            return DistributionInfo("flatpak", "Flatpak")
        self._log("Flatpak: no.")

        compiled = bool(config.is_compiled())
        self._log(f"Compiled/frozen build: {compiled}.")
        if compiled:
            if platforms.is_windows():
                self._log("Compiled Windows build -> Windows/MSI flow.")
                return DistributionInfo("windows_msi", "Windows / MSI")
            if platforms.is_linux():
                self._log("Compiled Linux build -> Linux/ZIP flow.")
                return DistributionInfo("linux_archive", "Linux / ZIP")
            self._log("Compiled build on unsupported platform.")
            return DistributionInfo("compiled_unsupported", "Standalone")

        app_path = os.path.abspath(config.get_app_path())
        self._log(f"Non-compiled application path: {app_path!r}.")

        # A real Git checkout always wins, including editable Python installs
        # made from that checkout. This keeps source development copies on the
        # git pull + requirements update path instead of treating them as PyPI.
        source_root = find_git_root(app_path)
        if source_root:
            self._log(f"Git metadata found: source_root={source_root!r} -> source/Git flow.")
            return DistributionInfo("source", "Git", source_root)
        self._log("No .git directory found in application path or its parents.")

        # Do not infer a pip installation merely because the package happens to
        # live under site-packages. Confirm that the currently running package
        # is the package owned by the installed `pygpt-net` distribution.
        if self._is_current_package_from_pypi_distribution(app_path):
            self._log("Current pygpt_net path matches installed pygpt-net distribution metadata -> pip flow.")
            return DistributionInfo("pip", "PyPI / pip")
        self._log("Current pygpt_net path does not match installed pygpt-net distribution metadata.")

        # A non-frozen copy without Git metadata and without matching PyPI
        # distribution metadata is a manually unpacked source tree (for
        # example a GitHub source ZIP). It must not run `pip install --upgrade`
        # against an unrelated package installation in the same environment.
        manual_root = self._manual_source_root(app_path)
        self._log(f"Falling back to manual source tree: source_root={manual_root!r}.")
        return DistributionInfo(
            "source_manual",
            "Source / ZIP",
            manual_root,
        )

    def _is_current_package_from_pypi_distribution(self, app_path: str) -> bool:
        """Return True only if `app_path` belongs to installed pygpt-net metadata."""
        self._log(f"Checking Python distribution metadata for {self.PYPI_DISTRIBUTION!r}.")
        try:
            dist = importlib_metadata.distribution(self.PYPI_DISTRIBUTION)
        except importlib_metadata.PackageNotFoundError:
            self._log("pygpt-net distribution metadata not found.")
            return False
        except Exception as exc:
            # Broken/partial metadata should never make us guess that a source
            # checkout is safe to update with pip.
            self._log(f"Unable to read pygpt-net distribution metadata: {type(exc).__name__}: {exc}")
            return False

        current = self._normalize_path(app_path)
        self._log(f"Normalized current package path: {current!r}.")

        # A regular pip installation must physically live in one of the
        # interpreter's package directories.  This extra guard matters when a
        # developer runs a manually copied/source ZIP tree with an interpreter
        # that also happens to have ``pygpt-net`` installed: importlib metadata
        # for that unrelated installation must not classify the source copy as
        # pip.  Editable installs/source trees outside site-packages therefore
        # stay on the source/manual path, which is the safer update behaviour.
        package_roots = self._python_package_roots()
        self._log(f"Interpreter package roots: {package_roots!r}.")
        if not any(self._path_is_within(current, root) for root in package_roots):
            self._log(
                "Current pygpt_net path is outside interpreter package roots "
                "-> not a regular pip installation."
            )
            return False

        candidates = set()

        try:
            located = self._normalize_path(dist.locate_file(self.PACKAGE_DIR))
            candidates.add(located)
            self._log(f"Metadata candidate from locate_file(): {located!r}.")
        except Exception as exc:
            self._log(f"locate_file({self.PACKAGE_DIR!r}) failed: {type(exc).__name__}: {exc}")

        # Some installers expose a useful file list even when locate_file() for
        # the package directory itself is not sufficient. Derive the package
        # root from any file that is explicitly owned by pygpt_net.
        try:
            for entry in dist.files or ():
                entry_path = Path(str(entry))
                parts = entry_path.parts
                if not parts or parts[0] != self.PACKAGE_DIR:
                    continue

                located = Path(dist.locate_file(entry))
                package_root = located
                for _ in range(max(0, len(parts) - 1)):
                    package_root = package_root.parent
                normalized = self._normalize_path(package_root)
                candidates.add(normalized)
                self._log(f"Metadata candidate derived from owned file {entry!s}: {normalized!r}.")
                break
        except Exception as exc:
            self._log(f"Unable to inspect distribution file list: {type(exc).__name__}: {exc}")

        matches = current in candidates
        self._log(f"PyPI path match result: {matches}; candidates={sorted(candidates)!r}.")
        return matches

    @staticmethod
    def _normalize_path(path) -> str:
        """Normalize paths for reliable comparisons across symlinks/platforms."""
        return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))

    @classmethod
    def _python_package_roots(cls) -> list[str]:
        """Return normalized package roots used by the running interpreter."""
        roots = set()

        try:
            for value in site.getsitepackages() or ():
                if value:
                    roots.add(cls._normalize_path(value))
        except Exception:
            pass

        try:
            user_site = site.getusersitepackages()
            if isinstance(user_site, (list, tuple, set)):
                values = user_site
            else:
                values = (user_site,)
            for value in values:
                if value:
                    roots.add(cls._normalize_path(value))
        except Exception:
            pass

        try:
            paths = sysconfig.get_paths() or {}
            for key in ("purelib", "platlib"):
                value = paths.get(key)
                if value:
                    roots.add(cls._normalize_path(value))
        except Exception:
            pass

        return sorted(roots)

    @classmethod
    def _path_is_within(cls, path: str, root: str) -> bool:
        """Return True when path is root itself or is located below root."""
        try:
            normalized_path = cls._normalize_path(path)
            normalized_root = cls._normalize_path(root)
            return os.path.commonpath((normalized_path, normalized_root)) == normalized_root
        except (TypeError, ValueError, OSError):
            # ValueError is expected for paths on different Windows drives.
            return False

    @staticmethod
    def _manual_source_root(app_path: str) -> str:
        """Return the likely project root for a manually unpacked source copy."""
        package_path = Path(app_path).resolve()
        if package_path.name == DistributionDetector.PACKAGE_DIR:
            return str(package_path.parent)
        return str(package_path)
