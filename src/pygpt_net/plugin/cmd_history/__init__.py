#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.02 18:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_history"
        self.name = "Command: Context history (calendar)"
        self.description = "Provides access to context history database, Execute commands option enabled is required."
        self.allowed_cmds = [
            "get_ctx_list_in_date_range",
            "get_ctx_content_by_id",
            "get_day_note",
            "add_day_note",
        ]
        self.order = 100
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options""" 
        self.add_option(
            "cmd_get_ctx_list_in_date_range",
            type="bool",
            value=True,
            label="Allow get date range context list",
            description="When enabled, it allows to get the list of context history (previous conversations)",
        )
        self.add_option(
            "cmd_get_ctx_content_by_id",
            type="bool",
            value=True,
            label="Allow get context content by ID",
            description="When enabled, it allows to get summarized content of context with defined ID",
        )
        self.add_option(
            "cmd_get_day_note",
            type="bool",
            value=True,
            label="Allow get day note",
            description="When enabled, it allows to get day note for specific date",
        )
        self.add_option(
            "cmd_add_day_note",
            type="bool",
            value=True,
            label="Allow add day note",
            description="When enabled, it allows to add day note for specific date",
        )
        self.add_option(
            "model_summarize",
            type="combo",
            value="gpt-3.5-turbo",
            label="Model",
            description="Model used for summarize, default: gpt-3.5-turbo",
            tooltip="Summarize model",
            use="models",
        )
        self.add_option(
            "summary_max_tokens",
            type="int",
            value=1500,
            label="Max summary tokens",
            description="Max tokens in output when generating summary",
            min=0,
            max=None,
        )
        self.add_option(
            "chunk_size",
            type="int",
            value=100000,
            label="Per-context items content chunk size",
            description="Per-context content chunk size (max characters per chunk)",
            min=1,
            max=None,
        )
        self.add_option(
            "syntax_get_ctx_list_in_date_range",
            type="textarea",
            value='"get_ctx_list_in_date_range": use to get the list of context history '
                  '(previous conversations between you and me), with corresponding IDs, '
                  'using the special date-range query syntax: "@date(YYYY-MM-DD)" for single day, '
                  '"@date(YYYY-MM-DD)," for date from, ",@date(YYYY-MM-DD)" for date to, '
                  'and "@date(YYYY-MM-DD),@date(YYYY-MM-DD)" for range from-to, params: "range_query"',
            label="Syntax: get_ctx_list_in_date_range",
            description="Syntax for get_ctx_list_in_date_range command",
            advanced=True,
        )
        self.add_option(
            "syntax_get_ctx_content_by_id",
            type="textarea",
            value='"get_ctx_content_by_id": use to get summarized content of context with defined ID, prepare summary '
                  'query to ask another model to summarize the content, '
                  'starting from e.g. "Summarize this discussion for... (additional query)", '
                  'params: "id", "summary_query"',
            label="Syntax: get_ctx_content_by_id",
            description="Syntax for get_ctx_content_by_id command",
            advanced=True,
        )
        self.add_option(
            "syntax_get_day_note",
            type="textarea",
            value='"get_day_note": use to get my day notes and plans for a specific date, '
                  'params: "year", "month", "day"',
            description="Syntax for get_day_note command",
            advanced=True,
        )
        self.add_option(
            "syntax_add_day_note",
            type="textarea",
            value='"add_day_note": use to add day note for specific date, '
                  'params: "year", "month", "day", "note"',
            label="Syntax: add_day_note",
            description="Syntax for add_day_note command",
            advanced=True,
        )

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: args
        :param kwargs: kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name in [
            # Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.is_cmd_allowed(option):
                key = "syntax_" + option
                if self.has_option(key):
                    data['syntax'].append(str(self.get_option_value(key)))

    def is_cmd_allowed(self, cmd: str) -> bool:
        """
        Check if cmd is allowed

        :param cmd: command name
        :return: True if allowed
        """
        key = "cmd_" + cmd
        if self.has_option(key) and self.get_option_value(key) is True:
            return True
        return False

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Events: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        for item in my_commands:
            try:
                if item["cmd"] == "get_ctx_list_in_date_range":
                    range = item["params"]["range_query"]
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.get_list(range)
                    response = {
                        "request": request,
                        "result": data,
                    }
                    ctx.results.append(response)
                    ctx.reply = True

                elif item["cmd"] == "get_ctx_content_by_id":
                    id = int(item["params"]["id"])
                    request = {
                        "cmd": item["cmd"],
                    }
                    prompt = item["params"]["summary_query"]
                    data = self.get_summary(id, prompt)
                    response = {
                        "request": request,
                        "result": data,
                    }
                    ctx.results.append(response)
                    ctx.reply = True

                elif item["cmd"] == "get_day_note":
                    year = int(item["params"]["year"])
                    month = int(item["params"]["month"])
                    day = int(item["params"]["day"])
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.get_day_note(year, month, day)
                    response = {
                        "request": request,
                        "result": data,
                    }
                    ctx.results.append(response)
                    ctx.reply = True

                elif item["cmd"] == "add_day_note":
                    year = int(item["params"]["year"])
                    month = int(item["params"]["month"])
                    day = int(item["params"]["day"])
                    note = item["params"]["note"]
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.add_day_note(year, month, day, note)
                    response = {
                        "request": request,
                        "result": data,
                    }
                    ctx.results.append(response)
                    ctx.reply = True
                    self.window.controller.calendar.setup()
            except Exception as e:
                self.log("Error: " + str(e))
                return

    def get_day_note(self, year: int, month: int, day: int) -> str:
        """
        Get day note

        :param year: year
        :param month: month
        :param day: day
        :return: day note
        """
        return self.window.core.calendar.load_note(year, month, day)

    def add_day_note(self, year: int, month: int, day: int, note: str) -> bool:
        """
        Add day note

        :param year: year
        :param month: month
        :param day: day
        :param note: note
        :return: True if success
        """
        return self.window.core.calendar.append_to_note(year, month, day, note)

    def get_list(self, range: str) -> list:
        """
        Get context list in date range

        :param range: date range
        :return: list of context
        """
        return self.window.core.ctx.get_list_in_date_range(range)

    def get_summary(self, id: int, prompt: str) -> str:
        """
        Get context content summary by ID

        :param id: context ID
        :param prompt: prompt
        :return: context content summary
        """
        chunk_size = int(self.get_option_value("chunk_size"))
        items = self.window.core.ctx.get_items_by_id(id)
        if items is None or len(items) == 0:
            return ""
        content = "\n".join(items)
        chunks = self.to_chunks(content, chunk_size)  # it returns list of chunks
        summary = self.get_summarized_text(chunks, prompt)
        return summary

    def to_chunks(
            self,
            text: str,
            chunk_size: int
    ) -> list:
        """
        Split text into chunks

        :param text: text to split
        :param chunk_size: chunk size
        :return: list of chunks
        """
        if text is None or text == "":
            return []
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def get_summarized_text(
            self,
            chunks: list,
            sys_prompt: str = None
    ) -> str:
        """
        Get summarized text from chunks

        :param chunks: chunks of text
        :param sys_prompt: system prompt
        :return: summarized text
        """
        summary = ""

        # get custom prompt if set
        max_tokens = int(self.get_option_value("summary_max_tokens"))

        # get model
        model = self.window.core.models.from_defaults()
        tmp_model = self.get_option_value("summary_model")
        if self.window.core.models.has(tmp_model):
            model = self.window.core.models.get(tmp_model)

        # summarize per chunk
        for chunk in chunks:
            try:
                response = self.window.core.bridge.quick_call(
                    prompt=chunk,
                    system_prompt=sys_prompt,
                    max_tokens=max_tokens,
                    model=model,
                )
                if response is not None and response != "":
                    summary += response
            except Exception as e:
                self.error(e)
        return summary

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CTX HISTORY] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        print(full_msg)
