#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.03 21:00:00                  #
# ================================================== #
import os
import threading

from PySide6.QtCore import QObject, Signal
from pydub import AudioSegment
from pydub.playback import play
from openai import OpenAI

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "audio_openai_tts"
        self.name = "Audio (OpenAI TTS)"
        self.description = "Enables audio/voice output (speech synthesis) using OpenAI TTS API"
        self.allowed_voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
        self.allowed_models = ['tts-1', 'tts-1-hd']
        self.options = {}
        self.options["model"] = {
            "type": "text",
            "slider": False,
            "label": "Model",
            "description": "Specify model, available models: tts-1, tts-1-hd",
            "tooltip": "Model",
            "value": 'tts-1',
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["voice"] = {
            "type": "text",
            "slider": False,
            "label": "Voice",
            "description": "Specify voice, available voices: alloy, echo, fable, onyx, nova, shimmer",
            "tooltip": "Voice",
            "value": 'alloy',
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
        text = ctx.output
        try:
            if text is not None and len(text) > 0:
                client = OpenAI(
                    api_key=self.window.config.data["api_key"],
                    organization=self.window.config.data["organization_key"],
                )
                voice = self.options['voice']['value']
                path = os.path.join(self.window.config.path, 'speech.mp3')
                model = self.options['model']['value']
                if model not in self.allowed_models:
                    model = 'tts-1'
                if voice not in self.allowed_voices:
                    voice = 'alloy'
                tts = TTS(client, model, path, voice, text)
                t = threading.Thread(target=tts.run)
                t.start()
        except Exception as e:
            print(e)

        return ctx


class TTS(QObject):
    def __init__(self, client, model, path, voice, text):
        """
        Text to speech

        :param client: OpenAI client
        :param model: Model name
        :param voice: Voice name
        :param text: Text to speech
        """
        super().__init__()
        self.client = client
        self.model = model
        self.path = path
        self.text = text
        self.voice = voice

    def run(self):
        """Run TTS thread"""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=self.text
            )
            response.stream_to_file(self.path)
            audio = AudioSegment.from_mp3(self.path)
            play(audio)
        except Exception as e:
            print(e)
