#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import sys
from urllib.parse import urlsplit, urlunsplit

from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.downloader import Downloader
from pygpt_net.core.auto_updater.helpers import appimage_arch, schedule_appimage_swap_after_exit
from pygpt_net.utils import trans


class AppImageUpdateFlow(BaseUpdateFlow):
    id = "appimage"

    def run(self) -> UpdateResult:
        version = self.payload.version
        current = os.environ.get("APPIMAGE") or sys.executable
        current = os.path.abspath(current)
        directory = os.path.dirname(current)
        if not os.access(directory, os.W_OK):
            raise UpdateError(trans("update.auto.error.install_not_writable").format(path=directory))

        arch = appimage_arch(self.window.core.platforms.get_architecture())
        url = self.payload.download_appimage or (
            f"https://github.com/szczyglis-dev/py-gpt/releases/download/"
            f"v{version}/PyGPT-{version}-{arch}.AppImage"
        )
        # The updater API may expose one release URL for AppImage. Normalize a
        # known architecture token so ARM never downloads the x86_64 artifact
        # (and vice versa); architecture-neutral URLs are left untouched.
        parsed = urlsplit(url)
        path = parsed.path
        for token in ("x86_64", "aarch64", "amd64", "arm64"):
            if token in path:
                path = path.replace(token, arch)
                break
        if path.endswith(".AppImage.zsync"):
            path = path[:-len(".zsync")]
        url = urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
        if not self.context.confirm(
                trans("update.auto.confirm.download.title"),
                trans("update.auto.confirm.download").format(version=version)):
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        staged = current + ".update"
        Downloader(self.context).download(url, staged, "update.auto.status.downloading")
        mode = os.stat(staged).st_mode
        os.chmod(staged, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        if not self.context.confirm(
                trans("update.auto.confirm.restart.title"),
                trans("update.auto.confirm.restart.apply").format(version=version)):
            try:
                os.remove(staged)
            except OSError:
                pass
            return UpdateResult(success=False, message=trans("update.auto.ready.not_installed"))

        self.context.progress("update.auto.status.preparing", percent=None)
        try:
            schedule_appimage_swap_after_exit(current, staged, list(sys.argv[1:]))
        except Exception:
            try:
                os.remove(staged)
            except OSError:
                pass
            raise
        return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
