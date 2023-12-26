#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #

from openai import OpenAI

from .chat import Chat
from .completion import Completion
from .vision import Vision
from pygpt_net.item.ctx import CtxItem


class Gpt:
    def __init__(self, window=None):
        """
        GPT Wrapper

        :param window: Window instance
        """
        self.window = window
        self.chat = Chat(window)
        self.completion = Completion(window)
        self.vision = Vision(window)
        self.ai_name = None
        self.user_name = None
        self.system_prompt = None
        self.attachments = {}
        self.thread_id = None  # assistant thread id
        self.assistant_id = None  # assistant id

    def get_client(self):
        """
        Return OpenAI client

        :return: OpenAI client
        :rtype: OpenAI
        """
        return OpenAI(
            api_key=self.window.core.config.get('api_key'),
            organization=self.window.core.config.get('organization_key'),
        )

    def call(self, prompt, ctx=None, stream_mode=False):
        """
        Call OpenAI API

        :param prompt: text input (user prompt)
        :param ctx: context item (CtxItem)
        :param stream_mode: stream mode, default: False
        :return: context item (CtxItem)
        :rtype: CtxItem
        """
        # prepare max tokens
        mode = self.window.core.config.get('mode')
        model_tokens = self.window.core.models.get_tokens(self.window.core.config.get('model'))
        max_tokens = self.window.core.config.get('max_output_tokens')

        # check max output tokens
        if max_tokens > model_tokens:
            max_tokens = model_tokens

        # minimum 1 token is required
        if max_tokens < 1:
            max_tokens = 1

        response = None
        used_tokens = 0

        # get response
        if mode == "completion":
            response = self.completion.send(prompt, max_tokens, stream_mode, system_prompt=self.system_prompt,
                                            ai_name=self.ai_name, user_name=self.user_name)
            used_tokens = self.completion.get_used_tokens()
        elif mode == "chat":
            response = self.chat.send(prompt, max_tokens, stream_mode, system_prompt=self.system_prompt,
                                      ai_name=self.ai_name, user_name=self.user_name)
            used_tokens = self.chat.get_used_tokens()
        elif mode == "vision":
            response = self.vision.send(prompt, max_tokens, stream_mode, system_prompt=self.system_prompt,
                                        attachments=self.attachments)
            used_tokens = self.vision.get_used_tokens()
        elif mode == "assistant":
            response = self.window.core.gpt_assistants.msg_send(self.thread_id, prompt)
            if response is not None:
                ctx.msg_id = response.id
                run = self.window.core.gpt_assistants.run_create(self.thread_id, self.assistant_id,
                                                                 self.system_prompt)
                if run is not None:
                    ctx.run_id = run.id
            return ctx  # if assistant then return here

        # if async mode (stream)
        if stream_mode:
            # store context (memory)
            if ctx is None:
                ctx = CtxItem(self.window.core.config.get('mode'))
                ctx.set_input(prompt, self.user_name)

            ctx.stream = response
            ctx.set_output("", self.ai_name)  # set empty output
            ctx.input_tokens = used_tokens  # get from input tokens calculation
            return ctx

        if response is None:
            return None

        # check for errors
        if "error" in response:
            print("Error in GPT response: " + str(response["error"]))
            return None

        # get output text from response
        output = ""
        if mode == "completion":
            output = response.choices[0].text.strip()
        elif mode == "chat" or mode == "vision":
            output = response.choices[0].message.content.strip()

        # store context (memory)
        if ctx is None:
            ctx = CtxItem(self.window.core.config.get('mode'))
            ctx.set_input(prompt, self.user_name)

        ctx.set_output(output, self.ai_name)
        ctx.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)
        return ctx

    def quick_call(self, prompt, sys_prompt, append_context=False,
                   max_tokens=500, model="gpt-3.5-turbo-1106", temp=0.0):
        """
        Quick call OpenAI API with custom prompt

        :param prompt: user input (prompt)
        :param sys_prompt: system input (prompt)
        :param append_context: append context (memory)
        :param max_tokens: max output tokens
        :param model: model name
        :param temp: temperature
        :return: response content
        :rtype: str
        """
        client = self.get_client()

        if append_context:
            messages = self.chat.build(prompt, sys_prompt)
        else:
            messages = []
            messages.append({"role": "system", "content": sys_prompt})
            messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temp,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=None,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error in GPT custom call: " + str(e))

    def prepare_ctx_name(self, ctx):
        """
        Summarize conversation begin

        :param ctx: context item (CtxItem)
        :return: response text (generated summary)
        :rtype: str
        """
        # default values
        model = 'gpt-3.5-turbo-1106'
        sys_prompt = "You are an expert in conversation summarization"
        text = "Summarize topic of this conversation in one sentence. Use best keywords to describe it. " \
               "Summary must be in the same language as the conversation and it will be used for conversation title " \
               "so it must be EXTREMELY SHORT and concise - use maximum 5 words: \n\n"
        text += "User: " + str(ctx.input) + "\nAI Assistant: " + str(ctx.output)

        # custom values
        if self.window.core.config.get('ctx.auto_summary.system') is not None \
                and self.window.core.config.get('ctx.auto_summary.system') != "":
            sys_prompt = self.window.core.config.get('ctx.auto_summary.system')
        if self.window.core.config.get('ctx.auto_summary.prompt') is not None \
                and self.window.core.config.get('ctx.auto_summary.prompt') != "":
            text = self.window.core.config.get('ctx.auto_summary.prompt'). \
                replace("{input}", str(ctx.input)).replace("{output}", str(ctx.output))
        if self.window.core.config.get('ctx.auto_summary.model') is not None \
                and self.window.core.config.get('ctx.auto_summary.model') != "":
            model = self.window.core.config.get('ctx.auto_summary.model')

        # quick call OpenAI API
        response = self.quick_call(text, sys_prompt, False, 500, model)
        if response is not None:
            return response

    def clear(self):
        """Clear context (memory)"""
        self.window.core.ctx.clear()

    def stop(self):
        """Stop OpenAI API"""
        pass
