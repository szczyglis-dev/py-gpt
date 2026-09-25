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

from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.helpers import current_restart_command, schedule_restart_after_exit
from pygpt_net.utils import trans


class SourceUpdateFlow(BaseUpdateFlow):
    id = "source"

    def __init__(self, window, payload, context, source_root: str):
        super().__init__(window, payload, context)
        self.source_root = source_root

    def run(self) -> UpdateResult:
        self.log(f"Flow started: source_root={self.source_root!r}, interpreter={sys.executable!r}.")
        git = shutil.which("git")
        self.log(f"git executable lookup result: {git!r}.")
        if not git:
            raise UpdateError(trans("update.auto.error.git_missing"))
        git_dir = os.path.join(self.source_root or "", ".git")
        if not self.source_root or not os.path.isdir(git_dir):
            self.log(f"Git repository metadata missing: expected={git_dir!r}.")
            raise UpdateError(trans("update.auto.error.git_repo_missing"))

        git_command = [git, "-C", self.source_root, "pull", "--ff-only"]
        self.log(f"Prepared git update command: {git_command!r}.")
        if not self.context.confirm(
                trans("update.auto.confirm.command.title"),
                trans("update.auto.confirm.git_pull").format(path=self.source_root)):
            self.log("git pull confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))
        self.context.run_process(git_command, status="update.auto.status.git_pull")
        self.log("git pull --ff-only completed successfully.")

        requirements = os.path.join(self.source_root, "requirements.txt")
        self.log(f"Requirements file path: {requirements!r}; exists={os.path.isfile(requirements)}.")
        if os.path.isfile(requirements):
            pip_command = [sys.executable, "-m", "pip", "install", "-r", requirements]
            self.log(f"Prepared requirements update command: {pip_command!r}.")
            if not self.context.confirm(
                    trans("update.auto.confirm.command.title"),
                    trans("update.auto.confirm.requirements").format(command=" ".join(pip_command))):
                self.log("requirements installation declined after successful git pull.")
                return UpdateResult(True, trans("update.auto.source.pulled_no_requirements"), quit_app=False)
            self.context.run_process(
                pip_command,
                cwd=self.source_root,
                status="update.auto.status.requirements",
            )
            self.log("requirements installation completed successfully.")
        else:
            self.log("No requirements.txt found; skipping dependency update.")

        if not self.context.confirm(
                trans("update.auto.confirm.restart.title"),
                trans("update.auto.confirm.restart.updated")):
            self.log("Restart declined after source update.")
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
