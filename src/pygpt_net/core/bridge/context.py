#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.04 00:00:00                  #
# ================================================== #

import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


@dataclass(slots=True)
class MultimodalContext:
    """
    Multimodal context
    """
    is_audio_input: bool = False  # is audio input
    is_audio_output: bool = False  # is audio output
    audio_data: Optional[Any] = None  # audio data (bytes or file-like object)
    audio_format: str = "wav"  # audio format (wav, mp3, etc.)

    def __init__(self, **kwargs):
        """
        Multimodal context

        :param kwargs: keyword arguments
        """
        # kwargs-based initialization
        self.is_audio_input = kwargs.get("is_audio_input", False)
        self.is_audio_output = kwargs.get("is_audio_output", False)
        self.audio_data = kwargs.get("audio_data", None)
        self.audio_format = kwargs.get("audio_format", "wav")

    def to_dict(self) -> Dict[str, Any]:
        """
        Return as dictionary

        :return: dictionary
        """
        data = {
            "is_audio_input": self.is_audio_input,
            "is_audio_output": self.is_audio_output,
            "audio_format": self.audio_format,
        }
        # sort by keys
        return dict(sorted(data.items(), key=lambda item: item[0]))


@dataclass(slots=True)
class BridgeContext:
    """
    Bridge context
    """
    assistant_id: str = "" # OpenAI Assistant ID
    attachments: dict = field(default_factory=dict) # id -> AttachmentItem
    ctx: Optional[CtxItem] = None # CtxItem instance
    external_functions: list = field(default_factory=list) # list of tools definitions
    file_ids: list = field(default_factory=list)  # list of uploaded file IDs
    force: bool = False  # force send
    force_sync: bool = False  # force synchronous plugin call
    history: list = field(default_factory=list) # list of messages
    idx: Optional[Any] = None  # index name for LlamaIndex
    idx_mode: str = "chat" # sub-mode for LlamaIndex
    is_expert_call: bool = False  # is expert call
    max_tokens: int = 0  # max tokens
    mode: Optional[Any] = None # mode to use
    model: Optional[ModelItem] = None  # model instance, not model name
    multimodal_ctx: MultimodalContext = field(default_factory=lambda: MultimodalContext())  # AudioContext
    parent_mode: Optional[Any] = None  # real mode (global)
    preset: Optional[Any] = None  # PresetItem
    prompt: str = "" # user input prompt
    reply_context: Optional[Any] = None  # ReplyContext
    request: bool = False  # use normal request instead of quick call
    stream: bool = False  # stream enabled
    system_prompt: str = "" # system prompt
    system_prompt_raw: str = ""  # system prompt without plugins addons
    temperature: float = 1.0  # temperature
    thread_id: str = "" # OpenAI Assistants thread ID for chat mode
    tools_outputs: list = field(default_factory=list)  # list of tools outputs

    def __init__(self, **kwargs):
        """
        Bridge context

        :param kwargs: keyword arguments
        """
        # Assign with defaults
        self.assistant_id = kwargs.get("assistant_id", "")
        self.attachments = dict(kwargs.get("attachments", []))
        self.ctx = kwargs.get("ctx", None)
        self.external_functions = list(kwargs.get("external_functions", []))
        self.file_ids = list(kwargs.get("file_ids", []))
        self.force = kwargs.get("force", False)
        self.force_sync = kwargs.get("force_sync", False)
        self.history = list(kwargs.get("history", []))
        self.idx = kwargs.get("idx", None)
        self.idx_mode = kwargs.get("idx_mode", "chat")
        self.is_expert_call = kwargs.get("is_expert_call", False)
        self.max_tokens = kwargs.get("max_tokens", 0)
        self.mode = kwargs.get("mode", None)
        self.model = kwargs.get("model", None)
        self.multimodal_ctx = kwargs.get("multimodal_ctx", MultimodalContext())
        self.parent_mode = kwargs.get("parent_mode", None)
        self.preset = kwargs.get("preset", None)
        self.prompt = kwargs.get("prompt", "")
        self.reply_context = kwargs.get("reply_ctx", kwargs.get("reply_context", None))
        self.request = kwargs.get("request", False)
        self.stream = kwargs.get("stream", False)
        self.system_prompt = kwargs.get("system_prompt", "")
        self.system_prompt_raw = kwargs.get("system_prompt_raw", "")
        self.temperature = kwargs.get("temperature", 1.0)
        self.thread_id = kwargs.get("thread_id", "")
        self.tools_outputs = list(kwargs.get("tools_outputs", []))

        # check types
        if self.ctx is not None and not isinstance(self.ctx, CtxItem):
            raise ValueError("Invalid context instance")
        if self.model is not None and not isinstance(self.model, ModelItem):
            raise ValueError("Invalid model instance")

    def to_dict(self) -> Dict[str, Any]:
        """
        Return as dictionary

        :return: dictionary
        """
        data = {
            "assistant_id": self.assistant_id,
            "attachments": self.attachments,
            "ctx": self.ctx,
            "external_functions": self.external_functions,
            "file_ids": self.file_ids,
            "force_sync": self.force_sync,
            "history": len(self.history),
            "idx": self.idx,
            "idx_mode": self.idx_mode,
            "is_expert_call": self.is_expert_call,
            "max_tokens": self.max_tokens,
            "mode": self.mode,
            "model": self.model,
            "parent_mode": self.parent_mode,
            "prompt": self.prompt,
            "reply_context": self.reply_context.to_dict() if self.reply_context else None,
            "request": self.request,
            "stream": self.stream,
            "system_prompt": self.system_prompt,
            "system_prompt_raw": self.system_prompt_raw,
            "temperature": self.temperature,
            "thread_id": self.thread_id,
            "tools_outputs": self.tools_outputs,
        }
        if self.ctx is not None:
            data["ctx"] = self.ctx.to_dict(True)
        if self.model is not None:
            data["model"] = self.model.to_dict()

        return dict(sorted(data.items(), key=lambda item: item[0]))  # sort by keys

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