#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.utils import trans
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "audio_openai_whisper"
        self.name = "Audio Input (OpenAI Whisper)"
        self.type = ['audio.input']
        self.description = "Enables speech recognition using OpenAI Whisper API"
        self.input_text = None
        self.window = None
        self.speech_enabled = False
        self.thread_started = False
        self.listening = False
        self.waiting = False
        self.stop = False
        self.magic_word_detected = False
        self.is_first_adjust = True
        self.empty_phrases = ['Thank you for watching']  # phrases to ignore (fix for empty phrases)
        self.order = 1
        self.use_locale = True
        self.input_file = "input.wav"
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.add_option("model", "text", "whisper-1",
                        "Model",
                        "Specify model, default: whisper-1")
        self.add_option("timeout", "int", 2,
                        "Timeout",
                        "Speech recognition timeout. Default: 2", min=0, max=30, slider=True,
                        tooltip="Timeout, default: 2")
        self.add_option("phrase_length", "int", 4,
                        "Phrase max length",
                        "Speech recognition phrase length. Default: 4", min=0, max=30, slider=True,
                        tooltip="Phrase max length, default: 4")
        self.add_option("min_energy", "float", 1.3,
                        "Min. energy",
                        "Minimum threshold multiplier above the noise level to begin recording; 1 = disabled. "
                        "Default: 1.3",
                        min=1, max=50, slider=True,
                        tooltip="Min. energy, default: 1.3, 1 = disabled, adjust for your microphone", multiplier=10)
        self.add_option("adjust_noise", "bool", True,
                        "Adjust ambient noise",
                        "Adjust for ambient noise. Default: True")
        self.add_option("continuous_listen", "bool", False,
                        "Continuous listening",
                        "EXPERIMENTAL: continuous listening - do not stop listening after a single input.\n"
                        "Warning: This feature may lead to unexpected results and requires fine-tuning with the rest "
                        "of the options!")
        self.add_option("auto_send", "bool", True,
                        "Auto send",
                        "Automatically send input when voice is detected. Default: True")
        self.add_option("wait_response", "bool", True,
                        "Wait for response",
                        "Wait for a response before listening for the next input. Default: True")
        self.add_option("magic_word", "bool", False,
                        "Magic word",
                        "Activate listening only after the magic word is provided, like 'Hey GPT' or 'OK GPT'. "
                        "Default: False")
        self.add_option("magic_word_reset", "bool", True,
                        "Reset Magic word",
                        "Reset the magic word status after it is received "
                        "(the magic word will need to be provided again). Default: True")
        self.add_option("magic_words", "text", "OK, Okay, Hey GPT, OK GPT",
                        "Magic words",
                        "Specify magic words for 'Magic word' option: if received this word then start listening, "
                        "put words separated by coma, "
                        "Magic word option must be enabled, examples: \"Hey GPT, OK GPT\"")
        self.add_option("magic_word_timeout", "int", 1,
                        "Magic word timeout",
                        "Magic word recognition timeout. Default: 1", min=0, max=30, slider=True,
                        tooltip="Timeout, default: 1")
        self.add_option("magic_word_phrase_length", "int", 2,
                        "Magic word phrase max length",
                        "Magic word phrase length. Default: 2", min=0, max=30, slider=True,
                        tooltip="Phrase length, default: 2")
        self.add_option("prefix_words", "text", "",
                        "Prefix words",
                        "Specify prefix words: if defined, only phrases starting with these words will be transmitted, "
                        "and the remainder will be ignored. Separate the words with a comma., eg. 'OK, Okay, GPT'. "
                        "Leave empty to disable")
        self.add_option("stop_words", "text", "stop, exit, quit, end, finish, close, terminate, kill, halt, abort",
                        "Stop words",
                        "Specify stop words: if any of these words are received, then stop listening. "
                        "Separate the words with a comma, or leave it empty to disable the feature, "
                        "default: stop, exit, quit, end, finish, close, terminate, kill, "
                        "halt, abort")

        # advanced options
        self.add_option("recognition_energy_threshold", "int", 300,
                        "energy_threshold",
                        "Represents the energy level threshold for sounds. Default: 300", min=0, max=10000,
                        slider=True, advanced=True)
        self.add_option("recognition_dynamic_energy_threshold", "bool", True,
                        "dynamic_energy_threshold",
                        "Represents whether the energy level threshold "
                        "for sounds should be automatically adjusted based on the currently "
                        "ambient noise level while listening. Default: True", advanced=True)
        self.add_option("recognition_dynamic_energy_adjustment_damping", "float", 0.15,
                        "dynamic_energy_adjustment_damping",
                        "Represents approximately the fraction of the current energy threshold that "
                        "is retained after one second of dynamic threshold adjustment. Default: 0.15", min=0, max=100,
                        slider=True, multiplier=100, advanced=True)
        self.add_option("recognition_pause_threshold", "float", 0.8,
                        "pause_threshold",
                        "Represents the minimum length of silence (in seconds) that will "
                        "register as the end of a phrase. \nDefault: 0.8",
                        min=0, max=100, slider=True, multiplier=10, advanced=True)
        self.add_option("recognition_adjust_for_ambient_noise_duration", "float", 1,
                        "adjust_for_ambient_noise: duration",
                        "The duration parameter is the maximum number of seconds that it will "
                        "dynamically adjust the threshold for before returning. Default: 1", min=0, max=100,
                        slider=True, multiplier=10, advanced=True)

    def setup(self):
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

    def get_words(self, key):
        """
        Get and parse words from option string

        :param key: option key
        :return: words
        :rtype: list
        """
        words_str = self.get_option_value(key)
        words = []
        if words_str is not None and len(words_str) > 0 and words_str.strip() != ' ':
            words = words_str.split(',')
            words = [x.strip() for x in words]  # remove white-spaces
        return words

    def toggle_speech(self, state):
        """
        Toggle speech

        :param state: state to set
        """
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

    def handle(self, event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == 'input.before':
            self.on_input_before(data['value'])
        elif name == 'ctx.begin':
            self.on_ctx_begin(ctx)
        elif name == 'ctx.end':
            self.on_ctx_end(ctx)
        elif name == 'enable':
            if data['value'] == self.id:
                self.on_enable()
        elif name == 'disable':
            if data['value'] == self.id:
                self.on_disable()
        elif name == 'audio.input.toggle':
            self.toggle_speech(data['value'])
        elif name == 'audio.input.stop':
            self.on_stop()

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: CtxItem
        """
        self.waiting = True

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: CtxItem
        """
        self.waiting = False

    def on_enable(self):
        """Event: On plugin enable"""
        self.speech_enabled = True
        self.handle_thread()

    def on_disable(self):
        """Event: On plugin disable"""
        self.speech_enabled = False
        self.listening = False
        self.stop = True
        self.window.ui.plugin_addon['audio.input'].btn_toggle.setChecked(False)
        self.set_status('')

    def on_stop(self):
        """Event: On input stop"""
        self.stop = True
        self.listening = False
        self.speech_enabled = False
        self.set_status('')

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: text
        """
        self.input_text = text

    def destroy(self):
        """Destroy thread"""
        self.waiting = True
        self.listening = False
        self.thread_started = False
        self.set_status('')

    def handle_thread(self):
        """Handle listener thread"""
        if self.thread_started:
            return

        # worker
        worker = Worker()
        worker.plugin = self
        worker.client = self.window.core.gpt.get_client()
        worker.path = os.path.join(self.window.core.config.path, self.input_file)

        # signals
        worker.signals.finished.connect(self.handle_input)
        worker.signals.destroyed.connect(self.handle_destroy)
        worker.signals.started.connect(self.handle_started)
        worker.signals.stopped.connect(self.handle_stop)
        worker.signals.status.connect(self.handle_status)
        worker.signals.error.connect(self.handle_error)

        # start
        self.window.threadpool.start(worker)
        self.thread_started = True

    def can_listen(self):
        """
        Check if can listen

        :return: true if can listen
        :rtype: bool
        """
        state = True
        if self.get_option_value('wait_response') and self.window.controller.input.generating:
            state = False
        if self.window.controller.input.locked:
            state = False
        return state

    def set_status(self, status):
        """
        Set status

        :param status: status
        """
        self.window.ui.plugin_addon['audio.input'].set_status(status)

    @Slot(object, object)
    def handle_input(self, text, ctx=None):
        """
        Insert text to input and send

        :param text: text
        :param ctx: CtxItem
        """
        if text is None or text.strip() == '':
            return

        if not self.can_listen():
            return

        # check prefix words
        prefix_words = self.get_words('prefix_words')
        if len(prefix_words) > 0:
            for word in prefix_words:
                check_text = text.lower().strip()
                check_word = word.lower().strip()
                if not check_text.startswith(check_word):
                    self.window.set_status(trans('audio.speak.ignoring'))
                    self.set_status(trans('audio.speak.ignoring'))
                    return

        # previous magic word detected state
        magic_prev_detected = self.magic_word_detected  # save magic word detected state before checking for magic word

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
                    self.window.set_status(trans('audio.magic_word.detected'))
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
                    self.window.set_status(trans('audio.magic_word.invalid'))
                self.window.ui.nodes['input'].setText(text)
                return
            else:
                self.window.set_status("")

        # update input text
        self.window.ui.nodes['input'].setText(text)

        # send text
        if self.get_option_value('auto_send'):
            self.set_status('...')
            self.window.set_status(trans('audio.speak.sending'))
            self.window.controller.input.send(text)
            self.set_status('')

    @Slot(object)
    def handle_status(self, data):
        """
        Handle thread status msg signal

        :param data: message
        """
        self.set_status(str(data))
        self.window.set_status(str(data))

    @Slot()
    def handle_destroy(self):
        """Handle listener destroyed"""
        self.thread_started = False
        self.set_status('')

    @Slot()
    def handle_started(self):
        """Handle listening started"""
        pass
        # print("Whisper is listening...")

    @Slot()
    def handle_stop(self):
        """Handle stop listening"""
        self.thread_started = False
        self.listening = False
        self.stop = False
        self.window.set_status("")
        self.set_status('')
        # print("Whisper stopped listening...")
        self.toggle_speech(False)
