#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.23 07:00:00                  #
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
        dockerfile = 'FROM python:3.9-alpine'
        dockerfile += '\n\n'
        dockerfile += 'RUN mkdir /data'
        dockerfile += '\n\n'
        dockerfile += '# Data directory, bound as a volume to the local \'data/\' directory'
        dockerfile += '\nWORKDIR /data'

        volumes_keys = {
            "enabled": "bool",
            "docker": "text",
            "host": "text",
        }
        volumes_items = [
            {
                "enabled": True,
                "docker": "/data",
                "host": "{workdir}",
            },
        ]
        ports_keys = {
            "enabled": "bool",
            "docker": "text",
            "host": "int",
        }
        ports_items = []

        # Sandbox / sys_exec (original)
        plugin.add_option(
            "sandbox_docker",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
            tab="sandbox",
        )
        plugin.add_option(
            "dockerfile",
            type="textarea",
            value=dockerfile,
            label="Dockerfile",
            description="Dockerfile",
            tooltip="Dockerfile",
            tab="sandbox",
        )
        plugin.add_option(
            "image_name",
            type="text",
            value='pygpt_system',
            label="Docker image name",
            tab="sandbox",
        )
        plugin.add_option(
            "container_name",
            type="text",
            value='pygpt_system_container',
            label="Docker container name",
            tab="sandbox",
        )
        plugin.add_option(
            "docker_entrypoint",
            type="text",
            value='tail -f /dev/null',
            label="Docker run command",
            tab="sandbox",
            advanced=True,
        )
        plugin.add_option(
            "docker_volumes",
            type="dict",
            value=volumes_items,
            label="Docker volumes",
            description="Docker volumes mapping",
            tooltip="Docker volumes mapping",
            keys=volumes_keys,
            tab="sandbox",
            advanced=True,
        )
        plugin.add_option(
            "docker_ports",
            type="dict",
            value=ports_items,
            label="Docker ports",
            description="Docker ports mapping",
            tooltip="Docker ports mapping",
            keys=ports_keys,
            tab="sandbox",
            advanced=True,
        )
        plugin.add_option(
            "auto_cwd",
            type="bool",
            value=True,
            label="Auto-append CWD to sys_exec",
            description="Automatically append current working directory to sys_exec command",
            tab="general",
        )
        plugin.add_cmd(
            "sys_exec",
            instruction="execute ANY system command, script or app in user's environment. "
                        "Do not use this command to install Python libraries, use IPython environment and IPython commands instead.",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "system command",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows system commands execution",
            tab="general",
        )

        # -------------------------------
        # WinAPI options (new tab)
        # -------------------------------
        plugin.add_option(
            "winapi_enabled",
            type="bool",
            value=True,
            label="Enable WinAPI",
            description="Enable Windows API features on Microsoft Windows.",
            tab="winapi",
        )
        plugin.add_option(
            "win_keys_per_char_delay_ms",
            type="int",
            value=2,
            label="Keys: per-char delay (ms)",
            description="Delay between characters for win_keys_text.",
            tab="winapi",
        )
        plugin.add_option(
            "win_keys_hold_ms",
            type="int",
            value=50,
            label="Keys: hold (ms)",
            description="Hold duration for modifiers in win_keys_send.",
            tab="winapi",
        )
        plugin.add_option(
            "win_keys_gap_ms",
            type="int",
            value=30,
            label="Keys: gap (ms)",
            description="Gap between normal key taps in win_keys_send.",
            tab="winapi",
        )
        plugin.add_option(
            "win_drag_step_delay_ms",
            type="int",
            value=10,
            label="Drag: step delay (ms)",
            description="Delay between intermediate drag steps in win_drag.",
            tab="winapi",
        )

        # -------------------------------
        # WinAPI commands
        # -------------------------------
        plugin.add_cmd(
            "win_list",
            instruction="List top-level windows. You can filter by title substring.",
            params=[
                {"name": "filter_title", "type": "str", "description": "Substring to filter by window title", "required": False},
                {"name": "visible_only", "type": "bool", "description": "Only visible windows", "required": False},
                {"name": "limit", "type": "int", "description": "Limit number of results", "required": False},
            ],
            enabled=True,
            description="List top-level windows",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_find",
            instruction="Find windows by multiple attributes.",
            params=[
                {"name": "title", "type": "str", "description": "Title or substring", "required": False},
                {"name": "class_name", "type": "str", "description": "Exact class name", "required": False},
                {"name": "exe", "type": "str", "description": "Process executable name", "required": False},
                {"name": "pid", "type": "int", "description": "Process ID", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
                {"name": "visible_only", "type": "bool", "description": "Only visible", "required": False},
            ],
            enabled=True,
            description="Find windows",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_children",
            instruction="List child windows for a given parent HWND.",
            params=[{"name": "hwnd", "type": "int", "description": "Parent window handle", "required": True}],
            enabled=True,
            description="List child windows",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_foreground",
            instruction="Return info about the current foreground window.",
            params=[],
            enabled=True,
            description="Foreground window info",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_rect",
            instruction="Return window rectangle (geometry).",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Get window rect",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_get_state",
            instruction="Return full window state and metadata.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Get window state",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_focus",
            instruction="Bring a window to foreground.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Set focus to a window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_move_resize",
            instruction="Move and/or resize a window. Omit any of x,y,width,height to keep current.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
                {"name": "x", "type": "int", "description": "Left position", "required": False},
                {"name": "y", "type": "int", "description": "Top position", "required": False},
                {"name": "width", "type": "int", "description": "Width", "required": False},
                {"name": "height", "type": "int", "description": "Height", "required": False},
            ],
            enabled=True,
            description="Move/resize window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_minimize",
            instruction="Minimize a window.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Minimize window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_maximize",
            instruction="Maximize a window.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Maximize window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_restore",
            instruction="Restore a minimized or maximized window.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Restore window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_close",
            instruction="Close a window (sends WM_CLOSE).",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Close window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_show",
            instruction="Show a window.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Show window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_hide",
            instruction="Hide a window.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Hide window",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_always_on_top",
            instruction="Toggle window always-on-top (topmost).",
            params=[
                {"name": "topmost", "type": "bool", "description": "True to set, False to clear", "required": True},
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Always on top",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_set_opacity",
            instruction="Set window opacity using layered style. Provide alpha (0..255) OR opacity (0..1).",
            params=[
                {"name": "alpha", "type": "int", "description": "Alpha 0..255", "required": False},
                {"name": "opacity", "type": "float", "description": "Opacity 0..1", "required": False},
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
            ],
            enabled=True,
            description="Set window opacity",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_screenshot",
            instruction="Take a window screenshot and save to a PNG file. Returns absolute path.",
            params=[
                {"name": "hwnd", "type": "int", "description": "Target window handle", "required": False},
                {"name": "title", "type": "str", "description": "Title substring to match", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
                {"name": "path", "type": "str", "description": "Output path (relative to data/ if not absolute)", "required": False},
            ],
            enabled=True,
            description="Window screenshot to PNG",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_area_screenshot",
            instruction="Take a rectangular screenshot of the screen or relative to a window.",
            params=[
                {"name": "x", "type": "int", "description": "Left", "required": True},
                {"name": "y", "type": "int", "description": "Top", "required": True},
                {"name": "width", "type": "int", "description": "Width", "required": True},
                {"name": "height", "type": "int", "description": "Height", "required": True},
                {"name": "hwnd", "type": "int", "description": "Base window (optional)", "required": False},
                {"name": "title", "type": "str", "description": "Base window by title (optional)", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
                {"name": "relative", "type": "bool", "description": "Coords relative to window when hwnd/title provided", "required": False},
                {"name": "path", "type": "str", "description": "Output path", "required": False},
            ],
            enabled=True,
            description="Area screenshot to PNG",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_clipboard_get",
            instruction="Get clipboard text.",
            params=[],
            enabled=True,
            description="Clipboard get",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_clipboard_set",
            instruction="Set clipboard text.",
            params=[{"name": "text", "type": "str", "description": "Text to set", "required": True}],
            enabled=True,
            description="Clipboard set",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_cursor_get",
            instruction="Get cursor position.",
            params=[],
            enabled=True,
            description="Cursor get",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_cursor_set",
            instruction="Set cursor position.",
            params=[
                {"name": "x", "type": "int", "description": "X coordinate", "required": True},
                {"name": "y", "type": "int", "description": "Y coordinate", "required": True},
            ],
            enabled=True,
            description="Cursor set",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_keys_text",
            instruction="Type Unicode text into the active window (uses SendInput).",
            params=[
                {"name": "text", "type": "str", "description": "Text to type", "required": True},
                {"name": "per_char_delay_ms", "type": "int", "description": "Delay between characters in ms", "required": False},
            ],
            enabled=True,
            description="Type text",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_keys_send",
            instruction="Send key combinations, e.g. ['CTRL','ALT','T'] or ['F5'].",
            params=[
                {"name": "keys", "type": "list", "description": "List of key tokens", "required": True},
                {"name": "hold_ms", "type": "int", "description": "Hold duration for modifiers", "required": False},
                {"name": "gap_ms", "type": "int", "description": "Gap between taps", "required": False},
            ],
            enabled=True,
            description="Send key combos",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_click",
            instruction="Click at a screen point or relative to a window.",
            params=[
                {"name": "x", "type": "int", "description": "X coordinate", "required": True},
                {"name": "y", "type": "int", "description": "Y coordinate", "required": True},
                {"name": "button", "type": "str", "description": "left/right/middle", "required": False},
                {"name": "double", "type": "bool", "description": "Double click", "required": False},
                {"name": "hwnd", "type": "int", "description": "Base window", "required": False},
                {"name": "title", "type": "str", "description": "Base window by title", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
                {"name": "relative", "type": "bool", "description": "Coords relative to window", "required": False},
            ],
            enabled=True,
            description="Mouse click",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_drag",
            instruction="Drag from (x1,y1) to (x2,y2), absolute or relative to a window.",
            params=[
                {"name": "x1", "type": "int", "description": "Start X", "required": True},
                {"name": "y1", "type": "int", "description": "Start Y", "required": True},
                {"name": "x2", "type": "int", "description": "End X", "required": True},
                {"name": "y2", "type": "int", "description": "End Y", "required": True},
                {"name": "hwnd", "type": "int", "description": "Base window", "required": False},
                {"name": "title", "type": "str", "description": "Base window by title", "required": False},
                {"name": "exact", "type": "bool", "description": "Exact title match", "required": False},
                {"name": "relative", "type": "bool", "description": "Coords relative to window", "required": False},
                {"name": "steps", "type": "int", "description": "Interpolation steps", "required": False},
                {"name": "hold_ms", "type": "int", "description": "Delay between steps (ms)", "required": False},
            ],
            enabled=True,
            description="Mouse drag",
            tab="winapi",
        )
        plugin.add_cmd(
            "win_monitors",
            instruction="List monitors/screens and their geometry.",
            params=[],
            enabled=True,
            description="List monitors",
            tab="winapi",
        )