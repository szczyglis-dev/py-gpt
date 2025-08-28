#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 09:00:00                  #
# ================================================== #

from typing import Tuple, List
from functools import lru_cache

import tiktoken

# from langchain_core.messages import ChatMessage as ChatMessageLangchain
from llama_index.core.base.llms.types import ChatMessage as ChatMessageLlama

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_RESEARCH,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_AGENT_OPENAI,
    MODE_COMPUTER,
)
from pygpt_net.item.ctx import CtxItem

CHAT_MODES = [
    MODE_CHAT,
    # MODE_VISION,
    # MODE_LANGCHAIN,
    MODE_ASSISTANT,
    MODE_LLAMA_INDEX,
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_EXPERT,
    MODE_AUDIO,
    MODE_RESEARCH,
    MODE_COMPUTER,
]

class Tokens:
    _default_encoding = "cl100k_base"
    _const_cache = {}

    def __init__(self, window=None):
        self.window = window

    @staticmethod
    @lru_cache(maxsize=128)
    def _encoding_name_for_model(model: str | None) -> str:
        if model:
            try:
                return tiktoken.encoding_for_model(model).name
            except KeyError:
                return Tokens._default_encoding
            except ValueError:
                return Tokens._default_encoding
        return Tokens._default_encoding

    @staticmethod
    @lru_cache(maxsize=64)
    def _get_encoding(encoding_name: str):
        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception:
            return tiktoken.get_encoding(Tokens._default_encoding)

    @classmethod
    def _const_tokens(cls, text: str, model: str = "gpt-4") -> int:
        enc_name = cls._encoding_name_for_model(model)
        key = (enc_name, text)
        cached = cls._const_cache.get(key)
        if cached is not None:
            return cached
        try:
            enc = cls._get_encoding(enc_name)
            val = len(enc.encode(text))
        except Exception:
            val = 0
        cls._const_cache[key] = val
        return val

    @staticmethod
    def from_str(
            string: str,
            model: str = "gpt-4"
    ) -> int:
        if not string:
            return 0
        try:
            try:
                enc_name = Tokens._encoding_name_for_model(model)
                encoding = Tokens._get_encoding(enc_name)
            except ValueError:
                return 0
            try:
                return len(encoding.encode(str(string)))
            except Exception as e:
                print("Tokens calc exception", e)
                return 0
        except Exception as e:
            print("Tokens calculation exception:", e)
            return 0

    @staticmethod
    def get_extra(model: str = "gpt-4") -> int:
        return 3

    @staticmethod
    def from_prompt(
            text: str,
            name: str,
            model: str = "gpt-4"
    ) -> int:
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        try:
            num += Tokens.from_str(text, model)
        except Exception as e:
            print("Tokens calc exception", e)
        if name:
            num += per_message + per_name
        else:
            num += per_message
        return num

    @staticmethod
    def from_text(
            text: str,
            model: str = "gpt-4"
    ) -> int:
        if not text:
            return 0
        try:
            return Tokens.from_str(text, model)
        except Exception as e:
            print("Tokens calc exception", e)
            return 0

    @staticmethod
    def from_messages(
            messages: List[dict],
            model: str = "gpt-4"
    ) -> int:
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        f = Tokens.from_str
        for message in messages:
            num += per_message
            for key, value in message.items():
                if isinstance(value, str):
                    num += f(value)
                    if key == "name":
                        num += per_name
                elif key == "content" and isinstance(value, list):
                    for part in value:
                        t = part.get("type")
                        if t == "text":
                            tv = part.get("text")
                            if tv:
                                num += f(tv)
        num += 3
        return num

    @staticmethod
    def from_langchain_messages(
            messages: List,
            model: str = "gpt-4"
    ) -> int:
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        f = Tokens.from_str
        for message in messages:
            num += per_message
            num += f(message.content)
        num += 3
        return num

    @staticmethod
    def from_llama_messages(
            query: str,
            messages: List[ChatMessageLlama],
            model: str = "gpt-4"
    ) -> int:
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        f = Tokens.from_str
        num += f(query)
        for message in messages:
            num += per_message
            num += f(message.content)
        num += 3
        return num

    @staticmethod
    def from_ctx(
            ctx: CtxItem,
            mode: str = MODE_CHAT,
            model: str = "gpt-4"
    ) -> int:
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        f = Tokens.from_str
        if mode in CHAT_MODES:
            try:
                num += f(str(ctx.final_input), model)
            except Exception as e:
                print("Tokens calc exception", e)
            try:
                num += f(str(ctx.final_output), model)
            except Exception as e:
                print("Tokens calc exception", e)
            num += per_message * 2
            num += per_name * 2
            try:
                num += Tokens._const_tokens("system", model) * 2
            except Exception as e:
                print("Tokens calc exception", e)
            name = ctx.input_name if ctx.input_name else "user"
            try:
                num += f(name, model)
            except Exception as e:
                print("Tokens calc exception", e)
            name = ctx.output_name if ctx.output_name else "assistant"
            try:
                num += f(name, model)
            except Exception as e:
                print("Tokens calc exception", e)
        elif mode == MODE_COMPLETION:
            parts = []
            if ctx.input_name and ctx.output_name:
                if ctx.final_input:
                    parts.append("\n" + ctx.input_name + ": " + ctx.final_input)
                if ctx.final_output:
                    parts.append("\n" + ctx.output_name + ": " + ctx.final_output)
            else:
                if ctx.final_input:
                    parts.append("\n" + ctx.final_input)
                if ctx.final_output:
                    parts.append("\n" + ctx.final_output)
            try:
                num += f("".join(parts), model)
            except Exception as e:
                print("Tokens calc exception", e)
        return num

    def get_current(
            self,
            input_prompt: str
    ) -> Tuple[int, int, int, int, int, int, int, int, int]:
        model = self.window.core.config.get('model')
        model_id = ""
        model_data = self.window.core.models.get(model)
        if model_data is not None:
            model_id = model_data.id
        mode = self.window.core.config.get('mode')
        user_name = self.window.core.config.get('user_name')
        ai_name = self.window.core.config.get('ai_name')

        system_prompt = ""
        system_tokens = 0
        input_tokens = 0
        max_total_tokens = self.window.core.config.get('max_total_tokens')
        extra_tokens = self.get_extra(model)

        if mode in CHAT_MODES:
            system_prompt = str(self.window.core.config.get('prompt')).strip()
            system_prompt = self.window.core.prompt.build_final_system_prompt(system_prompt, mode, model_data)
            if system_prompt:
                system_tokens = self.from_prompt(system_prompt, "", model_id)
                system_tokens += Tokens._const_tokens("system", model_id)
            if input_prompt:
                input_tokens = self.from_prompt(input_prompt, "", model_id)
                input_tokens += Tokens._const_tokens("user", model_id)
        elif mode == MODE_COMPLETION:
            system_prompt = str(self.window.core.config.get('prompt')).strip()
            system_prompt = self.window.core.prompt.build_final_system_prompt(system_prompt, mode, model_data)
            system_tokens = self.from_text(system_prompt, model_id)
            if input_prompt:
                if user_name and ai_name:
                    message = "\n" + user_name + ": " + str(input_prompt) + "\n" + ai_name + ":"
                else:
                    message = "\n" + str(input_prompt)
                input_tokens = self.from_text(message, model_id)
                extra_tokens = 0

        self.window.core.ctx.current_sys_prompt = system_prompt

        used_tokens = system_tokens + input_tokens

        max_current = max_total_tokens
        model_ctx = self.window.core.models.get_num_ctx(model)
        if max_current > model_ctx:
            max_current = model_ctx

        threshold = self.window.core.config.get('context_threshold')
        max_to_check = max_current - threshold

        ctx_len_all = self.window.core.ctx.count_items()
        ctx_len, ctx_tokens = self.window.core.ctx.count_prompt_items(model_id, mode, used_tokens, max_to_check)

        if not self.window.core.config.get('use_context'):
            ctx_tokens = 0
            ctx_len = 0

        sum_tokens = system_tokens + input_tokens + ctx_tokens + extra_tokens

        return input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
               sum_tokens, max_current, threshold

    def from_user(
            self,
            system_prompt: str,
            input_prompt: str
    ) -> int:
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)
        mode = self.window.core.config.get('mode')
        tokens = 0
        if mode in [MODE_CHAT, MODE_AUDIO, MODE_RESEARCH]:
            tokens += self.from_prompt(system_prompt, "", model_id)
            tokens += self.from_text("system", model_id)
            tokens += self.from_prompt(input_prompt, "", model_id)
            tokens += self.from_text("user", model_id)
        else:
            tokens += self.from_text(system_prompt, model_id)
            tokens += self.from_text(input_prompt, model_id)
        tokens += self.window.core.config.get('context_threshold')
        tokens += self.get_extra(model_id)
        return tokens

    @staticmethod
    def get_config(model: str) -> Tuple[str, int, int]:
        per_message = 4
        per_name = -1

        if model is not None:
            if model in {
                "gpt-3.5-turbo-0613",
                "gpt-3.5-turbo-16k-0613",
                "gpt-4-0314",
                "gpt-4-32k-0314",
                "gpt-4-0613",
                "gpt-4-32k-0613",
            }:
                per_message = 3
                per_name = 1
            elif model == "gpt-3.5-turbo-0301":
                per_message = 4
                per_name = -1
            elif "gpt-3.5-turbo" in model:
                return Tokens.get_config(model="gpt-3.5-turbo-0613")
            elif "gpt-4" in model:
                return Tokens.get_config(model="gpt-4-0613")
            elif model.startswith("text-davinci"):
                per_message = 1
                per_name = 0

        return model, per_message, per_name