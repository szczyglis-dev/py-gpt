#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.05 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.provider.audio_output.base import BaseProvider
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "audio_output"
        self.name = "Audio Output"
        self.type = ['audio.output']
        self.description = "Enables audio/voice output (speech synthesis)"
        self.input_text = None
        self.playback = None
        self.order = 1
        self.use_locale = True
        self.output_file = "output.mp3"

    def init_options(self):
        """Initialize options"""
        self.add_option(
            "provider",
            type="combo",
            value="openai_tts",
            label="Provider",
            description="Select audio output provider, default: OpenAI TTS",
            tooltip="Select audio output provider",
            keys=self.get_provider_options(),
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
        Get audio output providers

        :return: providers dict
        """
        return self.window.core.audio.get_providers("output")

    def get_provider_options(self) -> list:
        """Get provider options"""
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
        Get audio output provider

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

        elif name in [
            Event.CTX_AFTER,
            Event.AUDIO_READ_TEXT
        ]:
            self.on_ctx_after(ctx, event)

        elif name == Event.AUDIO_OUTPUT_STOP:
            self.stop_audio()

    def on_input_before(self, text: str):
        """
        Event: INPUT_BEFORE

        :param text: text to read
        """
        self.input_text = text

    def on_ctx_after(self, ctx: CtxItem, event: Event):
        """
        Events: CTX_AFTER, AUDIO_READ_TEXT

        :param ctx: CtxItem
        :param event: Event
        """
        # check if provider is configured
        if not self.get_provider().is_configured():
            msg = self.get_provider().get_config_message()
            self.window.ui.dialogs.alert(msg)
            return

        name = event.name
        text = ctx.output
        cache_file = None
        if event.data is not None and isinstance(event.data, dict) and "cache_file" in event.data:
            cache_file = event.data["cache_file"]
        
        try:
            if text is not None and len(text) > 0:
                # worker
                worker = Worker()
                worker.plugin = self
                worker.event = name
                worker.cache_file = cache_file
                worker.text = self.window.core.audio.clean_text(text)

                # signals
                worker.signals.playback.connect(self.handle_playback)
                worker.signals.stop.connect(self.handle_stop)
                worker.signals.status.connect(self.handle_status)  # base handler
                worker.signals.error.connect(self.handle_error)  # base handler

                # start
                self.window.threadpool.start(worker)

                # only for manual reading
                if name == Event.AUDIO_READ_TEXT:
                    self.window.controller.audio.on_begin(worker.text)

        except Exception as e:
            self.error(e)

    def destroy(self):
        """Destroy thread"""
        pass

    def set_status(self, status: str):
        """
        Set status

        :param status: status text
        """
        self.window.ui.plugin_addon['audio.output'].set_status(status)

    def show_stop_button(self):
        """Show stop button"""
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(True)

    def hide_stop_button(self):
        """Hide stop button"""
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(False)

    def stop_speak(self):
        """Stop speaking"""
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(False)
        self.window.ui.plugin_addon['audio.output'].set_status('Stopped')
        self.window.ui.plugin_addon['audio.output'].stop_audio()

    def stop_audio(self):
        """
        Event: AUDIO_OUTPUT_STOP

        Stop playing the audio
        """
        if self.playback is not None:
            self.playback.stop()
            self.playback = None

    @Slot(object, str)
    def handle_playback(self, playback, event: str):
        """
        Handle thread playback object

        :param playback: playback object
        :param event: event name
        """
        self.playback = playback
        self.window.controller.audio.on_play(event)

    @Slot()
    def handle_stop(self):
        """Handle thread playback stop"""
        self.stop_audio()
