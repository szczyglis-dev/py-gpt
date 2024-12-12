#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.12 20:00:00                  #
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
            "provider",
            type="combo",
            value="google_custom_search",
            label="Provider",
            description="Select search engine provider, default: Google",
            tooltip="Select search engine provider",
            keys=plugin.get_provider_options(),
        )
        plugin.add_option(
            "num_pages",
            type="int",
            value=10,
            label="Number of pages to search",
            description="Number of max pages to search per query",
            min=1,
            max=None,
        )
        plugin.add_option(
            "max_page_content_length",
            type="int",
            value=0,
            label="Max content characters",
            description="Max characters of page content to get (0 = unlimited)",
            min=0,
            max=None,
        )
        plugin.add_option(
            "chunk_size",
            type="int",
            value=20000,
            label="Per-page content chunk size",
            description="Per-page content chunk size (max characters per chunk)",
            min=1,
            max=None,
        )
        plugin.add_option(
            "raw",
            type="bool",
            value=False,
            label="Use raw content (without summarization)",
            description="Return raw content from web search instead of summarized content",
            tooltip="Use raw content for search",
        )
        plugin.add_option(
            "disable_ssl",
            type="bool",
            value=True,
            label="Disable SSL verify",
            description="Disables SSL verification when crawling web pages",
            tooltip="Disable SSL verify",
        )
        plugin.add_option(
            "timeout",
            type="int",
            value=5,
            label="Timeout",
            description="Connection timeout (seconds)",
            tooltip="Connection timeout (seconds)",
        )
        plugin.add_option(
            "user_agent",
            type="text",
            value="Mozilla/5.0",
            label="User agent",
            description="User agent to use when making requests, default: Mozilla/5.0",
            tooltip="User agent to use when making requests",
        )
        plugin.add_option(
            "max_result_length",
            type="int",
            value=1500,
            label="Max result length",
            description="Max length of summarized result (characters)",
            min=0,
            max=None,
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
            "model_tmp_query",
            type="combo",
            value="gpt-3.5-turbo",
            label="Model for query in-memory index",
            description="Model used for query in-memory index for `web_index_query` command, "
                        "default: gpt-3.5-turbo",
            tooltip="Query model",
            use="models",
            tab="indexing",
        )
        plugin.add_option(
            "auto_index",
            type="bool",
            value=False,
            label="Auto-index all used URLs using Llama-index",
            description="If enabled, every URL used by the model will be automatically indexed using Llama-index "
                        "(persistent index)",
            tooltip="If enabled, every URL used by the model will be automatically indexed using Llama-index "
                    "(persistent index)",
            tab="indexing",
        )
        plugin.add_option(
            "idx",
            type="text",
            value="base",
            label="Index to use",
            description="ID of index to use for web page indexing (persistent index)",
            tooltip="Index name",
            tab="indexing",
        )
        plugin.add_option(
            "summary_model",
            type="text",
            value="gpt-3.5-turbo-1106",
            label="Model used for web page summarize",
            description="Model used for web page summarize, default: gpt-3.5-turbo-1106",
            advanced=True,
        )
        plugin.add_option(
            "prompt_summarize",
            type="textarea",
            value="Summarize text in English in a maximum of 3 paragraphs, trying to find the most "
                  "important content that can help answer the following question: {query}",
            label="Summarize prompt",
            description="Prompt used for web search results summarize, use {query} "
                        "as a placeholder for search query",
            tooltip="Prompt",
            advanced=True,
        )
        plugin.add_option(
            "prompt_summarize_url",
            type="textarea",
            value="Summarize text in English in a maximum of 3 paragraphs, trying to find the most "
                  "important content.",
            label="Summarize prompt (URL open)",
            description="Prompt used for specified URL page summarize",
            tooltip="Prompt",
            advanced=True,
        )

        # commands
        plugin.add_cmd(
            "web_search",
            instruction="search the Web for more info, prepare a query for the search engine itself, start from page 1. "
                        "If no results, then try the next page. "
                        "Use a custom summary prompt if necessary, otherwise, a default summary will be used. "
                        "Max pages: {max_pages}",
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "search query",
                    "required": True,
                },
                {
                    "name": "page",
                    "type": "int",
                    "description": "page number",
                    "required": False,
                },
                {
                    "name": "summarize_prompt",
                    "type": "str",
                    "description": "summary prompt",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to search the Web",
        )
        plugin.add_cmd(
            "web_url_open",
            instruction="read and get summarized content from ANY website URL. Use a custom summary prompt if necessary, "
                        "otherwise default summary will be used",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
                {
                    "name": "summarize_prompt",
                    "type": "str",
                    "description": "summary prompt",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open URL and summarize content",
        )
        plugin.add_cmd(
            "web_url_raw",
            instruction="read and get raw HTML/txt content (not summarized) from ANY website URL",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open specified URL and get raw content",
        )
        plugin.add_cmd(
            "web_urls",
            instruction="search the Web for list of URLs, prepare search query itself, list of "
                        "URLs will be returned, 10 links per page max.",
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "search query",
                    "required": True,
                },
                {
                    "name": "page",
                    "type": "int",
                    "description": "page number",
                    "required": False,
                },
                {
                    "name": "num_links",
                    "type": "int",
                    "description": "links per page",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to search the Web and get founded URLs list",
        )
        plugin.add_cmd(
            "web_index",
            instruction="",
            params=[],  # prepared dynamically
            enabled=True,
            tab="indexing",
            description="If enabled, model will be able to index web content using Llama-index (persistent index)",
        )
        plugin.add_cmd(
            "web_index_query",
            instruction="read, index and query external content for additional context.",
            params=[],  # prepared dynamically
            enabled=True,
            tab="indexing",
            description="If enabled, model will be able to index and query web content using Llama-index "
                        "(temporary index, on the fly)",
        )