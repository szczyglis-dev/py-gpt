#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.01 23:00:00                  #
# ================================================== #

import base64, datetime, os, requests
import mimetypes
import time

from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types as gtypes

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Video:

    MODE_GENERATE = "generate"
    MODE_IMAGE_TO_VIDEO = "image2video"

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
        Generate video(s) using Google GenAI Veo.

        :param context: BridgeContext with prompt, model, attachments
        :param extra: extra parameters (num, inline, duration, aspect_ratio)
        :param sync: run synchronously (blocking) if True
        :return: True if started
        """
        extra = extra or {}
        ctx = context.ctx or CtxItem()
        model = context.model
        prompt = context.prompt
        num = int(extra.get("num", 1))
        inline = bool(extra.get("inline", False))

        # decide sub-mode based on attachments (image-to-video when image is attached)
        sub_mode = self.MODE_GENERATE
        attachments = context.attachments or {}
        if self._has_image_attachment(attachments):
            sub_mode = self.MODE_IMAGE_TO_VIDEO

        # model used to improve the prompt (not video model)
        prompt_model = self.window.core.models.from_defaults()
        tmp = self.window.core.config.get('video.prompt_model')
        if self.window.core.models.has(tmp):
            prompt_model = self.window.core.models.get(tmp)

        worker = VideoWorker()
        worker.window = self.window
        worker.client = self.window.core.api.google.get_client()
        worker.ctx = ctx
        worker.mode = sub_mode
        worker.attachments = attachments
        worker.model = model.id  # Veo model id
        worker.input_prompt = prompt
        worker.model_prompt = prompt_model  # LLM for prompt rewriting
        worker.system_prompt = self.window.core.prompt.get('video')
        worker.raw = self.window.core.config.get('img_raw')
        worker.num = num
        worker.inline = inline

        # optional params
        worker.aspect_ratio = str(extra.get("aspect_ratio") or self.window.core.config.get('video.aspect_ratio') or "16:9")
        worker.duration_seconds = int(extra.get("duration") or self.window.core.config.get('video.duration') or 8)
        worker.fps = int(extra.get("fps") or self.window.core.config.get('video.fps') or 24)
        worker.seed = extra.get("seed") or self.window.core.config.get('video.seed') or None
        worker.negative_prompt = extra.get("negative_prompt") or self.window.core.config.get('video.negative_prompt') or None
        worker.generate_audio = bool(extra.get("generate_audio", self.window.core.config.get('video.generate_audio') or False))
        worker.resolution = (extra.get("resolution") or self.window.core.config.get('video.resolution') or "720p")

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

    def _has_image_attachment(self, attachments: Dict[str, Any]) -> bool:
        """Check if at least one image attachment is present."""
        for _, att in (attachments or {}).items():
            try:
                p = getattr(att, "path", None)
                if p and os.path.exists(p):
                    mt, _ = mimetypes.guess_type(p)
                    if mt and mt.startswith("image/"):
                        return True
            except Exception:
                continue
        return False


class VideoSignals(QObject):
    finished = Signal(object, list, str)         # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object)                      # message
    error = Signal(object)                       # exception


class VideoWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = VideoSignals()
        self.window = None
        self.client: Optional[genai.Client] = None
        self.ctx: Optional[CtxItem] = None

        # params
        self.mode = Video.MODE_GENERATE
        self.attachments: Dict[str, Any] = {}
        self.model = "veo-3.0-generate-001"
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.raw = False
        self.num = 1

        # video generation params
        self.aspect_ratio = "16:9"
        self.duration_seconds = 8
        self.fps = 24
        self.seed: Optional[int] = None
        self.negative_prompt: Optional[str] = None
        self.generate_audio: bool = False  # Veo 3 only
        self.resolution: str = "720p"      # Veo 3 supports 720p/1080p

        # limits / capabilities
        # self.veo_max_num = 4  # Veo returns up to 4 videos
        self.veo_max_num = 1  # limit to 1 in Gemini API

        # fallbacks
        self.DEFAULT_VEO_MODEL = "veo-3.0-generate-001"

    @Slot()
    def run(self):
        try:
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

            # prepare config
            num = min(self.num, self.veo_max_num)
            cfg_kwargs = {
                "number_of_videos": num,
                #"duration_seconds": self._duration_for_model(self.model, self.duration_seconds),
            }
            if self.aspect_ratio:
                cfg_kwargs["aspect_ratio"] = self.aspect_ratio
            if self.seed is not None:
                cfg_kwargs["seed"] = int(self.seed)
            if self.negative_prompt:
                cfg_kwargs["negative_prompt"] = self.negative_prompt
            if self._is_veo3(self.model):
                # Veo 3 supports audio and resolution
                # WARN: but not Gemini API:
                pass
                """             
                cfg_kwargs["generate_audio"] = bool(self.generate_audio)   
                if self.resolution:
                    cfg_kwargs["resolution"] = self.resolution
                """

            config = gtypes.GenerateVideosConfig(**cfg_kwargs)

            # build request
            req_kwargs = {
                "model": self.model or self.DEFAULT_VEO_MODEL,
                "prompt": self.input_prompt or "",
                "config": config,
            }

            # image-to-video if an image attachment is present and supported
            base_img = self._first_image_attachment(self.attachments)
            if self.mode == Video.MODE_IMAGE_TO_VIDEO and base_img is not None and self._supports_image_to_video(self.model):
                req_kwargs["image"] = gtypes.Image.from_file(location=base_img)

            self.signals.status.emit(trans('vid.status.generating') + f": {self.input_prompt}...")

            # start long-running operation
            operation = self.client.models.generate_videos(**req_kwargs)

            # poll until done
            while not getattr(operation, "done", False):
                time.sleep(10)
                operation = self.client.operations.get(operation)

            # extract response payload
            op_resp = getattr(operation, "response", None) or getattr(operation, "result", None)
            if not op_resp:
                raise RuntimeError("Empty operation response.")

            gen_list = getattr(op_resp, "generated_videos", None) or []
            if not gen_list:
                raise RuntimeError("No videos generated.")

            # download and save all outputs up to num
            paths: List[str] = []
            for idx, gv in enumerate(gen_list[:num]):
                data = self._download_video_bytes(getattr(gv, "video", None))
                p = self._save(idx, data)
                if p:
                    paths.append(p)

            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.input_prompt)

        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self._cleanup()

    # ---------- helpers ----------

    def _is_veo3(self, model_id: str) -> bool:
        mid = str(model_id or "").lower()
        return mid.startswith("veo-3.")

    def _supports_image_to_video(self, model_id: str) -> bool:
        """Return True if the model supports image->video."""
        mid = str(model_id or "").lower()
        # Official support for image-to-video on veo-2 and veo-3 preview; keep extendable.
        return ("veo-2.0" in mid) or ("veo-3.0-generate-preview" in mid) or ("veo-3.0-fast-generate-preview" in mid)

    def _duration_for_model(self, model_id: str, requested: int) -> int:
        """Adjust duration constraints to model-specific limits."""
        mid = str(model_id or "").lower()
        if "veo-2.0" in mid:
            # Veo 2 supports 5–8s, default 8s.
            return max(5, min(8, int(requested or 8)))
        if "veo-3.0" in mid:
            # Veo 3 commonly uses 8s clips; honor request if provided, otherwise 8s.
            return int(requested or 8)
        return int(requested or 8)

    def _first_image_attachment(self, attachments: Dict[str, Any]) -> Optional[str]:
        """Return path of the first image attachment, if any."""
        for _, att in (attachments or {}).items():
            try:
                p = getattr(att, "path", None)
                if p and os.path.exists(p):
                    mt, _ = mimetypes.guess_type(p)
                    if mt and mt.startswith("image/"):
                        return p
            except Exception:
                continue
        return None

    def _download_video_bytes(self, file_ref) -> Optional[bytes]:
        """
        Download video bytes using the Files service.
        Falls back to direct URL download if necessary.
        """
        if not file_ref:
            return None

        # Preferred: SDK-managed download (handles URIs and sets video_bytes).
        try:
            data = self.client.files.download(file=file_ref)
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        except Exception:
            pass

        # Fallback: try to fetch by uri or url.
        uri = getattr(file_ref, "uri", None) or getattr(file_ref, "url", None) or getattr(file_ref, "download_uri", None)
        if uri:
            try:
                r = requests.get(uri, timeout=120)
                if r.status_code == 200:
                    return r.content
            except Exception:
                pass

        # Last resort: try inline/base64 if present.
        b64 = getattr(file_ref, "video_bytes", None)
        if isinstance(b64, (bytes, bytearray)):
            return bytes(b64)
        if isinstance(b64, str):
            try:
                return base64.b64decode(b64)
            except Exception:
                return None
        return None

    def _save(self, idx: int, data: Optional[bytes]) -> Optional[str]:
        """Save video bytes to file and return path."""
        if not data:
            return None
        name = (
            datetime.date.today().strftime("%Y-%m-%d") + "_" +
            datetime.datetime.now().strftime("%H-%M-%S") + "-" +
            self.window.core.video.make_safe_filename(self.input_prompt) + "-" +
            str(idx + 1) + ".mp4"
        )
        path = os.path.join(self.window.core.config.get_user_dir("video"), name)
        self.signals.status.emit(trans('vid.status.downloading') + f" ({idx + 1} / {self.num}) -> {path}")

        if self.window.core.video.save_video(path, data):
            return str(path)

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            return str(path)
        except Exception:
            return None

    def _cleanup(self):
        """Cleanup resources."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass