#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #

import copy
import datetime
import json
import time


class CtxItem:
    def __init__(self, mode=None):
        """
        Context item

        :param mode: Mode (completion, chat, img, vision, langchain, assistant, llama_index, agent)
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
        self.extra_ctx = None
        self.current = False
        self.internal = False
        self.is_vision = False
        self.idx = 0
        self.first = False
        self.tool_calls = []  # API tool calls
        self.index_meta = {}  # llama-index metadata ctx used
        self.doc_ids = []  # document ids
        self.prev_ctx = None  # previous context (reply output)
        self.stopped = False  # run stopped
        self.sub_calls = 0  # sub calls count
        self.sub_call = False  # is sub call
        self.sub_reply = False  # sub call reply
        self.hidden = False  # hidden context

    def clear_reply(self):
        """Clear current reply output"""
        if self.reply:
            self.urls = []

    def from_previous(self):
        """Copy data from previous context reply to current context"""
        if self.prev_ctx is not None:
            self.urls = copy.deepcopy(self.prev_ctx.urls)

    def add_doc_meta(self, meta: dict):
        """
        Add document meta

        :param meta: document meta data
        """
        self.index_meta = meta
        self.doc_ids.append(meta)

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
            # "stream": self.stream,  #  <-- do not dump stream response object
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
            "extra_ctx": self.extra_ctx,
            "current": self.current,
            "internal": self.internal,
            "is_vision": self.is_vision,
            "idx": self.idx,
            "first": self.first,
            "tool_calls": self.tool_calls,
            "index_meta": self.index_meta,
            "doc_ids": self.doc_ids,
            "sub_calls": 0,
            "sub_call": False,
            "sub_reply": False,
            "hidden": False,
        }

    def from_dict(self, data: dict):
        """
        Load context item from dict

        :param data: dict
        """
        self.id = data.get("id", None)
        self.meta_id = data.get("meta_id", None)
        self.external_id = data.get("external_id", None)
        self.stream = data.get("stream", None)
        self.cmds = data.get("cmds", [])
        self.results = data.get("results", [])
        self.urls = data.get("urls", [])
        self.images = data.get("images", [])
        self.files = data.get("files", [])
        self.attachments = data.get("attachments", [])
        self.reply = data.get("reply", False)
        self.input = data.get("input", None)
        self.output = data.get("output", None)
        self.mode = data.get("mode", None)
        self.model = data.get("model", None)
        self.thread = data.get("thread", None)
        self.msg_id = data.get("msg_id", None)
        self.run_id = data.get("run_id", None)
        self.input_name = data.get("input_name", None)
        self.output_name = data.get("output_name", None)
        self.input_timestamp = data.get("input_timestamp", None)
        self.output_timestamp = data.get("output_timestamp", None)
        self.input_tokens = data.get("input_tokens", 0)
        self.output_tokens = data.get("output_tokens", 0)
        self.total_tokens = data.get("total_tokens", 0)
        self.extra = data.get("extra", None)
        self.extra_ctx = data.get("extra_ctx", False)
        self.current = data.get("current", False)
        self.internal = data.get("internal", False)
        self.is_vision = data.get("is_vision", False)
        self.idx = data.get("idx", 0)
        self.first = data.get("first", False)
        self.tool_calls = data.get("tool_calls", [])
        self.index_meta = data.get("index_meta", {})
        self.doc_ids = data.get("doc_ids", [])
        self.sub_calls = data.get("sub_calls", 0)
        self.sub_call = data.get("sub_call", False)
        self.sub_reply = data.get("sub_reply", False)
        self.hidden = data.get("hidden", False)

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
        self.indexed = None
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
        self.indexes = {}  # indexes data
        self.group_id = None
        self.root_id = None
        self.parent_id = None
        self.owner_uuid = None

    def to_dict(self) -> dict:
        """
        Dump context meta to dict

        :return: dict
        """
        return {
            "id": self.id,
            "external_id": self.external_id,
            "uuid": self.uuid,
            "name": self.name,
            "date": self.date,
            "created": self.created,
            "updated": self.updated,
            "indexed": self.indexed,
            "mode": self.mode,
            "model": self.model,
            "last_mode": self.last_mode,
            "last_model": self.last_model,
            "thread": self.thread,
            "assistant": self.assistant,
            "preset": self.preset,
            "run": self.run,
            "status": self.status,
            "extra": self.extra,
            "initialized": self.initialized,
            "deleted": self.deleted,
            "important": self.important,
            "archived": self.archived,
            "label": self.label,
            "indexes": self.indexes,
            "group_id": self.group_id,
            "root_id": self.root_id,
            "parent_id": self.parent_id,
            "owner_uuid": self.owner_uuid,
        }

    def from_dict(self, data: dict):
        """
        Load context meta from dict

        :param data: dict
        """
        self.id = data.get("id", None)
        self.external_id = data.get("external_id", None)
        self.uuid = data.get("uuid", None)
        self.name = data.get("name", None)
        self.date = data.get("date", None)
        self.created = data.get("created", None)
        self.updated = data.get("updated", None)
        self.indexed = data.get("indexed", None)
        self.mode = data.get("mode", None)
        self.model = data.get("model", None)
        self.last_mode = data.get("last_mode", None)
        self.last_model = data.get("last_model", None)
        self.thread = data.get("thread", None)
        self.assistant = data.get("assistant", None)
        self.preset = data.get("preset", None)
        self.run = data.get("run", None)
        self.status = data.get("status", None)
        self.extra = data.get("extra", None)
        self.initialized = data.get("initialized", False)
        self.deleted = data.get("deleted", False)
        self.important = data.get("important", False)
        self.archived = data.get("archived", False)
        self.label = data.get("label", 0)
        self.indexes = data.get("indexes", {})
        self.group_id = data.get("group_id", None)
        self.root_id = data.get("root_id", None)
        self.parent_id = data.get("parent_id", None)
        self.owner_uuid = data.get("owner_uuid", None)

class CtxGroup:
    def __init__(self, id=None, name=None):
        """
        Context group

        :param id: Group ID
        :param name: Group name
        """
        self.id = id
        self.uuid = None
        self.name = name
        self.items = []
        self.created = int(time.time())
        self.updated = int(time.time())
        self.count = 0

    def to_dict(self) -> dict:
        """
        Dump context group to dict

        :return: dict
        """
        return {
            "id": self.id,
            "uuid": self.uuid,
            "name": self.name,
            "items": self.items,
            "created": self.created,
            "updated": self.updated,
            "count": self.count,
        }

    def from_dict(self, data: dict):
        """
        Load context group from dict

        :param data: dict
        """
        self.id = data.get("id", None)
        self.uuid = data.get("uuid", None)
        self.name = data.get("name", None)
        self.items = data.get("items", [])
        self.created = data.get("created", None)
        self.updated = data.get("updated", None)
        self.count = data.get("count", 0)
