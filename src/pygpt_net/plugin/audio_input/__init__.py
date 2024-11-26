#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 19:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Slot

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.provider.audio_input.base import BaseProvider
from pygpt_net.core.events import Event, KernelEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .config import Config
from .worker import Worker
from .simple import Simple


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
        self.prefix = "Audio Input"
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
        self.config = Config(self)

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)
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
        self.window.update_status("")

    def on_stop(self):
        """Event: AUDIO_INPUT_STOP"""
        if not self.is_advanced():
            return

        self.stop = True
        self.listening = False
        self.speech_enabled = False
        self.set_status('')
        self.window.update_status("")

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
            worker = Worker()
            worker.from_defaults(self)
            worker.path = path
            worker.transcribe = True  # file transcribe mode

            # signals
            worker.signals.transcribed.connect(self.handle_transcribed)
            worker.signals.finished.connect(self.handle_input)
            worker.signals.destroyed.connect(self.handle_destroy)
            worker.signals.started.connect(self.handle_started)
            worker.signals.stopped.connect(self.handle_stop)

            worker.run_async()

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
            worker = Worker()
            worker.from_defaults(self)
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
            worker.signals.on_realtime.connect(self.handle_realtime)

            worker.run_async()

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

    @Slot(str)
    def handle_realtime(self, path: str):
        """
        Handle realtime audio input

        :param path: audio input file path
        """
        self.window.controller.chat.audio.handle_input(path)

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
                        self.window.update_status(trans('audio.speak.ignoring'))
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
                        self.window.update_status(trans('audio.magic_word.detected'))
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
                        self.window.update_status(trans('audio.magic_word.invalid'))
                    self.window.ui.nodes['input'].setText(text)
                    return
                else:
                    self.window.update_status("")

        # update input text
        self.window.ui.nodes['input'].setText(text)

        # send text
        if self.get_option_value('auto_send'):
            # to: notepad
            if self.window.controller.notepad.is_active():
                idx = self.window.controller.notepad.get_current_active()
                self.window.controller.notepad.append_text(text, idx)
                self.set_status('')

                data = {}
                event = RenderEvent(RenderEvent.CLEAR_INPUT, data)
                self.window.dispatch(event)  # clear here

            # to: calendar
            elif self.window.controller.calendar.is_active():
                self.window.controller.calendar.note.append_text(text)
                self.set_status('')

                data = {}
                event = RenderEvent(RenderEvent.CLEAR_INPUT, data)
                self.window.dispatch(event)  # clear here

            # to: chat
            else:
                self.set_status('...')
                self.window.update_status(trans('audio.speak.sending'))
                prefix = ""
                if self.window.controller.agent.legacy.enabled():
                    prefix = "user: "

                context = BridgeContext()
                context.prompt = prefix + text
                extra = {}
                event = KernelEvent(KernelEvent.INPUT_SYSTEM, {
                    'context': context,
                    'extra': extra,
                })
                self.window.dispatch(event)  # send text, input clear in send method
                self.set_status('')

    @Slot(object)
    def handle_status(self, data: str):
        """
        Handle thread status msg signal

        :param data: message
        """
        self.set_status(str(data))
        self.window.update_status(str(data))

    @Slot()
    def handle_destroy(self):
        """Handle listener destroyed"""
        self.thread_started = False
        self.set_status('')
        self.window.update_status("")

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
        self.window.update_status("")
        self.set_status('')
        self.toggle_speech(False)
