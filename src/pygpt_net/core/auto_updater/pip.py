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

import sys

from pygpt_net.core.auto_updater import AUTO_UPDATER_PYPI_PACKAGE
from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateResult
from pygpt_net.core.auto_updater.helpers import current_restart_command, schedule_restart_after_exit
from pygpt_net.utils import trans


class PipUpdateFlow(BaseUpdateFlow):
    id = "pip"

    def run(self) -> UpdateResult:
        command = [sys.executable, "-m", "pip", "install", "--upgrade", AUTO_UPDATER_PYPI_PACKAGE]
        self.log(f"Flow started; interpreter={sys.executable!r}, update_command={command!r}.")
        if not self.context.confirm(
                trans("update.auto.confirm.command.title"),
                trans("update.auto.confirm.pip").format(command=" ".join(command))):
            self.log("pip upgrade confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        self.context.run_process(command, status="update.auto.status.pip")
        self.log("pip upgrade command completed successfully.")
        if not self.context.confirm(
                trans("update.auto.confirm.restart.title"),
                trans("update.auto.confirm.restart.updated")):
            self.log("Restart declined after successful pip update.")
            return UpdateResult(True, trans("update.auto.updated.no_restart"), quit_app=False)

        self.context.progress("update.auto.status.preparing", percent=None)
        restart = current_restart_command()
        self.log(f"Restart command resolved: {restart!r}.")
        helper = schedule_restart_after_exit(
            restart,
            debug=self.context.debug_enabled,
            trace=self.context.log,
        )
        self.log(f"Post-exit restart helper scheduled: {helper!r}.")
        return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
