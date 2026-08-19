#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT plugin tutorial                              #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin


class Plugin(BasePlugin):
    """Small plugin demonstrating options, events and a callable model command."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_plugin"  # must be unique
        self.name = "Example Plugin"
        self.description = "Tutorial plugin showing the current PyGPT plugin API."
        self.prefix = "Example"
        self.allowed_cmds = ["funny_cmd"]
        self.init_options()

    def init_options(self):
        """Declare plugin settings and callable commands.

        `add_option()` controls the plugin settings UI. `add_cmd()` is the current
        helper for declaring model-callable commands; do not manually recreate
        the command schema unless you need custom behavior.
        """
        self.add_option(
            "append_footer",
            type="bool",
            value=False,
            label="Append example footer",
            description="Append a short instruction to the final system prompt.",
        )
        self.add_option(
            "footer_text",
            type="text",
            value="End the response with: [example plugin enabled]",
            label="Footer instruction",
            description="Instruction appended when the example footer option is enabled.",
            advanced=True,
        )

        self.add_cmd(
            "funny_cmd",
            instruction="return an example funny response for the provided query",
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "topic or query to include in the example response",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable the example funny_cmd tool.",
        )

    def handle(self, event: Event, *args, **kwargs):
        """Receive application/model events dispatched to enabled plugins.

        The complete current event list is defined by
        `pygpt_net.core.events.Event`. Keeping the list in one source file avoids
        stale copies of event names in extension examples.
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        # POST_PROMPT_END is useful when you want to alter the final prepared
        # system prompt just before the request leaves the app.
        if name == Event.POST_PROMPT_END:
            if self.get_option_value("append_footer"):
                data["value"] = self.append_footer(data.get("value", ""))

        # Normal CMD_* events require +Tools. The INLINE variants are available
        # to plugins that intentionally expose commands without that switch.
        elif name in (Event.CMD_SYNTAX, Event.CMD_SYNTAX_INLINE):
            self.cmd_syntax(data)

        elif name in (Event.CMD_EXECUTE, Event.CMD_INLINE):
            self.cmd(ctx, data.get("commands", []))

        # Any handler can stop propagation to later listeners if necessary:
        # event.stop = True

    def append_footer(self, prompt: str) -> str:
        """Append an instruction without destroying the existing system prompt."""
        footer = str(self.get_option_value("footer_text") or "").strip()
        if not footer:
            return prompt
        if prompt and not prompt.endswith("\n"):
            prompt += "\n\n"
        return prompt + footer

    def cmd_syntax(self, data: dict):
        """Publish enabled command schemas to the current model request."""
        append = data["cmd"].append
        for cmd_name in self.allowed_cmds:
            if self.has_cmd(cmd_name):
                append(self.get_cmd(cmd_name))

    def cmd(self, ctx: CtxItem, cmds: list):
        """Execute commands belonging to this plugin and reply to the model."""
        for item in cmds or []:
            if not isinstance(item, dict):
                continue

            cmd_name = item.get("cmd")
            if cmd_name not in self.allowed_cmds or not self.has_cmd(cmd_name):
                continue

            if cmd_name == "funny_cmd":
                params = item.get("params") or {}
                query = str(params.get("query", "")).strip()

                # A plugin reply uses at least `request` + `result`. PyGPT stores
                # the result in the context/tool output and routes it back to the
                # model using the active command transport (native or internal).
                response = {
                    "request": {
                        "cmd": cmd_name,
                        "params": params,
                    },
                    "result": f"Example response for: {query or '(empty query)'}",
                }
                self.reply(response, ctx)
                return
