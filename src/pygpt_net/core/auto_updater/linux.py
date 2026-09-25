#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import sys
import tempfile

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
        url = self.payload.download_linux or f"https://pygpt.net/download/{version}/pygpt-{version}.zip"
        if not self.context.confirm(
                trans("update.auto.confirm.download.title"),
                trans("update.auto.confirm.download").format(version=version)):
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        tmp_root = os.path.join(self.window.core.config.get_user_dir("tmp"), "updates")
        os.makedirs(tmp_root, exist_ok=True)
        ext = ".zip" if ".zip" in url.lower() else ".tar.gz"
        archive_path = os.path.join(tmp_root, f"pygpt-{version}{ext}")
        Downloader(self.context).download(url, archive_path, "update.auto.status.downloading")

        extract_dir = tempfile.mkdtemp(prefix=f"pygpt-{version}-", dir=tmp_root)
        staged_names = []
        install_dir = os.path.dirname(os.path.abspath(sys.executable))
        try:
            self.context.progress("update.auto.status.extracting", 0)
            extract_update_archive(archive_path, extract_dir, self.context)
            payload_root = find_linux_payload(extract_dir)

            if not os.access(install_dir, os.W_OK):
                raise UpdateError(trans("update.auto.error.install_not_writable").format(path=install_dir))

            self.context.progress("update.auto.status.staging", 0)
            staged_names = stage_payload_with_update_suffix(payload_root, install_dir, self.context)
            if "pygpt" not in staged_names:
                raise UpdateError("Linux update payload does not contain top-level 'pygpt'")

            if not self.context.confirm(
                    trans("update.auto.confirm.restart.title"),
                    trans("update.auto.confirm.restart.apply").format(version=version)):
                for name in staged_names:
                    staged = os.path.join(install_dir, name + ".update")
                    if os.path.exists(staged) or os.path.islink(staged):
                        clear_path(staged)
                return UpdateResult(success=False, message=trans("update.auto.ready.not_installed"))

            self.context.progress("update.auto.status.preparing", percent=None)
            try:
                schedule_linux_swap_after_exit(install_dir, staged_names, "pygpt", list(sys.argv[1:]))
            except Exception:
                for name in staged_names:
                    staged = os.path.join(install_dir, name + ".update")
                    if os.path.exists(staged) or os.path.islink(staged):
                        clear_path(staged)
                raise
            return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
        finally:
            try:
                shutil.rmtree(extract_dir, ignore_errors=True)
            except Exception:
                pass
            try:
                if os.path.exists(archive_path):
                    os.remove(archive_path)
            except OSError:
                pass
