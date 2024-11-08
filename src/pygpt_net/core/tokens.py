#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.08 23:00:00                  #
# ================================================== #

import tiktoken

from pygpt_net.item.ctx import CtxItem

CHAT_MODES = [
    "chat",
    "vision",
    "langchain",
    "assistant",
    "llama_index",
    "agent",
    "expert",
]


class Tokens:
    def __init__(self, window=None):
        """
        Tokens core

        :param window: Window instance
        """
        self.window = window

    @staticmethod
    def from_str(string: str, model: str = "gpt-4") -> int:
        """
        Return number of tokens from string

        :param string: string
        :param model: model name
        :return: number of tokens
        """
        if string is None or string == "":
            return 0

        default = "cl100k_base"
        try:
            try:
                if model is not None and model != "":
                    encoding = tiktoken.encoding_for_model(model)
                else:
                    encoding = tiktoken.get_encoding(default)
            except KeyError:
                encoding = tiktoken.get_encoding(default)
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
        """
        Return number of extra tokens

        :param model: model name
        :return: number of tokens
        """
        return 3

    @staticmethod
    def from_prompt(text: str, name: str, model: str = "gpt-4") -> int:
        """
        Return number of tokens from prompt

        :param text: prompt text
        :param name: input name
        :param model: model name
        :return: number of tokens
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0

        try:
            num += Tokens.from_str(text, model)
        except Exception as e:
            print("Tokens calc exception", e)

        if name is not None and name != "":
            num += per_message + per_name
        else:
            num += per_message

        return num

    @staticmethod
    def from_text(text: str, model: str = "gpt-4") -> int:
        """
        Return number of tokens from text, without any extra tokens

        :param text: text
        :param model: model name
        :return: number of tokens
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0

        if text is None or text == "":
            return 0

        try:
            num += Tokens.from_str(text, model)
        except Exception as e:
            print("Tokens calc exception", e)

        return num

    @staticmethod
    def from_messages(messages: list, model: str = "gpt-4") -> int:
        """
        Return number of tokens from messages list

        :param messages: messages
        :param model: model name
        :return: number of tokens
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        for message in messages:
            num += per_message
            for key, value in message.items():
                # text message
                if isinstance(value, str):
                    num += Tokens.from_str(value)
                    if key == "name":
                        num += per_name
                # multimodal message
                elif key == "content" and isinstance(value, list):
                    for part in value:
                        if "type" in part and "text" in part:
                            if part["type"] == "text":
                                num += Tokens.from_str(part["text"])
        num += 3  # every reply is primed with <|start|>assistant<|message|>
        return num

    @staticmethod
    def from_langchain_messages(messages: list, model: str = "gpt-4") -> int:
        """
        Return number of tokens from prompt

        :param messages: messages
        :param model: model name
        :return: number of tokens
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        for message in messages:
            num += per_message
            num += Tokens.from_str(message.content)
        num += 3  # every reply is primed with <|start|>assistant<|message|>
        return num

    @staticmethod
    def from_llama_messages(query: str, messages: list, model: str = "gpt-4") -> int:
        """
        Return number of tokens from prompt

        :param query: query
        :param messages: messages
        :param model: model name
        :return: number of tokens
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        num += Tokens.from_str(query)
        for message in messages:
            num += per_message
            num += Tokens.from_str(message.content)
        num += 3  # every reply is primed with <|start|>assistant<|message|>
        return num

    @staticmethod
    def from_ctx(ctx: CtxItem, mode: str = "chat", model: str = "gpt-4") -> int:
        """
        Return number of tokens from context ctx

        :param ctx: CtxItem
        :param mode: mode
        :param model: model ID
        :return: number of tokens
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0

        if mode in CHAT_MODES:
            # input message
            try:
                num += Tokens.from_str(str(ctx.input), model)
            except Exception as e:
                print("Tokens calc exception", e)

            # output message
            try:
                num += Tokens.from_str(str(ctx.output), model)
            except Exception as e:
                print("Tokens calc exception", e)

            # + fixed tokens
            num += per_message * 2  # input + output
            num += per_name * 2  # input + output
            try:
                num += Tokens.from_str("system", model) * 2  # input + output
            except Exception as e:
                print("Tokens calc exception", e)

            # input name
            if ctx.input_name is not None and ctx.input_name != "":
                name = ctx.input_name
            else:
                name = "user"
            try:
                num += Tokens.from_str(name, model)
            except Exception as e:
                print("Tokens calc exception", e)

            # output name
            if ctx.output_name is not None and ctx.output_name != "":
                name = ctx.output_name
            else:
                name = "assistant"
            try:
                num += Tokens.from_str(name, model)
            except Exception as e:
                print("Tokens calc exception", e)

        # build tmp message if completion mode
        elif mode == "completion":
            message = ""
            # if with names
            if ctx.input_name is not None \
                    and ctx.output_name is not None \
                    and ctx.input_name != "" \
                    and ctx.output_name != "":
                if ctx.input is not None and ctx.input != "":
                    message += "\n" + ctx.input_name + ": " + ctx.input
                if ctx.output is not None and ctx.output != "":
                    message += "\n" + ctx.output_name + ": " + ctx.output
            # if without names
            else:
                if ctx.input is not None and ctx.input != "":
                    message += "\n" + ctx.input
                if ctx.output is not None and ctx.output != "":
                    message += "\n" + ctx.output
            try:
                num += Tokens.from_str(message, model)
            except Exception as e:
                print("Tokens calc exception", e)

        return num

    def get_current(self, input_prompt: str) -> (int, int, int, int, int, int, int, int, int):
        """
        Return current number of used tokens

        :param input_prompt: input prompt
        :return: A tuple of (input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
               sum_tokens, max_current, threshold)
        """
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)
        mode = self.window.core.config.get('mode')
        user_name = self.window.core.config.get('user_name')
        ai_name = self.window.core.config.get('ai_name')

        system_prompt = ""
        system_tokens = 0
        input_tokens = 0
        max_total_tokens = self.window.core.config.get('max_total_tokens')
        extra_tokens = self.get_extra(model)

        if mode in CHAT_MODES:
            # system prompt (without extra tokens)
            system_prompt = str(self.window.core.config.get('prompt')).strip()
            system_prompt = self.window.core.prompt.build_final_system_prompt(system_prompt)  # add addons

            if system_prompt is not None and system_prompt != "":
                system_tokens = self.from_prompt(system_prompt, "", model_id)
                system_tokens += self.from_text("system", model_id)

            # input prompt
            if input_prompt is not None and input_prompt != "":
                input_tokens = self.from_prompt(input_prompt, "", model_id)
                input_tokens += self.from_text("user", model_id)
        elif mode == "completion":
            # system prompt (without extra tokens)
            system_prompt = str(self.window.core.config.get('prompt')).strip()
            system_prompt = self.window.core.prompt.build_final_system_prompt(system_prompt)  # add addons
            system_tokens = self.from_text(system_prompt, model_id)

            # input prompt
            if input_prompt is not None and input_prompt != "":
                message = ""
                if user_name is not None \
                        and ai_name is not None \
                        and user_name != "" \
                        and ai_name != "":
                    message += "\n" + user_name + ": " + str(input_prompt)
                    message += "\n" + ai_name + ":"
                else:
                    message += "\n" + str(input_prompt)
                input_tokens = self.from_text(message, model_id)
                extra_tokens = 0  # no extra tokens in completion mode

        # TMP system prompt (for debug purposes)
        self.window.core.ctx.current_sys_prompt = system_prompt

        # used tokens
        used_tokens = system_tokens + input_tokens

        # check model max allowed ctx tokens
        max_current = max_total_tokens
        model_ctx = self.window.core.models.get_num_ctx(model_id)
        if max_current > model_ctx:
            max_current = model_ctx

        # context threshold (reserved for output)
        threshold = self.window.core.config.get('context_threshold')
        max_to_check = max_current - threshold

        # context tokens
        ctx_len_all = self.window.core.ctx.count_items()
        ctx_len, ctx_tokens = self.window.core.ctx.count_prompt_items(model_id, mode, used_tokens, max_to_check)

        # empty ctx tokens if context is not used
        if not self.window.core.config.get('use_context'):
            ctx_tokens = 0
            ctx_len = 0

        # sum of input tokens
        sum_tokens = system_tokens + input_tokens + ctx_tokens + extra_tokens

        return input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
               sum_tokens, max_current, threshold

    def from_user(self, system_prompt: str, input_prompt: str) -> int:
        """
        Count per-user used tokens

        :param system_prompt: system prompt
        :param input_prompt: input prompt
        :return: used tokens
        """
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)
        mode = self.window.core.config.get('mode')
        tokens = 0
        if mode == "chat" or mode == "vision":
            tokens += self.from_prompt(system_prompt, "", model_id)  # system prompt
            tokens += self.from_text("system", model_id)
            tokens += self.from_prompt(input_prompt, "", model_id)  # input prompt
            tokens += self.from_text("user", model_id)
        else:
            # rest of modes
            tokens += self.from_text(system_prompt, model_id)  # system prompt
            tokens += self.from_text(input_prompt, model_id)  # input prompt
        tokens += self.window.core.config.get('context_threshold')  # context threshold (reserved for output)
        tokens += self.get_extra(model_id)  # extra tokens (required for output)
        return tokens

    @staticmethod
    def get_config(model: str) -> (str, int, int):
        """
        Return tokens config values

        :param model: model ID
        :return: model, per_message, per_name
        """
        per_message = 4  # message follows <|start|>{role/name}\n{content}<|end|>\n
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
                per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
                per_name = -1  # if there's a name, the role is omitted
            elif "gpt-3.5-turbo" in model:
                return Tokens.get_config(model="gpt-3.5-turbo-0613")
            elif "gpt-4" in model:
                return Tokens.get_config(model="gpt-4-0613")
            elif model.startswith("text-davinci"):
                per_message = 1
                per_name = 0

        return model, per_message, per_name
