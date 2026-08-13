#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Mohit Varikuti                       #
# Updated Date: 2026.06.25 00:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        # Settings
        plugin.add_option(
            "api_key",
            type="text",
            value="",
            label="API Key",
            description="TwelveLabs API key. Get a free key at https://twelvelabs.io "
                        "(generous free tier). Falls back to the TWELVELABS_API_KEY "
                        "environment variable if left empty.",
            secret=True,
            urls={"API Key": "https://playground.twelvelabs.io/dashboard/api-key"},
        )
        plugin.add_option(
            "pegasus_model",
            type="text",
            value="pegasus1.5",
            label="Pegasus model",
            description="Model used for video analysis (e.g., pegasus1.5).",
        )
        plugin.add_option(
            "marengo_model",
            type="text",
            value="marengo3.0",
            label="Marengo model",
            description="Model used for multimodal embeddings (e.g., marengo3.0).",
        )
        plugin.add_option(
            "max_tokens",
            type="int",
            value=2048,
            label="Max tokens",
            description="Default max tokens for Pegasus analysis responses.",
        )
        plugin.add_option(
            "temperature",
            type="float",
            value=0.2,
            label="Temperature",
            description="Default sampling temperature for Pegasus analysis.",
            min=0.0,
            max=1.0,
            step=0.1,
        )
        plugin.add_option(
            "timeout",
            type="int",
            value=300,
            label="Request timeout (s)",
            description="Timeout in seconds for TwelveLabs API requests.",
        )

        # ---------------- Commands ----------------

        plugin.add_cmd(
            "tl_analyze_video",
            instruction="Analyze/understand a video using TwelveLabs Pegasus and answer a "
                        "prompt about it (summary, description, Q&A). Provide either a public "
                        "video 'url' or an already-indexed 'video_id'.",
            params=[
                {"name": "prompt", "type": "str", "required": True,
                 "description": "What to ask about the video, e.g. 'Summarize this video.'"},
                {"name": "url", "type": "str", "required": False,
                 "description": "Public URL of the video to analyze"},
                {"name": "video_id", "type": "str", "required": False,
                 "description": "ID of a video already indexed on TwelveLabs"},
                {"name": "max_tokens", "type": "int", "required": False,
                 "description": "Max tokens for the response"},
                {"name": "temperature", "type": "float", "required": False,
                 "description": "Sampling temperature (0.0-1.0)"},
            ],
            enabled=True,
            description="Video: analyze (Pegasus)",
            tab="video",
        )
        plugin.add_cmd(
            "tl_embed_text",
            instruction="Create a TwelveLabs Marengo multimodal text embedding for a piece of "
                        "text. Returns a vector that lives in the same space as Marengo video "
                        "embeddings, useful for text-to-video search.",
            params=[
                {"name": "text", "type": "str", "required": True,
                 "description": "Text to embed"},
            ],
            enabled=True,
            description="Embeddings: text (Marengo)",
            tab="embeddings",
        )
