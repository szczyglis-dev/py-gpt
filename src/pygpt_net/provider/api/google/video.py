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
        video_id = extra.get("video_id")
        extra_prompt = extra.get("extra_prompt", "")

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
        worker.extra_prompt = extra_prompt
        worker.video_id = video_id

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
        self.extra_prompt: Optional[str] = None
        self.video_id = None
        self.raw = False
        self.num = 1

        # video generation params
        self.aspect_ratio = "16:9"
        self.duration_seconds = 8
        self.fps = 24
        self.seed: Optional[int] = None
        self.generate_audio: bool = False  # generation includes audio by default on Veo 3.x
        self.resolution: str = "720p"      # Veo supports 720p/1080p depending on variant

        # limits / capabilities
        self.veo_max_num = 1  # limit to 1 in Gemini API

        # fallbacks
        self.DEFAULT_VEO_MODEL = "veo-3.0-generate-001"

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

            # prepare config
            num = min(self.num, self.veo_max_num)
            cfg_kwargs = {
                "number_of_videos": num,
            }

            # normalize and set aspect ratio
            ar = self._normalize_aspect_ratio(self.aspect_ratio)
            if ar:
                cfg_kwargs["aspect_ratio"] = ar

            # normalize and set resolution if supported
            res = self._normalize_resolution(self.resolution)
            if res:
                cfg_kwargs["resolution"] = res

            # set optional controls
            if self.seed is not None:
                cfg_kwargs["seed"] = int(self.seed)
            if self.extra_prompt:
                cfg_kwargs["negative_prompt"] = self.extra_prompt

            # set durationSeconds when supported; fall back gracefully if rejected by model
            cfg_try = dict(cfg_kwargs)
            cfg_try["duration_seconds"] = int(self._duration_for_model(self.model, self.duration_seconds))

            # remix / extension: if video_id provided, prefer video-to-video path
            is_remix = bool(self.video_id)
            if is_remix:
                # Veo extension support varies by API and model; choose a compatible model if needed
                model_for_ext = self._select_extension_model(self.model)
                if model_for_ext != self.model:
                    self.signals.status.emit(f"Please switch model for extension: {self.model} -> {model_for_ext}")
                    # self.model = model_for_ext # <-- do not override user selection, just inform

                # Build video input from identifier (URI, files/<id>, http(s), gs://, or local path)
                video_input = self._video_from_identifier(self.video_id)
                if not video_input:
                    raise RuntimeError("Invalid video_id for remix/extension. Provide a valid URI, file name, or local path.")

                # Minimal config for extension to avoid server-side rejections
                ext_config = gtypes.GenerateVideosConfig(number_of_videos=1)
                # Pass negative prompt to extension when provided
                if self.extra_prompt:
                    ext_config.negative_prompt = self.extra_prompt  # supported in python-genai

                label = trans('vid.status.generating') + " (remix)"
                self.signals.status.emit(label + f": {self.input_prompt or ''}...")

                # Start operation: video extension, prompt optional
                operation = self.client.models.generate_videos(
                    model=self.model or self.DEFAULT_VEO_MODEL,
                    prompt=self.input_prompt or "",
                    video=video_input,
                    config=ext_config,
                )

                # poll until done
                while not getattr(operation, "done", False):
                    if kernel.stopped():
                        break
                    time.sleep(10)
                    if kernel.stopped():
                        break
                    operation = self.client.operations.get(operation)

                # extract response payload
                op_resp = getattr(operation, "response", None) or getattr(operation, "result", None)
                if not op_resp:
                    raise RuntimeError("Empty operation response.")

                gen_list = getattr(op_resp, "generated_videos", None) or []
                if not gen_list:
                    raise RuntimeError("No videos generated.")

                # store remote reference for next remix calls (URI/name) in ctx
                self._store_video_reference(gen_list[0])

                # download and save
                paths: List[str] = []
                for idx, gv in enumerate(gen_list[:1]):
                    data = self._download_video_bytes(getattr(gv, "video", None))
                    p = self._save(idx, data)
                    if p:
                        paths.append(p)

                if self.inline:
                    self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
                else:
                    self.signals.finished.emit(self.ctx, paths, self.input_prompt)
                return  # remix path completed

            # normal generation path (text-to-video or image-to-video)
            self.signals.status.emit(trans('vid.status.generating') + f": {self.input_prompt}...")

            try:
                config = gtypes.GenerateVideosConfig(**cfg_try)
                operation = self.client.models.generate_videos(
                    model=self.model or self.DEFAULT_VEO_MODEL,
                    prompt=self.input_prompt or "",
                    config=config,
                    image=self._image_part_if_needed(),
                    video=None,
                )
            except Exception as e:
                if "durationSeconds isn't supported" in str(e) or "Unrecognized" in str(e):
                    # retry without duration_seconds
                    config = gtypes.GenerateVideosConfig(**cfg_kwargs)
                    operation = self.client.models.generate_videos(
                        model=self.model or self.DEFAULT_VEO_MODEL,
                        prompt=self.input_prompt or "",
                        config=config,
                        image=self._image_part_if_needed(),
                        video=None,
                    )
                else:
                    raise

            # poll until done
            while not getattr(operation, "done", False):
                if kernel.stopped():
                    break
                time.sleep(10)
                if kernel.stopped():
                    break
                operation = self.client.operations.get(operation)

            # extract response payload
            op_resp = getattr(operation, "response", None) or getattr(operation, "result", None)
            if not op_resp:
                raise RuntimeError("Empty operation response.")

            gen_list = getattr(op_resp, "generated_videos", None) or []
            if not gen_list:
                raise RuntimeError("No videos generated.")

            # store remote reference for potential future remix/extension
            self._store_video_reference(gen_list[0])

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

    def _normalize_aspect_ratio(self, ar: str) -> str:
        """Normalize aspect ratio to Veo-supported values."""
        val = (ar or "").strip()
        return val if val in ("16:9", "9:16") else "16:9"

    def _normalize_resolution(self, res: str) -> Optional[str]:
        """Normalize resolution to '720p' or '1080p'."""
        val = (res or "").lower().replace(" ", "")
        if val in ("720p", "1080p"):
            return val
        if val in ("1280x720", "720x1280"):
            return "720p"
        if val in ("1920x1080", "1080x1920"):
            return "1080p"
        return None

    def _is_veo3(self, model_id: str) -> bool:
        mid = str(model_id or "").lower()
        return mid.startswith("veo-3.")

    def _supports_image_to_video(self, model_id: str) -> bool:
        """Return True if the model supports image->video."""
        mid = str(model_id or "").lower()
        return any(p in mid for p in (
            "veo-2.0",
            "veo-3.0-generate",
            "veo-3.0-fast-generate",
            "veo-3.1-generate",
            "veo-3.1-fast-generate",
        ))

    def _duration_for_model(self, model_id: str, requested: int) -> int:
        """Adjust duration constraints to model-specific limits."""
        mid = str(model_id or "").lower()
        if "veo-2.0" in mid:
            return max(5, min(8, int(requested or 8)))
        if "veo-3.1" in mid:
            return max(4, min(8, int(requested or 8)))
        if "veo-3.0" in mid:
            return max(4, min(8, int(requested or 8)))
        return int(requested or 8)

    def _image_part_if_needed(self) -> Optional[gtypes.Image]:
        """Return Image part when in image-to-video mode and supported."""
        if self.mode != Video.MODE_IMAGE_TO_VIDEO:
            return None
        base_img = self._first_image_attachment(self.attachments)
        return gtypes.Image.from_file(location=base_img) if base_img else None

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

    def _video_from_identifier(self, identifier: str) -> Optional[gtypes.Video]:
        """
        Build a Video object from a generic identifier:
        - Local file path -> upload via types.Video.from_file
        - files/<id> -> resolve to URI using Files API
        - http(s) or gs:// URI -> pass-through
        """
        try:
            if not identifier:
                return None
            ident = str(identifier).strip()

            # Local path
            if os.path.exists(ident):
                return gtypes.Video.from_file(ident)

            # Files API name
            if ident.startswith("files/"):
                try:
                    f = self.client.files.get(name=ident)
                    uri = getattr(f, "uri", None)
                    if uri:
                        return gtypes.Video(uri=uri)
                except Exception:
                    pass

            # Generic URI (Gemini accepts URIs, Vertex expects GCS; SDK honors both via uri field)
            if ident.startswith("http://") or ident.startswith("https://") or ident.startswith("gs://"):
                return gtypes.Video(uri=ident)
        except Exception:
            return None
        return None

    def _select_extension_model(self, model_id: str) -> str:
        """
        Choose a compatible model for video extension:
        - Gemini API: Veo 3.1 only supports extension
        - Vertex AI: extension supported on Veo 2.0
        """
        mid = str(model_id or "").lower()
        use_vertex = bool(getattr(self.client, "vertexai", False))

        # Gemini Developer API path
        if not use_vertex:
            if "veo-3.1" in mid:
                return model_id
            # Prefer 3.1 preview if user selected older Veo
            return "veo-3.1-generate-preview"

        # Vertex AI path
        if "veo-2.0" in mid:
            return model_id
        return "veo-2.0-generate-001"

    def _store_video_reference(self, generated_video_item: Any) -> None:
        """
        Persist a reusable video reference (URI or name) to ctx.extra['video_id'] for future remix/extension calls.
        """
        try:
            vref = getattr(generated_video_item, "video", None)
            if not vref:
                return
            # Prefer URI, fallback to name
            uri = getattr(vref, "uri", None) or getattr(vref, "download_uri", None)
            name = getattr(vref, "name", None)
            ref = uri or name
            if not ref:
                return

            if not isinstance(self.ctx.extra, dict):
                self.ctx.extra = {}
            self.ctx.extra["video_id"] = ref
            self.window.core.ctx.update_item(self.ctx)
        except Exception:
            pass

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