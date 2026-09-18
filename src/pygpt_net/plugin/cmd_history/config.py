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

from pygpt_net.core.types import MODEL_DEFAULT_MINI
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
            "model_summarize",
            type="combo",
            value=MODEL_DEFAULT_MINI,
            label="Model",
            description="Model used for summarize, default: gpt-4o-mini",
            tooltip="Summarize model",
            use="models",
        )
        plugin.add_option(
            "summary_max_tokens",
            type="int",
            value=1500,
            label="Max summary tokens",
            description="Max tokens in each query-focused summary/reduction output. 0 = safe default (1500)",
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
            description="Secondary hard character cap per source chunk; model context/token budget is applied first",
            min=1,
            max=None,
        )
        plugin.add_option(
            "prompt_tag_summary",
            type="textarea",
            value="You retrieve context from a previous conversation for the current user request.\n"
                  "Previous conversation ID: {id}\n"
                  "Current request:\n{query}\n\n"
                  "Return a concise summary of the supplied conversation chunk that is useful for answering or "
                  "continuing the current request. Preserve relevant decisions, requirements, facts, filenames, code "
                  "identifiers, values, errors, current state, and unresolved work. Prefer newer state over superseded "
                  "older state. If the request is vague, unclear, or only refers to the conversation, summarize the "
                  "main topic, latest state, key decisions, and unresolved work. Always return the best useful summary "
                  "available; never return an empty response. If direct relevance is unclear, "
                  "summarize the most important content instead. Do not invent information and do not answer the "
                  "current request itself.",
            label="Prompt: conversation extraction",
            description="Prompt for query-focused extraction from previous conversation chunks",
            advanced=True,
        )
        plugin.add_option(
            "prompt_tag_reduce",
            type="textarea",
            value="You merge query-focused extracts from the same previous conversation.\n"
                  "Previous conversation ID: {id}\n"
                  "Current request:\n{query}\n\n"
                  "Produce one compact context summary useful for answering or continuing the current request. Remove "
                  "repetition, preserve exact technical details and unresolved work, and prefer newer state when extracts "
                  "conflict. If the request is vague or relevance is unclear, retain the main topic, latest state, key "
                  "decisions, and unresolved work. Always return the best useful summary available; never return an empty "
                  "response or NO_RELEVANT_CONTEXT. Do not invent information and do not answer the current request "
                  "itself.",
            label="Prompt: conversation reduction",
            description="Prompt for merging query-focused extracts from long previous conversations",
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
            instruction="get query-focused content of context by its ID; summary_query must describe what information is "
                        "needed from that previous conversation for the current request",
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