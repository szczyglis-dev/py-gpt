#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateResult
from pygpt_net.core.auto_updater.helpers import current_restart_command, schedule_restart_after_exit
from pygpt_net.utils import trans


class PipUpdateFlow(BaseUpdateFlow):
    id = "pip"

    def run(self) -> UpdateResult:
        command = [sys.executable, "-m", "pip", "install", "--upgrade", "pygpt-net"]
        if not self.context.confirm(
                trans("update.auto.confirm.command.title"),
                trans("update.auto.confirm.pip").format(command=" ".join(command))):
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        self.context.run_process(command, status="update.auto.status.pip")
        if not self.context.confirm(
                trans("update.auto.confirm.restart.title"),
                trans("update.auto.confirm.restart.updated")):
            return UpdateResult(True, trans("update.auto.updated.no_restart"), quit_app=False)

        self.context.progress("update.auto.status.preparing", percent=None)
        schedule_restart_after_exit(current_restart_command())
        return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
