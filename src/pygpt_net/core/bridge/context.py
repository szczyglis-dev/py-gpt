#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.30 00:00:00                  #
# ================================================== #

import json
from typing import Dict, Any

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

class BridgeContext:
    def __init__(self, **kwargs):
        """
        Bridge context

        :param kwargs: keyword arguments
        """
        self.ctx = kwargs.get("ctx", None)
        self.history = kwargs.get("history", [])
        self.mode = kwargs.get("mode", None)
        self.parent_mode = kwargs.get("parent_mode", None)  # real mode (global)
        self.model = kwargs.get("model", None)  # model instance, not model name
        self.temperature = kwargs.get("temperature", 1.0)
        self.prompt = kwargs.get("prompt", "")
        self.system_prompt = kwargs.get("system_prompt", "")
        self.system_prompt_raw = kwargs.get("system_prompt_raw", "")  # without plugins addons
        self.stream = kwargs.get("stream", False)
        self.assistant_id = kwargs.get("assistant_id", "")
        self.thread_id = kwargs.get("thread_id", "")
        self.external_functions = kwargs.get("external_functions", [])
        self.tools_outputs = kwargs.get("tools_outputs", [])
        self.max_tokens = kwargs.get("max_tokens", 150)
        self.idx = kwargs.get("idx", None)
        self.idx_mode = kwargs.get("idx_mode", "chat")
        self.attachments = kwargs.get("attachments", [])
        self.file_ids = kwargs.get("file_ids", [])
        self.reply_context = kwargs.get("reply_ctx", None)  # ReplyContext
        self.multimodal_ctx = kwargs.get("multimodal_ctx", MultimodalContext())  # AudioContext
        self.is_expert_call = kwargs.get("is_expert_call", False)  # Expert call flag
        self.force_sync = kwargs.get("force_sync", False)  # Force sync flag
        self.request = kwargs.get("request", False)  # Use normal request instead of quick call
        self.preset = kwargs.get("preset", None)  # PresetItem

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
            "ctx": self.ctx,
            "reply_context": self.reply_context.to_dict() if self.reply_context else None,
            "history": len(self.history),
            "mode": self.mode,
            "parent_mode": self.parent_mode,
            "model": self.model,
            "temperature": self.temperature,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "system_prompt_raw": self.system_prompt_raw,
            "stream": self.stream,
            "assistant_id": self.assistant_id,
            "thread_id": self.thread_id,
            "external_functions": self.external_functions,
            "tools_outputs": self.tools_outputs,
            "max_tokens": self.max_tokens,
            "idx": self.idx,
            "idx_mode": self.idx_mode,
            "attachments": self.attachments,
            "file_ids": self.file_ids,
            "is_expert_call": self.is_expert_call,
            "force_sync": self.force_sync,
            "request": self.request,
        }
        if self.ctx is not None:
            data["ctx"] = self.ctx.to_dict(True)
        if self.model is not None:
            data["model"] = self.model.to_dict()

        # sort by keys
        data = dict(sorted(data.items(), key=lambda item: item[0]))
        return data

    def dump(self) -> str:
        """
        Dump context item to JSON string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()

class MultimodalContext:
    def __init__(self, **kwargs):
        """
        Multimodal context

        :param kwargs: keyword arguments
        """
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
        data = dict(sorted(data.items(), key=lambda item: item[0]))
        return data