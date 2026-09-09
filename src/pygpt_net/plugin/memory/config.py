#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 20:45:00                  #
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
