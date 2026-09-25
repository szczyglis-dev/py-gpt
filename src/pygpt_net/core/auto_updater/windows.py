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

from pygpt_net.core.auto_updater import AUTO_UPDATER_WINDOWS_MSI_FILENAME, AUTO_UPDATER_WINDOWS_MSI_URL
from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateResult
from pygpt_net.core.auto_updater.downloader import Downloader
from pygpt_net.core.auto_updater.helpers import current_restart_command, schedule_windows_msi_after_exit
from pygpt_net.utils import trans


class WindowsMsiUpdateFlow(BaseUpdateFlow):
    id = "windows_msi"

    def run(self) -> UpdateResult:
        version = self.payload.version
        url = self.payload.download_windows or AUTO_UPDATER_WINDOWS_MSI_URL.format(version=version)
        self.log(f"Flow started: version={version!r}, download_url={url!r}.")
        if not self.context.confirm(
                trans("update.auto.confirm.download.title"),
                trans("update.auto.confirm.download").format(version=version)):
            self.log("Download confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        tmp_root = os.path.join(self.window.core.config.get_user_dir("tmp"), "updates")
        os.makedirs(tmp_root, exist_ok=True)
        target = os.path.join(tmp_root, AUTO_UPDATER_WINDOWS_MSI_FILENAME.format(version=version))
        self.log(f"MSI download target: {target!r}.")
        Downloader(self.context).download(url, target, "update.auto.status.downloading")

        if not self.context.confirm(
                trans("update.auto.confirm.install.title"),
                trans("update.auto.confirm.install.windows").format(version=version)):
            self.log("MSI install/restart confirmation declined; downloaded MSI is kept for this session.")
            return UpdateResult(success=False, message=trans("update.auto.ready.not_installed"))

        self.context.progress("update.auto.status.preparing", percent=None)
        restart = current_restart_command()
        self.log(f"Restart command resolved: {restart!r}.")
        helper = schedule_windows_msi_after_exit(
            target,
            restart,
            debug=self.context.debug_enabled,
            trace=self.context.log,
        )
        self.log(f"Post-exit MSI helper scheduled: {helper!r}.")
        return UpdateResult(
            success=True,
            message=trans("update.auto.status.restarting"),
            quit_app=True,
        )
