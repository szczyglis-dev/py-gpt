#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.18 17:30:00                  #
# ================================================== #

import os

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types import MODE_CHAT
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem


class Analyzer:
    IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp")

    def __init__(self, window=None):
        """
        Image analyzer

        :param window: Window instance
        """
        self.window = window

    def _get_model(self):
        """Return the image-capable model configured in Vision (inline)."""
        core = self.window.core
        model_id = core.plugins.get_option("openai_vision", "model")
        if model_id and core.models.has(model_id):
            model = core.models.get(model_id)
            if model.is_image_input() and model.is_supported(MODE_CHAT):
                return model

        # Keep the current model when it already supports image input in Chat.
        current_id = core.config.get("model")
        if current_id and core.models.has(current_id):
            model = core.models.get(current_id)
            if model.is_image_input() and model.is_supported(MODE_CHAT):
                return model

        # Backward-compatible fallback for old plugin configurations.
        if core.models.has("gpt-4o"):
            return core.models.get("gpt-4o")
        return None

    def _call(self, context: BridgeContext) -> str:
        """Run a synchronous Chat request using the selected model/provider."""
        core = self.window.core
        model = context.model
        if model is None:
            return ""

        # Use the same native-SDK routing policy as the main bridge worker.
        api = core.api.openai
        if model.provider == "google" and core.config.get("api_native_google", False):
            api = core.api.google
        elif model.provider == "anthropic" and core.config.get("api_native_anthropic", False):
            api = core.api.anthropic
        elif model.provider == "x_ai" and core.config.get("api_native_xai", False):
            api = core.api.xai

        # request=True redirects quick_call to the normal Chat path. This is
        # important for OpenAI/OpenAI-compatible clients because the normal
        # Chat path is responsible for attaching image content.
        context.request = True
        return api.quick_call(context=context, extra={}) or ""

    def send(
            self,
            ctx: CtxItem,
            prompt: str,
            files: dict
    ) -> str:
        """
        Send image-analysis request through Chat using the configured provider.

        :param ctx: context
        :param prompt: analyze prompt
        :param files: files
        :return: response
        """
        image_files = {
            file_id: attachment
            for file_id, attachment in (files or {}).items()
            if getattr(attachment, "path", "")
            and str(attachment.path).lower().endswith(self.IMAGE_EXTENSIONS)
        }

        try:
            if not image_files:
                return "FAILED: No image attachment was provided for analysis."

            model = self._get_model()
            if model is None:
                return "FAILED: No image-capable Chat model is configured in the Vision (inline) plugin."

            tmp_ctx = CtxItem(mode=MODE_CHAT)
            tmp_ctx.output_name = ctx.output_name or "assistant"
            context = BridgeContext(
                ctx=tmp_ctx,
                prompt=prompt,
                attachments=image_files,
                history=[],
                stream=False,
                model=model,
                mode=MODE_CHAT,
                parent_mode=MODE_CHAT,
                system_prompt=(
                    "You are an expert in image recognition. "
                    "Analyze the provided image and give a detailed, accurate description."
                ),
            )

            output = self._call(context).strip()
            for file_id, attachment in image_files.items():
                if attachment.path:
                    ctx.images_before.append(attachment.path)
                attachment.consumed = True  # allow for deletion
            return output
        finally:
            # re-allow clearing attachments even if the provider call fails
            self.window.controller.attachment.unlock()

    def from_screenshot(
            self,
            ctx: CtxItem,
            prompt: str
    ) -> str:
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

    def from_camera(
            self,
            ctx: CtxItem,
            prompt: str
    ) -> str:
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
        if path:
            return self.send(ctx, prompt, files)
        else:
            return "FAILED: There was a problem with capturing the image."

    def from_path(
            self,
            ctx: CtxItem,
            prompt: str,
            path: str
    ) -> str:
        """
        Image analysis from path

        :param ctx: context item
        :param prompt: analyze prompt
        :param path: path to file
        :return: response
        """
        if not path:
            return self.from_current_attachments(ctx, prompt)  # try current if no path provided

        if not os.path.exists(path):
            return "FAILED: File not found"

        attachment = AttachmentItem()
        attachment.path = path
        files = {
            "img": attachment,
        }
        return self.send(ctx, prompt, files)

    def from_current_attachments(
            self,
            ctx: CtxItem,
            prompt: str
    ) -> str:
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
