#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 15:15:00                  #
# ================================================== #

from pygpt_net.core.types import MODEL_DEFAULT_MINI
from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """Set default plugin options."""
        plugin.add_option(
            "model_update",
            type="combo",
            value=MODEL_DEFAULT_MINI,
            label="Memory update model",
            description="Model used for automatic memory updates and, when enabled, for refining memory_add operations.",
            tooltip="Model used to update and refine memory.",
            use="models",
        )
        plugin.add_option(
            "max_chars",
            type="int",
            value=15000,
            label="Maximum memory characters",
            description=(
                "Target maximum memory size in characters. The model is asked to stay within this limit; "
                "storage allows an additional 300-character safety margin before hard truncation."
            ),
            tooltip="Target memory size in characters; a 300-character safety margin is allowed before hard truncation.",
            min=1,
            max=None,
        )
        plugin.add_option(
            "refine_add",
            type="bool",
            value=True,
            label="Refine memory before adding",
            description=(
                "Applies only to manual memory_add calls. When enabled, the configured memory update model "
                "merges and rewrites the added information into the existing memory instead of appending raw text. "
                "Automatic end-of-context memory updates are always refined by the model regardless of this setting."
            ),
            tooltip=(
                "Refine manual memory_add calls with the configured model. Automatic context memory updates "
                "are always refined."
            ),
        )
        plugin.add_option(
            "key_search_content",
            type="bool",
            value=False,
            label="Search memory key content",
            description=(
                "Also search stored key values/content in memory_key_search. Key names are always searched with "
                "LIKE. Disabled by default to avoid scanning stored content."
            ),
            tooltip="Also search key content in memory_key_search. Disabled by default.",
        )
        plugin.add_option(
            "auto_attach",
            type="bool",
            value=False,
            label="Auto attach memory to every conversation",
            description="Automatically append the active global or project memory to the system prompt in every conversation.",
            tooltip="Attach memory automatically to all conversations.",
        )
        plugin.add_option(
            "auto_attach_project",
            type="bool",
            value=True,
            label="Auto attach memory only in projects",
            description="Automatically append memory to the system prompt when the current conversation belongs to a project.",
            tooltip="Attach memory automatically only for project conversations.",
        )

        plugin.add_cmd(
            "memory_get",
            instruction="read the current global or project memory",
            params=[],
            enabled=True,
            description="Enable: read the complete memory for the current scope.",
        )
        plugin.add_cmd(
            "memory_add",
            instruction=(
                "add only highly important, durable information to the current global or project memory and merge it "
                "with existing memory; use this tool sparingly and do not write memory for routine, temporary, or "
                "low-value details"
            ),
            params=[
                {
                    "name": "text",
                    "type": "str",
                    "description": "Information to add to memory.",
                    "required": True,
                },
            ],
            enabled=False,
            description=(
                "Enable: add only highly important, durable information to memory for the current scope. "
                "The model should use this tool sparingly, not after routine turns or for temporary details."
            ),
        )
        plugin.add_cmd(
            "memory_update",
            instruction="replace the current global or project memory with updated content",
            params=[
                {
                    "name": "text",
                    "type": "str",
                    "description": "Complete replacement content for memory.",
                    "required": True,
                },
            ],
            enabled=False,
            description="Enable: replace the complete memory content for the current scope.",
        )
        plugin.add_cmd(
            "memory_clear",
            instruction=(
                "clear the current global or project memory only after the user explicitly confirms the deletion; "
                "always ask for confirmation before calling this tool"
            ),
            params=[
                {
                    "name": "confirmed",
                    "type": "bool",
                    "description": "Must be true only after the user explicitly confirmed clearing memory.",
                    "required": True,
                },
            ],
            enabled=True,
            description=(
                "Enable: clear memory for the current scope. The model must first ask the user for explicit "
                "confirmation and call this tool only after confirmation."
            ),
        )
        plugin.add_cmd(
            "memory_key_get",
            instruction=(
                "read raw database-backed memory records by one key or a list of keys from the current global or "
                "project scope for later reuse; provide key or keys"
            ),
            params=[
                {
                    "name": "key",
                    "type": "str",
                    "description": "Single memory key to read. Use either key or keys.",
                    "required": False,
                },
                {
                    "name": "keys",
                    "type": "list",
                    "description": "List of memory keys to read. Use either key or keys.",
                    "required": False,
                },
            ],
            enabled=True,
            label="Read keyed memory",
            description="Enable: read raw keyed memory records from the current global or project scope.",
            tooltip="Read raw keyed memory records from the current global or project scope.",
        )
        plugin.add_cmd(
            "memory_key_add",
            instruction=(
                "store a new raw value in the database under a key for later use in the current global or project "
                "scope; use only for truly important data worth preserving and do not use for routine details"
            ),
            params=[
                {
                    "name": "key",
                    "type": "str",
                    "description": "New memory key.",
                    "required": True,
                },
                {
                    "name": "content",
                    "type": "str",
                    "description": "Raw content to store under the key without LLM processing.",
                    "required": True,
                },
            ],
            enabled=True,
            label="Add keyed memory",
            description=(
                "Enable: store a new raw database value by key for later use. Use only for truly important data; "
                "existing keys are not overwritten."
            ),
            tooltip="Store a new raw value by key. Use only for truly important data.",
        )
        plugin.add_cmd(
            "memory_key_append",
            instruction=(
                "append raw content exactly as provided to an existing database-backed memory key in the current "
                "global or project scope; use only for truly important data worth preserving"
            ),
            params=[
                {
                    "name": "key",
                    "type": "str",
                    "description": "Existing memory key.",
                    "required": True,
                },
                {
                    "name": "content",
                    "type": "str",
                    "description": "Raw content to append exactly as provided, without an automatic separator or LLM processing.",
                    "required": True,
                },
            ],
            enabled=True,
            label="Append keyed memory",
            description=(
                "Enable: append raw content to an existing keyed memory value. Use only for truly important data."
            ),
            tooltip="Append raw content to an existing key without LLM processing.",
        )
        plugin.add_cmd(
            "memory_key_update",
            instruction=(
                "replace the raw content of an existing database-backed memory key in the current global or project "
                "scope for later use; use only for truly important data worth preserving"
            ),
            params=[
                {
                    "name": "key",
                    "type": "str",
                    "description": "Existing memory key to update.",
                    "required": True,
                },
                {
                    "name": "content",
                    "type": "str",
                    "description": "Complete raw replacement content, stored without LLM processing.",
                    "required": True,
                },
            ],
            enabled=True,
            label="Update keyed memory",
            description=(
                "Enable: replace raw content for an existing database-backed memory key. Use only for truly important data."
            ),
            tooltip="Replace raw content for an existing key without LLM processing.",
        )
        plugin.add_cmd(
            "memory_key_list",
            instruction="list only the stored memory key names for the current global or project scope, without content",
            params=[],
            enabled=True,
            label="List memory keys",
            description="Enable: list memory key names for the current scope without returning their content.",
            tooltip="List memory key names without content.",
        )
        plugin.add_cmd(
            "memory_key_search",
            instruction=(
                "search database-backed memory keys in the current global or project scope using LIKE contains "
                "matching on key names; optionally search content too when enabled in plugin settings"
            ),
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "Text to find using LIKE '%query%' in key names and, if enabled, stored content.",
                    "required": True,
                },
            ],
            enabled=True,
            label="Search memory keys",
            description=(
                "Enable: search keyed memory with LIKE matching on key names. Content is searched only when the "
                "Search memory key content option is enabled."
            ),
            tooltip="Search key names with LIKE and optionally search stored content.",
        )
        plugin.add_cmd(
            "memory_key_remove",
            instruction=(
                "remove one database-backed memory key or a list of keys from the current global or project scope"
            ),
            params=[
                {
                    "name": "key",
                    "type": "str",
                    "description": "Single memory key to remove. Use either key or keys.",
                    "required": False,
                },
                {
                    "name": "keys",
                    "type": "list",
                    "description": "List of memory keys to remove. Use either key or keys.",
                    "required": False,
                },
            ],
            enabled=True,
            label="Remove memory keys",
            description="Enable: remove one or more memory keys from the current global or project scope.",
            tooltip="Remove one or more stored memory keys from the current scope.",
        )

