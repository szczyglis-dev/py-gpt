#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.04 11:00:00                  #
# ================================================== #

import json
import re
from datetime import datetime, timedelta

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.utils import trans
from .events import ControlEvent, AppEvent


class Voice:
    def __init__(self, window=None):
        """
        Voice access core

        :param window: Window instance
        """
        self.window = window
        self.commands = {
            ControlEvent.APP_STATUS: "Get the current application status",
            ControlEvent.APP_EXIT: "Exit the application",
            ControlEvent.AUDIO_OUTPUT_ENABLE: "Enable audio output",
            ControlEvent.AUDIO_OUTPUT_DISABLE: "Disable audio output",
            ControlEvent.AUDIO_INPUT_ENABLE: "Enable audio input",
            ControlEvent.AUDIO_INPUT_DISABLE: "Disable audio input",
            ControlEvent.CALENDAR_ADD: "Add a memo to the calendar",
            ControlEvent.CALENDAR_CLEAR: "Clear memos from calendar",
            ControlEvent.CALENDAR_READ: "Read the calendar memos",
            ControlEvent.CAMERA_ENABLE: "Enable the camera",
            ControlEvent.CAMERA_DISABLE: "Disable the camera",
            ControlEvent.CAMERA_CAPTURE: "Capture image from camera",
            ControlEvent.CMD_CONFIRM: "Confirmation of the command",
            ControlEvent.CMD_LIST: "Get available commands list",
            ControlEvent.CTX_NEW: "Create a new context",
            ControlEvent.CTX_PREV: "Go to the previous context",
            ControlEvent.CTX_NEXT: "Go to the next context",
            ControlEvent.CTX_LAST: "Go to the latest context",
            ControlEvent.CTX_INPUT_FOCUS: "Focus on the input",
            ControlEvent.CTX_INPUT_SEND: "Send the input",
            ControlEvent.CTX_INPUT_CLEAR: "Clear the input",
            ControlEvent.CTX_CURRENT: "Get current conversation info",
            ControlEvent.CTX_STOP: "Stop executing current action",
            ControlEvent.CTX_ATTACHMENTS_CLEAR: "Clear the attachments",
            ControlEvent.CTX_READ_LAST: "Read the last conversation entry",
            ControlEvent.CTX_READ_ALL: "Read the whole conversation",
            ControlEvent.CTX_RENAME: "Rename current context",
            ControlEvent.CTX_SEARCH_STRING: "Search for a conversation",
            ControlEvent.CTX_SEARCH_CLEAR: "Clear the search results",
            ControlEvent.INPUT_SEND: "Send the message to input",
            ControlEvent.INPUT_APPEND: "Append message to current input without sending it",
            ControlEvent.MODE_CHAT: "Switch to chat mode",
            ControlEvent.MODE_LLAMA_INDEX: "Switch to chat with files (llama-index) mode",
            ControlEvent.MODE_NEXT: "Switch to the next mode",
            ControlEvent.MODE_PREV: "Switch to the previous mode",
            ControlEvent.MODEL_NEXT: "Switch to the next model",
            ControlEvent.MODEL_PREV: "Switch to the previous model",
            ControlEvent.NOTE_ADD: "Add note to notepad",
            ControlEvent.NOTEPAD_CLEAR: "Clear notepad contents",
            ControlEvent.NOTEPAD_READ: "Read current notepad contents",
            ControlEvent.PRESET_NEXT: "Switch to the next preset",
            ControlEvent.PRESET_PREV: "Switch to the previous preset",
            ControlEvent.TAB_CHAT: "Switch to the chat tab",
            ControlEvent.TAB_CALENDAR: "Switch to the calendar tab",
            ControlEvent.TAB_DRAW: "Switch to the draw (painter) tab",
            ControlEvent.TAB_FILES: "Switch to the files tab",
            ControlEvent.TAB_NOTEPAD: "Switch to the notepad tab",
            ControlEvent.TAB_NEXT: "Switch to the next tab",
            ControlEvent.TAB_PREV: "Switch to the previous tab",
            ControlEvent.VOICE_MESSAGE_START: "Start listening for voice input",
            ControlEvent.VOICE_MESSAGE_STOP: "Stop listening for voice input",
            ControlEvent.VOICE_MESSAGE_TOGGLE: "Toggle listening for voice input",
        }

    def get_commands(self) -> dict:
        """
        Get available commands

        :return: commands
        """
        cmds = {}
        for k, v in self.commands.items():
            if not self.is_blacklisted(k):
                cmds[k] = v
        return cmds

    def get_commands_string(self, values: bool = False) -> str:
        """
        Get available commands as string

        :param values: if True, then only values are returned
        :return: commands list as string
        """
        if values:
            numbered = {}
            for i, v in enumerate(self.get_commands().values()):
                numbered[str(i+1)] = v
            return "\n".join([f"{k}) {v}" for k, v in numbered.items()])
        else:
            return "\n".join([f"{k} = {v}" for k, v in self.get_commands().items()])

    def get_prompt(self, text: str) -> str:
        """
        Get prompt for voice command recognition

        :param text: text to be spoken
        :return: prompt
        """
        commands_str = self.get_commands_string()
        prompt = """
        Recognize the voice command and select the corresponding command from the list below. 
        Return the chosen command ID as a JSON string in the following syntax:

        {"cmd": "command_id", "params": "optional message"}
        
        If no command matches the voice request, then return "unknown" as the command ID.
        If user provide additional message, it should be extracted from voice command and included (WITHOUT the command part) in the JSON response in "params" param.
        
        Important: Only the JSON specified above should be returned in the response, without any additional text.
        
        Available command IDs (with descriptions):
        ----------------------
        """+commands_str+"""        
        
        User's voice input to recognize:
        
        """+text

        return prompt.strip()

    def get_inline_prompt(self, prefix: str = None) -> str:
        """
        Get prompt for inline voice command recognition

        :return: prompt
        """
        prefix_addon = ""
        if prefix is not None and prefix.strip() != "":
            prefix_addon = ' or action prefixed via "{}" (or similar)'.format(prefix)

        prompt = """
           If user provides the voice action (as a text)"""+prefix_addon+""" then recognize this voice action and execute the corresponding voice action from the enum list.
           If no defined actions matches the requested action, then return "unknown" as the action. Do not try to execute any other voice commands.
           If user provide additional message, it should be extracted from query and included (WITHOUT the action part) in the "args" param.
           IMPORTANT: Only execute actions from provided list and remember than list describes only voice actions, not real commands, so don't execute any commands from this list separately.
           When calling voice action, the action should be returned in a JSON string, without any additional text.
           JSON schema required for voice action is below:
           {"cmd": "voice_cmd", "params": {"action": "action_id", "args": "optional message"}}
           """

        return prompt.strip()

    def extract_json(self, text: str) -> list:
        """
        Extract JSON from text

        :param text: text
        :return: JSON
        """
        json_pattern = r'(\{.*?\})'
        cmds = []
        enabled_cmds = self.get_commands()
        matches = re.findall(json_pattern, text, re.DOTALL)
        if len(matches) > 0:
            for match in matches:
                try:
                    data = json.loads(match)
                    if "cmd" in data:
                        cmd = data["cmd"]
                        if cmd in enabled_cmds:
                            item = {
                                "cmd": cmd,
                                "params": data.get("params", "")
                            }
                            cmds.append(item)
                        else:
                            cmds.append({
                                "cmd": "unrecognized",
                                "params": ""
                            })
                except Exception as e:
                    self.window.core.debug.log(e)
        return cmds

    def recognize_commands(self, text: str) -> list:
        """
        Recognize voice command

        :param text: voice input
        :return: recognized command
        """
        prompt = self.get_prompt(text)
        model = self.window.core.models.from_defaults()
        tmp_model = self.window.core.config.get("access.voice_control.model", "gpt-3.5-turbo")
        if self.window.core.models.has(tmp_model):
            model = self.window.core.models.get(tmp_model)
        bridge_context = BridgeContext(
            prompt=prompt,
            system_prompt="You are a helpful assistant",
            model=model,  # model instance
            max_tokens=0,
            temperature=0.0,
        )
        response = self.window.core.bridge.quick_call(
            context=bridge_context,
        )
        if response is None or response == "":
            return []

        return self.extract_json(response)

    def is_muted(self, action: str) -> bool:
        """
        Check if audio event is blacklisted

        :param action: event name
        :return: True if blacklisted
        """
        data = self.window.core.config.get("access.audio.event.speech.disabled")
        if data is None or not isinstance(data, list):
            return False
        for item in data:
            if "muted_action" in item and item["muted_action"] == action:
                return True
        return False

    def is_blacklisted(self, action: str) -> bool:
        """
        Check if audio control action is blacklisted

        :param action: action name
        :return: True if blacklisted
        """
        data = self.window.core.config.get("access.voice_control.blacklist")
        if data is None or not isinstance(data, list):
            return False
        for item in data:
            if "disabled_action" in item and item["disabled_action"] == action:
                return True
        return False

    def get_status(self) -> str:
        """
        Get the current application status

        :return: status, text to read
        """
        ctx = ""
        total = self.window.core.ctx.count_meta()
        meta = self.window.core.ctx.get_current_meta()
        mode = trans("mode." + self.window.core.config.get("mode"))
        mode += " " + self.get_selected_model()
        mode += " " + self.get_selected_preset()
        tab = self.window.controller.ui.get_current_tab_name()
        last = ""
        msg = ""
        if meta is not None:
            ctx = meta.name
            last = self.convert_date(meta.updated)
        try:
            msg = trans("event.audio.app.status").format(
                mode=mode,
                tab=tab,
                ctx=ctx,
                last=last,
                total=total,
            )
        except Exception as e:
            pass
        return msg

    def get_current_ctx(self) -> str:
        """
        Get current context

        :return: text to read
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is not None:
            name = meta.name
            updated = self.convert_date(meta.updated)
            try:
                msg = trans("event.audio.ctx.current").format(
                    ctx=name,
                    last=updated,
                )
            except Exception as e:
                msg = ""
            return msg
        return ""

    def get_selected_ctx(self) -> str:
        """
        Get current context

        :return: text to read
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is not None:
            name = meta.name
            updated = self.convert_date(meta.updated)
            try:
                msg = trans("event.audio.ctx.selected").format(
                    ctx=name,
                    last=updated,
                )
            except Exception as e:
                msg = ""
            return msg
        return ""

    def get_selected_tab(self) -> str:
        """
        Get current tab

        :return: text to read
        """
        msg = ""
        tab = self.window.controller.ui.get_current_tab_name()
        try:
            msg = trans("event.audio.tab.switch").format(
                tab=tab,
            )
        except Exception as e:
            pass
        return msg

    def get_selected_mode(self) -> str:
        """
        Get current mode

        :return: text to read
        """
        mode = self.window.core.config.get("mode")
        if mode is None:
            return ""
        try:
            msg = trans("event.audio.mode.selected").format(
                mode=trans("mode." + mode),
            )
        except Exception as e:
            msg = ""
        return msg

    def get_selected_model(self) -> str:
        """
        Get current model

        :return: text to read
        """
        model = self.window.core.config.get("model")
        if model is None:
            return ""
        try:
            msg = trans("event.audio.model.selected").format(
                model=model,
            )
        except Exception as e:
            msg = ""
        return msg

    def get_selected_preset(self) -> str:
        """
        Get current preset

        :return: text to read
        """
        preset_id = self.window.core.config.get("preset")
        if preset_id is None:
            return ""
        mode = self.window.core.config.get("mode")
        preset = self.window.core.presets.get_by_id(mode, preset_id)
        if preset is None:
            return ""
        try:
            msg = trans("event.audio.preset.selected").format(
                preset=preset.name,
            )
        except Exception as e:
            msg = ""
        return msg


    def get_last_ctx_item(self) -> str:
        """
        Get last context item

        :return: text to read
        """
        text = ""
        item = self.window.core.ctx.get_last()
        if item is not None:
            try:
                text = trans("event.audio.ctx.last").format(
                    input=item.input,
                    output=item.output,
                )
            except Exception as e:
                pass
        return text

    def get_all_ctx_items(self) -> str:
        """
        Get all context items

        :return: text to read
        """
        text = ""
        entries = []
        items = self.window.core.ctx.get_all_items(ignore_first=False)
        for item in items:
            try:
                entries.append(trans("event.audio.ctx.last").format(
                    input=item.input,
                    output=item.output,
                ))
            except Exception as e:
                pass
        if len(entries) > 0:
            text = "\n".join(entries)
        return text

    def convert_date(self, timestamp: int) -> str:
        """
        Convert timestamp to human readable format

        :param timestamp: timestamp
        :return: string
        """
        today = datetime.today().date()
        yesterday = today - timedelta(days=1)
        date = datetime.fromtimestamp(timestamp).date()
        hour_min = datetime.fromtimestamp(timestamp).strftime("%H:%M")

        days_ago = (today - date).days
        weeks_ago = days_ago // 7

        if date == today:
            return trans('dt.today') + " " + hour_min
        elif date == yesterday:
            return trans('dt.yesterday') + " " + hour_min
        elif weeks_ago == 1:
            return trans('dt.week')
        elif 1 < weeks_ago < 4:
            return f"{weeks_ago} " + trans('dt.weeks')
        elif days_ago < 30:
            return f"{days_ago} " + trans('dt.days_ago')
        elif 30 <= days_ago < 32:
            return trans('dt.month')
        else:
            return date.strftime("%Y-%m-%d")