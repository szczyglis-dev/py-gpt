#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 20:00:00                  #
# ================================================== #

import tiktoken


class Tokens:
    def __init__(self, window=None):
        """
        Tokens

        :param window: Window instance
        """
        self.window = window

    @staticmethod
    def from_str(string, model="gpt-4"):
        """
        Return number of tokens from string

        :param string: string
        :param model: model name
        :return: number of tokens
        :rtype: int
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
    def get_extra(model="gpt-4"):
        """
        Return number of extra tokens

        :param model: model name
        :return: number of tokens
        :rtype: int
        """
        return 3

    @staticmethod
    def from_prompt(text, name, model="gpt-4"):
        """
        Return number of tokens from prompt

        :param text: prompt text
        :param name: input name
        :param model: model name
        :return: number of tokens
        :rtype: int
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
    def from_text(text, model="gpt-4"):
        """
        Return number of tokens from text, without any extra tokens

        :param text: text
        :param model: model name
        :return: number of tokens
        :rtype: int
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
    def from_messages(messages, model="gpt-4"):
        """
        Return number of tokens from prompt

        :param messages: messages
        :param model: model name
        :return: number of tokens
        :rtype: int
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0
        for message in messages:
            num += per_message
            for key, value in message.items():
                num += Tokens.from_str(value)
                if key == "name":
                    num += per_name
        num += 3  # every reply is primed with <|start|>assistant<|message|>
        return num

    @staticmethod
    def from_ctx(ctx, mode="chat", model="gpt-4"):
        """
        Return number of tokens from context ctx

        :param ctx: CtxItem
        :param mode: mode
        :param model: model name
        :return: number of tokens
        :rtype: int
        """
        model, per_message, per_name = Tokens.get_config(model)
        num = 0

        if mode == "chat" or mode == "vision" or mode == "langchain" or mode == "assistant":
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

    def get_current(self):
        """
        Return current number of used tokens

        :return: A tuple of (input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
               sum_tokens, max_current, threshold)
        :rtype: tuple
        """
        model = self.window.core.config.get('model')
        mode = self.window.core.config.get('mode')
        user_name = self.window.core.config.get('user_name')
        ai_name = self.window.core.config.get('ai_name')

        system_tokens = 0
        input_tokens = 0
        max_total_tokens = self.window.core.config.get('max_total_tokens')
        extra_tokens = self.window.core.tokens.get_extra(model)

        if mode == "chat" or mode == "vision" or mode == "langchain" or mode == "assistant":
            # system prompt (without extra tokens)
            system_prompt = str(self.window.core.config.get('prompt')).strip()
            system_prompt = self.window.core.prompt.build_final_system_prompt(system_prompt)  # add addons
            system_tokens = self.window.core.tokens.from_prompt(system_prompt, "", model)
            system_tokens += self.window.core.tokens.from_text("system", model)

            # input prompt
            input_prompt = str(self.window.ui.nodes['input'].toPlainText().strip())
            input_tokens = self.window.core.tokens.from_prompt(input_prompt, "", model)
            input_tokens += self.window.core.tokens.from_text("user", model)
        elif mode == "completion":
            # system prompt (without extra tokens)
            system_prompt = str(self.window.core.config.get('prompt')).strip()
            system_prompt = self.window.core.prompt.build_final_system_prompt(system_prompt)  # add addons
            system_tokens = self.window.core.tokens.from_text(system_prompt, model)

            # input prompt
            input_prompt = str(self.window.ui.nodes['input'].toPlainText().strip())
            message = ""
            if user_name is not None \
                    and ai_name is not None \
                    and user_name != "" \
                    and ai_name != "":
                message += "\n" + user_name + ": " + str(input_prompt)
                message += "\n" + ai_name + ":"
            else:
                message += "\n" + str(input_prompt)
            input_tokens = self.window.core.tokens.from_text(message, model)
            extra_tokens = 0  # no extra tokens in completion mode

        # used tokens
        used_tokens = system_tokens + input_tokens

        # check model max allowed ctx tokens
        max_current = max_total_tokens
        model_ctx = self.window.core.models.get_num_ctx(model)
        if max_current > model_ctx:
            max_current = model_ctx

        # context threshold (reserved for output)
        threshold = self.window.core.config.get('context_threshold')
        max_to_check = max_current - threshold

        # context tokens
        ctx_len_all = len(self.window.core.ctx.items)
        ctx_len, ctx_tokens = self.window.core.ctx.count_prompt_items(model, mode, used_tokens, max_to_check)

        # empty ctx tokens if context is not used
        if not self.window.core.config.get('use_context'):
            ctx_tokens = 0
            ctx_len = 0

        # sum of input tokens
        sum_tokens = system_tokens + input_tokens + ctx_tokens + extra_tokens

        return input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
               sum_tokens, max_current, threshold

    @staticmethod
    def get_config(model):
        """
        Return tokens config values

        :param model: model name
        :return: model, per_message, per_name
        :rtype: (str, int, int)
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
