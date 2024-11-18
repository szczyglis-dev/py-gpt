#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 01:00:00                  #
# ================================================== #

import json
import re
from datetime import datetime

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_history"
        self.name = "Context history (calendar, inline)"
        self.type = ["cmd.inline"]
        self.description = "Provides real-time access to context history database"
        self.input_text = None
        self.allowed_cmds = [
            "get_ctx_list_in_date_range",
            "get_ctx_content_by_id",
            "count_ctx_in_date",
            "get_day_note",
            "add_day_note",
            "update_day_note",
            "remove_day_note",
        ]
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.add_option(
            "use_tags",
            type="bool",
            value=False,
            label="Enable: using context @ ID tags",
            description="When enabled, it allows to automatically retrieve context history using @ tags, "
                        "e.g. use @123 in question to retrieve summary of context with ID 123",
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
            "ctx_items_limit",
            type="int",
            value=30,
            label="Max contexts to retrieve",
            description="Max items in context history list to retrieve in one query. 0 = no limit",
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
            "prompt_tag_system",
            type="textarea",
            value="ADDITIONAL CONTEXT: Use the following JSON summary of previous discussions as additional context, "
                  "instead of using commands for retrieve content: {context}",
            label="Prompt: tag_system",
            description="Prompt for use @ tag (system)",
            advanced=True,
        )
        self.add_option(
            "prompt_tag_summary",
            type="textarea",
            value="You are an expert in context summarization. "
                  "Please summarize the given discussion (ID: {id}) by addressing the query and preparing it to serve "
                  "as additional context for a new discussion or to continue the current one: {query}",
            label="Prompt: tag_summary",
            description="Prompt for use @ tag (summary)",
            advanced=True,
        )

        # commands
        self.add_cmd(
            "get_ctx_list_in_date_range",
            instruction="get list of context history (previous conversations between you and me), using date-range "
                        "syntax: \"@date(YYYY-MM-DD)\" for single day, \"@date(YYYY-MM-DD,)\" for date FROM, "
                        "\"@date(,YYYY-MM-DD)\" for date TO, and \"@date(YYYY-MM-DD,YYYY-MM-DD)\" for date FROM-TO",
            params=[
                {
                    "name": "range_query",
                    "type": "str",
                    "description": "range query",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows getting the list of context history (previous conversations)",
        )
        self.add_cmd(
            "get_ctx_content_by_id",
            instruction="get summarized content of context by its ID, use summary query to ask another "
                        "model to summarize content, e.g. \"Summarize following discussion answering the query: (query)\"",
            params=[
                {
                    "name": "id",
                    "type": "int",
                    "description": "context ID",
                    "required": True,
                },
                {
                    "name": "summary_query",
                    "type": "str",
                    "description": "query",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows getting summarized content of context with defined ID",
        )
        self.add_cmd(
            "count_ctx_in_date",
            instruction="count items of context history (previous conversations between us), by providing year, "
                        "month, day or combination of them",
            params=[
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows counting contexts in date range",
        )
        self.add_cmd(
            "get_day_note",
            instruction="get day notes for date",
            params=[
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows retrieving day note for specific date",
        )
        self.add_cmd(
            "add_day_note",
            instruction="add day note",
            params=[
                {
                    "name": "note",
                    "type": "str",
                    "description": "content",
                    "required": True,
                },
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows adding day note for specific date",
        )
        self.add_cmd(
            "update_day_note",
            instruction="update day note",
            params=[
                {
                    "name": "note",
                    "type": "str",
                    "description": "content",
                    "required": True,
                },
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows updating day note for specific date",
        )
        self.add_cmd(
            "remove_day_note",
            instruction="remove day note",
            params=[
                {
                    "name": "year",
                    "type": "int",
                    "description": "year",
                    "required": True,
                },
                {
                    "name": "month",
                    "type": "int",
                    "description": "month",
                    "required": True,
                },
                {
                    "name": "day",
                    "type": "int",
                    "description": "day",
                    "required": True,
                },
            ],
            enabled=True,
            description="When enabled, it allows removing day note for specific date",
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

        if name in [
            Event.CMD_SYNTAX_INLINE,  # inline is allowed
            Event.CMD_SYNTAX,
        ]:
            self.cmd_syntax(data)

        # append current time to system prompt if time plugin is not enabled
        elif name == Event.SYSTEM_PROMPT:
            data['value'] = self.on_system_prompt(data['value'])

        elif name == Event.POST_PROMPT:
            data['value'] = self.on_post_prompt(
                data['value'],
                ctx,
            )

        elif name == Event.USER_SEND:
            self.on_user_send(data['value'])

        elif name in [
            Event.CMD_INLINE,  # inline is allowed
            Event.CMD_EXECUTE,
        ]:
            self.cmd(
                ctx,
                data['commands'],
            )

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        # current time
        if not self.window.controller.plugins.is_type_enabled("time"):
            prompt += "\nCurrent time is: " + datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S')
        return prompt

    def on_post_prompt(self, prompt: str, ctx: CtxItem) -> str:
        """
        Event: POST_PROMPT

        :param prompt: prompt
        :param ctx: context
        :return: updated prompt
        """
        # disable if internal context (autonomous mode)
        if ctx.internal:
            return prompt

        # hashtags
        if self.get_option_value("use_tags") and self.input_text:
            extra = self.handle_tags(self.input_text)
            if extra:
                prompt += "\n" + self.get_option_value("prompt_tag_system").format(
                    context=extra,
                )
        self.input_text = None  # reset input text
        return prompt

    def handle_tags(self, text: str) -> str:
        """
        Handle ID tags in input text

        :param text: input text
        :return: summary of contexts in JSON format
        """
        summary = ""
        contexts = []
        hashtags = self.extract_tags(text)
        ids = []
        for tag in hashtags:
            if tag.isdigit():
                id = int(tag)
                ids.append(id)
        for id in ids:
            try:
                prompt = self.get_option_value("prompt_tag_summary").format(
                    id=id,
                    query=self.input_text,
                )
            except Exception as e:
                self.log("Incorrect prompt: " + str(e))
                return ""
            summary = self.get_summary(id, prompt)
            if summary:
                self.log("@using: " + str(id))
                contexts.append({id: summary})
        if contexts:
            summary = json.dumps(contexts)
        return summary

    def extract_tags(self, text: str) -> list:
        """
        Extract tags from text

        :param text: text
        :return: list of tags
        """
        return re.findall(r"@(\d+)", text)

    def on_user_send(self, text: str):
        """
        Event: USER_SEND

        :param text: text
        """
        self.input_text = text

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    @Slot()
    def handle_updated(self):
        """Handle updated signal"""
        self.window.controller.calendar.setup()

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Events: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds and self.has_cmd(item["cmd"]):
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        # worker
        self.worker = Worker()
        self.worker.plugin = self
        self.worker.cmds = my_commands
        self.worker.ctx = ctx

        # signals (base handlers)
        self.worker.signals.updated.connect(self.handle_updated)
        self.worker.signals.finished_more.connect(self.handle_finished_more)
        self.worker.signals.log.connect(self.handle_log)
        self.worker.signals.debug.connect(self.handle_debug)
        self.worker.signals.status.connect(self.handle_status)
        self.worker.signals.error.connect(self.handle_error)

        # check if async allowed
        if not self.window.core.dispatcher.async_allowed(ctx):
            self.worker.run()
            return

        # start
        self.window.threadpool.start(self.worker)

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

    def update_day_note(self, year: int, month: int, day: int, note: str) -> bool:
        """
        Update day note

        :param year: year
        :param month: month
        :param day: day
        :param note: note
        :return: True if success
        """
        return self.window.core.calendar.update_note(year, month, day, note)

    def remove_day_note(self, year: int, month: int, day: int) -> bool:
        """
        Remove day note

        :param year: year
        :param month: month
        :param day: day
        :return: True if success
        """
        return self.window.core.calendar.remove_note(year, month, day)

    def get_list(self, range: str) -> list:
        """
        Get context list in date range

        :param range: date range
        :return: list of context
        """
        limit = int(self.get_option_value("ctx_items_limit"))
        return self.window.core.ctx.get_list_in_date_range(range, limit=limit)

    def get_summary(self, id: int, prompt: str) -> str:
        """
        Get context content summary by ID

        :param id: context ID
        :param prompt: prompt for summarization
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

    def count_ctx_in_date(
            self,
            year: int = None,
            month: int = None,
            day: int = None
    ) -> dict:
        """
        Get context counters

        :param year: year
        :param month: month
        :param day: day
        :return: counters dict
        """
        return self.window.core.ctx.provider.get_ctx_count_by_day(
            year=year,
            month=month,
            day=day,
        )

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
        Get summarized text from chunks, TODO: create external method for chunk summarization

        :param chunks: chunks of text
        :param sys_prompt: system prompt
        :return: summarized text
        """
        summary = []

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
                bridge_context = BridgeContext(
                    prompt=chunk,
                    system_prompt=sys_prompt,
                    max_tokens=max_tokens,
                    model=model,
                    temperature=0.0,
                )
                response = self.window.core.bridge.quick_call(
                    context=bridge_context,
                )
                if response is not None and response != "":
                    summary.append(response)
            except Exception as e:
                self.error(e)

        return "".join(summary)

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        if self.is_threaded():
            return
        full_msg = '[History] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
