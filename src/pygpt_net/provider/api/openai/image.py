#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.23 23:00:00                  #
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

    MODE_GENERATE = "generate"
    MODE_EDIT = "edit"

    def __init__(self, window=None):
        """
        Image generation core

        :param window: Window instance
        """
        self.window = window
        self.worker = None

    def generate(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            sync: bool = True
    ):
        """
        Call images API

        :param context: Bridge context
        :param extra: Extra arguments
        :param sync: Synchronous mode
        """
        extra = extra or {}
        prompt = context.prompt
        ctx = context.ctx
        model = context.model
        num = extra.get("num", 1)
        inline = extra.get("inline", False)
        sub_mode = self.MODE_GENERATE
        image_id = extra.get("image_id")  # previous image reference for remix
        extra_prompt = extra.get("extra_prompt", "")

        # if attachments then switch mode to EDIT
        attachments = context.attachments
        if attachments and len(attachments) > 0:
            sub_mode = self.MODE_EDIT

        if ctx is None:
            ctx = CtxItem()  # create empty context

        prompt_model = self.window.core.models.from_defaults()
        tmp_model = self.window.core.config.get('img_prompt_model')
        if self.window.core.models.has(tmp_model):
            prompt_model = self.window.core.models.get(tmp_model)

        # worker
        worker = ImageWorker()
        worker.window = self.window
        worker.client = self.window.core.api.openai.get_client()
        worker.ctx = ctx
        worker.mode = sub_mode  # mode can be "generate" or "edit"
        worker.attachments = attachments  # attachments for edit mode
        worker.raw = self.window.core.config.get('img_raw')
        worker.model = model.id  # model ID for generate image, e.g. "dall-e-3"
        worker.model_prompt = prompt_model  # model for generate prompt, not image!
        worker.input_prompt = prompt
        worker.system_prompt = self.window.core.prompt.get('img')
        worker.num = num
        worker.inline = inline
        worker.extra_prompt = extra_prompt
        worker.image_id = image_id  # remix: previous image path/identifier

        # config
        if self.window.core.config.has('img_quality'):
            worker.quality = self.window.core.config.get('img_quality')
        if self.window.core.config.has('img_resolution'):
            worker.resolution = self.window.core.config.get('img_resolution')

        self.worker = worker
        self.worker.signals.finished.connect(self.window.core.image.handle_finished)
        self.worker.signals.finished_inline.connect(self.window.core.image.handle_finished_inline)
        self.worker.signals.status.connect(self.window.core.image.handle_status)
        self.worker.signals.error.connect(self.window.core.image.handle_error)

        # sync
        if sync:
            self.worker.run()
            return True

        # check if async allowed
        if not self.window.controller.kernel.async_allowed(ctx):
            self.worker.run()
            return True

        # start
        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "id": "img",
        }))
        self.window.threadpool.start(self.worker)
        return True


class ImageSignals(QObject):
    finished = Signal(object, list, str)  # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object)  # status message
    error = Signal(object)  # error message


class ImageWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = ImageSignals()
        self.args = args
        self.kwargs = kwargs
        self.window = None
        self.client = None
        self.ctx: Optional[CtxItem] = None
        self.raw = False
        self.mode = Image.MODE_GENERATE  # default mode is generate
        self.model = "dall-e-3"
        self.quality = "standard"
        self.resolution = "1792x1024"
        self.attachments: Dict[str, Any] = {}  # attachments for edit mode
        self.model_prompt = None
        self.input_prompt: Optional[str] = None
        self.system_prompt = None
        self.inline = False
        self.extra_prompt: Optional[str] = None
        self.num = 1
        self.image_id: Optional[str] = None  # previous image reference for remix

        # legacy maps kept for backwards compatibility (dall-e-2 / dall-e-3 exact ids)
        self.allowed_max_num = {
            "dall-e-2": 4,
            "dall-e-3": 1,
        }
        self.allowed_resolutions = {
            "dall-e-2": [
                "1024x1024",
                "512x512",
                "256x256",
            ],
            "dall-e-3": [
                "1792x1024",
                "1024x1792",
                "1024x1024",
            ],
        }
        self.allowed_quality = {
            "dall-e-2": ["standard"],
            "dall-e-3": ["standard", "hd"],
        }

    # ---------- model helpers ----------

    def _is_gpt_image_model(self, model_id: Optional[str] = None) -> bool:
        mid = (model_id or self.model or "").lower()
        return mid.startswith("gpt-image-1") or mid.startswith("chatgpt-image")

    def _is_dalle2(self, model_id: Optional[str] = None) -> bool:
        mid = (model_id or self.model or "").lower()
        return mid == "dall-e-2"

    def _is_dalle3(self, model_id: Optional[str] = None) -> bool:
        mid = (model_id or self.model or "").lower()
        return mid == "dall-e-3"

    def _max_num_for_model(self) -> int:
        if self._is_gpt_image_model():
            return 1
        if self._is_dalle2():
            return self.allowed_max_num["dall-e-2"]
        if self._is_dalle3():
            return self.allowed_max_num["dall-e-3"]
        return 1

    def _normalize_resolution_for_model(self, resolution: Optional[str]) -> str:
        res = (resolution or "").strip() or "1024x1024"
        if self._is_gpt_image_model():
            allowed = {"1024x1024", "1536x1024", "1024x1536", "auto"}
            return res if res in allowed else "auto"
        if self._is_dalle2():
            allowed = set(self.allowed_resolutions["dall-e-2"])
            return res if res in allowed else "1024x1024"
        if self._is_dalle3():
            allowed = set(self.allowed_resolutions["dall-e-3"])
            return res if res in allowed else "1024x1024"
        return res

    def _normalize_quality_for_model(self, quality: Optional[str]) -> Optional[str]:
        q = (quality or "").strip().lower()
        if self._is_gpt_image_model():
            allowed = {"auto", "high", "medium", "low"}
            return q if q in allowed else "auto"
        if self._is_dalle2():
            return "standard"
        if self._is_dalle3():
            allowed = {"standard", "hd"}
            return q if q in allowed else "standard"
        return None

    @Slot()
    def run(self):
        """Run worker"""
        if not self.raw and not self.inline:  # disable on inline and raw modes
            try:
                # call GPT for generate better image generate prompt
                self.signals.status.emit(trans('img.status.prompt.wait'))
                bridge_context = BridgeContext(
                    prompt=self.input_prompt,
                    system_prompt=self.system_prompt,
                    model=self.model_prompt,  # model instance
                    max_tokens=200,
                    temperature=1.0,
                )
                event = KernelEvent(KernelEvent.CALL, {
                    'context': bridge_context,
                    'extra': {},
                })
                self.window.dispatch(event)
                response = event.data.get('response')
                if response is not None and response != "":
                    self.input_prompt = response

            except Exception as e:
                self.signals.error.emit(e)
                self.signals.status.emit(trans('img.status.prompt.error') + ": " + str(e))

        # Fallback negative prompt injection (OpenAI Images API has no native negative_prompt field)
        if self.extra_prompt and str(self.extra_prompt).strip():
            try:
                self.input_prompt = self._merge_negative_prompt(self.input_prompt or "", self.extra_prompt)
            except Exception:
                pass

        self.signals.status.emit(trans('img.status.generating') + ": {}...".format(self.input_prompt))

        paths: List[str] = []  # downloaded images paths
        try:
            # enforce model-specific limits/options
            self.num = min(max(1, int(self.num or 1)), self._max_num_for_model())
            resolution = self._normalize_resolution_for_model(self.resolution)
            quality = self._normalize_quality_for_model(self.quality)

            response = None

            # Remix path: if image_id provided, prefer editing with previous image reference
            if self.image_id:
                if self._is_dalle3():
                    try:
                        self.signals.status.emit("Remix is not supported for this model; generating a new image.")
                    except Exception:
                        pass
                else:
                    remix_images = []
                    try:
                        if isinstance(self.image_id, str) and os.path.exists(self.image_id):
                            remix_images.append(open(self.image_id, "rb"))
                    except Exception:
                        remix_images = []

                    if len(remix_images) > 0:
                        try:
                            edit_kwargs = {
                                "model": self.model,
                                "image": remix_images,
                                "prompt": self.input_prompt,
                                "n": self.num,
                                "size": resolution,
                            }
                            if self._is_gpt_image_model() or self._is_dalle3():
                                if quality:
                                    edit_kwargs["quality"] = quality
                            response = self.client.images.edit(**edit_kwargs)
                        finally:
                            for f in remix_images:
                                try:
                                    f.close()
                                except Exception:
                                    pass

            # Normal API paths when remix not executed or unsupported
            if response is None:
                if self.mode == Image.MODE_GENERATE:
                    if self._is_dalle2():
                        response = self.client.images.generate(
                            model=self.model,
                            prompt=self.input_prompt,
                            n=self.num,
                            size=resolution,
                        )
                    else:
                        gen_kwargs = {
                            "model": self.model,
                            "prompt": self.input_prompt,
                            "n": self.num,
                            "size": resolution,
                        }
                        if (self._is_gpt_image_model() or self._is_dalle3()) and quality:
                            gen_kwargs["quality"] = quality
                        response = self.client.images.generate(**gen_kwargs)
                elif self.mode == Image.MODE_EDIT:
                    images = []
                    for uuid in self.attachments or {}:
                        attachment = self.attachments[uuid]
                        if attachment.path and os.path.exists(attachment.path):
                            images.append(open(attachment.path, "rb"))
                    try:
                        edit_kwargs = {
                            "model": self.model,
                            "image": images,
                            "prompt": self.input_prompt,
                            "n": self.num,
                            "size": resolution,
                        }
                        if (self._is_gpt_image_model() or self._is_dalle3()) and quality:
                            edit_kwargs["quality"] = quality
                        response = self.client.images.edit(**edit_kwargs)
                    finally:
                        for f in images:
                            try:
                                f.close()
                            except Exception:
                                pass

            # check response
            if response is None:
                self.signals.status.emit("API Error: empty response")
                return

            # record usage if provided by API
            try:
                self._record_usage_openai(response)
            except Exception:
                pass

            # download images
            for i in range(self.num):
                if i >= len(response.data):
                    break

                # generate filename
                name = datetime.date.today().strftime(
                    "%Y-%m-%d") + "_" + datetime.datetime.now().strftime("%H-%M-%S") + "-" \
                       + self.window.core.image.make_safe_filename(self.input_prompt) + "-" + str(i + 1) + ".png"
                path = os.path.join(self.window.core.config.get_user_dir("img"), name)

                msg = trans('img.status.downloading') + " (" + str(i + 1) + " / " + str(self.num) + ") -> " + str(path)
                self.signals.status.emit(msg)

                item = response.data[i]
                data = None
                if getattr(item, "url", None):
                    res = requests.get(item.url)
                    data = res.content
                elif getattr(item, "b64_json", None):
                    data = base64.b64decode(item.b64_json)

                # save image
                if data and self.window.core.image.save_image(path, data):
                    paths.append(path)
                else:
                    self.signals.error.emit("Error saving image")

            # store image_id for future remix (use first saved path as reference)
            if paths:
                try:
                    if not isinstance(self.ctx.extra, dict):
                        self.ctx.extra = {}
                    self.ctx.extra["image_id"] = self.window.core.filesystem.make_local(paths[0])
                    self.window.core.ctx.update_item(self.ctx)
                except Exception:
                    pass

            # send finished signal
            if self.inline:
                self.signals.finished_inline.emit(  # separated signal for inline mode
                    self.ctx,
                    paths,
                    self.input_prompt,
                )
            else:
                self.signals.finished.emit(
                    self.ctx,
                    paths,
                    self.input_prompt,
                )

        except Exception as e:
            self.signals.error.emit(e)
            print(trans('img.status.error') + ": " + str(e))

        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources after worker execution."""
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

    # ---------- usage helpers (OpenAI Images API) ----------

    def _record_usage_openai(self, response: Any) -> None:
        """
        Extract and store token usage from OpenAI Images API response if present.
        Saves to:
          - ctx.set_tokens(input_tokens, output_tokens)
          - ctx.extra["usage"] = {...}
        """
        try:
            usage = getattr(response, "usage", None)
            if usage is None and isinstance(response, dict):
                usage = response.get("usage")

            if not usage:
                return

            def _as_int(v) -> int:
                try:
                    return int(v)
                except Exception:
                    try:
                        return int(float(v))
                    except Exception:
                        return 0

            # handle both attr and dict style
            getv = lambda o, k: getattr(o, k, None) if not isinstance(o, dict) else o.get(k)

            inp = _as_int(getv(usage, "input_tokens") or getv(usage, "prompt_tokens") or 0)
            outp = _as_int(getv(usage, "output_tokens") or getv(usage, "completion_tokens") or 0)
            total = _as_int(getv(usage, "total_tokens") or (inp + outp))

            # store basic tokens
            if self.ctx:
                self.ctx.set_tokens(inp, outp)

            # store detailed usage in ctx.extra["usage"]
            if not isinstance(self.ctx.extra, dict):
                self.ctx.extra = {}

            # pass through details if available
            input_details = getv(usage, "input_tokens_details") or getv(usage, "prompt_tokens_details") or {}
            output_details = getv(usage, "output_tokens_details") or getv(usage, "completion_tokens_details") or {}

            # normalize dict-like objects
            def _to_plain(o):
                try:
                    if hasattr(o, "model_dump"):
                        return o.model_dump()
                    if hasattr(o, "to_dict"):
                        return o.to_dict()
                except Exception:
                    pass
                return o if isinstance(o, dict) else {}

            self.ctx.extra["usage"] = {
                "vendor": "openai",
                "model": str(self.model),
                "input_tokens": inp,
                "output_tokens": outp,
                "total_tokens": total,
                "input_tokens_details": _to_plain(input_details),
                "output_tokens_details": _to_plain(output_details),
                "source": "images",
            }
        except Exception:
            # do not raise, usage is best-effort
            pass