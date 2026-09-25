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

import os
import shutil
import sys
import tempfile
from pathlib import Path

from pygpt_net.core.auto_updater import (
    AUTO_UPDATER_PACKAGE_DIR,
    AUTO_UPDATER_SOURCE_ARCHIVE_FILENAME,
    AUTO_UPDATER_SOURCE_ZIP_URL,
)
from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.downloader import Downloader
from pygpt_net.core.auto_updater.helpers import (
    clear_path,
    current_restart_command,
    safe_extract_zip,
    schedule_source_package_swap_after_exit,
)
from pygpt_net.utils import trans


PACKAGE_DIR = AUTO_UPDATER_PACKAGE_DIR


def github_source_zip_url(version: str) -> str:
    """Return the source-code ZIP behind the matching GitHub release tag."""
    version = str(version or "").strip().lstrip("v")
    return AUTO_UPDATER_SOURCE_ZIP_URL.format(version=version)


class SourceArchiveUpdateFlow(BaseUpdateFlow):
    """Update a manually unpacked/source-ZIP PyGPT installation."""

    id = "source_archive"

    def __init__(self, window, payload, context, source_root: str):
        super().__init__(window, payload, context)
        self.source_root = os.path.abspath(source_root or "")

    def _current_package_dir(self) -> str:
        candidate = os.path.join(self.source_root, PACKAGE_DIR)
        if os.path.isdir(candidate):
            return candidate

        app_path = os.path.abspath(self.window.core.config.get_app_path())
        if os.path.basename(app_path) == PACKAGE_DIR and os.path.isdir(app_path):
            return app_path
        raise UpdateError(
            f"Unable to locate current {PACKAGE_DIR!r} package directory for source ZIP update"
        )

    def _find_downloaded_package(self, extracted_root: str) -> str:
        candidates = []
        for dirpath, dirnames, filenames in os.walk(extracted_root):
            self.context.check_cancelled()
            if os.path.basename(dirpath) != PACKAGE_DIR or "__init__.py" not in filenames:
                continue
            path = Path(dirpath)
            score = 0
            if path.parent.name == "src":
                score += 20
            if (path / "data").is_dir():
                score += 5
            if (path / "core").is_dir():
                score += 5
            score -= len(path.parts)
            candidates.append((score, dirpath))
            self.log(f"Downloaded source package candidate: path={dirpath!r}, score={score}.")

        if not candidates:
            raise UpdateError(f"Downloaded source ZIP does not contain {PACKAGE_DIR}/__init__.py")
        candidates.sort(reverse=True)
        selected = candidates[0][1]
        self.log(f"Selected downloaded source package: {selected!r}.")
        return selected

    @staticmethod
    def _find_requirements(package_dir: str, extracted_root: str) -> str:
        root = Path(extracted_root).resolve()
        current = Path(package_dir).resolve().parent
        while True:
            candidate = current / "requirements.txt"
            if candidate.is_file():
                return str(candidate)
            if current == root or root not in current.parents:
                break
            current = current.parent
        return ""

    def run(self) -> UpdateResult:
        version = str(self.payload.version or "").strip()
        if not version:
            raise UpdateError("Missing target version for source ZIP update")

        url = github_source_zip_url(version)
        current_package = self._current_package_dir()
        package_parent = os.path.dirname(current_package)
        staged_package = current_package + ".update"
        self.log(
            f"Flow started: version={version!r}, source_root={self.source_root!r}, "
            f"current_package={current_package!r}, download_url={url!r}."
        )

        if not os.access(package_parent, os.W_OK):
            raise UpdateError(trans("update.auto.error.install_not_writable").format(path=package_parent))

        if not self.context.confirm(
                trans("update.auto.confirm.download.title"),
                trans("update.auto.confirm.download").format(version=version)):
            self.log("Source ZIP download confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        tmp_root = os.path.join(self.window.core.config.get_user_dir("tmp"), "updates")
        os.makedirs(tmp_root, exist_ok=True)
        archive_path = os.path.join(
            tmp_root,
            AUTO_UPDATER_SOURCE_ARCHIVE_FILENAME.format(version=version),
        )
        extract_dir = tempfile.mkdtemp(prefix=f"pygpt-source-{version}-", dir=tmp_root)
        self.log(f"Temporary archive={archive_path!r}; extract_dir={extract_dir!r}.")

        try:
            Downloader(self.context).download(
                url,
                archive_path,
                "update.auto.status.downloading",
                binary=True,
            )
            self.context.progress("update.auto.status.extracting", 0)
            safe_extract_zip(archive_path, extract_dir, self.context)
            downloaded_package = self._find_downloaded_package(extract_dir)

            self.context.progress("update.auto.status.staging", 0)
            if os.path.exists(staged_package) or os.path.islink(staged_package):
                clear_path(staged_package, self.context)
            self.log(f"Staging source package: {downloaded_package!r} -> {staged_package!r}.")
            shutil.copytree(downloaded_package, staged_package, symlinks=True)
            self.context.progress("update.auto.status.staging", 100)

            requirements = self._find_requirements(downloaded_package, extract_dir)
            self.log(f"Downloaded requirements file: {requirements!r}.")
            if requirements:
                pip_command = [sys.executable, "-m", "pip", "install", "-r", requirements]
                if self.context.confirm(
                        trans("update.auto.confirm.command.title"),
                        trans("update.auto.confirm.requirements").format(command=" ".join(pip_command))):
                    self.context.run_process(
                        pip_command,
                        status="update.auto.status.requirements",
                    )
                    self.log("Source ZIP dependency update completed successfully.")
                else:
                    self.log("Source ZIP dependency update skipped by user.")

            if not self.context.confirm(
                    trans("update.auto.confirm.restart.title"),
                    trans("update.auto.confirm.restart.apply").format(version=version)):
                self.log("Restart/apply confirmation declined; removing staged source package.")
                if os.path.exists(staged_package) or os.path.islink(staged_package):
                    clear_path(staged_package, self.context)
                return UpdateResult(success=False, message=trans("update.auto.ready.not_installed"))

            restart = current_restart_command()
            self.context.progress("update.auto.status.preparing", percent=None)
            self.log(f"Scheduling source package swap; restart_command={restart!r}.")
            helper = schedule_source_package_swap_after_exit(
                current_package,
                staged_package,
                restart,
                debug=self.context.debug_enabled,
                trace=self.context.log,
            )
            self.log(f"Post-exit source package swap helper scheduled: {helper!r}.")
            return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
        except Exception:
            # If handoff has not been scheduled, do not leave a stale staged
            # package that could be mistaken for a future update.
            if os.path.exists(staged_package) or os.path.islink(staged_package):
                try:
                    clear_path(staged_package, self.context)
                except Exception:
                    pass
            raise
        finally:
            self.log(f"Cleaning source ZIP extraction directory: {extract_dir!r}.")
            shutil.rmtree(extract_dir, ignore_errors=True)
            try:
                if os.path.exists(archive_path):
                    os.remove(archive_path)
            except OSError as exc:
                self.log(f"Source ZIP archive cleanup failed: {exc}")
