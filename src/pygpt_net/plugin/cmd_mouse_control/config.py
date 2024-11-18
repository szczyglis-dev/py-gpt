#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 19:00:00                  #
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
        plugin.add_option(
            "allow_mouse_move",
            type="bool",
            value=True,
            label="Allow mouse movement",
            description="Allow mouse movement",
        )
        plugin.add_option(
            "allow_mouse_click",
            type="bool",
            value=True,
            label="Allow mouse click",
            description="Allow mouse click",
        )
        plugin.add_option(
            "allow_mouse_scroll",
            type="bool",
            value=True,
            label="Allow mouse scroll",
            description="Allow mouse scroll",
        )
        plugin.add_option(
            "allow_keyboard",
            type="bool",
            value=True,
            label="Allow keyboard key press",
            description="Allow keyboard key press",
        )
        plugin.add_option(
            "allow_screenshot",
            type="bool",
            value=True,
            label="Allow making screenshot",
            description="Allow making screenshot",
        )
        plugin.add_option(
            "auto_focus",
            type="bool",
            value=False,
            label="Auto-focus on the window",
            description="Auto-focus on the window (mouse click) before keyboard typing",
        )
        plugin.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt used to instruct how to control the mouse and keyboard",
            description="Prompt used to instruct how to control the mouse and keyboard",
            tooltip="Prompt used to instruct how to control the mouse and keyboard",
        )

        # commands
        plugin.add_cmd(
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
        plugin.add_cmd(
            "get_screenshot",
            instruction="make screenshot",
            params=[],
            enabled=True,
            description="Enable: make screenshot",
        )
        plugin.add_cmd(
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
        plugin.add_cmd(
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
        plugin.add_cmd(
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
        plugin.add_cmd(
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
        plugin.add_cmd(
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
        plugin.add_cmd(
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