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
import sys

from pygpt_net.core.auto_updater import AUTO_UPDATER_PYPI_PACKAGE
from pygpt_net.core.auto_updater.base import BaseUpdateFlow, UpdateError, UpdateResult
from pygpt_net.core.auto_updater.helpers import (
    current_restart_command,
    schedule_restart_after_exit,
    schedule_windows_pip_update_after_exit,
)
from pygpt_net.utils import trans


class PipUpdateFlow(BaseUpdateFlow):
    id = "pip"

    def run(self) -> UpdateResult:
        command = [sys.executable, "-m", "pip", "install", "--upgrade", AUTO_UPDATER_PYPI_PACKAGE]
        self.log(f"Flow started; interpreter={sys.executable!r}, update_command={command!r}.")
        confirm_message = trans("update.auto.confirm.pip").format(command=" ".join(command))
        if os.name == "nt":
            # On Windows the running console-script executable can be locked,
            # so pip must run only after PyGPT has fully exited.
            confirm_message += "\n\n" + trans("update.auto.confirm.restart.apply").format(
                version=self.payload.version
            )

        if not self.context.confirm(
                trans("update.auto.confirm.command.title"),
                confirm_message):
            self.log("pip upgrade confirmation declined.")
            return UpdateResult(success=False, message=trans("update.auto.cancelled"))

        if os.name == "nt":
            self.context.progress("update.auto.status.preparing", percent=None)
            restart = current_restart_command()
            self.log(
                "Windows pip update will run after PyGPT exits because the "
                f"console-script launcher may be locked; restart={restart!r}."
            )
            try:
                helper = schedule_windows_pip_update_after_exit(
                    update_command=command,
                    restart_command=restart,
                    debug=self.context.debug_enabled,
                    trace=self.context.log,
                    timeout_seconds=30,
                )
            except OSError as exc:
                self.log(
                    "Unable to launch Windows pip post-exit helper: "
                    f"{type(exc).__name__}: {exc}"
                )
                raise UpdateError(f"Unable to prepare pip update helper: {exc}") from exc

            self.log(f"Windows pip post-exit helper scheduled: {helper!r}.")
            return UpdateResult(
                True,
                trans("update.auto.status.restarting"),
                quit_app=True,
                data={"helper": helper},
            )

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
