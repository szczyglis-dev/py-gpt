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

import json
import re
from datetime import datetime

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, KernelEvent
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_history"
        self.name = "Context history (calendar, inline)"
        self.type = ["cmd.inline"]
        self.description = "Provides real-time access to context history database"
        self.prefix = "History"
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
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

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

        elif name == Event.MODELS_CHANGED:
            # update models list
            self.refresh_option("model_summarize")

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

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        worker = Worker()
        worker.from_defaults(self)
        worker.cmds = my_commands
        worker.ctx = ctx

        worker.signals.updated.connect(self.handle_updated)

        if not self.is_async(ctx):
            worker.run()
            return
        worker.run_async()

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
                event = KernelEvent(KernelEvent.CALL, {
                    'context': bridge_context,
                    'extra': {},
                })
                self.window.dispatch(event)
                response = event.data.get('response')
                if response is not None and response != "":
                    summary.append(response)
            except Exception as e:
                self.error(e)

        return "".join(summary)
