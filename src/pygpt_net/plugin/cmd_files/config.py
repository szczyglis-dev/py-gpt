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
        plugin.add_option(
            "model_tmp_query",
            type="combo",
            value="gpt-4o-mini",
            label="Model for query in-memory index",
            description="Model used for query in-memory index for `query_file` command, "
                        "default: gpt-3.5-turbo",
            tooltip="Query model",
            use="models",
            tab="indexing",
        )
        plugin.add_option(
            "idx",
            type="text",
            value="base",
            label="Index to use when indexing files",
            description="ID of index to use for files indexing",
            tooltip="Index name",
            tab="indexing",
        )
        plugin.add_option(
            "use_loaders",
            type="bool",
            value=True,
            label="Use data loaders",
            description="Use data loaders from Llama-index for file reading (read_file command)",
        )
        plugin.add_option(
            "auto_index",
            type="bool",
            value=False,
            label="Auto index reading files",
            description="If enabled, every time file is read, it will be automatically indexed",
            tab="indexing",
        )
        plugin.add_option(
            "only_index",
            type="bool",
            value=False,
            label="Only index reading files",
            description="If enabled, file will be indexed without reading it",
            tab="indexing",
        )

        # commands
        plugin.add_cmd(
            "send_file",
            instruction="send file as attachment from my computer to you for analyze",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Upload file as attachment",
        )
        plugin.add_cmd(
            "read_file",
            instruction="read data from files",
            params=[
                {
                    "name": "path",
                    "type": "list",
                    "description": "path(s) to files",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Read file",
        )
        plugin.add_cmd(
            "query_file",
            instruction="read, index and quick query file for additional context",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "query",
                    "type": "str",
                    "description": "query",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Query file with Llama-index",
            tab="indexing",
        )
        plugin.add_cmd(
            "save_file",
            instruction="save data to file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path to file",
                    "required": True,
                },
                {
                    "name": "data",
                    "type": "str",
                    "description": "text data",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Save file",
        )
        plugin.add_cmd(
            "append_file",
            instruction="append data to file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "data",
                    "type": "str",
                    "description": "data",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Append to file",
        )
        plugin.add_cmd(
            "delete_file",
            instruction="delete file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Delete file",
        )
        plugin.add_cmd(
            "list_dir",
            instruction="list files and dirs",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: List files in directory (ls)",
        )
        plugin.add_cmd(
            "tree",
            instruction="get directory tree",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: get directory tree",
        )
        plugin.add_cmd(
            "mkdir",
            instruction="create directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Directory creation (mkdir)",
        )
        plugin.add_cmd(
            "download_file",
            instruction="download file",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "source URL",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Downloading files",
        )
        plugin.add_cmd(
            "rmdir",
            instruction="remove directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Removing directories",
        )
        plugin.add_cmd(
            "copy_file",
            instruction="copy file",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Copying files",
        )
        plugin.add_cmd(
            "copy_dir",
            instruction="recursive copy directory",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Copying directories (recursive)",
        )
        plugin.add_cmd(
            "move",
            instruction="move file or directory",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Move files and directories (rename)",
        )
        plugin.add_cmd(
            "is_dir",
            instruction="check if path is directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Check if path is directory",
        )
        plugin.add_cmd(
            "is_file",
            instruction="check if path is file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Check if path is file",
        )
        plugin.add_cmd(
            "file_exists",
            instruction="check if file or directory exists",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Check if file or directory exists",
        )
        plugin.add_cmd(
            "file_size",
            instruction="get file size",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Get file size",
        )
        plugin.add_cmd(
            "file_info",
            instruction="get file info",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Get file info",
        )
        plugin.add_cmd(
            "cwd",
            instruction="get current working directory (abs path)",
            params=[],
            enabled=True,
            description="Enable: Get current working directory (cwd)",
        )
        plugin.add_cmd(
            "file_index",
            instruction="index (embed as vectors in vector DB) file or directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to index file or directory using Llama-index",
        )
        plugin.add_cmd(
            "find",
            instruction="find file or directory, use empty path to search in current dir",
            params=[
                {
                    "name": "pattern",
                    "type": "str",
                    "description": "name pattern",
                    "required": True,
                },
                {
                    "name": "path",
                    "type": "str",
                    "description": "search directory",
                    "required": True,
                },
                {
                    "name": "recursive",
                    "type": "bool",
                    "description": "recursive search",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Find file or directory",
        )