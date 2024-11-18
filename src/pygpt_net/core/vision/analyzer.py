#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 00:00:00                  #
# ================================================== #

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem


class Analyzer:
    def __init__(self, window=None):
        """
        Image analyzer

        :param window: Window instance
        """
        self.window = window

    def send(self, ctx: CtxItem, prompt: str, files: dict) -> str:
        """
        Send text from user input (called from UI)

        :param ctx: context
        :param prompt: analyze prompt
        :param files: files
        :return: response
        """
        model = self.window.core.models.get("gpt-4o")
        context = BridgeContext()
        context.prompt = prompt
        context.attachments = files
        context.history = []
        context.stream = False
        context.model = model
        context.system_prompt = ("You are an expert in image recognition. "
                                 "You are analyzing the image and providing a detailed description of the image.")

        extra = {}
        output = ""
        response = self.window.core.gpt.vision.send(context, extra)
        if response.choices[0] and response.choices[0].message.content:
            output = response.choices[0].message.content.strip()
        for id in files:
            ctx.images_before.append(files[id].path)

        # re-allow clearing attachments
        self.window.controller.attachment.unlock()
        return output

    def from_screenshot(self, ctx: CtxItem, prompt: str) -> str:
        """
        Image analysis from screenshot

        :param ctx: context
        :param prompt: analyze prompt
        :return: response
        """
        path = self.window.controller.painter.capture.screenshot(
            attach_cursor=True,
            silent=True,
        )
        attachment = AttachmentItem()
        attachment.path = path
        files = {
            "screenshot": attachment,
        }
        return self.send(ctx, prompt, files)

    def from_camera(self, ctx: CtxItem, prompt: str) -> str:
        """
        Image analysis from camera

        :param ctx: context
        :param prompt: analyze prompt
        :return: response
        """
        path = self.window.controller.camera.capture_frame_save()
        attachment = AttachmentItem()
        attachment.path = path
        files = {
            "camera": attachment,
        }
        return self.send(ctx, prompt, files)

    def from_path(self, ctx: CtxItem, prompt: str, path: str) -> str:
        """
        Image analysis from path

        :param ctx: context item
        :param prompt: analyze prompt
        :param path: path to file
        :return: response
        """
        if not path:
            return self.from_current_attachments(ctx, prompt)  # try current if no path provided

        attachment = AttachmentItem()
        attachment.path = path
        files = {
            "img": attachment,
        }
        return self.send(ctx, prompt, files)

    def from_current_attachments(self, ctx: CtxItem, prompt: str) -> str:
        """
        Image analysis from current attachments

        :param ctx: context item
        :param prompt: analyze prompt
        :return: response
        """
        mode = self.window.core.config.get("mode")
        files = self.window.core.attachments.get_all(mode)  # clear is locked here
        result = self.send(ctx, prompt, files)  # unlocks clear

        # clear if capture clear
        if self.window.controller.attachment.is_capture_clear():
            self.window.controller.attachment.clear(True, auto=True)

        return result