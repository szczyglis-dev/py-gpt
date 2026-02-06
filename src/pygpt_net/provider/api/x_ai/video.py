#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.02.06 03.00:00                  #
# ================================================== #

import base64
import datetime
import mimetypes
import os
import time
from typing import Optional, Dict, Any, List

import requests
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Video:
    """
    xAI Grok Imagine video generation wrapper.
    Uses xai_sdk Client.video.generate(...) with automatic polling.
    """

    def __init__(self, window=None):
        self.window = window
        self.worker: Optional[VideoWorker] = None

    def generate(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            sync: bool = True,
    ) -> bool:
        """
        Generate video(s) using xAI Video API.

        :param context: BridgeContext with prompt, model, attachments
        :param extra: extra parameters:
                      - num: int number of outputs (sequential; API returns one per call)
                      - inline: bool – if True, emit finished_inline signal
                      - aspect_ratio: str, e.g. "16:9", "9:16", "1:1"
                      - duration: int seconds (1..15) for generation (not for edits)
                      - resolution: str ("720p" or "480p")
                      - image_url: optional remote URL (image-to-video)
                      - video_url: optional remote URL (edit mode)
                      - video_id: optional reference for remix/edit (URL or identifier)
                      - extra_prompt: optional negative or constraint text to append
        :param sync: run synchronously (blocking) if True
        :return: True if started
        """
        extra = extra or {}
        ctx = context.ctx or CtxItem()
        model = context.model
        prompt = context.prompt or ""
        num = int(extra.get("num", 1))
        inline = bool(extra.get("inline", False))
        video_id = extra.get("video_id")  # previous video reference (URL or id)
        video_url = extra.get("video_url")
        override_image_url = extra.get("image_url")
        extra_prompt = extra.get("extra_prompt", "")

        # prompt enhancement model (same approach as images)
        prompt_model = self.window.core.models.from_defaults()
        tmp = self.window.core.config.get('video.prompt_model')
        if self.window.core.models.has(tmp):
            prompt_model = self.window.core.models.get(tmp)

        worker = VideoWorker()
        worker.window = self.window
        worker.ctx = ctx
        worker.client = self.window.core.api.xai.get_client()  # configured xAI client
        worker.model = (model.id if model and getattr(model, "id", None) else "grok-imagine-video")
        worker.input_prompt = prompt
        worker.model_prompt = prompt_model
        worker.system_prompt = self.window.core.prompt.get('video')
        worker.raw = self.window.core.config.get('img_raw')  # keep same flag as images
        worker.num = max(1, int(num))
        worker.inline = inline
        worker.extra_prompt = extra_prompt
        worker.attachments = context.attachments or {}
        worker.override_image_url = override_image_url
        # remix/edit reference: prefer explicit video_id from UI; fallback to explicit video_url if provided
        worker.video_id = video_id
        worker.edit_video_url = video_url

        # output controls (defaults come from config if not supplied)
        worker.aspect_ratio = str(extra.get("aspect_ratio") or self.window.core.config.get('video.aspect_ratio') or "16:9")
        worker.duration = int(extra.get("duration") or self.window.core.config.get('video.duration') or 6)
        worker.resolution = str(extra.get("resolution") or self.window.core.config.get('video.resolution') or "720p")

        self.worker = worker
        self.worker.signals.finished.connect(self.window.core.video.handle_finished)
        self.worker.signals.finished_inline.connect(self.window.core.video.handle_finished_inline)
        self.worker.signals.status.connect(self.window.core.video.handle_status)
        self.worker.signals.error.connect(self.window.core.video.handle_error)

        if sync or not self.window.controller.kernel.async_allowed(ctx):
            self.worker.run()
            return True

        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {"id": "video"}))
        self.window.threadpool.start(self.worker)
        return True


class VideoSignals(QObject):
    finished = Signal(object, list, str)         # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object)                      # message
    error = Signal(object)                       # exception


class VideoWorker(QRunnable):
    """
    Worker that encapsulates xAI video job lifecycle with auto-polling via SDK:
    - client.video.generate(...) blocks until result or failure
    - response contains .url and optional metadata
    """

    # Allowed MIME types for inlined image data URI
    ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = VideoSignals()
        self.window = None
        self.client = None
        self.ctx: Optional[CtxItem] = None

        # params
        self.model = "grok-imagine-video"
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.extra_prompt: Optional[str] = None
        self.raw = False
        self.num = 1

        # generation/edit inputs
        self.attachments: Dict[str, Any] = {}
        self.override_image_url: Optional[str] = None
        self.video_id: Optional[str] = None
        self.edit_video_url: Optional[str] = None

        # output controls
        self.aspect_ratio: str = "16:9"
        self.duration: int = 6
        self.resolution: str = "720p"

    @Slot()
    def run(self):
        try:
            kernel = self.window.controller.kernel

            # optional prompt enhancement
            if not self.raw and not self.inline and self.input_prompt:
                try:
                    self.signals.status.emit(trans('vid.status.prompt.wait'))
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
                    self.signals.status.emit(trans('vid.status.prompt.error') + ": " + str(e))

            # Negative prompt merge (provider has no dedicated field)
            if self.extra_prompt and str(self.extra_prompt).strip():
                try:
                    self.input_prompt = self._merge_negative_prompt(self.input_prompt, self.extra_prompt)
                except Exception:
                    pass

            # resolve generation mode: edit (video_id/video_url) > image2video > text2video
            image_url = self._resolve_image_url()
            video_url = self._resolve_video_url()  # may come from explicit video_url or video_id
            if video_url and not (str(video_url).startswith("http://") or str(video_url).startswith("https://")):
                # xAI edit requires a publicly accessible video_url; local paths are unsupported
                self.signals.status.emit("xAI video edit requires a publicly accessible video_url; provided identifier is not a URL. Skipping edit path.")
                video_url = None

            # normalize controls
            duration = self._clamp_duration(self.duration, is_edit=bool(video_url))
            aspect_ratio = self._normalize_aspect_ratio(self.aspect_ratio)
            resolution = self._normalize_resolution(self.resolution)

            # status
            label = trans('vid.status.generating')
            if video_url:
                label += " (edit)"
            elif image_url:
                label += " (image-to-video)"
            else:
                label += " (text-to-video)"
            self.signals.status.emit(label + f": {self.input_prompt}...")

            # sequential jobs (API returns single URL per call)
            paths: List[str] = []
            for i in range(max(1, self.num)):
                if kernel.stopped():
                    break

                # Build kwargs: omit duration for edits per docs
                gen_kwargs: Dict[str, Any] = {
                    "prompt": self.input_prompt or "",
                    "model": self.model or "grok-imagine-video",
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                }
                if not video_url:
                    gen_kwargs["duration"] = duration
                if image_url:
                    gen_kwargs["image_url"] = image_url
                if video_url:
                    gen_kwargs["video_url"] = video_url

                resp = self.client.video.generate(**gen_kwargs)
                url = getattr(resp, "url", None) or (resp.get("url") if isinstance(resp, dict) else None)
                if not isinstance(url, str) or not url.strip():
                    raise RuntimeError("xAI video API returned no URL.")

                # persist reference for future remix/edit in ctx.extra['video_id']
                self._store_video_reference(url)

                # download to file
                path = self._download_video(url, i)
                if path:
                    paths.append(path)

                # small delay between sequential jobs to avoid rate spikes
                if i + 1 < self.num and not kernel.stopped():
                    time.sleep(0.2)

            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.input_prompt)

        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self._cleanup()

    # ---------- inputs resolution ----------

    def _resolve_image_url(self) -> Optional[str]:
        """
        Determine image_url to send:
        - if override_image_url provided, use it
        - else first image attachment as data URI (data:image/*;base64,...)
        """
        if isinstance(self.override_image_url, str) and self.override_image_url.strip():
            return self.override_image_url.strip()

        for _, att in (self.attachments or {}).items():
            try:
                p = getattr(att, "path", None)
                if not (p and os.path.exists(p)):
                    continue
                mt, _ = mimetypes.guess_type(p)
                if not (mt and mt.startswith("image/")):
                    continue
                # inline as data URI to avoid requiring a public host
                if mt not in self.ALLOWED_IMAGE_MIME:
                    mt = "image/jpeg"
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mt};base64,{b64}"
            except Exception:
                continue
        return None

    def _resolve_video_url(self) -> Optional[str]:
        """
        Return remote video_url for edit mode.
        Accepts explicit edit_video_url or a cross-provider 'video_id' value when it is a URL.
        """
        if isinstance(self.video_id, str) and (self.video_id.startswith("http://") or self.video_id.startswith("https://")):
            return self.video_id
        # Also try to use last stored ctx.extra['video_id'] when present and a URL
        try:
            if isinstance(self.ctx.extra, dict):
                ref = self.ctx.extra.get("video_id")
                if isinstance(ref, str) and (ref.startswith("http://") or ref.startswith("https://")):
                    return ref
        except Exception:
            pass
        return None

    # ---------- normalization ----------

    @staticmethod
    def _clamp_duration(val: int, is_edit: bool) -> int:
        """
        Clamp to SDK/Docs range [1..15]. Edits ignore user-specified duration.
        """
        if is_edit:
            return 0
        try:
            d = int(val or 6)
        except Exception:
            d = 6
        if d < 1:
            d = 1
        if d > 15:
            d = 15
        return d

    @staticmethod
    def _normalize_aspect_ratio(val: str) -> str:
        """
        Normalize arbitrary inputs to supported set: 16:9, 4:3, 1:1, 9:16, 3:4, 3:2, 2:3.
        """
        s = (val or "16:9").strip().lower()
        mapping = {
            "portrait": "9:16",
            "vertical": "9:16",
            "landscape": "16:9",
            "square": "1:1",
            "1x1": "1:1",
            "4x3": "4:3",
            "3x4": "3:4",
            "3x2": "3:2",
            "2x3": "2:3",
            "16x9": "16:9",
            "9x16": "9:16",
        }
        if s in mapping:
            return mapping[s]
        allowed = {"16:9", "4:3", "1:1", "9:16", "3:4", "3:2", "2:3"}
        return s if s in allowed else "16:9"

    @staticmethod
    def _normalize_resolution(val: str) -> str:
        """
        Supported resolutions: 720p, 480p.
        """
        s = (val or "720p").strip().lower()
        return "480p" if s.startswith("480") else "720p"

    # ---------- IO ----------

    def _download_video(self, url: str, idx: int) -> Optional[str]:
        """
        Download video from URL to user video dir and return path.
        """
        name = (
            datetime.date.today().strftime("%Y-%m-%d") + "_" +
            datetime.datetime.now().strftime("%H-%M-%S") + "-" +
            self.window.core.video.make_safe_filename(self.input_prompt) + "-" +
            str(idx + 1) + ".mp4"
        )
        path = os.path.join(self.window.core.config.get_user_dir("video"), name)
        self.signals.status.emit(trans('vid.status.downloading') + f" ({idx + 1}) -> {path}")

        try:
            with requests.get(url, stream=True, timeout=180) as r:
                r.raise_for_status()
                saved = self.window.core.video.save_video(path, r.content)
                if saved:
                    return path
                # fallback manual write
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return path
        except Exception:
            return None

    def _store_video_reference(self, url: str) -> None:
        """
        Store a reusable video reference for future remix/edit.
        """
        try:
            if not url or not isinstance(url, str):
                return
            if not isinstance(self.ctx.extra, dict):
                self.ctx.extra = {}
            # keep unified key 'video_id' across providers; value is the public URL returned by xAI
            self.ctx.extra["video_id"] = self.window.core.filesystem.make_local(url)
            self.window.core.ctx.update_item(self.ctx)
        except Exception:
            pass

    def _cleanup(self):
        """Cleanup signals."""
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