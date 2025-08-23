#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
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
        self.assistant_id = kwargs.get("assistant_id", "")
        self.attachments = kwargs.get("attachments", [])
        self.ctx = kwargs.get("ctx", None)
        self.external_functions = kwargs.get("external_functions", [])
        self.file_ids = kwargs.get("file_ids", [])
        self.force = kwargs.get("force", False)  # Force mode flag
        self.force_sync = kwargs.get("force_sync", False)  # Force sync flag
        self.history = kwargs.get("history", [])
        self.idx = kwargs.get("idx", None)
        self.idx_mode = kwargs.get("idx_mode", "chat")
        self.is_expert_call = kwargs.get("is_expert_call", False)  # Expert call flag
        self.max_tokens = kwargs.get("max_tokens", 0)
        self.mode = kwargs.get("mode", None)
        self.model = kwargs.get("model", None)  # model instance, not model name
        self.multimodal_ctx = kwargs.get("multimodal_ctx", MultimodalContext())  # AudioContext
        self.parent_mode = kwargs.get("parent_mode", None)  # real mode (global)
        self.preset = kwargs.get("preset", None)  # PresetItem
        self.prompt = kwargs.get("prompt", "")
        self.reply_context = kwargs.get("reply_ctx", None)  # ReplyContext
        self.request = kwargs.get("request", False)  # Use normal request instead of quick call
        self.stream = kwargs.get("stream", False)
        self.system_prompt = kwargs.get("system_prompt", "")
        self.system_prompt_raw = kwargs.get("system_prompt_raw", "")  # without plugins addons
        self.temperature = kwargs.get("temperature", 1.0)
        self.thread_id = kwargs.get("thread_id", "")
        self.tools_outputs = kwargs.get("tools_outputs", [])

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
        return dict(sorted(data.items(), key=lambda item: item[0]))