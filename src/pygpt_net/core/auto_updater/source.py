#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import sys

from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.helpers import current_restart_command, schedule_restart_after_exit
from pygpt_net.utils import trans


class SourceUpdateFlow(BaseUpdateFlow):
    id = "source"

    def __init__(self, window, payload, context, source_root: str):
        super().__init__(window, payload, context)
        self.source_root = source_root

    def run(self) -> UpdateResult:
        git = shutil.which("git")
        if not git:
            raise UpdateError(trans("update.auto.error.git_missing"))
        if not self.source_root or not os.path.isdir(os.path.join(self.source_root, ".git")):
            raise UpdateError(trans("update.auto.error.git_repo_missing"))

        git_command = [git, "-C", self.source_root, "pull", "--ff-only"]
        if not self.context.confirm(
                trans("update.auto.confirm.command.title"),
                trans("update.auto.confirm.git_pull").format(path=self.source_root)):
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))
        self.context.run_process(git_command, status="update.auto.status.git_pull")

        requirements = os.path.join(self.source_root, "requirements.txt")
        if os.path.isfile(requirements):
            pip_command = [sys.executable, "-m", "pip", "install", "-r", requirements]
            if not self.context.confirm(
                    trans("update.auto.confirm.command.title"),
                    trans("update.auto.confirm.requirements").format(command=" ".join(pip_command))):
                return UpdateResult(True, trans("update.auto.source.pulled_no_requirements"), quit_app=False)
            self.context.run_process(
                pip_command,
                cwd=self.source_root,
                status="update.auto.status.requirements",
            )

        if not self.context.confirm(
                trans("update.auto.confirm.restart.title"),
                trans("update.auto.confirm.restart.updated")):
            return UpdateResult(True, trans("update.auto.updated.no_restart"), quit_app=False)

        self.context.progress("update.auto.status.preparing", percent=None)
        schedule_restart_after_exit(current_restart_command())
        return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
