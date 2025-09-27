#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 00:00:00                  #
# ================================================== #

import mimetypes
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
        Generate or edit image(s) using Google GenAI API (Developer API or Vertex AI).

        :param context: BridgeContext with prompt, model, attachments
        :param extra: extra parameters (num, inline)
        :param sync: run synchronously (blocking) if True
        :return: True if started
        """
        # Music fast-path: delegate to Music flow if a music model is selected (e.g., Lyria).
        # This keeps image flow unchanged while enabling music in the same "image" mode.
        try:
            model_id = (context.model.id if context and context.model else "") or ""
            if self.window and hasattr(self.window.core.api.google, "music"):
                if self.window.core.api.google.music.is_music_model(model_id):
                    return self.window.core.api.google.music.generate(context=context, extra=extra, sync=sync)
        except Exception:
            pass

        extra = extra or {}
        ctx = context.ctx or CtxItem()
        model = context.model
        prompt = context.prompt
        num = int(extra.get("num", 1))
        inline = bool(extra.get("inline", False))

        # decide sub-mode based on attachments
        sub_mode = self.MODE_GENERATE
        attachments = context.attachments
        if attachments and len(attachments) > 0:
            pass # TODO: implement edit!
            # sub_mode = self.MODE_EDIT

        # model used to improve the prompt (not image model)
        prompt_model = self.window.core.models.from_defaults()
        tmp = self.window.core.config.get('img_prompt_model')
        if self.window.core.models.has(tmp):
            prompt_model = self.window.core.models.get(tmp)

        worker = ImageWorker()
        worker.window = self.window
        worker.client = self.window.core.api.google.get_client()
        worker.ctx = ctx
        worker.mode = sub_mode
        worker.attachments = attachments or {}
        worker.model = model.id  # image model id
        worker.input_prompt = prompt
        worker.model_prompt = prompt_model  # LLM for prompt rewriting
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
    finished = Signal(object, list, str)         # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object)                      # message
    error = Signal(object)                       # exception


class ImageWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = ImageSignals()
        self.window = None
        self.client: Optional[genai.Client] = None
        self.ctx: Optional[CtxItem] = None

        # params
        self.mode = Image.MODE_GENERATE
        self.attachments: Dict[str, Any] = {}
        self.model = "imagen-4.0-generate-preview-06-06"
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.raw = False
        self.num = 1
        self.resolution = "1024x1024"  # used to derive aspect ratio for Imagen

        # limits
        self.imagen_max_num = 4  # Imagen returns up to 4 images

        # fallbacks
        self.DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"

    @Slot()
    def run(self):
        try:
            # optional prompt enhancement
            if not self.raw and not self.inline:
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

            if self.mode == Image.MODE_EDIT:
                # EDIT
                if self._using_vertex():
                    # Vertex Imagen edit API (preferred)
                    resp = self._imagen_edit(self.input_prompt, self.attachments, self.num)
                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: self.num]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)
                else:
                    # Developer API fallback via Gemini image model; force v1 to avoid 404
                    resp = self._gemini_edit(self.input_prompt, self.attachments, self.num)
                    saved = 0
                    for cand in getattr(resp, "candidates", []) or []:
                        parts = getattr(getattr(cand, "content", None), "parts", None) or []
                        for part in parts:
                            inline = getattr(part, "inline_data", None)
                            if inline and getattr(inline, "data", None):
                                p = self._save(saved, inline.data)
                                if p:
                                    paths.append(p)
                                    saved += 1
                                    if saved >= self.num:
                                        break
                        if saved >= self.num:
                            break

            else:
                # GENERATE
                if self._is_imagen_generate(self.model) and self._using_vertex():
                    num = min(self.num, self.imagen_max_num)
                    resp = self._imagen_generate(self.input_prompt, num, self.resolution)
                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: num]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)
                else:
                    # Gemini Developer API image generation (needs response_modalities)
                    resp = self.client.models.generate_content(
                        model=self.model,
                        contents=[self.input_prompt],
                        config=gtypes.GenerateContentConfig(
                            response_modalities=[gtypes.Modality.TEXT, gtypes.Modality.IMAGE],
                        ),
                    )
                    saved = 0
                    for cand in getattr(resp, "candidates", []) or []:
                        parts = getattr(getattr(cand, "content", None), "parts", None) or []
                        for part in parts:
                            inline = getattr(part, "inline_data", None)
                            if inline and getattr(inline, "data", None):
                                p = self._save(saved, inline.data)
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

    # ---------- helpers ----------

    def _using_vertex(self) -> bool:
        """
        Detect if Vertex AI is configured via env vars.
        """
        val = os.getenv("GOOGLE_GENAI_USE_VERTEXAI") or ""
        return str(val).lower() in ("1", "true", "yes", "y")

    def _is_imagen_generate(self, model_id: str) -> bool:
        """True for Imagen generate models."""
        mid = str(model_id).lower()
        return "imagen" in mid and "generate" in mid

    def _imagen_generate(self, prompt: str, num: int, resolution: str):
        """Imagen text-to-image."""
        aspect = self._aspect_from_resolution(resolution)
        cfg = gtypes.GenerateImagesConfig(number_of_images=num)
        if aspect:
            cfg.aspect_ratio = aspect
        return self.client.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=cfg,
        )

    def _imagen_edit(self, prompt: str, attachments: Dict[str, Any], num: int):
        """
        Imagen edit: requires Vertex AI and capability model (e.g. imagen-3.0-capability-001).
        First attachment = base image, optional second = mask.
        """
        paths = self._collect_attachment_paths(attachments)
        if len(paths) == 0:
            raise RuntimeError("No attachment provided for edit mode.")

        base_img = gtypes.Image.from_file(location=paths[0])
        raw_ref = gtypes.RawReferenceImage(reference_id=0, reference_image=base_img)

        if len(paths) >= 2:
            mask_img = gtypes.Image.from_file(location=paths[1])
            mask_ref = gtypes.MaskReferenceImage(
                reference_id=1,
                reference_image=mask_img,
                config=gtypes.MaskReferenceConfig(
                    mask_mode="MASK_MODE_USER_PROVIDED",
                    mask_dilation=0.0,
                ),
            )
            edit_mode = "EDIT_MODE_INPAINT_INSERTION"
        else:
            mask_ref = gtypes.MaskReferenceImage(
                reference_id=1,
                reference_image=None,
                config=gtypes.MaskReferenceConfig(
                    mask_mode="MASK_MODE_BACKGROUND",
                    mask_dilation=0.0,
                ),
            )
            edit_mode = "EDIT_MODE_BGSWAP"

        cfg = gtypes.EditImageConfig(
            edit_mode=edit_mode,
            number_of_images=min(num, self.imagen_max_num),
            include_rai_reason=True,
        )

        # Ensure capability model for edit
        model_id = "imagen-3.0-capability-001"
        return self.client.models.edit_image(
            model=model_id,
            prompt=prompt,
            reference_images=[raw_ref, mask_ref],
            config=cfg,
        )

    def _gemini_edit(self, prompt: str, attachments: Dict[str, Any], num: int):
        """
        Gemini image-to-image editing via generate_content (Developer/Vertex depending on client).
        The first attachment is used as the input image.
        """
        paths = self._collect_attachment_paths(attachments)
        if len(paths) == 0:
            raise RuntimeError("No attachment provided for edit mode.")

        img_path = paths[0]
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        mime = self._guess_mime(img_path)

        return self.client.models.generate_content(
            model=self.model,
            contents=[prompt, gtypes.Part.from_bytes(data=img_bytes, mime_type=mime)],
        )

    def _collect_attachment_paths(self, attachments: Dict[str, Any]) -> List[str]:
        """Extract file paths from attachments dict."""
        out: List[str] = []
        for _, att in (attachments or {}).items():
            try:
                if getattr(att, "path", None) and os.path.exists(att.path):
                    out.append(att.path)
            except Exception:
                continue
        return out

    def _aspect_from_resolution(self, resolution: str) -> Optional[str]:
        """Derive aspect ratio for Imagen."""
        try:
            from math import gcd
            tolerance = 0.08
            w_str, h_str = resolution.lower().replace("×", "x").split("x")
            w, h = int(w_str.strip()), int(h_str.strip())
            if w <= 0 or h <= 0:
                return None
            supported = {
                "1:1": 1 / 1,
                "3:4": 3 / 4,
                "4:3": 4 / 3,
                "9:16": 9 / 16,
                "16:9": 16 / 9,
            }
            g = gcd(w, h)
            key = f"{w // g}:{h // g}"
            if key in supported:
                return key
            r = w / h
            best = min(supported.keys(), key=lambda k: abs(r - supported[k]))
            rel_err = abs(r - supported[best]) / supported[best]
            return best if rel_err <= tolerance else None
        except Exception:
            return None

    def _extract_imagen_bytes(self, generated_image) -> Optional[bytes]:
        """Extract bytes from Imagen GeneratedImage."""
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
        """Save image bytes to file and return path."""
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

    def _guess_mime(self, path: str) -> str:
        """
        Guess MIME type for a local image file.
        """
        mime, _ = mimetypes.guess_type(path)
        if mime:
            return mime
        ext = os.path.splitext(path.lower())[1]
        if ext in ('.jpg', '.jpeg'):
            return 'image/jpeg'
        if ext == '.webp':
            return 'image/webp'
        return 'image/png'

    def _cleanup(self):
        """Cleanup resources."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass