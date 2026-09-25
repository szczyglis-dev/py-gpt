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

import shlex
import shutil

from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.helpers import schedule_restart_after_exit
from pygpt_net.utils import trans


class SnapUpdateFlow(BaseUpdateFlow):
    id = "snap"

    @staticmethod
    def _terminal_command(shell_command: str):
        candidates = [
            ("gnome-terminal", lambda exe: [exe, "--wait", "--", "bash", "-lc", shell_command]),
            ("konsole", lambda exe: [exe, "-e", "bash", "-lc", shell_command]),
            ("xfce4-terminal", lambda exe: [exe, "--disable-server", "-e", f"bash -lc {shlex.quote(shell_command)}"]),
            ("x-terminal-emulator", lambda exe: [exe, "-e", "bash", "-lc", shell_command]),
            ("xterm", lambda exe: [exe, "-e", "bash", "-lc", shell_command]),
        ]
        for name, builder in candidates:
            exe = shutil.which(name)
            if exe:
                return builder(exe)
        return None

    def run(self) -> UpdateResult:
        self.log("Flow started.")
        # A manual snap refresh may refuse to update a running desktop app, so
        # run the privileged refresh only after PyGPT has shut down. The terminal
        # stays visible for sudo's password prompt and starts the refreshed snap
        # only when the command succeeds.
        shell_command = "sudo snap refresh pygpt && { nohup snap run pygpt >/dev/null 2>&1 & }"
        command = self._terminal_command(shell_command)
        self.log(f"Terminal command lookup result: {command!r}.")
        if not command:
            raise UpdateError(trans("update.auto.error.terminal_missing"))

        if not self.context.confirm(
                trans("update.auto.confirm.command.title"),
                trans("update.auto.confirm.snap").format(command="sudo snap refresh pygpt")):
            self.log("Snap refresh confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        self.context.progress("update.auto.status.preparing", percent=None)
        self.log(f"Scheduling terminal command after application exit: {command!r}.")
        helper = schedule_restart_after_exit(
            command,
            debug=self.context.debug_enabled,
            trace=self.context.log,
        )
        self.log(f"Post-exit Snap helper scheduled: {helper!r}.")
        return UpdateResult(True, trans("update.auto.status.restarting"), quit_app=True)
