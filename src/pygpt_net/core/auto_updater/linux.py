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
import shutil
import sys
import tempfile

from pygpt_net.core.auto_updater import AUTO_UPDATER_LINUX_ARCHIVE_FILENAME, AUTO_UPDATER_LINUX_ARCHIVE_URL
from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.downloader import Downloader
from pygpt_net.core.auto_updater.helpers import (
    clear_path,
    extract_update_archive,
    find_linux_payload,
    schedule_linux_swap_after_exit,
    stage_payload_with_update_suffix,
)
from pygpt_net.utils import trans


class LinuxArchiveUpdateFlow(BaseUpdateFlow):
    id = "linux_archive"

    def run(self) -> UpdateResult:
        version = self.payload.version
        url = self.payload.download_linux or AUTO_UPDATER_LINUX_ARCHIVE_URL.format(version=version)
        self.log(f"Flow started: version={version!r}, download_url={url!r}, executable={sys.executable!r}.")
        if not self.context.confirm(
                trans("update.auto.confirm.download.title"),
                trans("update.auto.confirm.download").format(version=version)):
            self.log("Download confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        tmp_root = os.path.join(self.window.core.config.get_user_dir("tmp"), "updates")
        os.makedirs(tmp_root, exist_ok=True)
        ext = ".zip" if ".zip" in url.lower() else ".tar.gz"
        archive_name = AUTO_UPDATER_LINUX_ARCHIVE_FILENAME.format(version=version) if ext == ".zip" else f"pygpt-{version}{ext}"
        archive_path = os.path.join(tmp_root, archive_name)
        self.log(f"Temporary update root={tmp_root!r}; archive_path={archive_path!r}.")
        Downloader(self.context).download(url, archive_path, "update.auto.status.downloading")

        extract_dir = tempfile.mkdtemp(prefix=f"pygpt-{version}-", dir=tmp_root)
        staged_names = []
        install_dir = os.path.dirname(os.path.abspath(sys.executable))
        self.log(f"Created extraction directory={extract_dir!r}; install_dir={install_dir!r}.")
        try:
            self.context.progress("update.auto.status.extracting", 0)
            extract_update_archive(archive_path, extract_dir, self.context)
            payload_root = find_linux_payload(extract_dir, self.context)
            self.log(f"Linux payload root selected: {payload_root!r}.")

            if not os.access(install_dir, os.W_OK):
                self.log(f"Install directory is not writable: {install_dir!r}.")
                raise UpdateError(trans("update.auto.error.install_not_writable").format(path=install_dir))

            self.context.progress("update.auto.status.staging", 0)
            staged_names = stage_payload_with_update_suffix(payload_root, install_dir, self.context)
            self.log(f"Staged payload names: {staged_names!r}.")
            if "pygpt" not in staged_names:
                raise UpdateError("Linux update payload does not contain top-level 'pygpt'")

            if not self.context.confirm(
                    trans("update.auto.confirm.restart.title"),
                    trans("update.auto.confirm.restart.apply").format(version=version)):
                self.log("Restart/apply confirmation declined; removing staged .update payload.")
                for name in staged_names:
                    staged = os.path.join(install_dir, name + ".update")
                    if os.path.exists(staged) or os.path.islink(staged):
                        clear_path(staged, self.context)
                return UpdateResult(success=False, message=trans("update.auto.ready.not_installed"))

            self.context.progress("update.auto.status.preparing", percent=None)
            try:
                args = list(sys.argv[1:])
                self.log(f"Scheduling Linux post-exit swap; args={args!r}.")
                helper = schedule_linux_swap_after_exit(
                    install_dir,
                    staged_names,
                    "pygpt",
                    args,
                    debug=self.context.debug_enabled,
                    trace=self.context.log,
                )
                self.log(f"Post-exit Linux swap helper scheduled: {helper!r}.")
            except Exception as exc:
                self.log(f"Unable to schedule Linux swap: {type(exc).__name__}: {exc}")
                for name in staged_names:
                    staged = os.path.join(install_dir, name + ".update")
                    if os.path.exists(staged) or os.path.islink(staged):
                        clear_path(staged, self.context)
                raise
            return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
        finally:
            self.log(f"Cleaning extraction directory: {extract_dir!r}.")
            try:
                shutil.rmtree(extract_dir, ignore_errors=True)
            except Exception as exc:
                self.log(f"Extraction directory cleanup failed: {exc}")
            self.log(f"Cleaning downloaded archive: {archive_path!r}.")
            try:
                if os.path.exists(archive_path):
                    os.remove(archive_path)
            except OSError as exc:
                self.log(f"Downloaded archive cleanup failed: {exc}")
