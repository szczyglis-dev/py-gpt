#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.metadata as importlib_metadata
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pygpt_net.core.auto_updater.helpers import find_git_root


@dataclass(frozen=True)
class DistributionInfo:
    kind: str
    label: str
    source_root: Optional[str] = None


class DistributionDetector:
    """Detect how the running PyGPT instance is distributed."""

    PYPI_DISTRIBUTION = "pygpt-net"
    PACKAGE_DIR = "pygpt_net"

    def __init__(self, window):
        self.window = window

    def detect(self) -> DistributionInfo:
        platforms = self.window.core.platforms
        config = self.window.core.config

        if platforms.is_ms_store():
            return DistributionInfo("ms_store", "Microsoft Store")
        if platforms.is_snap():
            return DistributionInfo("snap", "Snap")
        if platforms.is_appimage() or bool(os.environ.get("APPIMAGE")):
            return DistributionInfo("appimage", "AppImage")
        if platforms.is_flatpak():
            return DistributionInfo("flatpak", "Flatpak")

        if config.is_compiled():
            if platforms.is_windows():
                return DistributionInfo("windows_msi", "Windows / MSI")
            if platforms.is_linux():
                return DistributionInfo("linux_archive", "Linux / ZIP")
            return DistributionInfo("compiled_unsupported", "Standalone")

        app_path = os.path.abspath(config.get_app_path())

        # A real Git checkout always wins, including editable Python installs
        # made from that checkout. This keeps source development copies on the
        # git pull + requirements update path instead of treating them as PyPI.
        source_root = find_git_root(app_path)
        if source_root:
            return DistributionInfo("source", "Git", source_root)

        # Do not infer a pip installation merely because the package happens to
        # live under site-packages. Confirm that the currently running package
        # is the package owned by the installed `pygpt-net` distribution.
        if self._is_current_package_from_pypi_distribution(app_path):
            return DistributionInfo("pip", "PyPI / pip")

        # A non-frozen copy without Git metadata and without matching PyPI
        # distribution metadata is a manually unpacked source tree (for
        # example a GitHub source ZIP). It must not run `pip install --upgrade`
        # against an unrelated package installation in the same environment.
        return DistributionInfo(
            "source_manual",
            "Source / manual",
            self._manual_source_root(app_path),
        )

    @classmethod
    def _is_current_package_from_pypi_distribution(cls, app_path: str) -> bool:
        """Return True only if `app_path` belongs to installed pygpt-net metadata."""
        try:
            dist = importlib_metadata.distribution(cls.PYPI_DISTRIBUTION)
        except importlib_metadata.PackageNotFoundError:
            return False
        except Exception:
            # Broken/partial metadata should never make us guess that a source
            # checkout is safe to update with pip.
            return False

        current = cls._normalize_path(app_path)
        candidates = set()

        try:
            candidates.add(cls._normalize_path(dist.locate_file(cls.PACKAGE_DIR)))
        except Exception:
            pass

        # Some installers expose a useful file list even when locate_file() for
        # the package directory itself is not sufficient. Derive the package
        # root from any file that is explicitly owned by pygpt_net.
        try:
            for entry in dist.files or ():
                entry_path = Path(str(entry))
                parts = entry_path.parts
                if not parts or parts[0] != cls.PACKAGE_DIR:
                    continue

                located = Path(dist.locate_file(entry))
                package_root = located
                for _ in range(max(0, len(parts) - 1)):
                    package_root = package_root.parent
                candidates.add(cls._normalize_path(package_root))
                break
        except Exception:
            pass

        return current in candidates

    @staticmethod
    def _normalize_path(path) -> str:
        """Normalize paths for reliable comparisons across symlinks/platforms."""
        return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))

    @staticmethod
    def _manual_source_root(app_path: str) -> str:
        """Return the likely project root for a manually unpacked source copy."""
        package_path = Path(app_path).resolve()
        if package_path.name == DistributionDetector.PACKAGE_DIR:
            return str(package_path.parent)
        return str(package_path)
