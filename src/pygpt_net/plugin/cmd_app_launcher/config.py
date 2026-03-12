#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : PYGPT Contributors                   #
# Updated Date: 2026.03.11 00:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        # --- Commands ---

        plugin.add_cmd(
            "app_launch",
            instruction="Launch/open an application by name on the user's system. "
                        "Use the app name as it would appear in the Start Menu or PATH. "
                        "Examples: 'chrome', 'notepad', 'spotify', 'firefox', 'vscode'.",
            params=[
                {
                    "name": "app_name",
                    "type": "str",
                    "description": "Application name to launch (e.g. 'chrome', 'notepad', 'spotify')",
                    "required": True,
                },
                {
                    "name": "args",
                    "type": "str",
                    "description": "Optional arguments to pass to the application",
                    "required": False,
                },
            ],
            enabled=True,
        )

        plugin.add_cmd(
            "app_close",
            instruction="Close/kill a running application by name. "
                        "This will terminate all processes matching the given name.",
            params=[
                {
                    "name": "app_name",
                    "type": "str",
                    "description": "Application/process name to close (e.g. 'chrome', 'notepad')",
                    "required": True,
                },
            ],
            enabled=True,
        )

        plugin.add_cmd(
            "app_list_running",
            instruction="List currently running applications/processes with visible windows. "
                        "Returns a list of window titles and process names.",
            params=[],
            enabled=True,
        )

        plugin.add_cmd(
            "app_open_url",
            instruction="Open a URL in the user's default web browser. "
                        "Can also open specific sites like 'youtube.com', 'github.com', etc.",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to open (e.g. 'https://youtube.com' or just 'youtube.com')",
                    "required": True,
                },
            ],
            enabled=True,
        )

        plugin.add_cmd(
            "app_list_installed",
            instruction="List installed applications that can be launched. "
                        "Scans Start Menu shortcuts and PATH for available programs.",
            params=[
                {
                    "name": "filter",
                    "type": "str",
                    "description": "Optional filter to search by name (e.g. 'chrome')",
                    "required": False,
                },
            ],
            enabled=True,
        )

        plugin.add_cmd(
            "media_play_pause",
            instruction="Toggle play/pause on the current media player (system-wide media key).",
            params=[],
            enabled=True,
        )

        plugin.add_cmd(
            "media_next_track",
            instruction="Skip to the next track (system-wide media key).",
            params=[],
            enabled=True,
        )

        plugin.add_cmd(
            "media_prev_track",
            instruction="Go to the previous track (system-wide media key).",
            params=[],
            enabled=True,
        )

        plugin.add_cmd(
            "volume_set",
            instruction="Set system volume to a specific level (0-100).",
            params=[
                {
                    "name": "level",
                    "type": "int",
                    "description": "Volume level from 0 to 100",
                    "required": True,
                },
            ],
            enabled=True,
        )

        plugin.add_cmd(
            "volume_mute_toggle",
            instruction="Toggle system mute on/off.",
            params=[],
            enabled=True,
        )

        # --- Options ---

        plugin.add_option(
            "custom_app_aliases",
            type="dict",
            value={
                "chrome": "chrome",
                "firefox": "firefox",
                "notepad": "notepad",
                "explorer": "explorer",
                "calculator": "calc",
                "terminal": "cmd",
                "powershell": "powershell",
                "vscode": "code",
                "spotify": "spotify",
            },
            label="Custom app aliases",
            description="Map friendly names to executable names or paths. "
                        "Key = alias name, Value = executable name or full path.",
            keys={
                "name": "text",
                "value": "text",
            },
            persist=True,
        )

        plugin.add_option(
            "scan_start_menu",
            type="bool",
            value=True,
            label="Scan Start Menu",
            description="Scan Windows Start Menu for installed applications. "
                        "Enables launching apps by their Start Menu name. Default: True",
        )
