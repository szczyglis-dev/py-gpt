#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Mohit Varikuti                       #
# Updated Date: 2026.06.25 00:00:00                  #
# ================================================== #

from __future__ import annotations

import os

from PySide6.QtCore import Slot
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    TwelveLabs plugin worker: video analysis (Pegasus) and multimodal embeddings (Marengo).
    """

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    # ---------------------- Core runner ----------------------

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):
                        if item["cmd"] == "tl_analyze_video":
                            response = self.cmd_tl_analyze_video(item)
                        elif item["cmd"] == "tl_embed_text":
                            response = self.cmd_tl_embed_text(item)

                        if response:
                            responses.append(response)

                except Exception as e:
                    responses.append(self.make_response(item, self.throw_error(e)))

            if responses:
                self.reply_more(responses)
            if self.msg is not None:
                self.status(self.msg)
        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    # ---------------------- Helpers ----------------------

    def get_client(self):
        """
        Build a TwelveLabs client using the configured (or env) API key.

        :return: TwelveLabs client instance
        """
        try:
            from twelvelabs import TwelveLabs
        except ImportError:
            raise RuntimeError(
                "Missing 'twelvelabs' package. Install with: pip install twelvelabs"
            )
        api_key = (self.plugin.get_option_value("api_key") or "").strip()
        if not api_key:
            api_key = (os.environ.get("TWELVELABS_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError(
                "TwelveLabs API key is not set. Configure it in the plugin settings "
                "or via the TWELVELABS_API_KEY environment variable. "
                "Get a free key at https://twelvelabs.io"
            )
        return TwelveLabs(api_key=api_key)

    def _request_options(self) -> dict:
        timeout = self.plugin.get_option_value("timeout")
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 300
        return {"timeout_in_seconds": timeout}

    # ---------------------- Commands ----------------------

    def cmd_tl_analyze_video(self, item: dict) -> dict:
        p = item.get("params", {})
        prompt = (p.get("prompt") or "").strip()
        if not prompt:
            return self.make_response(item, "Param 'prompt' required")

        url = (p.get("url") or "").strip()
        video_id = (p.get("video_id") or "").strip()
        if not url and not video_id:
            return self.make_response(item, "Provide either 'url' or 'video_id'")

        model_name = (self.plugin.get_option_value("pegasus_model") or "pegasus1.5").strip()

        max_tokens = p.get("max_tokens")
        if max_tokens is None:
            max_tokens = self.plugin.get_option_value("max_tokens")
        try:
            max_tokens = int(max_tokens)
        except (TypeError, ValueError):
            max_tokens = 2048

        temperature = p.get("temperature")
        if temperature is None:
            temperature = self.plugin.get_option_value("temperature")
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            temperature = 0.2

        client = self.get_client()
        kwargs = dict(
            model_name=model_name,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            request_options=self._request_options(),
        )
        if video_id:
            kwargs["video_id"] = video_id
        else:
            from twelvelabs.types.video_context import VideoContext_Url
            kwargs["video"] = VideoContext_Url(url=url)

        result = client.analyze(**kwargs)
        self.msg = "Analyzed video with TwelveLabs Pegasus"
        return self.make_response(item, {
            "model": model_name,
            "data": getattr(result, "data", None),
            "finish_reason": getattr(result, "finish_reason", None),
        })

    def cmd_tl_embed_text(self, item: dict) -> dict:
        p = item.get("params", {})
        text = (p.get("text") or "").strip()
        if not text:
            return self.make_response(item, "Param 'text' required")

        model_name = (self.plugin.get_option_value("marengo_model") or "marengo3.0").strip()

        client = self.get_client()
        result = client.embed.create(
            model_name=model_name,
            text=text,
            request_options=self._request_options(),
        )
        segments = result.text_embedding.segments if result.text_embedding else []
        vector = list(segments[0].float_) if segments else []
        self.msg = "Created text embedding with TwelveLabs Marengo"
        return self.make_response(item, {
            "model": model_name,
            "dimensions": len(vector),
            "embedding": vector,
        })
