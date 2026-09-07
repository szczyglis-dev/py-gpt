#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.06 00:30:00                  #
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
            "pack_archive",
            "unpack_archive",
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
                data.get('mode'),
            )

    def on_post_prompt(self, prompt: str, ctx: CtxItem, mode: str = None) -> str:
        """
        Event: POST_PROMPT

        :param prompt: system prompt
        :param ctx: CtxItem
        :param mode: originating bridge/chat mode
        :return: updated system prompt
        """
        # Filesystem guidance is request/runtime state, not conversation data.
        # Never persist it in CtxItem.extra. Remove a stale key left by older
        # builds and append the dynamic context only to the in-flight system prompt.
        if ctx is not None and isinstance(ctx.extra, dict):
            ctx.extra.pop("agents_v2_filesystem_context", None)

        if self.get_option_value("auto_cwd") and self.window.core.command.is_cmd(inline=False):
            runtime_context = self.build_runtime_filesystem_context()
            if runtime_context:
                prompt += "\n\n" + runtime_context
        return prompt

    def build_runtime_filesystem_context(self) -> str:
        """Build host/sandbox filesystem guidance for the current runtime.

        The host data path is always the working directory for Files I/O. If an
        enabled Code Interpreter uses either Docker sandbox (IPython and/or legacy
        Python), explicitly describe the separate container namespace and /data
        volume mapping so the model does not pass host paths into sandbox code.

        :return: prompt fragment
        """
        host_data_dir = self.window.core.config.get_user_dir("data")
        parts = ["CURRENT WORKING DIRECTORY: " + host_data_dir]

        ipython_sandbox, legacy_sandbox = self.get_code_interpreter_sandbox_modes()
        if not ipython_sandbox and not legacy_sandbox:
            return "\n\n".join(parts)

        guidance = [
            "IMPORTANT FILESYSTEM CONTEXT:",
            "The CURRENT WORKING DIRECTORY shown above is a path on the HOST filesystem. "
            "Use this host path only with host-side Files I/O tools (for example read_file, "
            "save_file, append_file, list_dir, mkdir, file_* and other Files I/O operations).",
            "A Docker Code Interpreter sandbox has a separate filesystem namespace. Never use "
            "the host CURRENT WORKING DIRECTORY path directly inside sandboxed Python, IPython "
            "or sandbox shell/system commands.",
        ]

        if ipython_sandbox:
            guidance.append(
                "For the IPython Docker sandbox, use /data as the working directory inside "
                "ipython_execute/ipython_execute_new, IPython shell or magic commands, and "
                "ipython_sys_exec."
            )

        if legacy_sandbox:
            guidance.append(
                "For the legacy Python Docker sandbox, use /data as the working directory inside "
                "code_execute/code_execute_file/code_execute_all and python_sys_exec."
            )

        guidance.append(
            "The container path /data is mapped to the same host directory: " + host_data_dir
        )
        parts.append(" ".join(guidance))
        return "\n\n".join(parts)

    def get_code_interpreter_sandbox_modes(self) -> tuple[bool, bool]:
        """Return active Code Interpreter Docker sandbox modes.

        This is evaluated at prompt-build time so changing plugin activation or
        either sandbox option immediately changes the generated filesystem context.

        :return: (ipython_sandbox, legacy_python_sandbox)
        """
        plugin_id = "cmd_code_interpreter"
        try:
            if not self.window.controller.plugins.is_enabled(plugin_id):
                return False, False

            plugin = self.window.core.plugins.get(plugin_id)
            if plugin is None:
                return False, False

            return (
                bool(plugin.get_option_value("sandbox_ipython")),
                bool(plugin.get_option_value("sandbox_docker")),
            )
        except Exception as e:
            self.window.core.debug.log(e)
            return False, False

    def is_ipython_sandbox_active(self) -> bool:
        """Backward-compatible helper for the IPython Docker sandbox."""
        return self.get_code_interpreter_sandbox_modes()[0]

    def is_legacy_sandbox_active(self) -> bool:
        """Check whether the enabled Code Interpreter uses legacy Python Docker."""
        return self.get_code_interpreter_sandbox_modes()[1]

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
