#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 19:00:00                  #
# ================================================== #
import os
import threading

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QCheckBox
from pydub import AudioSegment
from pydub.playback import play
from openai import OpenAI

from ..base_plugin import BasePlugin
from ...utils import trans


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "audio_openai_tts"
        self.name = "Audio Output (OpenAI TTS)"
        self.description = "Enables audio/voice output (speech synthesis) using OpenAI TTS (Text-To-Speech) API"
        self.allowed_voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
        self.allowed_models = ['tts-1', 'tts-1-hd']
        self.input_text = None
        self.window = None
        self.order = 1
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        self.add_option("model", "text", "tts-1",
                        "Model",
                        "Specify model, available models: tts-1, tts-1-hd")
        self.add_option("voice", "text", "alloy",
                        "Voice",
                        "Specify voice, available voices: alloy, echo, fable, onyx, nova, shimmer")

    def setup(self):
        """
        Returns available config options

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
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: Text
        :return: text
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: Context
        :return: ctx
        """
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: Context
        :return: ctx
        """
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: prompt
        """
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: Name
        :return: name
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set user name

        :param name: Name
        :return: name
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
        :return: Text
        """
        self.input_text = text
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: Context
        :return: Context
        """
        text = ctx.output
        try:
            if text is not None and len(text) > 0:
                client = OpenAI(
                    api_key=self.window.config.get('api_key'),
                    organization=self.window.config.get('organization_key'),
                )
                voice = self.get_option_value('voice')
                model = self.get_option_value('model')
                path = os.path.join(self.window.config.path, 'output.mp3')

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

    def destroy(self):
        """
        Destroy thread
        """
        pass


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
