#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.16 05:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, QTimer

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
            "get_mouse_position",
            "mouse_move",
            "mouse_click",
            "mouse_scroll",
            "get_screenshot",
            "keyboard_key",
            "keyboard_type",
        ]
        self.use_locale = True
        self.worker = None
        self.init_options()

    def init_options(self):
        """Initialize options"""
        prompt = """
        # Controlling the Mouse and Keyboard:

        You have access to commands that allow you to control the mouse and keyboard on my computer. 
        Your objective is to perform tasks by precisely utilizing these commands. 

        ## Follow these instructions carefully to ensure accurate and effective actions:

        1. Task Analysis: When assigned a task, break it down into clear, sequential steps needed to accomplish the goal.        
        2. Screen Assessment: Use the provided screenshot to understand the current state of the screen. 
        Identify interactive elements such as buttons, menus, and text fields that are relevant to the task.        
        3. Command Utilization: Employ the available commands (e.g., mouse_move(x, y), mouse_click(button), 
        keyboard_type(text)) to interact with the identified elements. Ensure you use the correct syntax and parameters for each command.        
        4. Action Planning: Before executing commands, plan the exact coordinates and sequence of actions required. 
        This may involve calculating the position of an element based on the screenshot.        
        5. Step-by-Step Execution: Perform one command at a time. After each action, wait for the updated screenshot 
        to verify that the action had the intended effect before proceeding.        
        6. Verification and Adjustment: Use the feedback from each new screenshot to confirm successful execution. 
        If the outcome is not as expected, adjust your approach accordingly.        
        7. Focus on Relevant Areas: Begin by directing your actions to the area of the screen where the task is 
        to be performed. This may involve moving the cursor to a specific window or section.        
        8. Autonomous Completion: Complete the task independently using the commands provided. Avoid requesting 
        user intervention and ensure each step is necessary and contributes to the final goal.        
        9. Safety and Accuracy: Avoid any actions that may cause unintended side effects. Double-check coordinates 
        and command parameters to prevent errors.        
        10. Efficiency: Aim to accomplish the task in as few steps as possible while maintaining accuracy. 
        Consolidate actions when appropriate without skipping necessary verification.        
        11. Remember to focus on the correct window before typing on the keyboard.

        ## Example Workflow:

        Task: Find the window "App" and set the focus on it by clicking on it.        
        Step 1: Get current mouse position and current screenshot.        
        Step 2: Analyze the screenshot to locate the "App" window.        
        Step 3: Plan the mouse movement to the coordinates of the "App" window.        
        Step 4: Use mouse_move(x, y) to move the cursor to the window.        
        Step 5: Analyze the screenshot to confirm that the submission was successful.        
        Step 6: Execute mouse_click('left') to set the focus.        
        Step 7: Analyze the screenshot to confirm that the focus is set.        
        Step 8: If confirmation is visible, the task is complete. If not, try again, 
        without asking the user for permission.        

        ## Available Commands:

        mouse_move(x, y): Moves the cursor to the specified (x, y) screen coordinates.        
        mouse_click(button): Simulates a mouse click with the specified button ('left', 'right', or 'middle').        
        keyboard_type(text): Types the specified text string at the current cursor focus.        
        keyboard_key(text): Presses the keyboard key at the current cursor focus.        
        get_mouse_position(): Returns the current mouse cursor coordinates.        
        get_screenshot(): Provides an updated screenshot of the current screen.
        Note: Always ensure that your actions are context-aware and based on the most recent screenshot to 
        account for any changes on the screen.  

        ## Important: Use only one command at a time and wait for the updated screenshot before proceeding to the next step.

        Note: In case of failure, keep trying until the task is completed successfully.
        """
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
            "get_mouse_position",
            instruction="get current mouse coordinates and visual description of the screen provided by the vision model",
            params=[
                {
                    "name": "current_step",
                    "type": "text",
                    "description": "description of the current step in the task (for the vision model)",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: get current mouse position",
        )
        self.add_cmd(
            "get_screenshot",
            instruction="make screenshot",
            params=[],
            enabled=True,
            description="Enable: make screenshot",
        )
        self.add_cmd(
            "mouse_move",
            instruction="move mouse cursor to position (x, y)",
            params=[
                {
                    "name": "mouse_x",
                    "type": "int",
                    "description": "X coordinate",
                    "required": True,
                },
                {
                    "name": "mouse_y",
                    "type": "int",
                    "description": "Y coordinate",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: set mouse position to X,Y",
        )
        """
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
        """
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
            if self.cmd_exe():
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

        self.handle_delayed(ctx)

    @Slot(object)
    def handle_delayed(self, ctx: CtxItem):
        """
        Handle delayed screenshot

        :param ctx: context (CtxItem)
        """
        if self.get_option_value("allow_screenshot"):
            self.window.controller.attachment.clear_silent()
            path = self.window.controller.painter.capture.screenshot(attach_cursor=True,
                                                                     silent=True)  # attach screenshot
            ctx.images.append(path)
            ctx.images_before.append(path)
        self.window.core.dispatcher.reply(ctx, flush=True)

    @Slot(dict, object)
    def handle_screenshot(self, response: dict, ctx: CtxItem = None):
        """
        Handle screenshot

        :param response: response
        :param ctx: context (CtxItem)
        """
        self.window.controller.attachment.clear_silent()
        self.window.controller.painter.capture.screenshot(attach_cursor=True, silent=True)
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
        if self.is_threaded():
            return
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
