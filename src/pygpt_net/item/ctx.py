#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 02:10:00                  #
# ================================================== #

import copy
import datetime
import json
import time

from typing import Optional
from dataclasses import dataclass, field


@dataclass(slots=True)
class CtxItem:
    mode: Optional[str] = None
    additional_ctx: list = field(default_factory=list)
    agent_call: bool = False
    agent_final_response: str = ""
    async_disabled: bool = False
    attachments: list = field(default_factory=list)
    attachments_before: list = field(default_factory=list)
    audio_expires_ts: int = 0
    audio_id: Optional[object] = None
    audio_output: Optional[object] = None
    bag: Optional[object] = None
    cmds: list = field(default_factory=list)
    cmds_before: list = field(default_factory=list)
    current: bool = False
    doc_ids: list = field(default_factory=list)
    external_id: Optional[object] = None
    extra: dict = field(default_factory=dict)
    extra_ctx: Optional[object] = None
    files: list = field(default_factory=list)
    files_before: list = field(default_factory=list)
    first: bool = False
    force_call: bool = False
    hidden: bool = False
    hidden_input: Optional[str] = None
    hidden_output: Optional[str] = None
    id: Optional[object] = None
    idx: int = 0
    images: list = field(default_factory=list)
    images_before: list = field(default_factory=list)
    index_meta: dict = field(default_factory=dict)
    input: Optional[str] = None
    input_name: Optional[str] = None
    input_timestamp: Optional[int] = None
    input_tokens: int = 0
    internal: bool = False
    is_audio: bool = False
    is_vision: bool = False
    live: bool = False
    live_output: str = ""
    meta: Optional["CtxMeta"] = None
    meta_id: Optional[object] = None
    model: Optional[object] = None
    msg_id: Optional[object] = None
    output: Optional[str] = None
    output_name: Optional[str] = None
    output_timestamp: Optional[int] = None
    output_tokens: int = 0
    partial: bool = False
    pid: int = 0
    prev_ctx: Optional["CtxItem"] = None
    reply: bool = False
    response: Optional[object] = None
    results: list = field(default_factory=list)
    run_id: Optional[object] = None
    stopped: bool = False
    stream: Optional[object] = None
    stream_agent_output: bool = True
    sub_call: bool = False
    sub_calls: int = 0
    sub_reply: bool = False
    sub_tool_call: bool = False
    thread: Optional[object] = None
    tool_calls: list = field(default_factory=list)
    total_tokens: int = 0
    urls: list = field(default_factory=list)
    urls_before: list = field(default_factory=list)
    use_agent_final_response: bool = False
    use_responses_api: bool = False
    use_google_interactions_api : bool = False
    ai_name: Optional[str] = None

    def __init__(self, mode: Optional[str] = None):
        """
        Context item

        :param mode: Mode
        """
        self.additional_ctx = []
        self.agent_call = False  # prevents plugin reply if True
        self.agent_final_response = ""
        self.async_disabled = False  # async disabled
        self.attachments = []
        self.attachments_before = []
        self.audio_expires_ts = 0
        self.audio_id = None
        self.audio_output = None
        self.bag = None
        self.cmds = []
        self.cmds_before = []
        self.current = False
        self.doc_ids = []  # document ids
        self.external_id = None
        self.extra = {}
        self.extra_ctx = None
        self.files = []
        self.files_before = []
        self.first = False
        self.force_call = False  # force call even if command is not present
        self.hidden = False  # hidden context
        self.hidden_input = None
        self.hidden_output = None
        self.id = None
        self.idx = 0
        self.images = []
        self.images_before = []
        self.index_meta = {}  # llama-index metadata ctx used
        self.input = None
        self.input_name = None
        self.input_timestamp = None
        self.input_tokens = 0
        self.internal = False
        self.is_audio = False
        self.is_vision = False
        self.live = False  # True if is current flow (not loaded from DB)
        self.live_output = ""
        self.meta = None  # CtxMeta object
        self.meta_id = None
        self.model = None
        self.mode = mode
        self.msg_id = None
        self.output = None
        self.output_name = None
        self.output_timestamp = None
        self.output_tokens = 0
        self.partial = False  # not final output, used in cycle next ctx, force wait for final output, do not eval, etc
        self.pid = 0
        self.prev_ctx = None  # previous context (reply output)
        self.reply = False
        self.response = None  # response object
        self.results = []
        self.run_id = None
        self.stopped = False  # run stopped
        self.stream = None
        self.stream_agent_output = True  # stream agent output in real-time
        self.sub_call = False  # is sub call
        self.sub_calls = 0  # sub calls count
        self.sub_reply = False  # sub call reply
        self.sub_tool_call = False  # sub tool call
        self.thread = None
        self.tool_calls = []  # API tool calls
        self.total_tokens = 0
        self.urls = []
        self.urls_before = []
        self.use_agent_final_response = False  # use agent final response
        self.use_responses_api = False  # use responses API format
        self.use_google_interactions_api = False  # use Google Interactions API format
        self.ai_name = None  # AI name

    @property
    def final_input(self) -> Optional[str]:
        """
        Final input

        :return: input text
        """
        if self.input is None:
            return None
        if self.hidden_input:
            return "\n\n".join([self.input, self.hidden_input])
        return self.input

    @property
    def final_output(self) -> Optional[str]:
        """
        Final output

        :return: output text
        """
        if self.output is None:
            return None
        if self.hidden_output:
            return "\n\n".join([self.output, self.hidden_output])
        return self.output

    def clear_reply(self):
        """Clear current reply output"""
        if self.reply:
            self.urls = []
            self.urls_before = []

    def from_previous(self):
        """Copy data from previous context item"""
        p = self.prev_ctx
        if not p:
            return
        dp = copy.deepcopy
        for name in ("urls", "images", "files", "attachments"):
            src = getattr(p, f"{name}_before", None) or getattr(p, name, None)
            if src:
                setattr(self, name, dp(src))

    def set_agent_name(self, name: Optional[str]):
        """
        Set AI/agent name

        :param name: name
        """
        self.ai_name = name
        if name:
            if self.extra is None:
                self.extra = {}
            self.extra['agent_name'] = name

    def get_agent_name(self) -> Optional[str]:
        """
        Get AI/agent name

        :return: name
        """
        if self.extra and isinstance(self.extra, dict):
            return self.extra.get('agent_name', None)
        return None

    def is_empty(self) -> bool:
        """
        Check if context item is empty

        :return: True if context item is empty
        """
        return not self.final_output and not self.stream and not self.live_output

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

    def set_input(self, input: Optional[str], name: Optional[str] = None):
        """
        Set input

        :param input: input text (prompt)
        :param name: input person name
        """
        self.input = input
        self.input_name = name
        self.input_timestamp = int(time.time())

    def set_output(self, output: Optional[str], name: Optional[str] = None):
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

    def get_pid(self) -> int:
        """
        Get context item PID (process ID)

        :return: int
        """
        return 0

    def to_dict(self, dump: bool = False, format: bool = False) -> dict:
        """
        Dump context item to dict

        :param dump: if True, dump meta to dict
        :param format: if True, format output
        :return: dict
        """
        data = {
            "agent_call": self.agent_call,
            "attachments": self.attachments,
            "attachments_before": self.attachments_before,
            "audio_expires_ts": self.audio_expires_ts,
            "audio_id": self.audio_id,
            "cmds": self.cmds,
            "cmds_before": self.cmds_before,
            "current": self.current,
            "doc_ids": self.doc_ids,
            "external_id": self.external_id,
            "extra": self.extra,
            "extra_ctx": self.extra_ctx,
            "files": self.files,
            "files_before": self.files_before,
            "first": self.first,
            "force_call": self.force_call,
            "hidden": False,
            "hidden_input": self.hidden_input,
            "hidden_output": self.hidden_output,
            "id": self.id,
            "idx": self.idx,
            "images": self.images,
            "images_before": self.images_before,
            "index_meta": self.index_meta,
            "input": self.input,
            "input_name": self.input_name,
            "input_timestamp": self.input_timestamp,
            "input_tokens": self.input_tokens,
            "internal": self.internal,
            "is_audio": self.is_audio,
            "is_vision": self.is_vision,
            "live": self.live,
            "meta": self.meta.to_dict() if type(self.meta) == CtxMeta else self.meta,
            "meta_id": self.meta_id,
            "mode": self.mode,
            "model": self.model,
            "msg_id": self.msg_id,
            "output": self.output,
            "output_name": self.output_name,
            "output_timestamp": self.output_timestamp,
            "output_tokens": self.output_tokens,
            "pid": self.pid,
            "reply": self.reply,
            "results": self.results,
            "run_id": self.run_id,
            "stopped": self.stopped,
            "sub_call": False,
            "sub_calls": 0,
            "sub_reply": False,
            "sub_tool_call": False,
            "thread": self.thread,
            "tool_calls": self.tool_calls,
            "total_tokens": self.total_tokens,
            "urls": self.urls,
            "urls_before": self.urls_before,
        }
        if dump:
            data["hidden"] = self.hidden
            data["live_output"] = self.live_output
            data["sub_calls"] = self.sub_calls
            data["sub_call"] = self.sub_call
            data["sub_reply"] = self.sub_reply
            data["sub_tool_call"] = self.sub_tool_call

        return dict(sorted(data.items(), key=lambda item: item[0]))  # sort by keys

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
        self.agent_call = g("agent_call", False)
        self.attachments = g("attachments", [])
        self.attachments_before = g("attachments_before", [])
        self.audio_expires_ts = g("audio_expires_ts", None)
        self.audio_id = g("audio_id", None)
        self.cmds = g("cmds", [])
        self.current = g("current", False)
        self.doc_ids = g("doc_ids", [])
        self.external_id = g("external_id", None)
        self.extra = g("extra", None)
        self.extra_ctx = g("extra_ctx", False)
        self.files = g("files", [])
        self.files_before = g("files_before", [])
        self.first = g("first", False)
        self.hidden = g("hidden", False)
        self.hidden_input = g("hidden_input", None)
        self.hidden_output = g("hidden_output", None)
        self.id = g("id", None)
        self.idx = g("idx", 0)
        self.images = g("images", [])
        self.images_before = g("images_before", [])
        self.index_meta = g("index_meta", {})
        self.input = g("input", None)
        self.input_name = g("input_name", None)
        self.input_timestamp = g("input_timestamp", None)
        self.input_tokens = g("input_tokens", 0)
        self.internal = g("internal", False)
        self.is_vision = g("is_vision", False)
        self.meta = g("meta", None)
        self.meta_id = g("meta_id", None)
        self.model = g("model", None)
        self.mode = g("mode", None)
        self.msg_id = g("msg_id", None)
        self.output = g("output", None)
        self.output_name = g("output_name", None)
        self.output_timestamp = g("output_timestamp", None)
        self.output_tokens = g("output_tokens", 0)
        self.results = g("results", [])
        self.reply = g("reply", False)
        self.run_id = g("run_id", None)
        self.stream = g("stream", None)
        self.sub_call = g("sub_call", False)
        self.sub_calls = g("sub_calls", 0)
        self.sub_reply = g("sub_reply", False)
        self.sub_tool_call = g("sub_tool_call", False)
        self.thread = g("thread", None)
        self.tool_calls = g("tool_calls", [])
        self.total_tokens = g("total_tokens", 0)
        self.urls = g("urls", [])
        self.urls_before = g("urls_before", [])

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


@dataclass(slots=True)
class CtxMeta:
    id: Optional[int] = None
    additional_ctx: list = field(default_factory=list)
    archived: bool = False
    assistant: Optional[object] = None
    created: int = field(default_factory=lambda: int(time.time()))
    date: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d"))
    deleted: bool = False
    external_id: Optional[object] = None
    extra: Optional[object] = None
    group: Optional["CtxGroup"] = None
    group_id: Optional[object] = None
    important: bool = False
    indexed: Optional[object] = None
    indexes: dict = field(default_factory=dict)
    initialized: bool = False
    label: int = 0
    last_mode: Optional[object] = None
    last_model: Optional[object] = None
    model: Optional[object] = None
    mode: Optional[object] = None
    name: Optional[str] = None
    owner_uuid: Optional[object] = None
    parent_id: Optional[object] = None
    preset: Optional[object] = None
    root_id: Optional[object] = None
    run: Optional[object] = None
    status: Optional[object] = None
    thread: Optional[object] = None
    updated: int = field(default_factory=lambda: int(time.time()))
    uuid: Optional[object] = None

    def __init__(self, id: Optional[int] = None):
        """
        Context meta data

        :param id: Context ID
        """
        self.additional_ctx = []  # additional context data
        self.archived = False
        self.assistant = None
        self.created = int(time.time())
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.deleted = False
        self.external_id = None
        self.extra = None
        self.group = None  # parent group
        self.group_id = None
        self.id = id
        self.important = False
        self.indexed = None
        self.indexes = {}  # indexes data
        self.initialized = False
        self.label = 0  # label color
        self.last_mode = None
        self.last_model = None
        self.model = None
        self.mode = None
        self.name = None
        self.owner_uuid = None
        self.parent_id = None
        self.preset = None
        self.root_id = None
        self.run = None
        self.status = None
        self.thread = None
        self.updated = int(time.time())
        self.uuid = None

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
            "additional_ctx": self.additional_ctx,
            "archived": self.archived,
            "assistant": self.assistant,
            "created": self.created,
            "date": self.date,
            "deleted": self.deleted,
            "external_id": self.external_id,
            "extra": self.extra,
            "group_id": self.group_id,
            "id": self.id,
            "important": self.important,
            "indexed": self.indexed,
            "indexes": self.indexes,
            "initialized": self.initialized,
            "label": self.label,
            "last_mode": self.last_mode,
            "last_model": self.last_model,
            "mode": self.mode,
            "model": self.model,
            "name": self.name,
            "owner_uuid": self.owner_uuid,
            "parent_id": self.parent_id,
            "preset": self.preset,
            "root_id": self.root_id,
            "run": self.run,
            "status": self.status,
            "thread": self.thread,
            "updated": self.updated,
            "uuid": self.uuid,
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
        self.additional_ctx = g("additional_ctx", [])
        self.archived = g("archived", False)
        self.assistant = g("assistant", None)
        self.created = g("created", None)
        self.date = g("date", None)
        self.deleted = g("deleted", False)
        self.external_id = g("external_id", None)
        self.extra = g("extra", None)
        self.group_id = g("group_id", None)
        self.id = g("id", None)
        self.important = g("important", False)
        self.indexed = g("indexed", None)
        self.indexes = g("indexes", {})
        self.initialized = g("initialized", False)
        self.label = g("label", 0)
        self.last_mode = g("last_mode", None)
        self.last_model = g("last_model", None)
        self.mode = g("mode", None)
        self.model = g("model", None)
        self.name = g("name", None)
        self.owner_uuid = g("owner_uuid", None)
        self.parent_id = g("parent_id", None)
        self.preset = g("preset", None)
        self.root_id = g("root_id", None)
        self.run = g("run", None)
        self.status = g("status", None)
        self.thread = g("thread", None)
        self.updated = g("updated", None)
        self.uuid = g("uuid", None)

    def get_pid(self) -> int:
        """
        Get context item PID (process ID)

        :return: int
        """
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

    def __str__(self) -> str:
        """
        To string

        :return: JSON string
        """
        return self.dump()


@dataclass(slots=True)
class CtxGroup:
    id: Optional[int] = None
    name: Optional[str] = None
    additional_ctx: list = field(default_factory=list)
    count: int = 0
    created: int = field(default_factory=lambda: int(time.time()))
    items: list = field(default_factory=list)
    updated: int = field(default_factory=lambda: int(time.time()))
    uuid: Optional[object] = None

    def __init__(self, id: Optional[int] = None, name: Optional[str] = None):
        """
        Context group

        :param id: Group ID
        :param name: Group name
        """
        self.additional_ctx = []
        self.count = 0
        self.created = int(time.time())
        self.id = id
        self.items = []
        self.name = name
        self.updated = int(time.time())
        self.uuid = None

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
            "additional_ctx": self.additional_ctx,
            "count": self.count,
            "created": self.created,
            "id": self.id,
            "items": self.items,
            "name": self.name,
            "updated": self.updated,
            "uuid": self.uuid,
        }

    def from_dict(self, data: dict):
        """
        Load context group from dict

        :param data: dict
        """
        g = data.get
        self.count = g("count", 0)
        self.created = g("created", None)
        self.id = g("id", None)
        self.items = g("items", [])
        self.name = g("name", None)
        self.updated = g("updated", None)
        self.uuid = g("uuid", None)

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

    def __str__(self) -> str:
        """
        To string

        :return: JSON string
        """
        return self.dump()