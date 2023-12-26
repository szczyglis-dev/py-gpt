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

import base64
import os
import re


class Vision:
    def __init__(self, window=None):
        """
        Vision wrapper

        :param window: Window instance
        """
        self.window = window
        self.attachments = {}
        self.input_tokens = 0

    def send(self, prompt, max_tokens, stream_mode=False, system_prompt=None, attachments=None):
        """
        Call OpenAI API for chat with vision

        :param prompt: prompt (user message)
        :param max_tokens: max output tokens
        :param stream_mode: stream mode
        :param system_prompt: system prompt (optional)
        :param attachments: attachments
        :return: response or stream chunks
        """
        client = self.window.core.gpt.get_client()

        # build chat messages
        messages = self.build(prompt, system_prompt=system_prompt, attachments=attachments)
        response = client.chat.completions.create(
            messages=messages,
            model=self.window.core.config.get('model'),
            max_tokens=int(max_tokens),
            stream=stream_mode,
        )
        return response

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def build(self, input_prompt, system_prompt=None, attachments=None):
        """
        Build chat messages dict

        :param input_prompt: prompt
        :param system_prompt: system prompt (optional)
        :param attachments: attachments
        :return: messages dictionary
        """
        messages = []

        # tokens config
        model = self.window.core.config.get('model')
        mode = self.window.core.config.get('mode')

        used_tokens = self.window.core.tokens.from_user(input_prompt, system_prompt)  # threshold and extra included
        max_tokens = self.window.core.config.get('max_total_tokens')
        model_ctx = self.window.core.models.get_num_ctx(model)

        # fit to max model tokens
        if max_tokens > model_ctx:
            max_tokens = model_ctx

        # input tokens: reset
        self.reset_tokens()

        # append initial (system) message
        if system_prompt is not None and system_prompt != "":
            messages.append({"role": "system", "content": system_prompt})
        else:
            if system_prompt is not None and system_prompt != "":
                messages.append({"role": "system", "content": system_prompt})

        # append messages from context (memory)
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_prompt_items(model, mode, used_tokens, max_tokens)
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    content = self.build_content(item.input)
                    messages.append({"role": "user", "content": content})

                # output
                if item.output is not None and item.output != "":
                    content = self.build_content(item.output)
                    messages.append({"role": "assistant", "content": content})

        # append current prompt
        content = self.build_content(input_prompt, attachments)
        messages.append({"role": "user", "content": content})

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_messages(messages, model)

        return messages

    def build_content(self, input_prompt, attachments=None):
        """
        Build vision content

        :param input_prompt: prompt (user input)
        :param attachments: attachments (dict, optional)
        :return: Dictionary with content
        :rtype: dict
        """
        content = [{"type": "text", "text": str(input_prompt)}]

        # extract URLs from prompt
        urls = self.extract_urls(input_prompt)
        if len(urls) > 0:
            for url in urls:
                content.append({"type": "image_url", "image_url": {"url": url}})

        # local images (attachments)
        if attachments is not None and len(attachments) > 0:
            for id in attachments:
                attachment = attachments[id]
                if os.path.exists(attachment.path):
                    # check if it's an image
                    if self.is_image(attachment.path):
                        base64_image = self.encode_image(attachment.path)
                        content.append(
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})

        return content

    def extract_urls(self, text):
        """
        Extract urls from text

        :param text: text
        :return: list of urls
        :rtype: list
        """
        return re.findall(r'(https?://\S+)', text)

    def is_image(self, path):
        """
        Check if url is image

        :param path: url
        :return: true if image
        :rtype: bool
        """
        return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))

    def encode_image(self, image_path):
        """
        Encode image to base64

        :param image_path: path to image
        :return: base64 encoded image
        :rtype: str
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_used_tokens(self):
        """Get input tokens counter"""
        return self.input_tokens
