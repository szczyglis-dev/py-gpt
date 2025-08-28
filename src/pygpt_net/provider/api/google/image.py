#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 20:00:00                  #
# ================================================== #

from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types as gtypes
from PySide6.QtCore import QObject, Signal, QRunnable, Slot
import base64, datetime, os, requests

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Image:

    MODE_GENERATE = "generate"
    MODE_EDIT = "edit"

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
        Generate image(s) using Google GenAI API

        :param context: BridgeContext
        :param extra: Extra parameters (num, inline)
        :param sync: Run synchronously if True
        :return: bool
        """
        extra = extra or {}
        ctx = context.ctx or CtxItem()
        model = context.model
        prompt = context.prompt
        num = int(extra.get("num", 1))
        inline = bool(extra.get("inline", False))

        prompt_model = self.window.core.models.from_defaults()
        tmp = self.window.core.config.get('img_prompt_model')
        if self.window.core.models.has(tmp):
            prompt_model = self.window.core.models.get(tmp)

        worker = ImageWorker()
        worker.window = self.window
        worker.client = self.window.core.api.google.get_client()
        worker.ctx = ctx
        worker.model = model.id
        worker.input_prompt = prompt
        worker.model_prompt = prompt_model
        worker.system_prompt = self.window.core.prompt.get('img')
        worker.raw = self.window.core.config.get('img_raw')
        worker.num = num
        worker.inline = inline

        if self.window.core.config.has('img_resolution'):
            worker.resolution = self.window.core.config.get('img_resolution') or "1024x1024"

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
    finished = Signal(object, list, str)  # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object) # message
    error = Signal(object) # exception


class ImageWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = ImageSignals()
        self.window = None
        self.client: Optional[genai.Client] = None
        self.ctx: Optional[CtxItem] = None
        self.model = "imagen-4.0-generate-001"
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.raw = False
        self.num = 1
        self.resolution = "1024x1024"  # used to derive aspect ratio for Imagen

    @Slot()
    def run(self):
        try:
            # Optional prompt enhancement
            if not self.raw and not not self.inline:
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

            self.signals.status.emit(trans('img.status.generating') + f": {self.input_prompt}...")

            paths: List[str] = []
            if self._is_imagen(self.model):
                # Imagen: generate_images
                resp = self._imagen_generate(self.input_prompt, self.num, self.resolution)
                imgs = getattr(resp, "generated_images", None) or []
                for idx, gi in enumerate(imgs[: self.num]):
                    data = self._extract_imagen_bytes(gi)
                    p = self._save(idx, data)
                    if p:
                        paths.append(p)
            else:
                # Gemini image preview: generate_content -> parts[].inline_data.data
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=[self.input_prompt],
                )
                from PIL import Image as PILImage
                from io import BytesIO
                cands = getattr(resp, "candidates", None) or []
                saved = 0
                for cand in cands:
                    parts = getattr(getattr(cand, "content", None), "parts", None) or []
                    for part in parts:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            data = inline.data
                            p = self._save(saved, data)
                            if p:
                                paths.append(p)
                                saved += 1
                                if saved >= self.num:
                                    break
                    if saved >= self.num:
                        break

            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.input_prompt)
        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self._cleanup()

    def _is_imagen(self, model_id: str) -> bool:
        """
        Check if model_id is an Imagen model

        :param model_id: Model ID
        :return: True if Imagen model
        """
        return "imagen" in str(model_id).lower()

    def _imagen_generate(self, prompt: str, num: int, resolution: str):
        """
        Call Imagen generate_images with config (number_of_images, optional aspect_ratio).

        :param prompt: Prompt text
        :param num: Number of images to generate
        :param resolution: Resolution string, e.g. "1024x1024"
        :return: GenerateImagesResponse
        """
        aspect = self._aspect_from_resolution(resolution)  # "1:1", "3:4", …
        cfg = gtypes.GenerateImagesConfig(number_of_images=num)
        if aspect:
            cfg.aspect_ratio = aspect
        return self.client.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=cfg,
        )

    def _aspect_from_resolution(self, resolution: str) -> Optional[str]:
        """
        Derive aspect ratio string from resolution.

        :param resolution: Resolution string, e.g. "1024x1024"
        :return: Aspect ratio string, e.g. "1:1", "3:4", or None if unknown
        """
        try:
            w, h = [int(x) for x in resolution.lower().split("x")]
            # Reduce to small set supported in docs
            ratios = {(1, 1): "1:1", (3, 4): "3:4", (4, 3): "4:3", (9, 16): "9:16", (16, 9): "16:9"}
            # Find nearest
            from math import gcd
            g = gcd(w, h)
            key = (w // g, h // g)
            return ratios.get(key)
        except Exception:
            return None

    def _extract_imagen_bytes(self, generated_image) -> Optional[bytes]:
        """
        Extract bytes from Imagen generated image object.

        :param generated_image: GeneratedImage object
        :return: Image bytes or None
        """
        img = getattr(generated_image, "image", None)
        if not img:
            return None
        data = getattr(img, "image_bytes", None)
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, str):
            try:
                return base64.b64decode(data)
            except Exception:
                return None
        # fallback: url/uri if present
        url = getattr(img, "url", None) or getattr(img, "uri", None)
        if url:
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    return r.content
            except Exception:
                pass
        return None

    def _save(self, idx: int, data: Optional[bytes]) -> Optional[str]:
        """
        Save image bytes to file and return path.

        :param idx: Image index (for filename)
        :param data: Image bytes
        :return: Path string or None
        """
        if not data:
            return None
        name = (
            datetime.date.today().strftime("%Y-%m-%d") + "_" +
            datetime.datetime.now().strftime("%H-%M-%S") + "-" +
            self.window.core.image.make_safe_filename(self.input_prompt) + "-" +
            str(idx + 1) + ".png"
        )
        path = os.path.join(self.window.core.config.get_user_dir("img"), name)
        self.signals.status.emit(trans('img.status.downloading') + f" ({idx + 1} / {self.num}) -> {path}")
        if self.window.core.image.save_image(path, data):
            return path
        return None

    def _cleanup(self):
        """Cleanup resources"""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass