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

from typing import TYPE_CHECKING

from .base import UpdatePayload, UpdateResult, UpdateError, UpdateCancelled


# Global kill switch for the in-app automatic update mechanism.
# Set to False to keep version checking/manual update information only.
AUTO_UPDATER_ENABLED = True

# Per-distribution kill switches. These only disable the automatic procedure
# for the selected installation type; version checking and manual update info
# remain available.
DISABLE_AUTO_UPDATE_WINDOWS_MSI = True
DISABLE_AUTO_UPDATE_LINUX_ARCHIVE = False
DISABLE_AUTO_UPDATE_APPIMAGE = False
DISABLE_AUTO_UPDATE_PIP = False
DISABLE_AUTO_UPDATE_SOURCE_GIT = False
DISABLE_AUTO_UPDATE_SOURCE_ZIP = False
DISABLE_AUTO_UPDATE_SNAP = False

# Central update endpoints, package identifiers and artifact names.
# Keep external update locations here so changing the release/download
# infrastructure does not require editing individual update flows.
AUTO_UPDATER_GITHUB_OWNER = "szczyglis-dev"
AUTO_UPDATER_GITHUB_REPO = "py-gpt"
AUTO_UPDATER_GITHUB_HOSTS = ("github.com", "www.github.com")
AUTO_UPDATER_GITHUB_API_BASE_URL = "https://api.github.com"
AUTO_UPDATER_GITHUB_REPO_URL = (
    f"https://github.com/{AUTO_UPDATER_GITHUB_OWNER}/{AUTO_UPDATER_GITHUB_REPO}"
)
AUTO_UPDATER_DOWNLOAD_BASE_URL = "https://pygpt.net/download"
AUTO_UPDATER_PYPI_PACKAGE = "pygpt-net"
AUTO_UPDATER_PACKAGE_DIR = "pygpt_net"

AUTO_UPDATER_WINDOWS_MSI_FILENAME = "pygpt-{version}.msi"
AUTO_UPDATER_LINUX_ARCHIVE_FILENAME = "pygpt-{version}.zip"
AUTO_UPDATER_SOURCE_ARCHIVE_FILENAME = "pygpt-source-{version}.zip"
AUTO_UPDATER_APPIMAGE_FILENAME = "PyGPT-{version}-{arch}.AppImage"

AUTO_UPDATER_WINDOWS_MSI_URL = (
    AUTO_UPDATER_DOWNLOAD_BASE_URL + "/{version}/" + AUTO_UPDATER_WINDOWS_MSI_FILENAME
)
AUTO_UPDATER_LINUX_ARCHIVE_URL = (
    AUTO_UPDATER_DOWNLOAD_BASE_URL + "/{version}/" + AUTO_UPDATER_LINUX_ARCHIVE_FILENAME
)
AUTO_UPDATER_SOURCE_ZIP_URL = (
    AUTO_UPDATER_GITHUB_REPO_URL + "/archive/refs/tags/v{version}.zip"
)
AUTO_UPDATER_APPIMAGE_URL = (
    AUTO_UPDATER_GITHUB_REPO_URL
    + "/releases/download/v{version}/"
    + AUTO_UPDATER_APPIMAGE_FILENAME
)


if TYPE_CHECKING:
    from .manager import AutoUpdater


def is_auto_update_method_enabled(kind: str) -> bool:
    """Return whether the automatic updater is enabled for a distribution kind."""
    disabled = {
        "windows_msi": DISABLE_AUTO_UPDATE_WINDOWS_MSI,
        "linux_archive": DISABLE_AUTO_UPDATE_LINUX_ARCHIVE,
        "appimage": DISABLE_AUTO_UPDATE_APPIMAGE,
        "pip": DISABLE_AUTO_UPDATE_PIP,
        "source": DISABLE_AUTO_UPDATE_SOURCE_GIT,
        "source_manual": DISABLE_AUTO_UPDATE_SOURCE_ZIP,
        "snap": DISABLE_AUTO_UPDATE_SNAP,
    }
    return not bool(disabled.get(str(kind or ""), False))


__all__ = [
    "AUTO_UPDATER_ENABLED",
    "AUTO_UPDATER_GITHUB_OWNER",
    "AUTO_UPDATER_GITHUB_REPO",
    "AUTO_UPDATER_GITHUB_HOSTS",
    "AUTO_UPDATER_GITHUB_API_BASE_URL",
    "AUTO_UPDATER_GITHUB_REPO_URL",
    "AUTO_UPDATER_DOWNLOAD_BASE_URL",
    "AUTO_UPDATER_PYPI_PACKAGE",
    "AUTO_UPDATER_PACKAGE_DIR",
    "AUTO_UPDATER_WINDOWS_MSI_FILENAME",
    "AUTO_UPDATER_LINUX_ARCHIVE_FILENAME",
    "AUTO_UPDATER_SOURCE_ARCHIVE_FILENAME",
    "AUTO_UPDATER_APPIMAGE_FILENAME",
    "AUTO_UPDATER_WINDOWS_MSI_URL",
    "AUTO_UPDATER_LINUX_ARCHIVE_URL",
    "AUTO_UPDATER_SOURCE_ZIP_URL",
    "AUTO_UPDATER_APPIMAGE_URL",
    "DISABLE_AUTO_UPDATE_WINDOWS_MSI",
    "DISABLE_AUTO_UPDATE_LINUX_ARCHIVE",
    "DISABLE_AUTO_UPDATE_APPIMAGE",
    "DISABLE_AUTO_UPDATE_PIP",
    "DISABLE_AUTO_UPDATE_SOURCE_GIT",
    "DISABLE_AUTO_UPDATE_SOURCE_ZIP",
    "DISABLE_AUTO_UPDATE_SNAP",
    "is_auto_update_method_enabled",
    "AutoUpdater",
    "UpdatePayload",
    "UpdateResult",
    "UpdateError",
    "UpdateCancelled",
]


def __getattr__(name):
    # Keep the package lightweight for helper/test imports. Qt is only required
    # when the actual UI coordinator is requested by the application core.
    if name == "AutoUpdater":
        from .manager import AutoUpdater
        return AutoUpdater
    raise AttributeError(name)
