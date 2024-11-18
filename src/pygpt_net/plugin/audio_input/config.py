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
        plugin.add_option(
            "provider",
            type="combo",
            value="openai_whisper",
            label="Provider",
            description="Select audio transcribe provider, default: OpenAI Whisper",
            tooltip="Select audio transcribe provider",
            keys=plugin.get_provider_options(),
        )
        plugin.add_option(
            "auto_send",
            type="bool",
            value=True,
            label="Auto send",
            description="Automatically send input when voice is detected. Default: True",
        )
        plugin.add_option(
            "advanced",
            type="bool",
            value=False,
            label="Enable advanced mode",
            description="Enable only if you want to use advanced mode and settings below, "
                        "do not enable this option if you just want to use simple mode (default)",
        )
        plugin.add_option(
            "timeout",
            type="int",
            value=5,
            label="Timeout",
            description="Speech recognition timeout. Default: 5",
            min=0,
            max=30,
            slider=True,
            tooltip="Timeout, default: 5",
            advanced=True,
        )
        plugin.add_option(
            "phrase_length",
            type="int",
            value=10,
            label="Phrase max length",
            description="Speech recognition phrase length. Default: 10",
            min=0,
            max=30,
            slider=True,
            tooltip="Phrase max length, default: 10",
            advanced=True,
        )
        plugin.add_option(
            "min_energy",
            type="float",
            value=1.3,
            label="Min. energy",
            description="Minimum threshold multiplier above the noise level to begin recording;"
                        " 1 = disabled. Default: 1.3",
            min=1,
            max=50,
            slider=True,
            tooltip="Min. energy, default: 1.3, 1 = disabled, adjust for your microphone",
            multiplier=10,
            advanced=True,
        )
        plugin.add_option(
            "adjust_noise",
            type="bool",
            value=True,
            label="Adjust ambient noise",
            description="Adjust for ambient noise. Default: True",
            advanced=True,
        )
        plugin.add_option(
            "continuous_listen",
            type="bool",
            value=False,
            label="Continuous listening",
            description="EXPERIMENTAL: continuous listening - do not stop listening after a single input.\n"
                        "Warning: This feature may lead to unexpected results and requires fine-tuning "
                        "with the rest of the options!",
            advanced=True,
        )
        plugin.add_option(
            "wait_response",
            type="bool",
            value=True,
            label="Wait for response",
            description="Wait for a response before listening for the next input. Default: True",
            advanced=True,
        )
        plugin.add_option(
            "magic_word",
            type="bool",
            value=False,
            label="Magic word",
            description="Activate listening only after the magic word is provided, "
                        "like 'Hey GPT' or 'OK GPT'. Default: False",
            advanced=True,
        )
        plugin.add_option(
            "magic_word_reset",
            type="bool",
            value=True,
            label="Reset Magic word",
            description="Reset the magic word status after it is received "
                        "(the magic word will need to be provided again). Default: True",
            advanced=True,
        )
        plugin.add_option(
            "magic_words",
            type="text",
            value="OK, Okay, Hey GPT, OK GPT",
            label="Magic words",
            description="Specify magic words for 'Magic word' option: if received this word then "
                        "start listening, put words separated by comma. Magic word option must be enabled, "
                        "examples: \"Hey GPT, OK GPT\"",
            advanced=True,
        )
        plugin.add_option(
            "magic_word_timeout",
            type="int",
            value=1,
            label="Magic word timeout",
            description="Magic word recognition timeout. Default: 1",
            min=0,
            max=30,
            slider=True,
            tooltip="Timeout, default: 1",
            advanced=True,
        )
        plugin.add_option(
            "magic_word_phrase_length",
            type="int",
            value=2,
            label="Magic word phrase max length",
            description="Magic word phrase length. Default: 2",
            min=0,
            max=30,
            slider=True,
            tooltip="Phrase length, default: 2",
            advanced=True,
        )
        plugin.add_option(
            "prefix_words",
            type="text",
            value="",
            label="Prefix words",
            description="Specify prefix words: if defined, only phrases starting with these words "
                        "will be transmitted, and the remainder will be ignored. Separate the words with "
                        "a comma., eg. 'OK, Okay, GPT'. Leave empty to disable",
            advanced=True,
        )
        plugin.add_option(
            "stop_words",
            type="text",
            value="stop, exit, quit, end, finish, close, terminate, kill, halt, abort",
            label="Stop words",
            description="Specify stop words: if any of these words are received, then stop listening. "
                        "Separate the words with a comma, or leave it empty to disable the feature, "
                        "default: stop, exit, quit, end, finish, close, terminate, kill, halt, abort",
            advanced=True,
        )

        # advanced options
        plugin.add_option(
            "recognition_energy_threshold",
            type="int",
            value=300,
            label="energy_threshold",
            description="Represents the energy level threshold for sounds. Default: 300",
            min=0,
            max=10000,
            slider=True,
            advanced=True,
        )
        plugin.add_option(
            "recognition_dynamic_energy_threshold",
            type="bool",
            value=True,
            label="dynamic_energy_threshold",
            description="Represents whether the energy level threshold for sounds should be automatically "
                        "adjusted based on the currently ambient noise level while listening. "
                        "Default: True",
            advanced=True,
        )
        plugin.add_option(
            "recognition_dynamic_energy_adjustment_damping",
            type="float",
            value=0.15,
            label="dynamic_energy_adjustment_damping",
            description="Represents approximately the fraction of the current energy threshold that is "
                        "retained after one second of dynamic threshold adjustment. Default: 0.15",
            min=0,
            max=100,
            slider=True,
            multiplier=100,
            advanced=True,
        )
        plugin.add_option(
            "recognition_pause_threshold",
            type="float",
            value=0.8,
            label="pause_threshold",
            description="Represents the minimum length of silence (in seconds) that will register as the end "
                        "of a phrase.\nDefault: 0.8",
            min=0,
            max=100,
            slider=True,
            multiplier=10,
            advanced=True,
        )
        plugin.add_option(
            "recognition_adjust_for_ambient_noise_duration",
            type="float",
            value=1,
            label="adjust_for_ambient_noise: duration",
            description="The duration parameter is the maximum number of seconds that it will dynamically "
                        "adjust the threshold for before returning. Default: 1",
            min=0,
            max=100,
            slider=True,
            multiplier=10,
            advanced=True,
        )