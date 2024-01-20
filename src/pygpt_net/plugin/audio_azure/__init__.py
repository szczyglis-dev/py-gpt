#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.20 12:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Slot

from .worker import Worker
from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "audio_azure"
        self.name = "Audio Output (MS Azure)"
        self.type = ['audio.output']
        self.description = "Enables audio/voice output (speech synthesis) using Microsoft Azure API"
        self.input_text = None
        self.playback = None
        self.order = 9999
        self.use_locale = True
        self.output_file = "output.mp3"
        self.init_options()

    def init_options(self):
        """Initialize options"""
        url_api = {
            "API Key": "https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech",
        }
        self.add_option("azure_api_key",
                        type="text",
                        value="",
                        label="Azure API Key",
                        description="You can obtain your own API key at: "
                        "https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/",
                        tooltip="Azure API Key",
                        secret=True,
                        persist=True,
                        urls=url_api)
        self.add_option("azure_region",
                        type="text",
                        value="eastus",
                        label="Azure Region",
                        description="Specify Azure region, e.g. eastus",
                        tooltip="Azure Region")
        self.add_option("voice_en",
                        type="text",
                        value="en-US-AriaNeural",
                        label="Voice (EN)",
                        description="Specify voice for English language, e.g. en-US-AriaNeural",
                        tooltip="Voice (EN)")
        self.add_option("voice_pl",
                        type="text",
                        value="pl-PL-AgnieszkaNeural",
                        label="Voice (non-English)",
                        description="Specify voice for non-English languages, "
                                    "e.g. pl-PL-MarekNeural or pl-PL-AgnieszkaNeural",
                        tooltip="Voice (PL)")

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.INPUT_BEFORE:
            self.on_input_before(data['value'])
        elif name == Event.CTX_AFTER:
            self.on_ctx_after(ctx)
        elif name == Event.AUDIO_OUTPUT_STOP:
            self.stop_audio()

    def on_input_before(self, text: str):
        """
        Event: Before input

        :param text: Text
        """
        self.input_text = text

    def on_ctx_after(self, ctx: CtxItem):
        """
        Event: After ctx

        :param ctx: CtxItem
        """
        # Check if api key is set
        api_key = self.get_option_value("azure_api_key")
        region = self.get_option_value("azure_region")

        if api_key is None or api_key == "":
            self.window.ui.dialogs.alert("Azure API KEY is not set. Please set it in plugin settings.")
            return
        if region is None or region == "":
            self.window.ui.dialogs.alert("Azure Region is not set. Please set it in plugin settings.")
            return

        text = ctx.output
        path = os.path.join(self.window.core.config.path, self.output_file)
        try:
            if text is not None and len(text) > 0:
                lang = self.window.core.config.get('lang')
                if lang == "en":
                    voice = self.get_option_value("voice_en")
                else:
                    voice = self.get_option_value("voice_pl")

                # worker
                worker = Worker()
                worker.plugin = self
                worker.api_key = api_key
                worker.region = region
                worker.voice = voice
                worker.text = self.window.core.audio.clean_text(text)
                worker.path = path

                # signals
                worker.signals.playback.connect(self.handle_playback)
                worker.signals.stop.connect(self.handle_stop)
                worker.signals.status.connect(self.handle_status)  # base handler
                worker.signals.error.connect(self.handle_error)  # base handler

                # start
                self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

    def set_status(self, status: str):
        """
        Set status

        :param status: status
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
        """Stop playing the audio"""
        if self.playback is not None:
            self.playback.stop()
            self.playback = None

    @Slot(object)
    def handle_playback(self, playback):
        """
        Handle thread playback object

        :param playback
        """
        self.playback = playback

    @Slot()
    def handle_stop(self):
        """Handle thread playback stop"""
        self.stop_audio()
