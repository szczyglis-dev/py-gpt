#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateResult
from pygpt_net.core.auto_updater.downloader import Downloader
from pygpt_net.core.auto_updater.helpers import current_restart_command, schedule_windows_msi_after_exit
from pygpt_net.utils import trans


class WindowsMsiUpdateFlow(BaseUpdateFlow):
    id = "windows_msi"

    def run(self) -> UpdateResult:
        version = self.payload.version
        url = self.payload.download_windows or f"https://pygpt.net/download/{version}/pygpt-{version}.msi"
        if not self.context.confirm(
                trans("update.auto.confirm.download.title"),
                trans("update.auto.confirm.download").format(version=version)):
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        tmp_root = os.path.join(self.window.core.config.get_user_dir("tmp"), "updates")
        os.makedirs(tmp_root, exist_ok=True)
        target = os.path.join(tmp_root, f"pygpt-{version}.msi")
        Downloader(self.context).download(url, target, "update.auto.status.downloading")

        if not self.context.confirm(
                trans("update.auto.confirm.install.title"),
                trans("update.auto.confirm.install.windows").format(version=version)):
            return UpdateResult(success=False, message=trans("update.auto.ready.not_installed"))

        self.context.progress("update.auto.status.preparing", percent=None)
        schedule_windows_msi_after_exit(target, current_restart_command())
        return UpdateResult(
            success=True,
            message=trans("update.auto.status.restarting"),
            quit_app=True,
        )
