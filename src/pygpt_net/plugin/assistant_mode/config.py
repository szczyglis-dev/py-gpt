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
        plugin.add_option(
            "auto_listen_after_response",
            type="bool",
            value=True,
            label="Auto-listen after response",
            description="Automatically start listening for voice input after the AI finishes "
                        "speaking its response. Creates a continuous conversation loop. Default: True",
        )
        plugin.add_option(
            "require_wake_word_each_turn",
            type="bool",
            value=False,
            label="Require wake word each turn",
            description="If enabled, the user must say the wake word before each command. "
                        "If disabled, after the first wake word the assistant stays in "
                        "continuous conversation mode until a stop word is detected. Default: False",
        )
        plugin.add_option(
            "conversation_timeout",
            type="int",
            value=30,
            label="Conversation timeout (seconds)",
            description="If no input is received within this time, the assistant goes back to "
                        "wake word listening mode. Set to 0 to disable. Default: 30",
            min=0,
            max=120,
            slider=True,
            tooltip="Conversation timeout in seconds, default: 30, 0 = disabled",
        )
        plugin.add_option(
            "stop_words",
            type="text",
            value="goodbye, bye, stop listening, that's all, go to sleep",
            label="Stop words",
            description="Phrases that end the conversation loop and return to wake word mode. "
                        "Separate with commas.",
        )
        plugin.add_option(
            "greeting_enabled",
            type="bool",
            value=True,
            label="Greeting on activation",
            description="Speak a short greeting when the assistant is activated by wake word. "
                        "Default: True",
        )
        plugin.add_option(
            "greeting_text",
            type="text",
            value="Yes?",
            label="Greeting text",
            description="Text to speak when the assistant is activated. Default: Yes?",
        )
        plugin.add_option(
            "auto_enable_plugins",
            type="bool",
            value=True,
            label="Auto-enable required plugins",
            description="Automatically enable Wake Word, Audio Input, and Audio Output plugins "
                        "when Assistant Mode is enabled. Default: True",
        )
        plugin.add_option(
            "response_delay",
            type="float",
            value=0.5,
            label="Post-response delay (seconds)",
            description="Delay after audio response finishes before listening again. "
                        "Prevents the assistant from hearing its own voice. Default: 0.5",
            min=0.0,
            max=3.0,
            slider=True,
            multiplier=10,
        )
