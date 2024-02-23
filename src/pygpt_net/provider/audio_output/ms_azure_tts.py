#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 19:00:00                  #
# ================================================== #

import os
import requests

from .base import BaseProvider


class MSAzureTextToSpeech(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Microsoft Azure Text to Speech provider

        :param args: args
        :param kwargs: kwargs
        """
        super(MSAzureTextToSpeech, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "ms_azure"
        self.name = "Microsoft Azure TTS"

    def init_options(self):
        """Initialize options"""
        url_api = {
            "API Key": "https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech",
        }
        self.plugin.add_option(
            "azure_api_key",
            type="text",
            value="",
            label="Azure API Key",
            tab="ms_azure",
            description="You can obtain your own API key at: "
                        "https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/",
            tooltip="Azure API Key",
            secret=True,
            persist=True,
            urls=url_api,
        )
        self.plugin.add_option(
            "azure_region",
            type="text",
            value="eastus",
            label="Azure Region",
            tab="ms_azure",
            description="Specify Azure region, e.g. eastus",
            tooltip="Azure Region",
        )
        self.plugin.add_option(
            "azure_voice_en",
            type="text",
            value="en-US-AriaNeural",
            label="Voice (EN)",
            tab="ms_azure",
            description="Specify voice for English language, e.g. en-US-AriaNeural",
            tooltip="Voice (EN)",
        )
        self.plugin.add_option(
            "azure_voice_pl",
            type="text",
            value="pl-PL-AgnieszkaNeural",
            label="Voice (non-English)",
            tab="ms_azure",
            description="Specify voice for non-English languages, "
                        "e.g. pl-PL-MarekNeural or pl-PL-AgnieszkaNeural",
            tooltip="Voice (PL)",
        )

    def speech(self, text: str) -> str:
        """
        Speech text to audio

        :param text: text to speech
        :return: path to generated audio file or None if audio playback is handled here
        """
        api_key = self.plugin.get_option_value("azure_api_key")
        region = self.plugin.get_option_value("azure_region")
        lang = self.plugin.window.core.config.get('lang')
        output_file = self.plugin.output_file
        path = os.path.join(
            self.plugin.window.core.config.path,
            output_file,
        )
        if lang == "en":
            voice = self.plugin.get_option_value("azure_voice_en")
        else:
            voice = self.plugin.get_option_value("azure_voice_pl")

        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
        }
        body = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' " \
               f"xml:lang='en-US'><voice name='{voice}'>{text}</voice></speak>"
        response = requests.post(
            url,
            headers=headers,
            data=body.encode('utf-8'),
        )
        if response.status_code == 200:
            with open(path, "wb") as file:
                file.write(response.content)
            return path

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        api_key = self.plugin.get_option_value("azure_api_key")
        region = self.plugin.get_option_value("azure_region")
        return api_key is not None and api_key != "" and region is not None and region != ""

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        api_key = self.plugin.get_option_value("azure_api_key")
        region = self.plugin.get_option_value("azure_region")
        if api_key is None or api_key == "":
            return "Azure API KEY is not set. Please set it in plugin settings."
        if region is None or region == "":
            return "Azure Region is not set. Please set it in plugin settings."

