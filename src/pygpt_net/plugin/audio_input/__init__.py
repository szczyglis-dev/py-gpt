#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.provider.audio_input.base import BaseProvider
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .worker import Worker
from. simple import Simple


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.handler_simple = Simple(self)
        self.id = "audio_input"
        self.name = "Audio Input"
        self.type = [
            'audio.input',
        ]
        self.description = "Enables speech recognition"
        self.input_text = None
        self.speech_enabled = False
        self.thread_started = False
        self.listening = False
        self.waiting = False
        self.stop = False
        self.magic_word_detected = False
        self.is_first_adjust = True
        self.empty_phrases = [
            'Thank you for watching',
        ]  # phrases to ignore (fix for empty phrases)
        self.order = 1
        self.use_locale = True
        self.input_file = "input.wav"

    def init_options(self):
        """Initialize options"""
        self.add_option(
            "provider",
            type="combo",
            value="openai_whisper",
            label="Provider",
            description="Select audio transcribe provider, default: OpenAI Whisper",
            tooltip="Select audio transcribe provider",
            keys=self.get_provider_options(),
        )
        self.add_option(
            "auto_send",
            type="bool",
            value=True,
            label="Auto send",
            description="Automatically send input when voice is detected. Default: True",
        )
        self.add_option(
            "advanced",
            type="bool",
            value=False,
            label="Enable advanced mode",
            description="Enable only if you want to use advanced mode and settings below, "
                        "do not enable this option if you just want to use simple mode (default)",
        )
        self.add_option(
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
        self.add_option(
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
        self.add_option(
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
        self.add_option(
            "adjust_noise",
            type="bool",
            value=True,
            label="Adjust ambient noise",
            description="Adjust for ambient noise. Default: True",
            advanced=True,
        )
        self.add_option(
            "continuous_listen",
            type="bool",
            value=False,
            label="Continuous listening",
            description="EXPERIMENTAL: continuous listening - do not stop listening after a single input.\n"
                        "Warning: This feature may lead to unexpected results and requires fine-tuning "
                        "with the rest of the options!",
            advanced=True,
        )
        self.add_option(
            "wait_response",
            type="bool",
            value=True,
            label="Wait for response",
            description="Wait for a response before listening for the next input. Default: True",
            advanced=True,
        )
        self.add_option(
            "magic_word",
            type="bool",
            value=False,
            label="Magic word",
            description="Activate listening only after the magic word is provided, "
                        "like 'Hey GPT' or 'OK GPT'. Default: False",
            advanced=True,
        )
        self.add_option(
            "magic_word_reset",
            type="bool",
            value=True,
            label="Reset Magic word",
            description="Reset the magic word status after it is received "
                        "(the magic word will need to be provided again). Default: True",
            advanced=True,
        )
        self.add_option(
            "magic_words",
            type="text",
            value="OK, Okay, Hey GPT, OK GPT",
            label="Magic words",
            description="Specify magic words for 'Magic word' option: if received this word then "
                        "start listening, put words separated by comma. Magic word option must be enabled, "
                        "examples: \"Hey GPT, OK GPT\"",
            advanced=True,
        )
        self.add_option(
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
        self.add_option(
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
        self.add_option(
            "prefix_words",
            type="text",
            value="",
            label="Prefix words",
            description="Specify prefix words: if defined, only phrases starting with these words "
                        "will be transmitted, and the remainder will be ignored. Separate the words with "
                        "a comma., eg. 'OK, Okay, GPT'. Leave empty to disable",
            advanced=True,
        )
        self.add_option(
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
        self.add_option(
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
        self.add_option(
            "recognition_dynamic_energy_threshold",
            type="bool",
            value=True,
            label="dynamic_energy_threshold",
            description="Represents whether the energy level threshold for sounds should be automatically "
                        "adjusted based on the currently ambient noise level while listening. "
                        "Default: True",
            advanced=True,
        )
        self.add_option(
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
        self.add_option(
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
        self.add_option(
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

        # register provider options
        self.init_provider()

    def init_provider(self):
        """Initialize provider options"""
        providers = self.get_providers()
        for id in providers:
            providers[id].init(self)

    def get_providers(self) -> dict:
        """
        Get audio input providers

        :return: providers dict
        """
        return self.window.core.audio.get_providers("input")

    def get_provider_options(self) -> list:
        """
        Get provider options

        :return: list of provider options
        """
        options = []
        providers = self.get_providers()
        for id in providers:
            options.append({id: providers[id].name})
        return options

    def init_tabs(self) -> dict:
        """
        Initialize provider tabs

        :return: dict of tabs
        """
        tabs = {}
        tabs["general"] = "General"
        providers = self.get_providers()
        for id in providers:
            tabs[id] = providers[id].name
        return tabs

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def setup_ui(self):
        """
        Setup UI
        """
        pass

    def is_advanced(self) -> bool:
        """
        Check if advanced options are enabled

        :return: True if advanced options are enabled
        """
        return self.get_option_value("advanced")

    def get_words(self, key: str) -> list:
        """
        Get and parse words from option string

        :param key: option key
        :return: words list
        """
        words_str = self.get_option_value(key)
        words = []
        if words_str is not None and len(words_str) > 0 and words_str.strip() != ' ':
            words = words_str.split(',')
            words = [x.strip() for x in words]  # remove white-spaces
        return words

    def toggle_recording_simple(self):
        """
        Event: AUDIO_INPUT_RECORD_TOGGLE

        Toggle recording
        """
        self.handler_simple.toggle_recording()

    def toggle_speech(self, state: bool):
        """
        Event: AUDIO_INPUT_TOGGLE

        Toggle speech

        :param state: state to set
        """
        if not self.is_advanced():
            return

        self.speech_enabled = state
        self.window.ui.plugin_addon['audio.input'].btn_toggle.setChecked(state)

        # Start thread if not started
        if state:
            self.listening = True
            self.stop = False
            self.handle_thread()
        else:
            self.listening = False
            self.set_status('')

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

        # register provider tabs
        self.tabs = self.init_tabs()

        # register options
        self.init_options()

    def get_provider(self) -> BaseProvider:
        """
        Get audio input provider

        :return: provider instance
        """
        current = self.get_option_value("provider")
        providers = self.get_providers()
        if current not in providers:
            raise Exception("Provider '{}' not found!".format(current))
        return providers[current]

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: args
        :param kwargs: kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.INPUT_BEFORE:
            self.on_input_before(data['value'])

        elif name == Event.CTX_BEGIN:
            self.on_ctx_begin(ctx)

        elif name == Event.CTX_END:
            self.on_ctx_end(ctx)

        elif name == Event.ENABLE:
            if data['value'] == self.id:
                self.on_enable()

        elif name == Event.DISABLE:
            if data['value'] == self.id:
                self.on_disable()

        elif name == Event.AUDIO_INPUT_TOGGLE:
            self.toggle_speech(data['value'])

        elif name == Event.AUDIO_INPUT_RECORD_TOGGLE:
            self.toggle_recording_simple()

        elif name == Event.AUDIO_INPUT_STOP:
            self.on_stop()

        elif name == Event.AUDIO_INPUT_TRANSCRIBE:
            self.handle_transcribe(data["path"])

        elif name == Event.PLUGIN_OPTION_GET:
            if "name" in data and data["name"] == "audio.input.advanced":
                data["value"] = self.is_advanced()

    def on_ctx_begin(self, ctx: CtxItem):
        """
        Event: CTX_BEGIN

        :param ctx: CtxItem
        """
        self.waiting = True

    def on_ctx_end(self, ctx: CtxItem):
        """
        Event: CTX_END

        :param ctx: CtxItem
        """
        self.waiting = False

    def on_enable(self):
        """Event: ENABLE"""
        if not self.is_advanced():
            return

        self.speech_enabled = True
        self.handle_thread()

    def on_disable(self):
        """Event: DISABLE"""
        self.speech_enabled = False
        self.listening = False
        self.stop = True
        self.window.ui.plugin_addon['audio.input'].btn_toggle.setChecked(False)
        self.set_status('')
        self.window.ui.status("")

    def on_stop(self):
        """Event: AUDIO_INPUT_STOP"""
        if not self.is_advanced():
            return

        self.stop = True
        self.listening = False
        self.speech_enabled = False
        self.set_status('')
        self.window.ui.status("")

    def on_input_before(self, text: str):
        """
        Event: INPUT_BEFORE

        :param text: text from input
        """
        self.input_text = text

    def destroy(self):
        """Destroy thread"""
        self.waiting = True
        self.listening = False
        self.thread_started = False
        self.set_status('')

    @Slot(str, str)
    def handle_transcribed(self, path: str, text: str):
        """
        Handle transcribed text

        :param path: audio file path
        :param text: transcribed text
        """
        self.window.tools.get("transcriber").on_transcribe(path, text)

    def handle_transcribe(self, path: str):
        """
        Handle transcribe thread

        :param path: audio file path
        """
        try:
            # worker
            worker = Worker()
            worker.plugin = self
            worker.path = path
            worker.transcribe = True  # file transcribe mode

            # signals
            worker.signals.transcribed.connect(self.handle_transcribed)
            worker.signals.finished.connect(self.handle_input)
            worker.signals.destroyed.connect(self.handle_destroy)
            worker.signals.started.connect(self.handle_started)
            worker.signals.stopped.connect(self.handle_stop)
            worker.signals.status.connect(self.handle_status)
            worker.signals.error.connect(self.handle_error)

            # start
            self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

    def handle_thread(self, force: bool = False):
        """
        Handle listener thread

        :param force: force start
        """
        if self.thread_started and not force:
            return

        try:
            # worker
            worker = Worker()
            worker.plugin = self
            worker.path = os.path.join(
                self.window.core.config.path,
                self.input_file,
            )
            worker.advanced = self.is_advanced()  # advanced mode

            # signals
            worker.signals.transcribed.connect(self.handle_transcribed)
            worker.signals.finished.connect(self.handle_input)
            worker.signals.destroyed.connect(self.handle_destroy)
            worker.signals.started.connect(self.handle_started)
            worker.signals.stopped.connect(self.handle_stop)
            worker.signals.status.connect(self.handle_status)
            worker.signals.error.connect(self.handle_error)

            # start
            self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

    def can_listen(self) -> bool:
        """
        Check if can listen

        :return: True if can listen
        """
        state = True
        if self.get_option_value('wait_response') \
                and self.window.controller.chat.input.generating:
            state = False
        if self.window.controller.chat.input.locked:
            state = False
        return state

    def set_status(self, status: str):
        """
        Set status

        :param status: status text
        """
        self.window.ui.plugin_addon['audio.input'].set_status(status)

    @Slot(object, object)
    def handle_input(self, text: str, ctx: CtxItem = None):
        """
        Insert text to input and send

        :param text: text
        :param ctx: CtxItem
        """
        if text is None or text.strip() == '':
            return

        # simple mode
        if not self.is_advanced():
            check = text.strip().lower()
            for phrase in self.empty_phrases:
                phrase_check = phrase.strip().lower()
                if phrase_check in check:
                    return

        # advanced mode
        if self.is_advanced():
            if not self.can_listen():
                return

            # check prefix words
            prefix_words = self.get_words('prefix_words')
            if len(prefix_words) > 0:
                for word in prefix_words:
                    check_text = text.lower().strip()
                    check_word = word.lower().strip()
                    if not check_text.startswith(check_word):
                        self.window.ui.status(trans('audio.speak.ignoring'))
                        self.set_status(trans('audio.speak.ignoring'))
                        return

            # previous magic word detected state
            magic_prev_detected = self.magic_word_detected
            # save the magic word detected state before checking for magic word

            # check for magic word
            is_magic_word = False
            if self.get_option_value('magic_word'):
                for word in self.get_words('magic_words'):
                    # prepare magic word
                    check_word = word.lower().replace('.', '')
                    check_text = text.lower()
                    if check_text.startswith(check_word):
                        is_magic_word = True
                        self.set_status(trans('audio.magic_word.detected'))
                        self.window.ui.status(trans('audio.magic_word.detected'))
                        break

            # if magic word enabled
            if self.get_option_value('magic_word'):
                if not is_magic_word:
                    if self.get_option_value('magic_word_reset'):
                        self.magic_word_detected = False
                else:
                    self.magic_word_detected = True

                # if not previously detected, then abort now
                if not magic_prev_detected:
                    if not is_magic_word:
                        self.window.ui.status(trans('audio.magic_word.invalid'))
                    self.window.ui.nodes['input'].setText(text)
                    return
                else:
                    self.window.ui.status("")

        # update input text
        self.window.ui.nodes['input'].setText(text)

        # send text
        if self.get_option_value('auto_send'):
            # to: notepad
            if self.window.controller.notepad.is_active():
                idx = self.window.controller.notepad.get_current_active()
                self.window.controller.notepad.append_text(text, idx)
                self.set_status('')
                self.window.controller.chat.render.clear_input()  # clear here
            # to: calendar
            elif self.window.controller.calendar.is_active():
                self.window.controller.calendar.note.append_text(text)
                self.set_status('')
                self.window.controller.chat.render.clear_input()  # clear here
            # to: chat
            else:
                self.set_status('...')
                self.window.ui.status(trans('audio.speak.sending'))
                prefix = ""
                if self.window.controller.agent.enabled():
                    prefix = "user: "
                self.window.controller.chat.input.send(prefix + text)  # send text, input clear in send method
                self.set_status('')

    @Slot(object)
    def handle_status(self, data: str):
        """
        Handle thread status msg signal

        :param data: message
        """
        self.set_status(str(data))
        self.window.ui.status(str(data))

    @Slot()
    def handle_destroy(self):
        """Handle listener destroyed"""
        self.thread_started = False
        self.set_status('')
        self.window.ui.status("")

    @Slot()
    def handle_started(self):
        """Handle listening started"""
        self.thread_started = True
        # print("Whisper is listening...")

    @Slot()
    def handle_stop(self):
        """Handle stop listening"""
        self.thread_started = False
        self.listening = False
        self.stop = False
        self.window.ui.status("")
        self.set_status('')
        self.toggle_speech(False)
