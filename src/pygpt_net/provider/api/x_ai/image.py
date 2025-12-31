#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.31 16:00:00                  #
# ================================================== #

import base64
import datetime
import os
from typing import Optional, Dict, Any, List

import requests
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Image:
    def __init__(self, window=None):
        self.window = window
        self.worker = None

    def generate(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            sync: bool = True
    ) -> bool:
        """
        Generate image(s) via xAI REST API /v1/images/generations (OpenAI-compatible).
        Model: grok-2-image (or -1212 variants).

        :param context: BridgeContext with prompt, model, ctx
        :param extra: Extra parameters (num: int, inline: bool, etc.)
        :param sync: Run synchronously (blocking) if True
        :return: True if started
        """
        extra = extra or {}
        ctx = context.ctx or CtxItem()
        model = context.model
        prompt = context.prompt
        num = int(extra.get("num", 1))
        inline = bool(extra.get("inline", False))
        extra_prompt = extra.get("extra_prompt", "")

        # Optional prompt enhancement model (same as in your Google path)
        prompt_model = self.window.core.models.from_defaults()
        tmp = self.window.core.config.get('img_prompt_model')
        if self.window.core.models.has(tmp):
            prompt_model = self.window.core.models.get(tmp)

        worker = ImageWorker()
        worker.window = self.window
        worker.ctx = ctx
        worker.model = model.id or "grok-2-image"
        worker.input_prompt = prompt
        worker.model_prompt = prompt_model
        worker.system_prompt = self.window.core.prompt.get('img')
        worker.raw = self.window.core.config.get('img_raw')
        worker.num = num
        worker.inline = inline
        worker.extra_prompt = extra_prompt

        self.worker = worker
        self.worker.signals.finished.connect(self.window.core.image.handle_finished)
        self.worker.signals.finished_inline.connect(self.window.core.image.handle_finished_inline)
        self.worker.signals.status.connect(self.window.core.image.handle_status)
        self.worker.signals.error.connect(self.window.core.image.handle_error)

        if sync or not self.window.controller.kernel.async_allowed(ctx):
            self.worker.run()
            return True

        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {"id": "img"}))
        self.window.threadpool.start(self.worker)
        return True


class ImageSignals(QObject):
    finished = Signal(object, list, str)         # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object)                      # message
    error = Signal(object)                       # exception


class ImageWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = ImageSignals()
        self.window = None
        self.ctx: Optional[CtxItem] = None

        # params
        self.model = "grok-2-image"
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.extra_prompt: Optional[str] = None
        self.raw = False
        self.num = 1

        # API
        self.api_url = "https://api.x.ai/v1/images/generations"  # OpenAI-compatible endpoint

    @Slot()
    def run(self):
        try:
            # optional prompt enhancement
            if not self.raw and not self.inline and self.input_prompt:
                try:
                    self.signals.status.emit(trans('img.status.prompt.wait'))
                    bridge_context = BridgeContext(
                        prompt=self.input_prompt,
                        system_prompt=self.system_prompt,
                        model=self.model_prompt,
                        max_tokens=200,
                        temperature=1.0,
                    )
                    ev = KernelEvent(KernelEvent.CALL, {'context': bridge_context, 'extra': {}})
                    self.window.dispatch(ev)
                    resp = ev.data.get('response')
                    if resp:
                        self.input_prompt = resp
                except Exception as e:
                    self.signals.error.emit(e)
                    self.signals.status.emit(trans('img.status.prompt.error') + ": " + str(e))

            # Negative prompt fallback: append as textual instruction (xAI has no native field for it)
            if self.extra_prompt and str(self.extra_prompt).strip():
                try:
                    self.input_prompt = self._merge_negative_prompt(self.input_prompt or "", self.extra_prompt)
                except Exception:
                    pass

            self.signals.status.emit(trans('img.status.generating') + f": {self.input_prompt}...")

            cfg = self.window.core.config
            api_key = cfg.get("api_key_xai") or os.environ.get("XAI_API_KEY") or ""
            self.api_url = cfg.get("api_endpoint_xai") + "/images/generations"
            if not api_key:
                raise RuntimeError("Missing xAI API key. Set `api_key_xai` in config or XAI_API_KEY in env.")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model or "grok-2-image",
                "prompt": self.input_prompt or "",
                "n": max(1, min(int(self.num), 10)),
                "response_format": "b64_json",  # get base64 so we can save locally
            }

            r = requests.post(self.api_url, headers=headers, json=payload, timeout=180)
            r.raise_for_status()
            data = r.json()

            images = []
            for idx, img in enumerate((data.get("data") or [])[: self.num]):
                b64 = img.get("b64_json")
                if not b64:
                    # fallback: url download
                    url = img.get("url")
                    if url:
                        try:
                            rr = requests.get(url, timeout=60)
                            if rr.status_code == 200:
                                images.append(rr.content)
                        except Exception:
                            pass
                    continue
                try:
                    images.append(base64.b64decode(b64))
                except Exception:
                    continue

            paths: List[str] = []
            for i, content in enumerate(images):
                name = (
                    datetime.date.today().strftime("%Y-%m-%d") + "_" +
                    datetime.datetime.now().strftime("%H-%M-%S") + "-" +
                    self.window.core.image.make_safe_filename(self.input_prompt) + "-" +
                    str(i + 1) + ".jpg"
                )
                path = os.path.join(self.window.core.config.get_user_dir("img"), name)
                self.signals.status.emit(trans('img.status.downloading') + f" ({i + 1} / {self.num}) -> {path}")

                if self.window.core.image.save_image(path, content):
                    paths.append(path)

            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.input_prompt)

        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleanup signals to avoid multiple calls."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass

    # ---------- prompt utilities ----------

    @staticmethod
    def _merge_negative_prompt(prompt: str, negative: Optional[str]) -> str:
        """
        Append a negative prompt to the main text prompt for providers without a native negative_prompt field.
        """
        base = (prompt or "").strip()
        neg = (negative or "").strip()
        if not neg:
            return base
        return (base + ("\n" if base else "") + f"Negative prompt: {neg}").strip()