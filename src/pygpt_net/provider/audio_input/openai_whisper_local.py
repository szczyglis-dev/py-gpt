#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.01 03:00:00                  #
# ================================================== #

from typing import cast

from .base import BaseProvider


class OpenAIWhisperLocal(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        OpenAI Whisper provider (local model)

        :param args: args
        :param kwargs: kwargs
        """
        super(OpenAIWhisperLocal, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "openai_whisper_local"
        self.name = "Whisper (local)"

    def init_options(self):
        """Initialize options"""
        self.plugin.add_option(
            "whisper_local_model",
            type="text",
            value="base",
            label="Model",
            tab="openai_whisper_local",
            description="Specify local model, default: base. Local models are not available in compiled version, use "
                        "API version if you are using compiled or Snap version.",
            urls={
                "Models": "https://github.com/openai/whisper"
            }
        )

    def transcribe(self, path: str) -> str:
        """
        Audio to text transcription

        :param path: path to audio file to transcribe
        :return: transcribed text
        """
        is_compiled = self.plugin.window.core.config.is_compiled() or self.plugin.window.core.platforms.is_snap()
        if is_compiled:
            raise ValueError("Local models are not available in compiled version.")

        if not self.is_configured():
            raise ImportError(self.get_config_message())

        import whisper

        model = whisper.load_model(self.plugin.get_option_value('whisper_local_model'))
        config = {"model": model}
        model = cast(whisper.Whisper, config["model"])
        result = model.transcribe(path)
        return str(result["text"])

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        is_compiled = self.plugin.window.core.config.is_compiled() or self.plugin.window.core.platforms.is_snap()
        if is_compiled:
            raise ValueError("Local models are not available in compiled version.")
        try:
            import whisper
        except ImportError:
            return False
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return ("Please install OpenAI whisper model "
                "'pip install git+https://github.com/openai/whisper.git' "
                "or pip install openai-whisper to use the model")
