#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        prompt = 'ADDITIONAL CONTEXT: I will provide you with additional context about my question. ' \
                 'When it is provided, then use this data as additional context and use it in your response. ' \
                 'Additional context will be prefixed with an "ADDITIONAL CONTEXT:" prefix. You can also provide a ' \
                 'command to query my context database anytime you need any additional context - to do this, return ' \
                 'to me the prepared prompt in JSON format, all in one line, using the following syntax: ' \
                 '~###~{"cmd": "get_context", "params": {"query": "<simple question here>"}}~###~. ' \
                 'Use ONLY this syntax and remember to surround the JSON string with ~###~. DO NOT use any other ' \
                 'syntax. When making query use language that I spoke to you.'

        plugin.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt",
            description="Prompt used for instruct how to use additional data provided from Llama-index",
            tooltip="Prompt",
            advanced=True,
        )
        plugin.add_option(
            "ask_llama_first",
            type="bool",
            value=False,
            label="Ask Llama-index first",
            description="When enabled, then Llama-index will be asked first, and response will be used "
                        "as additional knowledge in prompt. When disabled, then Llama-index will be "
                        "asked only when needed.",
        )
        plugin.add_option(
            "prepare_question",
            type="bool",
            value=False,
            label="Auto-prepare question before asking Llama-index first",
            description="When enabled, then question will be prepared before asking Llama-index first to create"
                        "best question for Llama-index.",
        )
        plugin.add_option(
            "model_prepare_question",
            type="combo",
            use="models",
            value="gpt-4o-mini",
            label="Model for question preparation",
            description="Model used to prepare question before asking Llama-index, default: gpt-3.5-turbo",
            tooltip="Model",
        )
        plugin.add_option(
            "prepare_question_max_tokens",
            type="int",
            value=500,
            label="Max output tokens for question preparation",
            description="Max tokens in output when preparing question before asking Llama-index",
            min=1,
            max=None,
        )
        plugin.add_option(
            "model_query",
            type="combo",
            value="gpt-4o-mini",
            label="Model",
            description="Model used for querying Llama-index, default: gpt-3.5-turbo",
            tooltip="Query model",
            use="models",
        )
        plugin.add_option(
            "max_question_chars",
            type="int",
            value=1000,
            label="Max characters in question",
            description="Max characters in question when querying Llama-index, 0 = no limit",
            min=0,
            max=None,
        )
        plugin.add_option(
            "append_meta",
            type="bool",
            value=False,
            label="Append metadata to context",
            description="If enabled, then metadata from Llama-index will be appended to additional context",
        )
        plugin.add_option(
            "syntax_prepare_question",
            type="textarea",
            value='Simplify the question into a short query for retrieving information from a vector store.',
            label="Prompt for question preparation",
            description="System prompt for question preparation",
            advanced=True,
        )
        plugin.add_cmd(
            "get_context",
            instruction="get additional context for a given query",
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "query to retrieve additional context for",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to get additional context for a given query",
        )
        plugin.add_option(
            "idx",
            type="bool_list",
            use="idx",
            use_params={
                "none": False,
            },
            value="base",
            label="Indexes to use",
            description="ID's of indexes to use, default: base, separate by comma if you want to use "
                        "more than one index at once",
            tooltip="Index name",
        )
