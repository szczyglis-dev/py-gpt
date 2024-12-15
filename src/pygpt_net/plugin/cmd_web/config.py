#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.15 01:00:00                  #
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
            "max_open_urls",
            type="int",
            value=1,
            label="Number of max URLs to open at once",
            description="Number of max URLs to open at once",
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
            value=True,
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
            "img_thumbnail",
            type="bool",
            value=True,
            label="Show thumbnail images",
            description="Enable fetching thumbnails from opened websites",
            tooltip="Enable fetching thumbnails from opened websites",
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
            value=50000,
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
            value="gpt-4o-mini",
            label="Model for query in-memory index",
            description="Model used for query in-memory index for `web_index_query` command, "
                        "default: gpt-4o-mini",
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
            type="combo",
            value="base",
            label="Index to use",
            description="ID of index to use for web page indexing (persistent index)",
            tooltip="Index name",
            use="idx",
            tab="indexing",
        )
        plugin.add_option(
            "summary_model",
            type="combo",
            value="gpt-4o-mini",
            label="Model used for web page summarize",
            description="Model used for web page summarize, default: gpt-4o-mini",
            use="models",
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
            "web_url_open",
            instruction="read and get text content from ANY website URL. Always open a max of {max_urls} URLs at a time.",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open URL and read text content from it",
        )
        plugin.add_cmd(
            "web_url_raw",
            instruction="read and get raw HTML body from ANY website URL. Always open a max of {max_urls} URLs at a time.",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open specified URL and get raw HTML body from it",
        )
        plugin.add_cmd(
            "web_search",
            instruction="search the Web for list of URLs, prepare search query itself, list of "
                        "URLs will be returned, 10 links per page max. After receiving the list of URLs, "
                        "choose the best matched URLs and use the `web_url_open` command to read the content. "
                        "Always open a max of {max_urls} URLs at a time.",
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
            "web_request",
            instruction="send HTTP request to specified URL or API endpoint, using `requests` library. Tip: to "
                        "send raw data, use `data` parameter. To send data in `application/x-www-form-urlencoded` format, "
                        "use `data_form` parameter. To send data in `application/json` format, use `data_json` parameter. "
                        "Sending data in `data_form` and `data_json` parameters will automatically set `Content-Type`. To "
                        "upload files, use `files` parameter. To send cookies, use `cookies` parameter. To set custom headers, "
                        "use `headers` parameter. You can combine all parameters.",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website or API endpoint",
                    "required": True,
                },
                {
                    "name": "method",
                    "type": "str",
                    "description": "HTTP method, default: GET",
                    "required": False,
                },
                {
                    "name": "headers",
                    "type": "dict",
                    "description": "HTTP headers",
                    "required": False,
                },
                {
                    "name": "params",
                    "type": "dict",
                    "description": "GET parameters",
                    "required": False,
                },
                {
                    "name": "data",
                    "type": "str",
                    "description": "raw data to send in POST requests",
                    "required": False,
                },
                {
                    "name": "data_form",
                    "type": "dict",
                    "description": "data to send in POST `application/x-www-form-urlencoded` requests",
                    "required": False,
                },
                {
                    "name": "data_json",
                    "type": "dict",
                    "description": "JSON data to send in POST `application/json` requests",
                    "required": False,
                },
                {
                    "name": "cookies",
                    "type": "dict",
                    "description": "Cookies",
                    "required": False,
                },
                {
                    "name": "files",
                    "type": "dict",
                    "description": "Files to upload, key is form field name, value is absolute path to file",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to send any HTTP request to specified URL or API endpoint",
        )
        plugin.add_cmd(
            "web_extract_links",
            instruction="open webpage and get list of all links from it",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open URL and get list of all links from it",
        )
        plugin.add_cmd(
            "web_extract_images",
            instruction="open webpage and get list of all images from it",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
                {
                    "name": "download",
                    "type": "bool",
                    "description": "Download images to disk if user wants to, default: False",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open URL and get list of all images from it",
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