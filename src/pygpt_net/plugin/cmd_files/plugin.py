#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 20:35:00                  #
# ================================================== #

import os

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .output import Output


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_files"
        self.name = "Files I/O"
        self.description = "Provides commands to read and write files"
        self.prefix = "I/O"
        self.order = 100
        self.allowed_cmds = [
            "read_file",
            "query_file",
            "save_file",
            "append_file",
            "delete_file",
            "list_dir",
            "mkdir",
            "download_file",
            "rmdir",
            "copy_file",
            "copy_dir",
            "move",
            "find",
            "is_dir",
            "is_file",
            "tree",
            "file_exists",
            "file_size",
            "file_info",
            "send_file",
            "cwd",
            "file_index",
        ]
        self.use_locale = True
        self.worker = None
        self.output = Output(self)
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

        elif name == Event.TOOL_OUTPUT_RENDER:
            if data['tool'] == self.id:
                data['html'] = self.output.handle(ctx, data['content'])

        elif name == Event.MODELS_CHANGED:
            # update models list
            self.refresh_option("model_tmp_query")

        elif name == Event.POST_PROMPT_END:
            # ignore if reply for command or internal
            if ctx.reply or data["reply"]:
                return

            data['value'] = self.on_post_prompt(
                data['value'],
                ctx,
            )

    def on_post_prompt(self, prompt: str, ctx: CtxItem) -> str:
        """
        Event: POST_PROMPT

        :param prompt: system prompt
        :param ctx: CtxItem
        :return: updated system prompt
        """
        if self.get_option_value("auto_cwd") and self.window.core.command.is_cmd(inline=False):
            host_data_dir = self.window.core.config.get_user_dir("data")
            prompt += "\n\nCURRENT WORKING DIRECTORY: " + host_data_dir

            if self.is_ipython_sandbox_active():
                prompt += (
                    "\n\nIMPORTANT FILESYSTEM CONTEXT: The CURRENT WORKING DIRECTORY shown above is a path "
                    "on the HOST filesystem and applies only to host-side Files I/O tools "
                    "(for example read_file, save_file, append_file, list_dir, mkdir, file_* and "
                    "other Files I/O operations). The Code Interpreter IPython environment is running "
                    "inside a Docker sandbox and must not use the host path directly. Inside IPython "
                    "code, IPython shell/magic commands and ipython_sys_exec, use /data for the same "
                    "working directory. The container path /data is mapped to the host directory: " + host_data_dir
                )
        return prompt

    def is_ipython_sandbox_active(self) -> bool:
        """
        Check whether the enabled Code Interpreter uses the IPython Docker sandbox.

        This is evaluated at prompt-build time so switching either the plugin or its
        sandbox option immediately changes the filesystem guidance without requiring
        a restart.

        :return: True if Code Interpreter is enabled and IPython sandbox is active
        """
        plugin_id = "cmd_code_interpreter"
        try:
            if not self.window.controller.plugins.is_enabled(plugin_id):
                return False

            plugin = self.window.core.plugins.get(plugin_id)
            if plugin is None:
                return False

            return bool(plugin.get_option_value("sandbox_ipython"))
        except Exception as e:
            self.window.core.debug.log(e)
            return False

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        from .worker import Worker

        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx

            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)

    def get_index_names(self) -> list:
        """Return effective index targets for file indexing.

        The isolated current-project index takes precedence when project-aware
        indexing is enabled. Otherwise, return all global indexes selected in
        the plugin bool-list option.
        """
        if self.get_option_value("use_project_index"):
            idx = self.window.core.idx.get_current_project_idx(virtual=True)
            if idx is not None:
                return [idx]

        value = self.get_option_value("idx")
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            raw = value
        else:
            raw = str(value).split(",")

        indexes = []
        for idx in raw:
            idx = str(idx).strip()
            if (not idx
                    or idx == "_"
                    or idx == self.window.core.idx.project.VIRTUAL_ID
                    or idx in indexes):
                continue
            indexes.append(idx)
        return indexes

    def get_index_name(self) -> str:
        """Return first effective index target (backward-compatible helper)."""
        indexes = self.get_index_names()
        return indexes[0] if indexes else ""

    def read_as_text(self, path: str, use_loaders: bool = True) -> str:
        """
        Read file and return content as text

        :param path: file path
        :param use_loaders: use Llama-index loader to read file
        :return: text content
        """
        # use_loaders = False
        self.window.core.security.ensure_read(path, sandbox=False)
        if use_loaders:
            content, docs = self.window.core.idx.indexing.read_text_content(path)
            return content
        else:
            data = ""
            if os.path.isfile(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = file.read()
            return data
