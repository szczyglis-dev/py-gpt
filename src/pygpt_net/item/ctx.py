#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

import copy
import datetime
import json
import time


class CtxItem:

    def __init__(self, mode=None):
        """
        Context item

        :param mode: Mode (completion, chat, img, vision, langchain, assistant, llama_index, agent, expert)
        """
        self.id = None
        self.meta = None  # CtxMeta object
        self.meta_id = None
        self.external_id = None
        self.stream = None
        self.cmds = []
        self.cmds_before = []
        self.results = []
        self.urls = []
        self.urls_before = []
        self.images = []
        self.images_before = []
        self.files = []
        self.files_before = []
        self.attachments = []
        self.attachments_before = []
        self.additional_ctx = []
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
        self.hidden_input = None
        self.hidden_output = None
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.extra = {}
        self.extra_ctx = None
        self.current = False
        self.internal = False
        self.is_vision = False
        self.is_audio = False
        self.idx = 0
        self.first = False
        self.live = False  # True if is current flow (not loaded from DB)
        self.agent_call = False # prevents plugin reply if True
        self.agent_final_response = ""
        self.use_agent_final_response = False  # use agent final response
        self.stream_agent_output = True  # stream agent output in real-time
        self.tool_calls = []  # API tool calls
        self.index_meta = {}  # llama-index metadata ctx used
        self.doc_ids = []  # document ids
        self.prev_ctx = None  # previous context (reply output)
        self.stopped = False  # run stopped
        self.sub_calls = 0  # sub calls count
        self.sub_call = False  # is sub call
        self.sub_reply = False  # sub call reply
        self.sub_tool_call = False  # sub tool call
        self.hidden = False  # hidden context
        self.use_responses_api = False  # use responses API format
        self.pid = 0
        self.audio_id = None
        self.audio_output = None
        self.audio_expires_ts = 0
        self.response = None  # response object
        self.async_disabled = False  # async disabled
        self.bag = None
        self.live_output = ""
        self.force_call = False  # force call even if command is not present
        self.partial = False  # not final output, used in cycle next ctx, force wait for final output, do not eval, etc


    @property
    def final_input(self) -> str:
        """
        Final input

        :return: input text
        """
        if self.input is None:
            return None
        if self.hidden_input:
            return self.input + "\n\n" + self.hidden_input
        return self.input

    @property
    def final_output(self) -> str:
        """
        Final output

        :return: output text
        """
        if self.output is None:
            return None
        if self.hidden_output:
            return self.output + "\n\n" + self.hidden_output
        return self.output

    def clear_reply(self):
        """Clear current reply output"""
        if self.reply:
            self.urls = []
            self.urls_before = []

    def from_previous(self):
        """Copy data from previous context reply to current context"""
        p = self.prev_ctx
        if not p:
            return
        dp = copy.deepcopy
        if p.urls or p.urls_before:
            src = p.urls_before if p.urls_before else p.urls
            if src:
                self.urls = dp(src)
        if p.images or p.images_before:
            src = p.images_before if p.images_before else p.images
            if src:
                self.images = dp(src)
        if p.files_before:
            self.files = dp(p.files_before)
        if p.attachments_before:
            self.attachments = dp(p.attachments_before)

    def has_commands(self) -> bool:
        """
        Check if commands are

        :return: True if commands are present
        """
        return bool(self.cmds or self.tool_calls)

    def audio_read_allowed(self) -> bool:
        """
        Check if audio read allowed

        :return: True if audio read allowed
        """
        if self.has_commands():
            return False
        out = self.output
        if isinstance(out, str) and '<tool>{"cmd":' in out:
            return False
        return True

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

    def set_agent_final_response(self, output: str):
        """
        Set agent final response

        :param output: final response output
        """
        self.agent_final_response = output

    def set_tokens(self, input_tokens: int, output_tokens: int):
        """
        Set tokens usage

        :param input_tokens: prompt tokens
        :param output_tokens: output tokens
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens

    def get_pid(self):
        return 0

    def to_dict(self, dump: bool = False, format: bool = False) -> dict:
        """
        Dump context item to dict

        :param dump: if True, dump meta to dict
        :param format: if True, format output
        :return: dict
        """
        data = {
            "id": self.id,
            "meta_id": self.meta_id,
            "idx": self.idx,
            "first": self.first,
            "live": self.live,
            "hidden": False,
            "internal": self.internal,
            "external_id": self.external_id,
            # "stream": self.stream,  #  <-- do not dump stream response object
            "reply": self.reply,
            "current": self.current,
            "stopped": self.stopped,
            "is_audio": self.is_audio,
            "is_vision": self.is_vision,
            "agent_call": self.agent_call,
            "tool_calls": self.tool_calls,
            "index_meta": self.index_meta,
            "doc_ids": self.doc_ids,
            "sub_calls": 0,
            "sub_call": False,
            "sub_reply": False,
            "sub_tool_call": False,
            "extra": self.extra,
            "extra_ctx": self.extra_ctx,
            "cmds": self.cmds,
            "cmds_before": self.cmds_before,
            "results": self.results,
            "urls": self.urls,
            "urls_before": self.urls_before,
            "images": self.images,
            "images_before": self.images_before,
            "files": self.files,
            "files_before": self.files_before,
            "attachments": self.attachments,
            "attachments_before": self.attachments_before,
            "pid": self.pid,
            "mode": self.mode,
            "model": self.model,
            "thread": self.thread,
            "msg_id": self.msg_id,
            "run_id": self.run_id,
            "audio_id": self.audio_id,
            "audio_expires_ts": self.audio_expires_ts,
            "input": self.input,
            "output": self.output,
            'hidden_input': self.hidden_input,
            'hidden_output': self.hidden_output,
            "input_name": self.input_name,
            "output_name": self.output_name,
            "input_timestamp": self.input_timestamp,
            "output_timestamp": self.output_timestamp,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "force_call": self.force_call,
            "meta": self.meta.to_dict() if type(self.meta) == CtxMeta else self.meta,
        }
        if dump:
            data["live_output"] = self.live_output
            data["hidden"] = self.hidden
            data["sub_calls"] = self.sub_calls
            data["sub_call"] = self.sub_call
            data["sub_reply"] = self.sub_reply
            data["sub_tool_call"] = self.sub_tool_call

        return data

    def to_debug(self):
        """
        Dump context item to dict for debug

        :return: dict
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=4)

    def from_dict(self, data: dict):
        """
        Load context item from dict

        :param data: dict
        """
        g = data.get
        self.id = g("id", None)
        self.meta = g("meta", None)
        self.meta_id = g("meta_id", None)
        self.external_id = g("external_id", None)
        self.stream = g("stream", None)
        self.cmds = g("cmds", [])
        self.results = g("results", [])
        self.urls = g("urls", [])
        self.urls_before = g("urls_before", [])
        self.images = g("images", [])
        self.images_before = g("images_before", [])
        self.files = g("files", [])
        self.files_before = g("files_before", [])
        self.attachments = g("attachments", [])
        self.attachments_before = g("attachments_before", [])
        self.reply = g("reply", False)
        self.input = g("input", None)
        self.output = g("output", None)
        self.mode = g("mode", None)
        self.model = g("model", None)
        self.thread = g("thread", None)
        self.msg_id = g("msg_id", None)
        self.run_id = g("run_id", None)
        self.audio_id = g("audio_id", None)
        self.audio_expires_ts = g("audio_expires_ts", None)
        self.input_name = g("input_name", None)
        self.output_name = g("output_name", None)
        self.input_timestamp = g("input_timestamp", None)
        self.output_timestamp = g("output_timestamp", None)
        self.hidden_input = g("hidden_input", None)
        self.hidden_output = g("hidden_output", None)
        self.input_tokens = g("input_tokens", 0)
        self.output_tokens = g("output_tokens", 0)
        self.total_tokens = g("total_tokens", 0)
        self.extra = g("extra", None)
        self.extra_ctx = g("extra_ctx", False)
        self.current = g("current", False)
        self.internal = g("internal", False)
        self.is_vision = g("is_vision", False)
        self.idx = g("idx", 0)
        self.first = g("first", False)
        self.agent_call = g("agent_call", False)
        self.tool_calls = g("tool_calls", [])
        self.index_meta = g("index_meta", {})
        self.doc_ids = g("doc_ids", [])
        self.sub_calls = g("sub_calls", 0)
        self.sub_call = g("sub_call", False)
        self.sub_reply = g("sub_reply", False)
        self.sub_tool_call = g("sub_tool_call", False)
        self.hidden = g("hidden", False)


    def dump(self, dump: bool = True) -> str:
        """
        Dump context item to JSON string

        :param dump: if True, dump meta to dict
        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict(dump), ensure_ascii=False, indent=2)
        except Exception:
            pass
        return ""

    def print(self):
        """Print context item"""
        print("\n----------------------------")
        print(f"[{self.id}]")
        print("Input:", self.input)
        print("Output:", self.output)
        print("Extra:", self.extra)
        print("\n-----------------------------")

    def __str__(self):
        """To string"""
        return self.dump(True)


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
        self.additional_ctx = [] # additional context data
        self.group = None  # parent group
        self.group_id = None
        self.root_id = None
        self.parent_id = None
        self.owner_uuid = None

    def has_additional_ctx(self) -> bool:
        """
        Check if additional context data is attached

        :return: True if additional context data is present
        """
        if self.additional_ctx:
            return True
        if self.group and self.group.additional_ctx:
            return True
        return False

    def get_additional_ctx(self) -> list:
        """
        Get additional context data

        :return: list
        """
        if self.group and self.group.additional_ctx:
            return self.group.additional_ctx
        return self.additional_ctx or []

    def reset_additional_ctx(self):
        """Delete additional context data"""
        if self.group:
            self.group.additional_ctx = []
        else:
            self.additional_ctx = []

    def remove_additional_ctx(self, item: dict):
        """
        Remove additional context data item

        :param item: dict
        """
        if self.group:
            lst = self.group.additional_ctx
            if item in lst:
                lst.remove(item)
        else:
            lst = self.additional_ctx
            if item in lst:
                lst.remove(item)

    def get_attachment_names(self) -> list:
        """
        Get attachment names

        :return: list
        """
        if self.group:
            if self.group.additional_ctx:
                return self.group.get_attachment_names()
        return [item['name'] for item in self.additional_ctx]

    def to_dict(self) -> dict:
        """
        Dump context meta to dict

        :return: dict
        """
        data = {
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
            "additional_ctx": self.additional_ctx,
            "group_id": self.group_id,
            "root_id": self.root_id,
            "parent_id": self.parent_id,
            "owner_uuid": self.owner_uuid,
        }
        if self.group:
            data["__group__"] = self.group.to_dict()
        return data

    def from_dict(self, data: dict):
        """
        Load context meta from dict

        :param data: dict
        """
        g = data.get
        self.id = g("id", None)
        self.external_id = g("external_id", None)
        self.uuid = g("uuid", None)
        self.name = g("name", None)
        self.date = g("date", None)
        self.created = g("created", None)
        self.updated = g("updated", None)
        self.indexed = g("indexed", None)
        self.mode = g("mode", None)
        self.model = g("model", None)
        self.last_mode = g("last_mode", None)
        self.last_model = g("last_model", None)
        self.thread = g("thread", None)
        self.assistant = g("assistant", None)
        self.preset = g("preset", None)
        self.run = g("run", None)
        self.status = g("status", None)
        self.extra = g("extra", None)
        self.initialized = g("initialized", False)
        self.deleted = g("deleted", False)
        self.important = g("important", False)
        self.archived = g("archived", False)
        self.label = g("label", 0)
        self.indexes = g("indexes", {})
        self.additional_ctx = g("additional_ctx", [])
        self.group_id = g("group_id", None)
        self.root_id = g("root_id", None)
        self.parent_id = g("parent_id", None)
        self.owner_uuid = g("owner_uuid", None)

    def get_pid(self):
        return 0

    def dump(self) -> str:
        """
        Dump context item to JSON string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except Exception:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()

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
        self.additional_ctx = []
        self.count = 0

    def has_additional_ctx(self) -> bool:
        """
        Check if additional context data is attached

        :return: True if additional context data is present
        """
        return bool(self.additional_ctx)

    def get_additional_ctx(self) -> list:
        """
        Get additional context data

        :return: list
        """
        return self.additional_ctx

    def get_attachments_count(self) -> int:
        """
        Get attachments count

        :return: int
        """
        return len(self.additional_ctx)

    def get_attachment_names(self) -> list:
        """
        Get attachment names

        :return: list
        """
        return [item['name'] for item in self.additional_ctx]

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
            "additional_ctx": self.additional_ctx,
            "created": self.created,
            "updated": self.updated,
            "count": self.count,
        }

    def from_dict(self, data: dict):
        """
        Load context group from dict

        :param data: dict
        """
        g = data.get
        self.id = g("id", None)
        self.uuid = g("uuid", None)
        self.name = g("name", None)
        self.items = g("items", [])
        self.created = g("created", None)
        self.updated = g("updated", None)
        self.count = g("count", 0)

    def dump(self) -> str:
        """
        Dump context item to JSON string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except Exception:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()