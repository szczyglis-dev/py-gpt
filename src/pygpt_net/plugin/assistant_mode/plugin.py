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

import time
import threading

from PySide6.QtCore import Slot, QTimer

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "assistant_mode"
        self.name = "Assistant Mode"
        self.type = [
            "audio.control",
        ]
        self.description = (
            "Orchestrates Wake Word, Audio Input, and Audio Output plugins into a "
            "seamless voice assistant loop: wake word -> listen -> respond -> repeat."
        )
        self.prefix = "Assistant"
        self.order = 200  # after other plugins
        self.use_locale = True
        self.config = Config(self)

        # State
        self.active = False  # assistant mode is active
        self.in_conversation = False  # currently in a conversation turn
        self.last_interaction_time = 0
        self.timeout_timer = None
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

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

        if name == Event.ENABLE:
            if data["value"] == self.id:
                self.on_enable()

        elif name == Event.DISABLE:
            if data["value"] == self.id:
                self.on_disable()

        elif name == Event.INPUT_BEFORE:
            if self.active:
                self.on_input_before(data.get("value", ""))

        elif name == Event.CTX_BEGIN:
            if self.active:
                self.in_conversation = True

        elif name == Event.CTX_END:
            if self.active and self.in_conversation:
                self.on_response_complete(ctx)

    def on_enable(self):
        """Enable assistant mode and set up required plugins"""
        self.active = True
        self.log("Assistant Mode activated")

        if self.get_option_value("auto_enable_plugins"):
            plugins_to_enable = ["wake_word", "audio_input", "audio_output"]
            for pid in plugins_to_enable:
                plugin = self.window.core.plugins.get(pid)
                if plugin and not plugin.enabled:
                    self.window.controller.plugins.enable(pid)
                    self.log("Auto-enabled plugin: {}".format(pid))

    def on_disable(self):
        """Disable assistant mode"""
        self.active = False
        self.in_conversation = False
        self.stop_timeout_timer()
        self.log("Assistant Mode deactivated")

    def on_input_before(self, text: str):
        """
        Called before user input is sent. Check for stop words.

        :param text: user input text
        """
        self.last_interaction_time = time.time()

        stop_words_str = self.get_option_value("stop_words")
        if stop_words_str:
            stop_words = [w.strip().lower() for w in stop_words_str.split(",") if w.strip()]
            text_lower = text.strip().lower().replace(".", "").replace("!", "").replace("?", "")
            for stop_word in stop_words:
                if stop_word in text_lower:
                    self.log("Stop word detected: '{}'. Ending conversation.".format(stop_word))
                    self.end_conversation()
                    return

    def on_response_complete(self, ctx: CtxItem):
        """
        Called when AI response is complete (after TTS playback).
        Decides whether to continue listening.

        :param ctx: context item
        """
        self.in_conversation = False

        if not self.active:
            return

        if self.get_option_value("require_wake_word_each_turn"):
            # Go back to wake word mode
            self.log("Waiting for wake word...")
            return

        # Auto-listen for next command
        if self.get_option_value("auto_listen_after_response"):
            delay = self.get_option_value("response_delay")
            if delay and delay > 0:
                # Use QTimer for thread-safe delayed execution
                QTimer.singleShot(int(delay * 1000), self.start_listening)
            else:
                self.start_listening()

            # Start conversation timeout
            self.start_timeout_timer()

    def start_listening(self):
        """Trigger audio input to start listening"""
        if not self.active:
            return

        audio_input = self.window.core.plugins.get("audio_input")
        if audio_input is None or not audio_input.enabled:
            return

        self.log("Listening for next command...")
        self.last_interaction_time = time.time()

        if not audio_input.is_advanced():
            audio_input.toggle_recording_simple(state=True, auto=True)
        else:
            audio_input.magic_word_detected = True
            if not audio_input.speech_enabled:
                audio_input.toggle_speech(True)

    def end_conversation(self):
        """End the conversation loop, go back to wake word mode"""
        self.in_conversation = False
        self.stop_timeout_timer()
        self.log("Conversation ended, returning to wake word mode")

    def start_timeout_timer(self):
        """Start the conversation timeout timer"""
        timeout = self.get_option_value("conversation_timeout")
        if timeout <= 0:
            return

        self.stop_timeout_timer()
        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.on_timeout)
        self.timeout_timer.start(timeout * 1000)

    def stop_timeout_timer(self):
        """Stop the conversation timeout timer"""
        if self.timeout_timer is not None:
            try:
                self.timeout_timer.stop()
            except RuntimeError:
                pass
            self.timeout_timer = None

    @Slot()
    def on_timeout(self):
        """Handle conversation timeout"""
        if not self.active:
            return

        elapsed = time.time() - self.last_interaction_time
        timeout = self.get_option_value("conversation_timeout")
        if elapsed >= timeout:
            self.log("Conversation timed out ({} seconds)".format(timeout))
            self.end_conversation()

    def on_wake_word_activated(self):
        """
        Called by wake_word plugin when wake word is detected.
        Can be used to speak a greeting.
        """
        if not self.active:
            return

        self.last_interaction_time = time.time()

        if self.get_option_value("greeting_enabled"):
            greeting = self.get_option_value("greeting_text")
            if greeting:
                self.speak_text(greeting)

    def speak_text(self, text: str):
        """
        Speak text using the audio output system

        :param text: text to speak
        """
        audio_output = self.window.core.plugins.get("audio_output")
        if audio_output is None or not audio_output.enabled:
            return

        try:
            ctx = CtxItem()
            ctx.output = text
            event = Event(Event.AUDIO_READ_TEXT, ctx=ctx)
            self.window.dispatch(event)
        except Exception as e:
            self.log("Error speaking text: {}".format(str(e)))

    def destroy(self):
        """Destroy plugin"""
        self.active = False
        self.in_conversation = False
        self.stop_timeout_timer()
