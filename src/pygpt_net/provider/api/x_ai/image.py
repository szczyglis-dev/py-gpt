#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 14:10:00                  #
# ================================================== #

import base64
import datetime
import os
from typing import Optional, Dict, Any, List, Iterable
import mimetypes

import requests
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.types import IMAGE_XAI_AVAILABLE_ASPECT_RATIOS
from pygpt_net.utils import trans

DEFAULT_GROK_IMAGE_MODEL="grok-imagine-image-quality-latest"

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
        Generate image(s) via xAI SDK image API.
        Model: current Grok Imagine image model.

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
        worker.model = (model.id or DEFAULT_GROK_IMAGE_MODEL)
        worker.input_prompt = prompt
        worker.model_prompt = prompt_model
        worker.system_prompt = self.window.core.prompt.get('img')
        worker.raw = self.window.core.config.get('img_raw')
        worker.num = num
        worker.inline = inline
        worker.extra_prompt = extra_prompt
        worker.attachments = context.attachments or {}
        worker.image_id = extra.get("image_id")
        resolution = str(extra.get("resolution") or "").strip().lower()
        if not resolution and self.window.core.config.has('img_resolution'):
            resolution = str(self.window.core.config.get('img_resolution') or "").strip().lower()
        worker.resolution = resolution if resolution in {"1k", "2k"} else None

        aspect_ratio = str(
            extra.get("aspect_ratio")
            or self.window.core.config.get('img.aspect_ratio', 'auto')
            or "auto"
        ).strip().lower()
        worker.aspect_ratio = (
            aspect_ratio if aspect_ratio in IMAGE_XAI_AVAILABLE_ASPECT_RATIOS else "auto"
        )

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
        self.model = DEFAULT_GROK_IMAGE_MODEL
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.extra_prompt: Optional[str] = None
        self.raw = False
        self.num = 1
        self.attachments: Dict[str, Any] = {}
        self.image_id: Optional[str] = None
        self.resolution: Optional[str] = None
        self.aspect_ratio: str = "auto"

        # SDK image_format:
        # - "base64": returns raw image bytes in SDK response (preferred for local saving)
        # - "url": returns URL on xAI managed storage (fallback: we download)
        self.image_format = "base64"

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

            # use xAI SDK client
            client = self.window.core.api.xai.get_client()

            # enforce n range [1..10] as per docs
            n = max(1, min(int(self.num or 1), 10))
            reference_image_url = self._resolve_reference_image_url()
            gen_kwargs = {
                "model": self.model or DEFAULT_GROK_IMAGE_MODEL,
                "prompt": self.input_prompt or "",
                "image_format": ("base64" if self.image_format == "base64" else "url"),
            }
            if reference_image_url:
                gen_kwargs["image_url"] = reference_image_url
            if self.resolution in {"1k", "2k"}:
                gen_kwargs["resolution"] = self.resolution
            if self.aspect_ratio in IMAGE_XAI_AVAILABLE_ASPECT_RATIOS:
                gen_kwargs["aspect_ratio"] = self.aspect_ratio

            images_bytes: List[bytes] = []
            if n == 1:
                resp = client.image.sample(**gen_kwargs)
                images_bytes = self._extract_bytes_from_single(resp)
            else:
                try:
                    resp_iter = client.image.sample_batch(n=n, **gen_kwargs)
                    images_bytes = self._extract_bytes_from_batch(resp_iter)
                except TypeError:
                    # Fallback for SDK variants without sample_batch(image_url=...)
                    if reference_image_url:
                        for _ in range(n):
                            resp = client.image.sample(**gen_kwargs)
                            images_bytes.extend(self._extract_bytes_from_single(resp))
                    else:
                        resp_iter = client.image.sample_batch(n=n, **gen_kwargs)
                        images_bytes = self._extract_bytes_from_batch(resp_iter)

            # save images to files
            paths: List[str] = []
            for i, content in enumerate(images_bytes):
                # generate filename
                name = (
                    datetime.date.today().strftime("%Y-%m-%d") + "_" +
                    datetime.datetime.now().strftime("%H-%M-%S") + "-" +
                    self.window.core.image.make_safe_filename(self.input_prompt) + "-" +
                    str(i + 1) + ".jpg"
                )
                path = os.path.join(self.window.core.filesystem.get_runtime_dir("img", ctx=self.ctx), name)
                self.signals.status.emit(trans('img.status.downloading') + f" ({i + 1} / {len(images_bytes)}) -> {path}")

                if self.window.core.image.save_image(path, content):
                    paths.append(path)

            if not paths:
                raise RuntimeError("xAI image API returned no image data.")

            self._store_image_reference(paths[0])

            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.input_prompt)

        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self._cleanup()

    # ---------- SDK response helpers ----------

    def _extract_bytes_from_single(self, resp) -> List[bytes]:
        """
        Normalize single-image SDK response to a list of bytes.
        Accepts:
        - resp.image -> bytes or base64 str (docs say raw bytes)
        - resp.url -> download
        - dict-like/legacy: {'b64_json': ..., 'url': ...}
        """
        out: List[bytes] = []
        try:
            # preferred path: raw bytes when image_format="base64"
            img_bytes = getattr(resp, "image", None)
            if isinstance(img_bytes, (bytes, bytearray)):
                out.append(bytes(img_bytes))
                return out
            if isinstance(img_bytes, str):
                try:
                    out.append(base64.b64decode(img_bytes))
                    return out
                except Exception:
                    pass

            # url fallback
            url = getattr(resp, "url", None)
            if isinstance(url, str) and url:
                try:
                    r = requests.get(url, timeout=60)
                    if r.status_code == 200:
                        out.append(r.content)
                        return out
                except Exception:
                    pass

            # dict-like fallbacks
            if isinstance(resp, dict):
                if "b64_json" in resp and resp["b64_json"]:
                    try:
                        out.append(base64.b64decode(resp["b64_json"]))
                        return out
                    except Exception:
                        pass
                if "url" in resp and resp["url"]:
                    try:
                        r = requests.get(resp["url"], timeout=60)
                        if r.status_code == 200:
                            out.append(r.content)
                            return out
                    except Exception:
                        pass
        except Exception:
            pass
        return out

    def _extract_bytes_from_batch(self, resp_iter: Iterable) -> List[bytes]:
        """
        Normalize batch SDK response (iterable of images) to a list of bytes.
        Handles item.image (bytes/str), item.url, dict-like or bytes directly.
        """
        out: List[bytes] = []
        if resp_iter is None:
            return out
        try:
            for item in resp_iter:
                # bytes directly
                if isinstance(item, (bytes, bytearray)):
                    out.append(bytes(item))
                    continue

                # preferred: raw bytes in item.image
                img_bytes = getattr(item, "image", None)
                if isinstance(img_bytes, (bytes, bytearray)):
                    out.append(bytes(img_bytes))
                    continue
                if isinstance(img_bytes, str):
                    try:
                        out.append(base64.b64decode(img_bytes))
                        continue
                    except Exception:
                        pass

                # url fallback
                url = getattr(item, "url", None)
                if isinstance(url, str) and url:
                    try:
                        r = requests.get(url, timeout=60)
                        if r.status_code == 200:
                            out.append(r.content)
                            continue
                    except Exception:
                        pass

                # dict-like fallbacks
                if isinstance(item, dict):
                    if "b64_json" in item and item["b64_json"]:
                        try:
                            out.append(base64.b64decode(item["b64_json"]))
                            continue
                        except Exception:
                            pass
                    if "url" in item and item["url"]:
                        try:
                            r = requests.get(item["url"], timeout=60)
                            if r.status_code == 200:
                                out.append(r.content)
                                continue
                        except Exception:
                            pass
        except Exception:
            pass
        return out

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
    def _collect_attachment_paths(self) -> List[str]:
        """Collect local image attachment paths."""
        out: List[str] = []
        for _, att in (self.attachments or {}).items():
            try:
                path = getattr(att, "path", None)
                if path and os.path.exists(path):
                    mime = self._guess_mime(path)
                    if mime.startswith("image/"):
                        out.append(path)
            except Exception:
                continue
        return out

    def _resolve_reference_image_url(self) -> Optional[str]:
        """Resolve explicit image_id or first image attachment into a data URI for xAI image editing."""
        candidate = None
        if isinstance(self.image_id, str) and self.image_id.strip():
            candidate = self.image_id.strip()
        if not candidate:
            paths = self._collect_attachment_paths()
            if paths:
                candidate = paths[0]
        if not candidate:
            return None

        if candidate.startswith("data:image/"):
            return candidate
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return candidate
        if os.path.exists(candidate):
            return self._file_to_data_url(candidate)
        return None

    def _file_to_data_url(self, path: str) -> Optional[str]:
        try:
            with open(path, "rb") as f:
                data = f.read()
            if not data:
                return None
            mime = self._guess_mime(path)
            return f"data:{mime};base64,{base64.b64encode(data).decode('utf-8')}"
        except Exception:
            return None

    def _guess_mime(self, path: str) -> str:
        mime, _ = mimetypes.guess_type(path)
        if mime:
            return mime
        ext = os.path.splitext(str(path).lower())[1]
        if ext in (".jpg", ".jpeg"):
            return "image/jpeg"
        if ext == ".webp":
            return "image/webp"
        if ext in (".gif",):
            return "image/gif"
        return "image/png"

    def _store_image_reference(self, value: Optional[str]) -> None:
        if not value:
            return
        try:
            if not isinstance(self.ctx.extra, dict):
                self.ctx.extra = {}
            self.ctx.extra["image_id"] = self.window.core.filesystem.make_local(str(value), ctx=self.ctx)
            self.window.core.ctx.update_item(self.ctx)
        except Exception:
            pass
