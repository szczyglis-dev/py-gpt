#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.03 12:00:00                  #
# ================================================== #

import threading

import requests
from PySide6.QtCore import QObject, Signal
from pydub import AudioSegment
from pydub.playback import play
import io

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "audio_azure"
        self.name = "Audio (Azure)"
        self.description = "Enables audio/voice output (speech synthesis) using Microsoft Azure API"
        self.options = {}
        self.options["azure_api_key"] = {
            "type": "text",
            "slider": False,
            "label": "Azure API Key",
            "description": "You can obtain your own API key at: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/",
            "tooltip": "Azure API Key",
            "value": '',
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["azure_region"] = {
            "type": "text",
            "slider": False,
            "label": "Azure Region",
            "description": "Specify Azure region, e.g. eastus",
            "tooltip": "Azure Region",
            "value": 'eastus',
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["voice_en"] = {
            "type": "text",
            "slider": False,
            "label": "Voice (EN)",
            "description": "Specify voice for English language, e.g. en-US-AriaNeural",
            "tooltip": "Voice (EN)",
            "value": 'en-US-AriaNeural',
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["voice_pl"] = {
            "type": "text",
            "slider": False,
            "label": "Voice (PL)",
            "description": "Specify voice for Polish language, e.g. pl-PL-MarekNeural or pl-PL-AgnieszkaNeural",
            "tooltip": "Voice (PL)",
            "value": 'pl-PL-AgnieszkaNeural',
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.input_text = None
        self.window = None

    def setup(self):
        """
        Returns available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """Event: On user send text"""
        return text

    def on_ctx_begin(self, ctx):
        """Event: On new context begin"""
        return ctx

    def on_ctx_end(self, ctx):
        """Event: On context end"""
        return ctx

    def on_system_prompt(self, prompt):
        """Event: On prepare system prompt"""
        return prompt

    def on_ai_name(self, name):
        """Event: On set AI name"""
        return name

    def on_user_name(self, name):
        """Event: On set user name"""
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
        """
        self.input_text = text
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Text
        :return: ctx
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        :return: ctx
        """
        # Check if api key is set
        if self.options['azure_api_key']['value'] is None or self.options['azure_api_key']['value'] == "":
            self.window.ui.dialogs.alert("Azure API KEY is not set. Please set it in plugins settings.")
            return ctx
        if self.options['azure_region']['value'] is None or self.options['azure_region']['value'] == "":
            self.window.ui.dialogs.alert("Azure Region is not set. Please set it in plugins settings.")
            return ctx

        text = ctx.output
        try:
            if text is not None and len(text) > 0:
                lang = self.window.config.data['lang']
                voice = None
                if lang == "pl":
                    voice = self.options['voice_pl']['value']
                elif lang == "en":
                    voice = self.options['voice_en']['value']
                tts = TTS(self.options['azure_api_key']['value'], self.options['azure_region']['value'], voice, text)
                t = threading.Thread(target=tts.run)
                t.start()
        except Exception as e:
            print(e)

        return ctx


class TTS(QObject):
    finished = Signal(object)

    def __init__(self, subscription_key, region, voice, text):
        """
        Text to speech

        :param subscription_key: Azure API Key
        :param region: Azure region
        :param voice: Voice name
        :param text: Text to speech
        """
        super().__init__()
        self.subscription_key = subscription_key
        self.region = region
        self.text = text
        self.voice = voice

    def run(self):
        """Run TTS thread"""
        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
        }
        body = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><voice name='{self.voice}'>{self.text}</voice></speak>"
        response = requests.post(url, headers=headers, data=body.encode('utf-8'))
        if response.status_code == 200:
            audio_file = response.content
            voice = AudioSegment.from_file(io.BytesIO(audio_file), format="mp3")
            play(voice)
            self.finished.emit(audio_file)
        else:
            error_msg = f"Error: {response.status_code} - {response.text}"
            print(error_msg)
            self.finished.emit(error_msg)
