#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.15 10:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event

from datetime import datetime
from croniter import croniter

from pygpt_net.utils import trans


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "crontab"
        self.name = "Crontab / Task scheduler"
        self.type = [
            'schedule',
        ]
        self.description = "Plugin provides cron-based job scheduling - " \
                           "you can schedule prompts to be sent at any time using cron-based syntax for task setup."
        self.order = 100
        self.use_locale = True
        self.timers = []
        self.init_options()

    def init_options(self):
        """Initialize options"""
        keys = {
            "enabled": "bool",
            "crontab": "text",
            "prompt": "textarea",
            "preset": {
                "type": "combo",
                "use": "presets",
                "keys": [],
            },
        }
        items = [
            {
                "enabled": False,
                "crontab": "30 9 * * *",
                "prompt": "Hi! This prompt should be sent at 9:30 every day. What time is it?",
                "preset": "_",
            },
        ]
        desc = "Add your cron-style tasks here. They will be executed automatically at the times you specify in " \
               "the cron-based job format. If you are unfamiliar with Cron, consider visiting the Cron Guru " \
               "page for assistance."
        tooltip = "Check out the tutorials about Cron or visit the Crontab Guru for help on how to use Cron syntax."
        self.add_option(
            "crontab",
            type="dict",
            value=items,
            label="Your tasks",
            description=desc,
            tooltip=tooltip,
            keys=keys,
            urls={
                "Crontab Guru": "https://crontab.guru",
            },
        )
        self.add_option(
            "new_ctx",
            type="bool",
            value=True,
            label="Create a new context on job run",
            description="If enabled, then a new context will be created on every run of the job",
        )
        self.add_option(
            "show_notify",
            type="bool",
            value=True,
            label="Show notification on job run",
            description="If enabled, then a tray notification will be shown on every run of the job",
        )

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def on_update(self):
        pass

    def on_post_update(self):
        """
        On post update hook
        """
        self.schedule_tasks()

    def count_active(self) -> int:
        """
        Count active tasks

        :return: number of active tasks
        """
        count = 0
        for item in self.get_option_value("crontab"):
            if item["enabled"]:
                count += 1
        return count

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data

        if name == Event.PLUGIN_SETTINGS_CHANGED:
            self.window.ui.tray.update_schedule_tasks(
                self.count_active()
            )

        elif name == Event.PLUGIN_OPTION_GET:
            if "name" in data and data["name"] == "scheduled_tasks_count":
                data["value"] = self.count_active()  # return number of active tasks

    def job(self, item: dict):
        """
        Execute task

        :param item: task item dict
        """
        if item["prompt"] == "" or item["prompt"] is None:
            self.log("Prompt is empty, skipping task")
            return

        self.log("Executing task: {}: {}".format(datetime.now(), item["prompt"]))

        # show notification
        if self.get_option_value("show_notify"):
            self.window.ui.tray.show_msg(
                trans("notify.cron.title"),
                item["prompt"][0:30] + "...",
            )

        # select preset if defined and exists
        if item["preset"] != "_" and item["preset"] is not None:
            if self.window.core.presets.exists(item["preset"]):
                mode = self.window.core.presets.get_first_mode(item["preset"])
                if mode is not None:
                    self.log("Using preset: {}".format(item["preset"]))
                    self.window.controller.presets.set(mode, item["preset"])
                    self.window.controller.presets.select_current()
                    self.window.controller.presets.select_model()

        # send prompt
        if self.get_option_value("new_ctx"):
            self.window.controller.ctx.new(
                force=True,
            )
        self.window.controller.chat.input.send(
            text=item["prompt"],
            force=True,
        )

    def schedule_tasks(self):
        """Schedule tasks based on crontab"""
        crontab = self.get_option_value("crontab")
        # remove unused or inactive items
        for timer in self.timers:
            if not timer["item"]["enabled"] or timer["item"] not in crontab:
                self.timers.remove(timer)

        for item in crontab:
            try:
                if not item["enabled"]:
                    continue
                cron = item["crontab"]
                base_time = datetime.now()
                iter = croniter(cron, base_time)
                is_timer = False
                timer = None
                for timer in self.timers:
                    if item == timer["item"]:
                        is_timer = True
                        break

                # add to timers if not exists
                if not is_timer:
                    timer = {
                        "item": item,
                        "next_time": None,
                    }
                    self.timers.append(timer)

                next_time = timer["next_time"]

                # if first run
                if next_time is None:
                    next_time = iter.get_next(datetime)
                    timer["next_time"] = next_time
                    continue

                if datetime.now() >= next_time:
                    next_time = iter.get_next(datetime)
                    timer["next_time"] = next_time
                    self.job(item)

                timer["next_time"] = iter.get_next(datetime)
            except Exception as e:
                self.log("Error: {}".format(e))

        # show number of scheduled jobs
        num_jobs = len(self.timers)
        if num_jobs > 0:
            self.window.ui.plugin_addon['schedule'].setVisible(True)
            self.window.ui.plugin_addon['schedule'].setText(
                "+ Cron: {} job(s)".format(len(self.timers)),
            )
        else:
            self.window.ui.plugin_addon['schedule'].setVisible(False)
            self.window.ui.plugin_addon['schedule'].setText("")

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CRON] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
