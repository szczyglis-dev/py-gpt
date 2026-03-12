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
            "wake_word_model",
            type="combo",
            value="hey_jarvis",
            label="Wake word model",
            description="Select the wake word model to use for activation. "
                        "Default: hey_jarvis",
            tooltip="Select wake word model",
            keys=[
                {"hey_jarvis": "Hey Jarvis"},
                {"hey_mycroft": "Hey Mycroft"},
                {"alexa": "Alexa"},
                {"ok_google": "OK Google"},
                {"hey_siri": "Hey Siri"},
                {"custom": "Custom (specify path below)"},
            ],
        )
        plugin.add_option(
            "custom_model_path",
            type="text",
            value="",
            label="Custom model path",
            description="Path to a custom OpenWakeWord .tflite model file. "
                        "Only used when 'Custom' is selected above.",
            tooltip="Path to custom .tflite model",
        )
        plugin.add_option(
            "threshold",
            type="float",
            value=0.5,
            label="Detection threshold",
            description="Confidence threshold for wake word detection. "
                        "Higher = fewer false positives. Range: 0.1 - 1.0. Default: 0.5",
            min=0.1,
            max=1.0,
            slider=True,
            multiplier=10,
            tooltip="Detection threshold, default: 0.5",
        )
        plugin.add_option(
            "cooldown_seconds",
            type="int",
            value=3,
            label="Cooldown (seconds)",
            description="Minimum seconds between consecutive wake word detections "
                        "to prevent rapid re-triggering. Default: 3",
            min=1,
            max=15,
            slider=True,
            tooltip="Cooldown between detections, default: 3",
        )
        plugin.add_option(
            "audio_feedback",
            type="bool",
            value=True,
            label="Audio feedback on detection",
            description="Play a short beep sound when wake word is detected. Default: True",
        )
        plugin.add_option(
            "auto_enable_audio_input",
            type="bool",
            value=True,
            label="Auto-enable Audio Input plugin",
            description="Automatically enable the Audio Input plugin when this plugin is enabled. "
                        "Default: True",
        )
