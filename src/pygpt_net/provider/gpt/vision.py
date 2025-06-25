#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.25 02:00:00                  #
# ================================================== #

import base64
import os
import re
from typing import Optional, Union, Dict, Any, List

from pygpt_net.core.types import (
    MODE_VISION,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


class Vision:
    def __init__(self, window=None):
        """
        Vision wrapper

        :param window: Window instance
        """
        self.window = window
        self.attachments = {}
        self.urls = []
        self.input_tokens = 0

    def send(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ):
        """
        Call OpenAI API for chat with vision

        :param context: Bridge context
        :param extra: Extra arguments
        :return: response or stream chunks
        """
        prompt = context.prompt
        stream = context.stream
        max_tokens = int(context.max_tokens or 0)
        system_prompt = context.system_prompt
        attachments = context.attachments
        model = context.model
        model_id = model.id
        client = self.window.core.gpt.get_client()

        # extra API kwargs
        response_kwargs = {}
        if max_tokens > 0:
            response_kwargs['max_tokens'] = max_tokens

        # build chat messages
        messages = self.build(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            history=context.history,
            attachments=attachments,
        )
        response = client.chat.completions.create(
            messages=messages,
            model=model_id,
            stream=stream,
            **response_kwargs
        )

        return response

    def build(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
    ) -> List[dict]:
        """
        Build chat messages list

        :param prompt: user prompt
        :param system_prompt: system prompt
        :param model: model item
        :param history: history
        :param attachments: attachments
        :return: messages list
        """
        messages = []

        # tokens config
        mode = MODE_VISION
        used_tokens = self.window.core.tokens.from_user(
            prompt,
            system_prompt,
        )  # threshold and extra included
        max_ctx_tokens = self.window.core.config.get('max_total_tokens')

        # fit to max model tokens
        if max_ctx_tokens > model.ctx:
            max_ctx_tokens = model.ctx

        # input tokens: reset
        self.reset_tokens()

        # append initial (system) message
        if system_prompt is not None and system_prompt != "":
            messages.append({
                "role": "system",
                "content": system_prompt,
            })
        else:
            if system_prompt is not None and system_prompt != "":
                messages.append({
                    "role": "system",
                    "content": system_prompt,
                })

        # append messages from context (memory)
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                mode,
                used_tokens,
                max_ctx_tokens,
            )
            for item in items:
                # input
                if item.final_input is not None and item.final_input != "":
                    messages.append({
                        "role": "user",
                        "content": item.final_input,
                    })

                # output
                if item.final_output is not None and item.final_output != "":
                    messages.append({
                        "role": "assistant",
                        "content": item.final_output,
                    })

        # append current prompt
        content = self.build_content(prompt, attachments)
        messages.append({
            "role": "user",
            "content": content,
        })

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_messages(
            messages,
            model.id,
        )
        return messages

    def build_content(
            self,
            content: Union[str, list],
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            responses_api: Optional[bool] = False,
    ) -> List[dict]:
        """
        Build vision content

        :param content: content (str or list)
        :param attachments: attachments (dict, optional)
        :param responses_api: if True, use responses API format
        :return: List of contents
        """
        type_text = "text"
        type_image = "image_url"
        if responses_api:
            type_text = "input_text"
            type_image = "input_image"

        if not isinstance(content, list):
            content = [
                {
                    "type": type_text,
                    "text": str(content)
                }
            ]

        prompt = content[0]['text']

        self.attachments = {}  # reset attachments, only current prompt
        self.urls = []

        # extract URLs from prompt
        urls = self.extract_urls(prompt)
        if len(urls) > 0:
            for url in urls:
                if not responses_api:
                    content.append(
                        {
                            "type": type_image,
                            "image_url": {
                                "url": url,
                            }
                        }
                    )
                else:
                    content.append(
                        {
                            "type": type_image,
                            "image_url": url,
                        }
                    )
                self.urls.append(url)

        # local images (attachments)
        if attachments is not None and len(attachments) > 0:
            for id in attachments:
                attachment = attachments[id]
                if os.path.exists(attachment.path):
                    # check if it's an image
                    if self.is_image(attachment.path):
                        base64_image = self.encode_image(attachment.path)
                        if not responses_api:
                            content.append(
                                {
                                    "type": type_image,
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                    }
                                }
                            )
                        else:
                            content.append(
                                {
                                    "type": type_image,
                                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                                }
                            )
                        self.attachments[id] = attachment.path
                        attachment.consumed = True

        return content

    def extract_urls(self, text: str) -> List[str]:
        """
        Extract img urls from text

        :param text: text
        :return: list of img urls
        """
        urls = re.findall(r'(https?://\S+)', text)
        img_urls = []
        for url in urls:
            if self.is_image(url):
                img_urls.append(url)

        # if single url, return it
        if "".join(urls).strip() == text.strip():
            return urls

        return img_urls

    def is_image(self, path: str) -> bool:
        """
        Check if url is image

        :param path: url
        :return: True if image
        """
        return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))

    def encode_image(self, image_path: str) -> str:
        """
        Encode image to base64

        :param image_path: path to image
        :return: base64 encoded image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_attachments(self) -> Dict[str, str]:
        """
        Get attachments

        :return: attachments dict
        """
        return self.attachments

    def get_urls(self) -> List[str]:
        """
        Get urls

        :return: urls list
        """
        return self.urls

    def get_used_tokens(self) -> int:
        """
        Get input tokens counter

        :return: input tokens
        """
        return self.input_tokens

    def append_images(self, ctx: CtxItem):
        """
        Append images content to context item

        :param ctx: context
        """
        images = self.get_attachments()  # dict -> key: id, value: path
        urls = self.get_urls()  # list

        # store sent images in ctx
        if len(images) > 0:
            ctx.images = self.window.core.filesystem.make_local_list(list(images.values()))
        if len(urls) > 0:
            ctx.images = urls
            ctx.urls = urls
