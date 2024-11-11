#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.11 19:00:00                  #
# ================================================== #
import time

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_mouse_control"
        self.name = "Command: Mouse And Keyboard"
        self.description = "Provides ability to control mouse and keyboard"
        self.order = 100
        self.allowed_cmds = [
            "mouse_get_pos",
            "mouse_set_pos",
            "mouse_move",
            "mouse_click",
            "mouse_scroll",
            "make_screenshot",
            "keyboard_key",
            "keyboard_type",
        ]
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options"""
        prompt = ("MOUSE AND KEYBOARD CONTROL:\nYou can control the mouse and keyboard on my computer. "
                  "When I ask you, use the available commands to move the cursor for a specific task. "
                  "After each command, I will provide you with a screenshot showing the current cursor "
                  "position (so you don't need to make the screenshot manually), so you can adjust it "
                  "if necessary. In response to the screenshot, if needed, adjust the cursor position "
                  "again by sending another command to update the position instead of a text reply. "
                  "If you need to type something on the keyboard, use the appropriate commands - "
                  "keys will be pressed (or text will be typed) and you'll receive the result in a "
                  "screenshot. Always start your work by getting the current mouse position and screenshot. "
                  "The next step is to focus on the external window where you will perform the action by "
                  "clicking on it. Complete the assigned task by yourself using the available commands, "
                  "without asking the user to perform any actions. Finally, always check with the last screenshot "
                  "if the command has been executed correctly. Always use only one command per single response and "
                  "wait for the result before next command.\n")
        self.add_option(
            "allow_mouse_move",
            type="bool",
            value=True,
            label="Allow mouse movement",
            description="Allow mouse movement",
        )
        self.add_option(
            "allow_mouse_click",
            type="bool",
            value=True,
            label="Allow mouse click",
            description="Allow mouse click",
        )
        self.add_option(
            "allow_mouse_scroll",
            type="bool",
            value=True,
            label="Allow mouse scroll",
            description="Allow mouse scroll",
        )
        self.add_option(
            "allow_keyboard",
            type="bool",
            value=True,
            label="Allow keyboard key press",
            description="Allow keyboard key press",
        )
        self.add_option(
            "allow_screenshot",
            type="bool",
            value=True,
            label="Allow making screenshot",
            description="Allow making screenshot",
        )
        self.add_option(
            "auto_focus",
            type="bool",
            value=False,
            label="Auto-focus on the window",
            description="Auto-focus on the window (mouse click) before keyboard typing",
        )
        self.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt used to instruct how to control the mouse and keyboard",
            description="Prompt used to instruct how to control the mouse and keyboard",
            tooltip="Prompt used to instruct how to control the mouse and keyboard",
        )            

        # commands
        self.add_cmd(
            "mouse_get_pos",
            instruction="get current mouse X,Y position",
            params=[],
            enabled=True,
            description="Enable: get current mouse position",
        )
        self.add_cmd(
            "make_screenshot",
            instruction="make screenshot",
            params=[],
            enabled=True,
            description="Enable: make screenshot",
        )
        self.add_cmd(
            "mouse_set_pos",
            instruction="set mouse position to X,Y",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "on screen X coordinate",
                    "required": True,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "on screen Y coordinate",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: set mouse position to X,Y",
        )
        self.add_cmd(
            "mouse_move",
            instruction="move mouse position by X offset, Y offset",
            params=[
                {
                    "name": "offset_x",
                    "type": "int",
                    "description": "offset X in pixels",
                    "required": True,
                },
                {
                    "name": "offset_y",
                    "type": "int",
                    "description": "offset Y in pixels",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: move mouse position by offset X,Y",
        )
        self.add_cmd(
            "mouse_click",
            instruction="mouse button click",
            params=[
                {
                    "name": "button",
                    "type": "str",
                    "description": "button to click, enum: left|middle|right",
                    "required": True,
                },
                {
                    "name": "num_clicks",
                    "type": "int",
                    "description": "number of clicks, e.g. use 2 to double-click",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Mouse click",
        )
        self.add_cmd(
            "mouse_scroll",
            instruction="mouse scroll",
            params=[
                {
                    "name": "dx",
                    "type": "int",
                    "description": "steps to scroll horizontally, positive to the left, negative to the right",
                    "required": True,
                },
                {
                    "name": "dy",
                    "type": "int",
                    "description": "steps to scroll vertically, positive to scroll down, negative to scroll up",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Mouse scroll",
        )
        self.add_cmd(
            "keyboard_key",
            instruction="press keyboard key",
            params=[
                {
                    "name": "key",
                    "type": "str",
                    "description": "key to press",
                    "required": True,
                },
                {
                    "name": "modifier",
                    "type": "str",
                    "description": "modifier key, enum: shift|ctrl|alt|cmd",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Press keyboard keys",
        )
        self.add_cmd(
            "keyboard_type",
            instruction="type text on keyboard",
            params=[
                {
                    "name": "text",
                    "type": "str",
                    "description": "text to type on keyboard",
                    "required": True,
                },
                {
                    "name": "modifier",
                    "type": "str",
                    "description": "modifier key, enum: shift|ctrl|alt|cmd",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Type text on keyboard",
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

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )
        elif name == Event.SYSTEM_PROMPT:
            data['value'] = self.on_system_prompt(data['value'])

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        try:
            # worker
            worker = Worker()
            worker.plugin = self
            worker.window = self.window
            worker.cmds = my_commands
            worker.ctx = ctx

            # signals (base handlers)
            worker.signals.finished_more.connect(self.handle_finished)
            worker.signals.log.connect(self.handle_log)
            worker.signals.debug.connect(self.handle_debug)
            worker.signals.status.connect(self.handle_status)
            worker.signals.error.connect(self.handle_error)
            worker.signals.screenshot.connect(self.handle_screenshot)

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                worker.run()
                return

            # start
            self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

    @Slot(list, object, dict)
    def handle_finished(self, responses: list, ctx: CtxItem = None, extra_data: dict = None):
        """
        Handle finished responses signal

        :param responses: responses list
        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        # dispatch response (reply) - collect all responses and make screenshot only once at the end
        for response in responses:
            if ctx is not None:
                ctx.results.append(response)
                ctx.reply = True
        if self.get_option_value("allow_screenshot"):
            QApplication.processEvents()
            time.sleep(1)  # wait for a second
            self.window.controller.painter.capture.screenshot(attach_cursor=True)  # attach screenshot
        self.window.core.dispatcher.reply(ctx)

    @Slot(dict, object)
    def handle_screenshot(self, response: dict, ctx: CtxItem = None):
        """
        Handle screenshot

        :param response: response
        :param ctx: context (CtxItem)
        """
        self.window.controller.painter.capture.screenshot(attach_cursor=True)
        self.reply(response, ctx)

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        if prompt is not None and prompt.strip() != "":
            prompt += "\n\n"
        return prompt + self.get_option_value("prompt")

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
