#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

import os
import threading

import requests
from PySide6.QtCore import QObject, Signal, Slot
import pygame

from pygpt_net.plugin.base import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "audio_azure"
        self.name = "Audio Output (MS Azure)"
        self.type = ['audio.output']
        self.description = "Enables audio/voice output (speech synthesis) using Microsoft Azure API"
        self.input_text = None
        self.window = None
        self.thread = None
        self.tts = None
        self.playback = None
        self.audio = None
        self.order = 9999
        self.use_locale = True
        self.tts = None
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        url_api = {
            "API Key": "https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech",
        }
        self.add_option("azure_api_key", "text", "",
                        "Azure API Key",
                        "You can obtain your own API key at: "
                        "https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/",
                        tooltip="Azure API Key", secret=True, persist=True, urls=url_api)
        self.add_option("azure_region", "text", "eastus",
                        "Azure Region",
                        "Specify Azure region, e.g. eastus",
                        tooltip="Azure Region")
        self.add_option("voice_en", "text", "en-US-AriaNeural",
                        "Voice (EN)",
                        "Specify voice for English language, e.g. en-US-AriaNeural",
                        tooltip="Voice (EN)")
        self.add_option("voice_pl", "text", "pl-PL-AgnieszkaNeural",
                        "Voice (PL)",
                        "Specify voice for Polish language, e.g. pl-PL-MarekNeural or pl-PL-AgnieszkaNeural",
                        tooltip="Voice (PL)")

    def setup(self):
        """
        Return available config options

        :return: config options
        :rtype: dict
        """
        return self.options

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
        elif name == 'ctx.after':
            self.on_ctx_after(ctx)
        elif name == 'audio.output.stop':
            self.stop_audio()

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: Text
        """
        self.input_text = text

    def on_ctx_after(self, ctx):
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
        path = os.path.join(self.window.core.config.path, 'output.mp3')
        try:
            if text is not None and len(text) > 0:
                lang = self.window.core.config.get('lang')
                voice = None
                if lang == "pl":
                    voice = self.get_option_value("voice_pl")
                elif lang == "en":
                    voice = self.get_option_value("voice_en")
                self.tts = TTS(self, api_key, region, voice, text, path)
                self.tts.status_signal.connect(self.handle_status)
                self.tts.error_signal.connect(self.handle_error)
                self.thread = threading.Thread(target=self.tts.run)
                self.thread.start()
        except Exception as e:
            self.window.core.debug.log(e)

    def set_status(self, status):
        """
        Set status

        :param status: status
        """
        self.window.ui.plugin_addon['audio.output'].set_status(status)

    def show_stop_button(self):
        """
        Show stop button
        """
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(True)

    def hide_stop_button(self):
        """
        Hide stop button
        """
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(False)

    def stop_speak(self):
        """
        Stop speaking
        """
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(False)
        self.window.ui.plugin_addon['audio.output'].set_status('Stopped')
        self.window.ui.plugin_addon['audio.output'].stop_audio()

    @Slot(object)
    def handle_status(self, data):
        """
        Handle thread debug log
        :param data
        """
        self.set_status(str(data))

    @Slot(object)
    def handle_error(self, error):
        """
        Handle thread error
        :param error
        """
        self.window.core.debug.log(error)

    def stop_audio(self):
        """
        Stop TTS thread and stop playing the audio
        """
        if self.tts is not None:
            self.tts.stop()
        if self.thread is not None:
            self.thread.stop()
        if self.playback is not None:
            self.playback.stop()
            self.playback = None
            self.audio = None


class TTS(QObject):
    # setup signals
    status_signal = Signal(object)
    error_signal = Signal(object)

    def __init__(self, plugin, subscription_key, region, voice, text, path):
        """
        Text to speech

        :param subscription_key: Azure API Key
        :param region: Azure region
        :param voice: Voice name
        :param text: Text to speech
        """
        super().__init__()
        self.plugin = plugin
        self.subscription_key = subscription_key
        self.region = region
        self.text = text
        self.voice = voice
        self.path = path

    def run(self):
        """Run TTS thread"""
        self.stop()
        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
        }
        body = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' " \
               f"xml:lang='en-US'><voice name='{self.voice}'>{self.text}</voice></speak>"
        response = requests.post(url, headers=headers, data=body.encode('utf-8'))
        if response.status_code == 200:
            with open(self.path, "wb") as file:
                file.write(response.content)
            pygame.mixer.init()
            self.plugin.playback = pygame.mixer.Sound(self.path)
            self.plugin.playback.play()
        else:
            error_msg = f"Error: {response.status_code} - {response.text}"
            self.error_signal.emit(error_msg)

        self.status_signal.emit('')

    def stop(self):
        """Stop TTS thread"""
        self.status_signal.emit('')
        # self.plugin.hide_stop_button()
        if self.plugin.playback is not None:
            self.plugin.playback.stop()
            self.plugin.playback = None
            self.plugin.audio = None
