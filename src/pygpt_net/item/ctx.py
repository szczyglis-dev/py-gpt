#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 15:00:00                  #
# ================================================== #

import datetime
import json
import time


class CtxItem:
    def __init__(self, mode=None):
        """
        Context item

        :param mode: Mode (completion, chat, img, vision, langchain, assistant)
        """
        self.id = None
        self.meta_id = None
        self.external_id = None
        self.stream = None
        self.cmds = []
        self.results = []
        self.urls = []
        self.images = []
        self.files = []
        self.attachments = []
        self.reply = False
        self.input = None
        self.output = None
        self.mode = mode
        self.model = None
        self.thread = None
        self.msg_id = None
        self.run_id = None
        self.input_name = None
        self.output_name = None
        self.input_timestamp = None
        self.output_timestamp = None
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.extra = None
        self.current = False
        self.internal = False
        self.is_vision = False
        self.idx = 0
        self.first = False

    def set_input(self, input: str | None, name: str = None):
        """
        Set input

        :param input: input text (prompt)
        :param name: input person name
        """
        self.input = input
        self.input_name = name
        self.input_timestamp = int(time.time())

    def set_output(self, output: str | None, name: str = None):
        """
        Set output

        :param output: output text
        :param name: output person name
        """
        self.output = output
        self.output_name = name
        self.output_timestamp = int(time.time())

    def set_tokens(self, input_tokens: int, output_tokens: int):
        """
        Set tokens usage

        :param input_tokens: prompt tokens
        :param output_tokens: output tokens
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens

    def to_dict(self) -> dict:
        """
        Dump context item to dict

        :return: dict
        """
        return {
            "id": self.id,
            "meta_id": self.meta_id,
            "external_id": self.external_id,
            "stream": self.stream,
            "cmds": self.cmds,
            "results": self.results,
            "urls": self.urls,
            "images": self.images,
            "files": self.files,
            "attachments": self.attachments,
            "reply": self.reply,
            "input": self.input,
            "output": self.output,
            "mode": self.mode,
            "model": self.model,
            "thread": self.thread,
            "msg_id": self.msg_id,
            "run_id": self.run_id,
            "input_name": self.input_name,
            "output_name": self.output_name,
            "input_timestamp": self.input_timestamp,
            "output_timestamp": self.output_timestamp,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "extra": self.extra,
            "current": self.current,
            "internal": self.internal,
        }

    def dump(self) -> str:
        """
        Dump context item to JSON string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()


class CtxMeta:
    def __init__(self, id=None):
        """
        Context meta data

        :param id: Context ID
        """
        self.id = id
        self.external_id = None
        self.uuid = None
        self.name = None
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.created = int(time.time())
        self.updated = int(time.time())
        self.mode = None
        self.model = None
        self.last_mode = None
        self.last_model = None
        self.thread = None
        self.assistant = None
        self.preset = None
        self.run = None
        self.status = None
        self.extra = None
        self.initialized = False
        self.deleted = False
        self.important = False
        self.archived = False
        self.label = 0  # label color
