#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 02:00:00                  #
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

        # Playwright sandbox options
        plugin.add_option(
            "sandbox_path",
            type="text",
            value="",
            label="Browsers directory",
            description="Path to Playwright browsers installation - leave empty to use default",
            tab="Sandbox (Playwright)"
        )
        plugin.add_option(
            "sandbox_engine",
            type="text",
            value="chromium",
            label="Engine",
            description="Playwright browser engine to use (chromium, firefox, webkit) - must be installed",
            tab="Sandbox (Playwright)"
        )
        plugin.add_option(
            "sandbox_headless",
            type="bool",
            value=False,
            label="Headless mode",
            description="Run Playwright browser in headless mode (default: False)",
            tab="Sandbox (Playwright)"
        )
        plugin.add_option(
            "sandbox_args",
            type="textarea",
            value="--disable-extensions,\n--disable-file-system",
            label="Browser args",
            description="Additional Playwright browser arguments (comma-separated)",
            tab="Sandbox (Playwright)"
        )
        plugin.add_option(
            "sandbox_home",
            type="text",
            value="https://duckduckgo.com",
            label="Home URL",
            description="Playwright browser home URL",
            tab="Sandbox (Playwright)"
        )
        plugin.add_option(
            "sandbox_viewport_w",
            type="int",
            value=1440,
            label="Viewport width",
            description="Playwright viewport width in pixels",
            tab="Sandbox (Playwright)"
        )
        plugin.add_option(
            "sandbox_viewport_h",
            type="int",
            value=900,
            label="Viewport height",
            description="Playwright viewport height in pixels",
            tab="Sandbox (Playwright)"
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
            "open_web_browser",
            instruction="open web browser",
            params=[],
            enabled=True,
            description="Enable: open web browser",
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
                {
                    "name": "click",
                    "type": "str",
                    "description": "button to click after moving the mouse, enum: left|middle|right",
                    "required": False,
                },
                {
                    "name": "num_clicks",
                    "type": "int",
                    "description": "number of clicks, e.g. use 2 to double-click",
                    "required": False,
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
                    "name": "x",
                    "type": "int",
                    "description": "move to initial position X before scrolling",
                    "required": False,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "move to initial position Y before scrolling",
                    "required": False,
                },
                {
                    "name": "dx",
                    "type": "int",
                    "description": "steps or px to scroll horizontally, positive to the left, negative to the right",
                    "required": True,
                },
                {
                    "name": "dy",
                    "type": "int",
                    "description": "steps or px to scroll vertically, positive to scroll up, negative to scroll down",
                    "required": True,
                },
                {
                    "name": "unit",
                    "type": "str",
                    "description": "unit of scroll value, enum: pixel|step",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Mouse scroll",
        )
        plugin.add_cmd(
            "mouse_drag",
            instruction="mouse drag",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "move to initial position X before scrolling",
                    "required": False,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "move to initial position Y before scrolling",
                    "required": False,
                },
                {
                    "name": "dx",
                    "type": "int",
                    "description": "px to drag horizontally, positive to the left, negative to the right",
                    "required": True,
                },
                {
                    "name": "dy",
                    "type": "int",
                    "description": "px to drag vertically, positive to scroll down, negative to scroll up",
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
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Press keyboard key",
        )
        plugin.add_cmd(
            "keyboard_keys",
            instruction="press multiple keyboard keys at once",
            params=[
                {
                    "name": "keys",
                    "type": "list",
                    "description": "keys to press",
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
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Type text on keyboard",
        )
        plugin.add_cmd(
            "wait",
            instruction="wait for a moment",
            params=[],
            enabled=True,
            description="Enable: Wait for a moment",
        )

        # --------------------------------------------------------------------- #
        # Google based additional commands
        # --------------------------------------------------------------------- #

        plugin.add_cmd(
            "wait_5_seconds",
            instruction="wait for 5 seconds",
            params=[],
            enabled=True,
            description="Enable: Wait 5 seconds",
        )
        plugin.add_cmd(
            "go_back",
            instruction="go back in browser history",
            params=[],
            enabled=True,
            description="Enable: Browser back",
        )
        plugin.add_cmd(
            "go_forward",
            instruction="go forward in browser history",
            params=[],
            enabled=True,
            description="Enable: Browser forward",
        )
        plugin.add_cmd(
            "search",
            instruction="open the default search engine homepage",
            params=[],
            enabled=True,
            description="Enable: Open default search engine",
        )
        plugin.add_cmd(
            "navigate",
            instruction="navigate to a specific URL",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "destination URL",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Navigate to URL",
        )
        plugin.add_cmd(
            "click_at",
            instruction="click at normalized coordinates (0..999)",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "normalized X (0..999)",
                    "required": True,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "normalized Y (0..999)",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Click at normalized coordinates",
        )
        plugin.add_cmd(
            "hover_at",
            instruction="move cursor to normalized coordinates (0..999) without clicking",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "normalized X (0..999)",
                    "required": True,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "normalized Y (0..999)",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Hover at normalized coordinates",
        )
        plugin.add_cmd(
            "type_text_at",
            instruction="focus at normalized coordinates and type text; optionally press Enter and/or clear field first",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "normalized X (0..999)",
                    "required": True,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "normalized Y (0..999)",
                    "required": True,
                },
                {
                    "name": "text",
                    "type": "str",
                    "description": "text to type",
                    "required": True,
                },
                {
                    "name": "press_enter",
                    "type": "bool",
                    "description": "press Enter after typing (default: true)",
                    "required": False,
                },
                {
                    "name": "clear_before_typing",
                    "type": "bool",
                    "description": "clear input before typing (default: true)",
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Type text at normalized coordinates",
        )
        plugin.add_cmd(
            "key_combination",
            instruction="press a key combination (e.g., control+shift+tab)",
            params=[
                {
                    "name": "keys",
                    "type": "list",
                    "description": "list of keys to press in a combination or sequence",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Press key combination",
        )
        plugin.add_cmd(
            "scroll_document",
            instruction="scroll the document in a direction by a magnitude in pixels",
            params=[
                {
                    "name": "direction",
                    "type": "str",
                    "description": "scroll direction, enum: up|down|left|right",
                    "required": False,
                },
                {
                    "name": "magnitude",
                    "type": "int",
                    "description": "pixels to scroll (default around 800)",
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Scroll document",
        )
        plugin.add_cmd(
            "scroll_at",
            instruction="scroll at normalized coordinates (0..999) in a direction by a magnitude in pixels",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "normalized X (0..999)",
                    "required": False,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "normalized Y (0..999)",
                    "required": False,
                },
                {
                    "name": "direction",
                    "type": "str",
                    "description": "scroll direction, enum: up|down|left|right",
                    "required": False,
                },
                {
                    "name": "magnitude",
                    "type": "int",
                    "description": "pixels to scroll (default around 800)",
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Scroll at normalized coordinates",
        )
        plugin.add_cmd(
            "drag_and_drop",
            instruction="drag from normalized (x,y) to (destination_x,destination_y)",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "normalized start X (0..999)",
                    "required": True,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "normalized start Y (0..999)",
                    "required": True,
                },
                {
                    "name": "destination_x",
                    "type": "int",
                    "description": "normalized destination X (0..999)",
                    "required": True,
                },
                {
                    "name": "destination_y",
                    "type": "int",
                    "description": "normalized destination Y (0..999)",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Drag and drop using normalized coordinates",
        )
        plugin.add_cmd(
            "click",
            instruction="click at optional coordinates; if provided as normalized (0..999) they will be converted",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "X coordinate (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "Y coordinate (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "button",
                    "type": "str",
                    "description": "mouse button, enum: left|middle|right",
                    "required": False,
                },
                {
                    "name": "num_clicks",
                    "type": "int",
                    "description": "number of clicks, default 1",
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Generic click",
        )
        plugin.add_cmd(
            "double_click",
            instruction="double-click at optional coordinates; if provided as normalized (0..999) they will be converted",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "X coordinate (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "Y coordinate (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "button",
                    "type": "str",
                    "description": "mouse button, enum: left|middle|right",
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Generic double click",
        )
        plugin.add_cmd(
            "move",
            instruction="move pointer to the given coordinates; normalized (0..999) will be converted",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "X coordinate (pixel or normalized 0..999)",
                    "required": True,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "Y coordinate (pixel or normalized 0..999)",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Generic move",
        )
        plugin.add_cmd(
            "type",
            instruction="type literal text into the focused element",
            params=[
                {
                    "name": "text",
                    "type": "str",
                    "description": "text to type",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Generic type text",
        )
        plugin.add_cmd(
            "keypress",
            instruction="press a sequence of keys",
            params=[
                {
                    "name": "keys",
                    "type": "list",
                    "description": "list of keys to press sequentially",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Generic keypress sequence",
        )
        plugin.add_cmd(
            "scroll",
            instruction="scroll by dx, dy in pixels at an optional (x,y) position",
            params=[
                {
                    "name": "x",
                    "type": "int",
                    "description": "X position to move before scrolling (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "Y position to move before scrolling (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "dx",
                    "type": "int",
                    "description": "horizontal delta in pixels (positive right, negative left)",
                    "required": True,
                },
                {
                    "name": "dy",
                    "type": "int",
                    "description": "vertical delta in pixels (positive down, negative up)",
                    "required": True,
                },
                {
                    "name": "unit",
                    "type": "str",
                    "description": "unit of scroll value, enum: px|step",
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Generic scroll",
        )
        plugin.add_cmd(
            "drag",
            instruction="drag pointer along a path or from (x,y) to (dx,dy). Normalized coordinates (0..999) are supported.",
            params=[
                {
                    "name": "path",
                    "type": "list",
                    "description": "list of points with fields x,y (at least 2 points)",
                    "required": False,
                },
                {
                    "name": "x",
                    "type": "int",
                    "description": "start X (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "y",
                    "type": "int",
                    "description": "start Y (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "dx",
                    "type": "int",
                    "description": "destination X (pixel or normalized 0..999)",
                    "required": False,
                },
                {
                    "name": "dy",
                    "type": "int",
                    "description": "destination Y (pixel or normalized 0..999)",
                    "required": False,
                },
            ],
            enabled=True,
            description="Enable: Generic drag",
        )