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

import os
import stat
import sys
from urllib.parse import urlsplit, urlunsplit

from pygpt_net.core.auto_updater import (
    AUTO_UPDATER_APPIMAGE_FILENAME,
    AUTO_UPDATER_APPIMAGE_URL,
    AUTO_UPDATER_GITHUB_HOSTS,
    AUTO_UPDATER_GITHUB_OWNER,
    AUTO_UPDATER_GITHUB_REPO,
)
from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.downloader import Downloader
from pygpt_net.core.auto_updater.helpers import appimage_arch, schedule_appimage_swap_after_exit
from pygpt_net.utils import trans


def appimage_release_url(version: str, arch: str) -> str:
    """Return the canonical GitHub Releases asset URL for an AppImage."""
    return AUTO_UPDATER_APPIMAGE_URL.format(version=version, arch=arch)


def normalize_appimage_url(url: str, version: str, arch: str) -> str:
    """
    Normalize updater/API AppImage URLs to a concrete binary asset.

    The version API may return the repository releases page instead of a
    release asset. A browser page such as ``.../releases`` is never a valid
    updater payload and, with ``Accept: application/octet-stream``, GitHub may
    answer it with HTTP 406. For the official PyGPT GitHub repository convert
    releases/list/latest/tag URLs to the deterministic asset name produced by
    the release workflow.
    """
    fallback = appimage_release_url(version, arch)
    url = str(url or "").strip()
    if not url:
        return fallback

    try:
        parsed = urlsplit(url)
    except Exception:
        return fallback

    host = parsed.netloc.lower()
    path = parsed.path or ""
    lower_path = path.lower()

    if host in AUTO_UPDATER_GITHUB_HOSTS:
        repo_prefix = f"/{AUTO_UPDATER_GITHUB_OWNER}/{AUTO_UPDATER_GITHUB_REPO}/releases"
        lower_prefix = repo_prefix.lower()
        # A generic releases/list/latest/tag URL points to HTML, not an asset.
        if lower_path.rstrip("/") == lower_prefix \
                or lower_path.rstrip("/") == lower_prefix + "/latest" \
                or lower_path.startswith(lower_prefix + "/tag/"):
            return fallback

    # Exact asset URLs are preserved, but normalize the architecture token so
    # an API value for x86_64 cannot be used on aarch64 and vice versa.
    normalized_path = path
    for token in ("x86_64", "aarch64", "amd64", "arm64"):
        if token in normalized_path:
            normalized_path = normalized_path.replace(token, arch)
            break

    # The .zsync file is metadata for AppImageUpdate; the in-app updater needs
    # the actual ELF AppImage binary.
    if normalized_path.endswith(".AppImage.zsync"):
        normalized_path = normalized_path[:-len(".zsync")]

    return urlunsplit((
        parsed.scheme,
        parsed.netloc,
        normalized_path,
        parsed.query,
        parsed.fragment,
    ))


class AppImageUpdateFlow(BaseUpdateFlow):
    id = "appimage"

    def run(self) -> UpdateResult:
        version = self.payload.version
        current = os.environ.get("APPIMAGE") or sys.executable
        current = os.path.abspath(current)
        directory = os.path.dirname(current)
        self.log(f"Flow started: version={version!r}, current_appimage={current!r}, install_dir={directory!r}.")
        if not os.access(directory, os.W_OK):
            self.log(f"Install directory is not writable: {directory!r}.")
            raise UpdateError(trans("update.auto.error.install_not_writable").format(path=directory))

        raw_arch = self.window.core.platforms.get_architecture()
        arch = appimage_arch(raw_arch)
        self.log(f"Architecture resolved: raw={raw_arch!r}, appimage_arch={arch!r}.")

        input_url = self.payload.download_appimage
        self.log(f"Initial AppImage URL from update payload: {input_url!r}.")
        url = normalize_appimage_url(input_url, version, arch)
        if url != str(input_url or "").strip():
            self.log(
                f"Normalized AppImage URL to concrete release asset: "
                f"input={input_url!r}, final={url!r}."
            )
        else:
            self.log(f"AppImage URL already points to a concrete asset: {url!r}.")

        if not self.context.confirm(
                trans("update.auto.confirm.download.title"),
                trans("update.auto.confirm.download").format(version=version)):
            self.log("Download confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        # Stage the new binary under its target-version filename.  The
        # currently running AppImage may contain the old version in its name
        # (e.g. PyGPT-2.8.30-...).  Keeping the staged/final path separate
        # ensures a successful update ends up as PyGPT-<new version>-<arch>.AppImage
        # instead of silently replacing the contents of the old-version name.
        target = os.path.join(
            directory,
            AUTO_UPDATER_APPIMAGE_FILENAME.format(version=version, arch=arch),
        )
        staged = target + ".update"
        self.log(
            f"AppImage paths resolved: current={current!r}, target={target!r}, "
            f"staged={staged!r}."
        )
        self.log(f"Downloading new AppImage to staged path: {staged!r}.")
        Downloader(self.context).download(
            url,
            staged,
            "update.auto.status.downloading",
            binary=True,
            expected_magic=b"\x7fELF",
        )
        mode = os.stat(staged).st_mode
        os.chmod(staged, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.log(f"Downloaded AppImage chmod +x applied: {staged!r}.")

        if not self.context.confirm(
                trans("update.auto.confirm.restart.title"),
                trans("update.auto.confirm.restart.apply").format(version=version)):
            self.log("Restart/apply confirmation declined; removing staged AppImage.")
            try:
                os.remove(staged)
                self.log(f"Removed staged AppImage: {staged!r}.")
            except OSError as exc:
                self.log(f"Unable to remove staged AppImage {staged!r}: {exc}")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        try:
            args = list(sys.argv[1:])
            self.log(f"Scheduling post-exit AppImage swap; args={args!r}.")
            helper = schedule_appimage_swap_after_exit(
                current,
                staged,
                args,
                target_path=target,
                debug=self.context.debug_enabled,
            )
            self.log(f"Post-exit AppImage helper scheduled: {helper!r}.")
        except Exception as exc:
            self.log(f"Unable to schedule AppImage swap: {type(exc).__name__}: {exc}")
            try:
                os.remove(staged)
                self.log(f"Removed staged AppImage after scheduling failure: {staged!r}.")
            except OSError as cleanup_exc:
                self.log(f"Unable to remove staged AppImage after failure: {cleanup_exc}")
            raise

        # Do not request QApplication shutdown from the worker thread.
        # Returning quit_app=True hands shutdown back to AutoUpdater._on_finished(),
        # which executes on the Qt main thread and follows the normal app exit path.
        return UpdateResult(
            success=True,
            message=trans("update.auto.status.restart_pending"),
            quit_app=True,
        )
