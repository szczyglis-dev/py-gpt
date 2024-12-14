#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 19:00:00                  #
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
        plugin.add_option(
            "use_tags",
            type="bool",
            value=False,
            label="Enable: using context @ ID tags",
            description="When enabled, it allows to automatically retrieve context history using @ tags, "
                        "e.g. use @123 in question to retrieve summary of context with ID 123",
        )
        plugin.add_option(
            "model_summarize",
            type="combo",
            value="gpt-4o-mini",
            label="Model",
            description="Model used for summarize, default: gpt-3.5-turbo",
            tooltip="Summarize model",
            use="models",
        )
        plugin.add_option(
            "summary_max_tokens",
            type="int",
            value=1500,
            label="Max summary tokens",
            description="Max tokens in output when generating summary",
            min=0,
            max=None,
        )
        plugin.add_option(
            "ctx_items_limit",
            type="int",
            value=30,
            label="Max contexts to retrieve",
            description="Max items in context history list to retrieve in one query. 0 = no limit",
            min=0,
            max=None,
        )
        plugin.add_option(
            "chunk_size",
            type="int",
            value=100000,
            label="Per-context items content chunk size",
            description="Per-context content chunk size (max characters per chunk)",
            min=1,
            max=None,
        )
        plugin.add_option(
            "prompt_tag_system",
            type="textarea",
            value="ADDITIONAL CONTEXT: Use the following JSON summary of previous discussions as additional context, "
                  "instead of using commands for retrieve content: {context}",
            label="Prompt: tag_system",
            description="Prompt for use @ tag (system)",
            advanced=True,
        )
        plugin.add_option(
            "prompt_tag_summary",
            type="textarea",
            value="You are an expert in context summarization. "
                  "Please summarize the given discussion (ID: {id}) by addressing the query and preparing it to serve "
                  "as additional context for a new discussion or to continue the current one: {query}",
            label="Prompt: tag_summary",
            description="Prompt for use @ tag (summary)",
            advanced=True,
        )

        # commands
        plugin.add_cmd(
            "get_ctx_list_in_date_range",
            instruction="get list of context history (previous conversations between you and me), using date-range "
                        "syntax: \"@date(YYYY-MM-DD)\" for single day, \"@date(YYYY-MM-DD,)\" for date FROM, "
                        "\"@date(,YYYY-MM-DD)\" for date TO, and \"@date(YYYY-MM-DD,YYYY-MM-DD)\" for date FROM-TO",
            params=[
                {
                    "name": "range_query",
                    "type": "str",
                    "description": "range query",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows getting the list of context history (previous conversations)",
        )
        plugin.add_cmd(
            "get_ctx_content_by_id",
            instruction="get summarized content of context by its ID, use summary query to ask another "
                        "model to summarize content, e.g. \"Summarize following discussion answering the query: (query)\"",
            params=[
                {
                    "name": "id",
                    "type": "int",
                    "description": "context ID",
                    "required": True,
                },
                {
                    "name": "summary_query",
                    "type": "str",
                    "description": "query",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows getting summarized content of context with defined ID",
        )
        plugin.add_cmd(
            "count_ctx_in_date",
            instruction="count items of context history (previous conversations between us), by providing year, "
                        "month, day or combination of them",
            params=[
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows counting contexts in date range",
        )
        plugin.add_cmd(
            "get_day_note",
            instruction="get day notes for date",
            params=[
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows retrieving day note for specific date",
        )
        plugin.add_cmd(
            "add_day_note",
            instruction="add day note",
            params=[
                {
                    "name": "note",
                    "type": "str",
                    "description": "content",
                    "required": True,
                },
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows adding day note for specific date",
        )
        plugin.add_cmd(
            "update_day_note",
            instruction="update day note",
            params=[
                {
                    "name": "note",
                    "type": "str",
                    "description": "content",
                    "required": True,
                },
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows updating day note for specific date",
        )
        plugin.add_cmd(
            "remove_day_note",
            instruction="remove day note",
            params=[
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows removing day note for specific date",
        )