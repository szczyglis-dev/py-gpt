#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.01 00:45:00                  #
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
            "auto_cwd",
            type="bool",
            value=True,
            label="Auto-append CWD to system prompt",
            description="Automatically append current working directory to system prompt",
        )
        plugin.add_option(
            "model_tmp_query",
            type="combo",
            value=MODEL_DEFAULT_MINI,
            label="Model for query in-memory index",
            description="Model used for query in-memory index for `fs_query_file` command, "
                        "default: gpt-4o-mini",
            tooltip="Query model",
            use="models",
            tab="indexing",
        )
        plugin.add_option(
            "use_project_index",
            type="bool",
            value=True,
            label="Use project index if in use",
            description="When the current conversation is inside a project, index files into that project's isolated index instead of the configured global index.",
            tab="indexing",
        )
        plugin.add_option(
            "idx",
            type="bool_list",
            use="idx",
            use_params={
                "none": False,
                "project": False,
            },
            value="base",
            label="Indexes to use when indexing files",
            description="Select one or more global indexes to use for file indexing. "
                        "If project indexing is enabled and the current conversation is in a project, "
                        "the current project's isolated index is used instead.",
            tooltip="Index names",
            tab="indexing",
        )
        plugin.add_option(
            "use_loaders",
            type="bool",
            value=True,
            label="Use data loaders",
            description="Use data loaders from Llama-index for file reading (fs_read_file command)",
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
            "fs_send_file",
            tab="delivery",
            instruction=(
                "send file as a normal persistent chat attachment; use fs_attach_runtime_file (if available) instead when a local "
                "file should be passed only to the immediate next model request for native analysis without adding "
                "it to the persistent chat attachment list"
            ),
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Adds a local file as a persistent chat attachment for the model.",
        )
        plugin.add_cmd(
            "fs_deliver_file_to_user",
            tab="delivery",
            instruction=(
                "deliver an existing local file to the user as a response artifact; use only for an intentional "
                "user-facing deliverable after it is ready, never for files merely read, searched or inspected. "
                "Use fs_send_file/fs_attach_runtime_file when the file is input for the model rather than output for the user"
            ),
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path to the file to deliver",
                    "required": True,
                },
            ],
            enabled=True,
            description="Delivers a ready file to the user as a response artifact.",
        )
        plugin.add_cmd(
            "fs_attach_runtime_file",
            tab="delivery",
            instruction=(
                "attach one or more existing local files as runtime-only attachments to the next model request; "
                "use this especially when you need the active multimodal model to inspect a local image natively "
                "(for example a PNG/JPEG/WebP screenshot) instead of reading or describing it through fs_read_file; "
                "available only in agents and expert runtimes; the attachment is available immediately after this tool result, "
                "does not need to be added to the persistent chat attachment list, and is analyzed only when the "
                "active model/provider supports that attachment type"
            ),
            params=[
                {
                    "name": "path",
                    "type": "list",
                    "description": "path(s) to local files to attach to the immediate next model request",
                    "required": True,
                },
            ],
            enabled=True,
            description="Temporarily attaches local files or images to the next model request for analysis.",
        )
        plugin.add_cmd(
            "fs_runtime_artifacts",
            tab="delivery",
            instruction=(
                "resolve files/images created or downloaded by provider-native remote tools or other tools "
                "into shared temporary runtime storage before using them with local Python/IPython/System tools; "
                "omit path to resolve artifacts already present in the current tool context, or provide explicit "
                "path(s). The result returns path, host_path, sandbox_path and runtime_paths. When invoking a "
                "execution tool, use runtime_paths.filesystem for Python and system commands; "
                "use host_path for host filesystem tools. These paths already reflect the active runtime. "
                "Do not show internal paths to the user unless asked"
            ),
            params=[
                {
                    "name": "path",
                    "type": "list",
                    "description": "optional local artifact path(s); omit to use current generated/downloaded artifacts",
                    "required": False,
                },
            ],
            enabled=True,
            description="Prepares generated or downloaded files for use by local tools and returns their paths.",
        )
        plugin.add_cmd(
            "fs_read_file",
            instruction=(
                "read text/data from local files. Do not call filesystem tools merely to access an image that the "
                "user already supplied through the chat attachment UI; System handles user images through the "
                "chat/vision attachment pipeline. Binary images are not meaningfully inspected with fs_read_file."
            ),
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
            "fs_query_file",
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
            enabled=False,
            description="Enable: Query file with Llama-index",
            tab="indexing",
        )
        plugin.add_cmd(
            "fs_save_file",
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
            "fs_append_file",
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
            "fs_delete_file",
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
            "fs_list_dir",
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
            "fs_tree",
            instruction="get directory fs_tree",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: get directory fs_tree",
        )
        plugin.add_cmd(
            "fs_mkdir",
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
            description="Enable: Directory creation (fs_mkdir)",
        )
        plugin.add_cmd(
            "fs_download_file",
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
            "fs_rmdir",
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
            "fs_copy_file",
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
            "fs_copy_dir",
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
            "fs_move",
            instruction="fs_move file or directory",
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
            "fs_is_dir",
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
            "fs_is_file",
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
            "fs_file_exists",
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
            "fs_file_size",
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
            "fs_file_info",
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
            "fs_cwd",
            instruction="get current working directory (abs path)",
            params=[],
            enabled=True,
            description="Enable: Get current working directory (fs_cwd)",
        )
        plugin.add_cmd(
            "fs_file_index",
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
            "fs_pack_archive",
            instruction="pack files or directories into a ZIP or TAR archive; archive format is detected from destination extension",
            params=[
                {
                    "name": "src",
                    "type": "list",
                    "description": "source file(s) or directory/directories to pack",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "destination archive path (.zip, .tar, .tar.gz/.tgz, .tar.bz2/.tbz2, .tar.xz/.txz)",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Pack files/directories into ZIP or TAR archive",
        )
        plugin.add_cmd(
            "fs_unpack_archive",
            instruction="unpack a ZIP or TAR archive into a directory; archive format is detected automatically",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "source archive path (.zip, .tar, .tar.gz/.tgz, .tar.bz2/.tbz2, .tar.xz/.txz)",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "destination directory",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Unpack ZIP or TAR archive",
        )
        plugin.add_cmd(
            "fs_find",
            instruction=(
                "fs_find files or directories by their name/basename pattern only; "
                "this tool searches filesystem entry names, NOT text or other content inside files. "
                "Use an empty path to search in the current directory"
            ),
            params=[
                {
                    "name": "pattern",
                    "type": "str",
                    "description": (
                        "file or directory name glob pattern, e.g. '*.py', 'test_*', "
                        "or 'config.json'; matches names only, never file contents"
                    ),
                    "required": True,
                },
                {
                    "name": "path",
                    "type": "str",
                    "description": "directory in which to search; use an empty value for the current directory",
                    "required": True,
                },
                {
                    "name": "recursive",
                    "type": "bool",
                    "description": "search recursively through subdirectories",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Find file or directory by name",
        )