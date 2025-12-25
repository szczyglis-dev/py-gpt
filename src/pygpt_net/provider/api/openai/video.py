#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.25 20:00:00                  #
# ================================================== #

import datetime
import io
import json
import mimetypes
import os
import time
from typing import Optional, Dict, Any, List, Tuple

from openai import OpenAI

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Video:
    """
    OpenAI Sora 2 video generation wrapper.
    """

    MODE_GENERATE = "generate"
    MODE_IMAGE_TO_VIDEO = "image2video"

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
        Generate video(s) using OpenAI Sora 2 API.

        :param context: BridgeContext with prompt, model, attachments
        :param extra: extra parameters (num, inline, aspect_ratio, duration, resolution)
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
        worker.client = self.window.core.api.openai.get_client()  # configured client
        worker.ctx = ctx
        worker.mode = sub_mode
        worker.attachments = attachments
        worker.model = (model.id if model and getattr(model, "id", None) else "sora-2")
        worker.input_prompt = prompt or ""
        worker.model_prompt = prompt_model  # LLM for prompt rewriting
        worker.system_prompt = self.window.core.prompt.get('video')
        worker.raw = self.window.core.config.get('img_raw')
        worker.num = num
        worker.inline = inline

        # optional params (app-level options)
        worker.aspect_ratio = str(extra.get("aspect_ratio") or self.window.core.config.get('video.aspect_ratio') or "16:9")
        worker.duration_seconds = int(extra.get("duration") or self.window.core.config.get('video.duration') or 8)
        worker.resolution = (extra.get("resolution") or self.window.core.config.get('video.resolution') or "720p")

        # Sora limits; one output per job
        worker.max_per_job = 1

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
    """
    Worker that encapsulates Sora 2 async job lifecycle:
    - POST /videos to create job
    - Poll GET /videos/{id} until status=completed or failed
    - GET /videos/{id}/content to download MP4 bytes
    """

    # Allowed MIME types for input_reference per API
    ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = VideoSignals()
        self.window = None
        self.client: Optional[OpenAI] = None
        self.ctx: Optional[CtxItem] = None

        # params
        self.mode = Video.MODE_GENERATE
        self.attachments: Dict[str, Any] = {}
        self.model = "sora-2"
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.raw = False
        self.num = 1

        # video generation params (mapped to Sora API)
        self.aspect_ratio = "16:9"
        self.duration_seconds = 8
        self.resolution: str = "720p"

        # Sora limits
        self.max_per_job = 1

    @Slot()
    def run(self):
        try:
            # Optional prompt enhancement via app default LLM
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

            # Sora API accepts a single video per create call; honor app's num but cap to 1 per job
            _ = max(1, min(self.num, self.max_per_job))

            # Build request parameters
            seconds = self._clamp_seconds(self.duration_seconds)
            size = self._resolve_size(self.aspect_ratio, self.resolution, self.model)

            # Image-to-video: first image attachment as input_reference, must match "size"
            image_path = self._first_image_attachment(self.attachments) if self.mode == Video.MODE_IMAGE_TO_VIDEO else None

            self.signals.status.emit(trans('vid.status.generating') + f": {self.input_prompt}...")

            # Create job
            create_kwargs: Dict[str, Any] = {
                "model": self.model or "sora-2",
                "prompt": self.input_prompt or "",
                "seconds": str(seconds),
                "size": size,
            }

            # Attach image as input_reference; auto-resize to match requested size if needed
            file_handle = None
            if image_path:
                prepared = self._prepare_input_reference(image_path, size)
                if prepared is not None:
                    # tuple (filename, bytes, mime) supported by OpenAI Python SDK
                    create_kwargs["input_reference"] = prepared
                else:
                    # Fallback: use original file (may fail if size/mime mismatch)
                    try:
                        file_handle = open(image_path, "rb")
                        create_kwargs["input_reference"] = file_handle
                    except Exception as e:
                        self.signals.error.emit(e)

            job = self.client.videos.create(**create_kwargs)
            video_id = self._safe_get(job, "id")
            if not video_id:
                # include raw payload for debugging
                raise RuntimeError("Video job ID missing in create response.")

            # Poll until completed (or failed/canceled)
            last_progress = None
            last_status = None
            while True:
                time.sleep(5)
                job = self.client.videos.retrieve(video_id)
                status = self._safe_get(job, "status") or ""
                progress = self._safe_get(job, "progress")

                if status != last_status or (progress is not None and progress != last_progress):
                    try:
                        pr_txt = f" [{int(progress)}%]" if isinstance(progress, (int, float)) else ""
                        self.signals.status.emit(f"{trans('vid.status.generating')} {status}{pr_txt}")
                    except Exception:
                        pass
                    last_progress = progress
                    last_status = status

                if status in ("completed", "failed", "canceled"):
                    break

            if file_handle is not None:
                try:
                    file_handle.close()
                except Exception:
                    pass

            if status != "completed":
                # Extract detailed reason, surface policy hints if present
                reason = self._format_job_error(job)
                if reason:
                    self.signals.status.emit(reason)
                raise RuntimeError(f"Video generation did not complete: {status}. {reason or ''}".strip())

            # Download content
            response = self.client.videos.download_content(video_id=video_id)
            data = response.read()  # bytes stream per OpenAI Python SDK

            # Save file to user video dir
            paths: List[str] = []
            p = self._save(0, data)
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

    @staticmethod
    def _clamp_seconds(requested: int) -> int:
        """
        Clamp duration to Sora allowed values (4, 8, 12).
        """
        allowed = [4, 8, 12]
        try:
            r = int(requested or 8)
        except Exception:
            r = 8
        return min(allowed, key=lambda x: abs(x - r))

    @staticmethod
    def _parse_size(size: str) -> Tuple[int, int]:
        """
        Parse "WxH" string into integers; returns (W, H). Raises ValueError on invalid format.
        """
        parts = str(size or "").lower().split("x")
        if len(parts) != 2:
            raise ValueError(f"Invalid size format: {size}")
        w = int(parts[0].strip())
        h = int(parts[1].strip())
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid size values: {size}")
        return w, h

    @staticmethod
    def _resolve_size(aspect_ratio: str, resolution: str, model_id: str) -> str:
        """
        Map app-level aspect ratio and resolution to Sora size enumerations.
        Supported sizes:
          - sora-2:       1280x720, 720x1280
          - sora-2-pro:   1280x720, 720x1280, 1024x1792, 1792x1024

        Fallback to 1280x720 or 720x1280 depending on orientation.
        """
        ar = (aspect_ratio or "16:9").strip().lower()
        res = (resolution or "720p").lower().strip()
        model = (model_id or "").lower()
        portrait = ar in ("9:16", "9x16", "portrait")

        if "sora-2-pro" in model:
            if "1024" in res or "1792" in res or "hd" in res:
                return "1024x1792" if portrait else "1792x1024"

        return "720x1280" if portrait else "1280x720"

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

    def _prepare_input_reference(self, image_path: str, size: str) -> Optional[Tuple[str, bytes, str]]:
        """
        Ensure the input image matches required WxH and mime. Returns a (filename, bytes, mime) tuple.
        - Converts on the fly using Pillow if dimensions do not match.
        - Strips EXIF metadata and normalizes orientation.
        - Fit mode configurable via `video.image_to_video.fit`: crop | pad | stretch (default crop).
        """
        try:
            w, h = self._parse_size(size)
        except Exception:
            self.signals.status.emit(f"Invalid target size: {size}, using default 1280x720")
            w, h = 1280, 720

        # Try Pillow import lazily
        try:
            from PIL import Image, ImageOps
        except Exception:
            # Fallback: pass original file; may still fail if size mismatches.
            try:
                with open(image_path, "rb") as f:
                    data = f.read()
                mime = (mimetypes.guess_type(image_path)[0] or "image/jpeg")
                if mime not in self.ALLOWED_MIME:
                    mime = "image/jpeg"
                filename = os.path.basename(image_path)
                return filename, data, mime
            except Exception:
                return None

        try:
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img)  # honor EXIF orientation

            # If already exact size and mime allowed -> pass-through with re-encode to strip EXIF
            if img.width == w and img.height == h:
                buf = io.BytesIO()
                # choose output mime based on original extension but restrict to allowed set
                target_mime = (mimetypes.guess_type(image_path)[0] or "image/jpeg")
                if target_mime not in self.ALLOWED_MIME:
                    target_mime = "image/jpeg"

                fmt = "WEBP" if target_mime == "image/webp" else "PNG" if target_mime == "image/png" else "JPEG"
                if fmt == "JPEG" and img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                save_kwargs = {"optimize": True}
                if fmt == "JPEG":
                    save_kwargs.update({"quality": 95})
                img.save(buf, format=fmt, **save_kwargs)
                data = buf.getvalue()
                buf.close()
                filename = os.path.basename(image_path) if fmt != "JPEG" else "input.jpg"
                return filename, data, target_mime

            fit_mode = str(self.window.core.config.get('video.image_to_video.fit') or "crop").lower()
            if fit_mode not in ("crop", "pad", "stretch"):
                fit_mode = "crop"

            # Convert to RGB for JPEG output by default
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            if fit_mode == "stretch":
                resized = img.resize((w, h), Image.Resampling.LANCZOS)
            elif fit_mode == "pad":
                scale = min(w / img.width, h / img.height)
                new_w = max(1, int(img.width * scale))
                new_h = max(1, int(img.height * scale))
                tmp = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (w, h), color=(0, 0, 0))
                left = (w - new_w) // 2
                top = (h - new_h) // 2
                canvas.paste(tmp, (left, top))
                resized = canvas
            else:  # crop (fill then center-crop)
                scale = max(w / img.width, h / img.height)
                new_w = max(1, int(img.width * scale))
                new_h = max(1, int(img.height * scale))
                tmp = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left = max(0, (new_w - w) // 2)
                top = max(0, (new_h - h) // 2)
                resized = tmp.crop((left, top, left + w, top + h))

            # Encode as JPEG (safe default per API)
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=95, optimize=True)
            data = buf.getvalue()
            buf.close()

            self.signals.status.emit(f"Auto-resized input image to {w}x{h} (mode={fit_mode}).")
            return "input.jpg", data, "image/jpeg"

        except Exception:
            # As a last resort, send original image
            try:
                with open(image_path, "rb") as f:
                    data = f.read()
                mime = (mimetypes.guess_type(image_path)[0] or "image/jpeg")
                if mime not in self.ALLOWED_MIME:
                    mime = "image/jpeg"
                filename = os.path.basename(image_path)
                self.signals.status.emit("Image preprocessing failed; sending original file (may fail if size/policy mismatch).")
                return filename, data, mime
            except Exception:
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
        self.signals.status.emit(trans('vid.status.downloading') + f" ({idx + 1} / 1) -> {path}")

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

    # ---------- error utilities ----------

    @staticmethod
    def _safe_get(obj: Any, key: str, default=None):
        """
        Access attribute or dict key safely.
        """
        try:
            if isinstance(obj, dict):
                return obj.get(key, default)
            if hasattr(obj, key):
                return getattr(obj, key)
        except Exception:
            return default
        return default

    def _format_job_error(self, job: Any) -> str:
        """
        Build a human-readable error message from the video job.
        Includes error.message/type/code and common policy hints.
        """
        # Extract error payload
        err = self._safe_get(job, "error")
        details: Dict[str, Any] = {}
        message = ""
        code = ""
        etype = ""

        # Normalize to dict
        if err is not None:
            try:
                if isinstance(err, dict):
                    details = err
                elif hasattr(err, "model_dump"):
                    details = err.model_dump()  # pydantic v2
                elif hasattr(err, "to_dict"):
                    details = err.to_dict()
                else:
                    # last resort string
                    message = str(err)
            except Exception:
                message = str(err)

        message = details.get("message", message) if isinstance(details, dict) else message
        code = details.get("code", code) if isinstance(details, dict) else code
        etype = details.get("type", etype) if isinstance(details, dict) else etype

        # Policy-related hints
        hint = ""
        lower = (message or "").lower()
        if any(x in lower for x in ("public figure", "likeness", "real person", "people", "face", "biometric")):
            hint = "Policy: input images with real people or public figures are blocked. Use a non-real/persona or generated image."
        elif any(x in lower for x in ("copyright", "trademark", "brand", "ip infringement")):
            hint = "Policy: potential IP restriction detected. Avoid brand logos or copyrighted assets."
        elif "inpaint" in lower and "width and height" in lower:
            hint = "The reference image must exactly match the requested size (size=WxH). The app auto-resizes now; verify your aspect and chosen model allow this size."

        parts = []
        if message:
            parts.append(f"reason: {message}")
        if etype:
            parts.append(f"type: {etype}")
        if code:
            parts.append(f"code: {code}")
        if hint:
            parts.append(hint)

        # Include minimal structured fallback if nothing above was present
        if not parts and isinstance(details, dict) and details:
            try:
                parts.append(json.dumps(details, ensure_ascii=False))
            except Exception:
                pass

        return " ".join(parts).strip()