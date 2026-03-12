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

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event

from .config import Config
from .worker import WakeWordWorker


# Built-in model name mapping for OpenWakeWord
BUILTIN_MODELS = {
    "hey_jarvis": ["hey_jarvis_v0.1"],
    "hey_mycroft": ["hey_mycroft_v0.1"],
    "alexa": ["alexa_v0.1"],
    "ok_google": ["ok_google_v0.1"],
    "hey_siri": ["hey_siri_v0.1"],
}


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "wake_word"
        self.name = "Wake Word"
        self.type = [
            "audio.control",
        ]
        self.description = (
            "Provides always-on wake word detection using OpenWakeWord. "
            "When the wake word is detected, it triggers audio input recording."
        )
        self.prefix = "WakeWord"
        self.urls = {
            "OpenWakeWord": "https://github.com/dscripka/openWakeWord",
        }
        self.order = 0  # before audio_input
        self.use_locale = True
        self.listening = False
        self.worker = None
        self.config = Config(self)
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

        if name == Event.ENABLE:
            if data["value"] == self.id:
                self.on_enable()

        elif name == Event.DISABLE:
            if data["value"] == self.id:
                self.on_disable()

        elif name == Event.CTX_END:
            # After response is complete, restart listening
            if self.listening:
                self.log("Response complete, wake word listener active")

    def on_enable(self):
        """Start wake word listener when plugin is enabled"""
        if self.get_option_value("auto_enable_audio_input"):
            self.window.controller.plugins.enable("audio_input")

        self.start_listener()

    def on_disable(self):
        """Stop wake word listener when plugin is disabled"""
        self.stop_listener()

    def start_listener(self):
        """Start the wake word background listener thread"""
        if self.listening:
            return

        self.listening = True

        try:
            worker = WakeWordWorker()
            worker.from_defaults(self)
            worker.threshold = self.get_option_value("threshold")
            worker.cooldown_seconds = self.get_option_value("cooldown_seconds")

            # Resolve model paths
            model_key = self.get_option_value("wake_word_model")
            if model_key == "custom":
                custom_path = self.get_option_value("custom_model_path")
                if custom_path:
                    worker.model_paths = [custom_path]
            elif model_key in BUILTIN_MODELS:
                # OpenWakeWord handles built-in models by name
                worker.model_paths = None  # use defaults or specify
            else:
                worker.model_paths = None

            # Connect signals
            worker.signals.wake_word_detected.connect(self.handle_wake_word_detected)

            self.worker = worker
            worker.run_async()

            self.log("Wake word listener started")

        except Exception as e:
            self.listening = False
            self.error(e)

    def stop_listener(self):
        """Stop the wake word background listener thread"""
        self.listening = False
        self.worker = None
        self.log("Wake word listener stopped")

    @Slot(str)
    def handle_wake_word_detected(self, model_name: str):
        """
        Handle wake word detection event

        :param model_name: name of the detected wake word model
        """
        self.log("Wake word detected: {}".format(model_name))

        # Play audio feedback if enabled
        if self.get_option_value("audio_feedback"):
            self.play_detection_sound()

        # Notify assistant mode if active
        self.notify_assistant_mode()

        # Trigger audio input recording
        self.trigger_audio_input()

    def trigger_audio_input(self):
        """Trigger the audio input plugin to start recording"""
        audio_input = self.window.core.plugins.get("audio_input")
        if audio_input is None or not audio_input.enabled:
            self.log("Audio Input plugin is not enabled, cannot trigger recording")
            return

        # For simple mode: toggle recording on
        if not audio_input.is_advanced():
            audio_input.toggle_recording_simple(state=True, auto=True)
        else:
            # For advanced mode: set magic word as detected and enable listening
            audio_input.magic_word_detected = True
            if not audio_input.speech_enabled:
                audio_input.toggle_speech(True)

    def notify_assistant_mode(self):
        """Notify the assistant mode plugin about wake word activation"""
        assistant = self.window.core.plugins.get("assistant_mode")
        if assistant is not None and assistant.enabled:
            assistant.on_wake_word_activated()

    def play_detection_sound(self):
        """Play a short beep sound to indicate wake word detection"""
        try:
            from PySide6.QtMultimedia import QSoundEffect
            from PySide6.QtCore import QUrl
            import os

            # Use system beep as fallback
            beep_path = os.path.join(
                self.window.core.config.get_app_path(),
                "data", "audio", "wake_word_beep.wav",
            )
            if os.path.exists(beep_path):
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(beep_path))
                effect.play()
            else:
                # Fallback: system bell
                print("\a", end="", flush=True)
        except Exception:
            # Silent fallback
            print("\a", end="", flush=True)

    def destroy(self):
        """Destroy plugin and stop listener"""
        self.stop_listener()
