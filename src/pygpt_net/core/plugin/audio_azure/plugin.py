#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

import threading

import requests
from PySide6.QtCore import QObject, Signal
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import io

from ..base_plugin import BasePlugin


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
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        url_api = {
            "API Key": "https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/",
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

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: Text
        :return: text
        :rtype: str
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: Context
        :return: Context (modified)
        :rtype: ContextItem
        """
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: Context
        :return: Context (modified)
        :rtype: ContextItem
        """
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: prompt
        :rtype: str
        """
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: Name
        :return: name
        :rtype: str
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set user name

        :param name: Name
        :return: name
        :rtype: str
        """
        return name

    def on_enable(self):
        """Event: On plugin enable"""
        pass

    def on_disable(self):
        """Event: On plugin disable"""
        pass

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: Text
        :return: text
        :rtype: str
        """
        self.input_text = text
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Context
        :return: Context (modified)
        :rtype: ContextItem
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: Context
        :return: Context (modified)
        :rtype: ContextItem
        """
        # Check if api key is set
        api_key = self.get_option_value("azure_api_key")
        region = self.get_option_value("azure_region")

        if api_key is None or api_key == "":
            self.window.ui.dialogs.alert("Azure API KEY is not set. Please set it in plugin settings.")
            return ctx
        if region is None or region == "":
            self.window.ui.dialogs.alert("Azure Region is not set. Please set it in plugin settings.")
            return ctx

        text = ctx.output
        try:
            if text is not None and len(text) > 0:
                lang = self.window.config.get('lang')
                voice = None
                if lang == "pl":
                    voice = self.get_option_value("voice_pl")
                elif lang == "en":
                    voice = self.get_option_value("voice_en")
                tts = TTS(self, api_key, region, voice, text)
                self.thread = threading.Thread(target=tts.run)
                self.thread.start()
        except Exception as e:
            print(e)

        return ctx

    def set_status(self, status):
        """
        Set status

        :param status: Status
        """
        self.window.plugin_addon['audio.output'].set_status(status)

    def show_stop_button(self):
        """
        Show stop button
        """
        self.window.plugin_addon['audio.output'].stop.setVisible(True)

    def hide_stop_button(self):
        """
        Hide stop button
        """
        self.window.plugin_addon['audio.output'].stop.setVisible(False)

    def stop_speak(self):
        """
        Stop speaking
        """
        self.window.plugin_addon['audio.output'].stop.setVisible(False)
        self.window.plugin_addon['audio.output'].set_status('Stopped')
        self.window.plugin_addon['audio.output'].stop_audio()

    def stop_audio(self):
        """
        Stop TTS thread and stop playing the audio
        """
        if self.thread is not None:
            self.thread.stop()
        if self.tts is not None:
            self.tts.stop()

    def on_signal(self, signal):
        """
        Event: On signal

        :param signal: Signal
        """
        if signal == 'audio.output.stop':
            self.stop_audio()


class TTS(QObject):
    finished = Signal(object)

    def __init__(self, plugin, subscription_key, region, voice, text):
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

    def run(self):
        """Run TTS thread"""
        self.stop()
        # self.plugin.set_status('...')
        # self.plugin.hide_stop_button()
        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
        }
        body = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><voice name='{self.voice}'>{self.text}</voice></speak>"
        response = requests.post(url, headers=headers, data=body.encode('utf-8'))
        if response.status_code == 200:
            # self.plugin.set_status('Saying...')
            # self.plugin.show_stop_button()
            audio_file = response.content
            self.plugin.audio = AudioSegment.from_file(io.BytesIO(audio_file), format="mp3")
            self.plugin.playback = _play_with_simpleaudio(self.plugin.audio)
            self.plugin.set_status('')
            # self.plugin.hide_stop_button()
            self.finished.emit(audio_file)
        else:
            self.plugin.set_status('')
            # self.plugin.hide_stop_button()
            error_msg = f"Error: {response.status_code} - {response.text}"
            print(error_msg)
            self.finished.emit(error_msg)

    def stop(self):
        """Stop TTS thread"""
        self.plugin.set_status('')
        # self.plugin.hide_stop_button()
        if self.plugin.playback is not None:
            self.plugin.playback.stop()
            self.plugin.playback = None
            self.plugin.audio = None
