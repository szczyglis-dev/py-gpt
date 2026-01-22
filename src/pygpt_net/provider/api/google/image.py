#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 23:00:00                  #
# ================================================== #

import mimetypes
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types as gtypes
from PySide6.QtCore import QObject, Signal, QRunnable, Slot
import base64, datetime, os, requests, tempfile

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
        """
        # Music fast-path: delegate to Music flow if a music model is selected (e.g., Lyria).
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
        extra_prompt = extra.get("extra_prompt", "")

        # decide sub-mode based on attachments
        sub_mode = self.MODE_GENERATE
        attachments = context.attachments

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
        worker.extra_prompt = extra_prompt

        # remix: previous image reference (ID/URI/path) from extra
        worker.image_id = extra.get("image_id")

        if attachments and len(attachments) > 0:
            mid = str(model.id).lower()
            if "imagen" in mid:
                worker.mode = self.MODE_EDIT

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
        self.model = "imagen-4.0-generate-001"
        self.model_prompt = None
        self.input_prompt = ""
        self.system_prompt = ""
        self.inline = False
        self.extra_prompt: Optional[str] = None
        self.raw = False
        self.num = 1
        self.resolution = "1024x1024"  # used to derive aspect ratio or image_size
        self.image_id: Optional[str] = None  # remix/extend previous image

        # limits
        self.imagen_max_num = 4  # Imagen returns up to 4 images

        # fallbacks
        self.DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"

        # Canonical 1K dimensions for Nano Banana Pro (Gemini 3 Pro Image Preview).
        # Used to infer 2K/4K by 2x/4x multiples and to normalize UI inputs.
        self._NB_PRO_1K = {
            "1024x1024",  # 1:1
            "848x1264",   # 2:3
            "1264x848",   # 3:2
            "896x1200",   # 3:4
            "1200x896",   # 4:3
            "928x1152",   # 4:5
            "1152x928",   # 5:4
            "768x1376",   # 9:16
            "1376x768",   # 16:9
            "1584x672",   # 21:9
        }

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

            # Decide how to apply negative prompt: native param on Vertex Imagen 3.0 (-001) or inline fallback.
            use_param = (
                bool(self.extra_prompt and str(self.extra_prompt).strip())
                and self._using_vertex()
                and self._imagen_supports_negative_prompt(self.model)
            )
            if (self.extra_prompt and str(self.extra_prompt).strip()) and not use_param:
                try:
                    self.input_prompt = self._merge_negative_prompt(self.input_prompt or "", self.extra_prompt)
                except Exception:
                    pass

            paths: List[str] = []

            # Remix path: if image_id provided, prefer image-to-image remix using the given identifier.
            if self.image_id:
                self.signals.status.emit(trans('img.status.generating') + " (remix): " + (self.input_prompt or "") + "...")
                if self._using_vertex() and self._is_imagen_generate(self.model):
                    # Vertex / Imagen edit flow with a single base image (no explicit mask).
                    img_ref = self._imagen_image_from_identifier(self.image_id)
                    if not img_ref:
                        raise RuntimeError("Invalid image_id for remix. Provide a valid local path, Files API name, or gs:// URI.")

                    raw_ref = gtypes.RawReferenceImage(reference_id=0, reference_image=img_ref)
                    mask_ref = gtypes.MaskReferenceImage(
                        reference_id=1,
                        reference_image=None,
                        config=gtypes.MaskReferenceConfig(
                            mask_mode="MASK_MODE_BACKGROUND",
                            mask_dilation=0.0,
                        ),
                    )
                    # Prepare edit config with optional negative prompt when supported
                    cfg_kwargs = dict(
                        edit_mode="EDIT_MODE_DEFAULT",
                        number_of_images=min(self.num, self.imagen_max_num),
                        include_rai_reason=True,
                    )
                    if self.extra_prompt and self._imagen_supports_negative_prompt(self.model):
                        cfg_kwargs["negative_prompt"] = self.extra_prompt
                    try:
                        cfg = gtypes.EditImageConfig(**cfg_kwargs)
                    except Exception:
                        # Fallback without negative_prompt if SDK doesn't recognize it
                        cfg_kwargs.pop("negative_prompt", None)
                        cfg = gtypes.EditImageConfig(**cfg_kwargs)

                    resp = self.client.models.edit_image(
                        model="imagen-3.0-capability-001",
                        prompt=self.input_prompt or "",
                        reference_images=[raw_ref, mask_ref],
                        config=cfg,
                    )

                    # record usage if provided
                    try:
                        self._record_usage_google(resp)
                    except Exception:
                        pass

                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: min(self.num, self.imagen_max_num)]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)

                    # store reference for future remix: prefer remote URI if available, otherwise saved path
                    if paths:
                        self._store_image_reference_imagen(imgs[0] if imgs else None, paths[0])

                else:
                    # Gemini Developer API remix via generate_content with prompt + reference image part.
                    ref_part = self._image_part_from_identifier(self.image_id)
                    if not ref_part:
                        raise RuntimeError("Invalid image_id for remix. Provide a valid local path, Files API name, http(s) URL, or gs:// URI.")
                    img_cfg = self._build_gemini_image_config(self.model, self.resolution)
                    resp = self.client.models.generate_content(
                        model=self.model or self.DEFAULT_GEMINI_IMAGE_MODEL,
                        contents=[self.input_prompt or "", ref_part],
                        config=gtypes.GenerateContentConfig(
                            image_config=img_cfg,
                        ),
                    )

                    # record usage if provided
                    try:
                        self._record_usage_google(resp)
                    except Exception:
                        pass

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

                    # store reference: saved local path is a reusable identifier for next remix
                    if paths:
                        self._store_image_id(paths[0])

                if self.inline:
                    self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
                else:
                    self.signals.finished.emit(self.ctx, paths, self.input_prompt)
                return  # remix path finished

            # Normal paths
            self.signals.status.emit(trans('img.status.generating') + f": {self.input_prompt}...")

            if self.mode == Image.MODE_EDIT:
                # EDIT
                if self._using_vertex():
                    # Vertex Imagen edit API (preferred)
                    resp = self._imagen_edit(self.input_prompt, self.attachments, self.num)

                    # record usage if provided
                    try:
                        self._record_usage_google(resp)
                    except Exception:
                        pass

                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: self.num]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)
                    # store reference
                    if paths:
                        self._store_image_reference_imagen(imgs[0] if imgs else None, paths[0])
                else:
                    # Gemini Developer API via Gemini image models (Nano Banana / Nano Banana Pro)
                    resp = self._gemini_edit(self.input_prompt, self.attachments, self.num)

                    # record usage if provided
                    try:
                        self._record_usage_google(resp)
                    except Exception:
                        pass

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
                    # store reference
                    if paths:
                        self._store_image_id(paths[0])

            else:
                # GENERATE
                if self._is_imagen_generate(self.model) and self._using_vertex():
                    num = min(self.num, self.imagen_max_num)
                    resp = self._imagen_generate(self.input_prompt, num, self.resolution)

                    # record usage if provided
                    try:
                        self._record_usage_google(resp)
                    except Exception:
                        pass

                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: num]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)
                    # store reference
                    if paths:
                        self._store_image_reference_imagen(imgs[0] if imgs else None, paths[0])
                else:
                    # Gemini Developer API image generation (Nano Banana / Nano Banana Pro) with robust sizing + optional reference images
                    resp = self._gemini_generate_image(self.input_prompt, self.model, self.resolution)

                    # record usage if provided
                    try:
                        self._record_usage_google(resp)
                    except Exception:
                        pass

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
                    # store reference
                    if paths:
                        self._store_image_id(paths[0])

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

    def _imagen_supports_negative_prompt(self, model_id: str) -> bool:
        """
        Return True if the Imagen model supports native negative_prompt.
        Supported: imagen-3.0-generate-001, imagen-3.0-fast-generate-001, imagen-3.0-capability-001.
        """
        mid = str(model_id or "").lower()
        return any(x in mid for x in (
            "imagen-3.0-generate-001",
            "imagen-3.0-fast-generate-001",
            "imagen-3.0-capability-001",
        ))

    def _imagen_generate(self, prompt: str, num: int, resolution: str):
        """Imagen text-to-image."""
        aspect = self._aspect_from_resolution(resolution)
        # Build config with optional negative_prompt when supported by model and provided.
        cfg_kwargs: Dict[str, Any] = {"number_of_images": num}
        if aspect:
            cfg_kwargs["aspect_ratio"] = aspect
        if self.extra_prompt and self._imagen_supports_negative_prompt(self.model):
            cfg_kwargs["negative_prompt"] = self.extra_prompt
        try:
            cfg = gtypes.GenerateImagesConfig(**cfg_kwargs)
        except Exception:
            # Fallback without negative_prompt if SDK doesn't recognize it
            cfg_kwargs.pop("negative_prompt", None)
            cfg = gtypes.GenerateImagesConfig(**cfg_kwargs)

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

        # Build edit config with optional negative_prompt
        cfg_kwargs = dict(
            edit_mode=edit_mode,
            number_of_images=min(num, self.imagen_max_num),
            include_rai_reason=True,
        )
        if self.extra_prompt and self._imagen_supports_negative_prompt(self.model):
            cfg_kwargs["negative_prompt"] = self.extra_prompt
        try:
            cfg = gtypes.EditImageConfig(**cfg_kwargs)
        except Exception:
            cfg_kwargs.pop("negative_prompt", None)
            cfg = gtypes.EditImageConfig(**cfg_kwargs)

        # Ensure capability model for edit
        model_id = "imagen-3.0-capability-001"
        return self.client.models.edit_image(
            model=model_id,
            prompt=prompt,
            reference_images=[raw_ref, mask_ref],
            config=cfg,
        )

    def _is_gemini_pro_image_model(self, model_id: str) -> bool:
        """
        Detect Gemini 3 Pro Image (Nano Banana Pro) by id or UI alias.
        """
        mid = (model_id or "").lower()
        return mid.startswith("gemini-") or mid.startswith("nano-banana") or mid.startswith("nb-")

    def _infer_nb_pro_size_for_dims(self, w: int, h: int) -> Optional[str]:
        """
        Infer '1K' | '2K' | '4K' for Nano Banana Pro from WxH.
        """
        dims = f"{w}x{h}"
        if dims in self._NB_PRO_1K:
            return "1K"
        if (w % 2 == 0) and (h % 2 == 0):
            if f"{w // 2}x{h // 2}" in self._NB_PRO_1K:
                return "2K"
        if (w % 4 == 0) and (h % 4 == 0):
            if f"{w // 4}x{h // 4}" in self._NB_PRO_1K:
                return "4K"
        mx = max(w, h)
        if mx >= 4000:
            return "4K"
        if mx >= 2000:
            return "2K"
        return "1K"

    def _build_gemini_image_config(self, model_id: str, resolution: str) -> Optional[gtypes.ImageConfig]:
        """
        Build ImageConfig for Gemini image models.
        """
        try:
            aspect = self._aspect_from_resolution(resolution)
            cfg = gtypes.ImageConfig()
            if aspect:
                cfg.aspect_ratio = aspect

            # Only Pro supports image_size; detect by id/alias and set 1K/2K/4K from WxH.
            if self._is_gemini_pro_image_model(model_id):
                w_str, h_str = resolution.lower().replace("×", "x").split("x")
                w, h = int(w_str.strip()), int(h_str.strip())
                k = self._infer_nb_pro_size_for_dims(w, h)
                if k:
                    cfg.image_size = k
            return cfg
        except Exception:
            return None

    def _attachment_image_parts(self) -> List[gtypes.Part]:
        """
        Build image Parts from current attachments for Gemini models.
        """
        parts: List[gtypes.Part] = []
        paths = self._collect_attachment_paths(self.attachments)
        for p in paths:
            try:
                mime = self._guess_mime(p)
                if not mime or not mime.startswith("image/"):
                    continue
                with open(p, "rb") as f:
                    data = f.read()
                parts.append(gtypes.Part.from_bytes(data=data, mime_type=mime))
            except Exception:
                continue
        return parts

    def _gemini_generate_image(self, prompt: str, model_id: str, resolution: str):
        """
        Call Gemini generate_content with robust fallback for image_size.
        Supports optional reference images uploaded as attachments.
        """
        cfg = self._build_gemini_image_config(model_id, resolution)
        image_parts = self._attachment_image_parts()

        def _do_call(icfg: Optional[gtypes.ImageConfig]):
            contents: List[Any] = []
            contents.append(prompt or "")
            if image_parts:
                contents.extend(image_parts)
            return self.client.models.generate_content(
                model=model_id or self.DEFAULT_GEMINI_IMAGE_MODEL,
                contents=contents,
                config=gtypes.GenerateContentConfig(
                    response_modalities=[gtypes.Modality.TEXT, gtypes.Modality.IMAGE],
                    image_config=icfg,
                ),
            )

        try:
            return _do_call(cfg)
        except Exception as e:
            msg = str(e)
            if "imageSize" in msg or "image_size" in msg or "Unrecognized" in msg or "unsupported" in msg:
                try:
                    if cfg and getattr(cfg, "image_size", None):
                        cfg2 = gtypes.ImageConfig()
                        cfg2.aspect_ratio = getattr(cfg, "aspect_ratio", None)
                        return _do_call(cfg2)
                except Exception:
                    pass
            raise

    def _gemini_edit(self, prompt: str, attachments: Dict[str, Any], num: int):
        """
        Gemini image-to-image editing via generate_content.
        The first attachment is used as the input image. Honors aspect_ratio and (for Pro) image_size.
        """
        paths = self._collect_attachment_paths(attachments)
        if len(paths) == 0:
            raise RuntimeError("No attachment provided for edit mode.")

        img_path = paths[0]
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        mime = self._guess_mime(img_path)

        cfg = self._build_gemini_image_config(self.model, self.resolution)

        def _do_call(icfg: Optional[gtypes.ImageConfig]):
            return self.client.models.generate_content(
                model=self.model or self.DEFAULT_GEMINI_IMAGE_MODEL,
                contents=[prompt, gtypes.Part.from_bytes(data=img_bytes, mime_type=mime)],
                config=gtypes.GenerateContentConfig(
                    image_config=icfg,
                ),
            )

        try:
            return _do_call(cfg)
        except Exception as e:
            msg = str(e)
            if "imageSize" in msg or "image_size" in msg or "Unrecognized" in msg or "unsupported" in msg:
                if cfg and getattr(cfg, "image_size", None):
                    cfg2 = gtypes.ImageConfig()
                    cfg2.aspect_ratio = getattr(cfg, "aspect_ratio", None)
                    return _do_call(cfg2)
            raise

    def _image_part_from_identifier(self, identifier: str) -> Optional[gtypes.Part]:
        """
        Build a Gemini Part from a generic image identifier:
        - Local path -> Part.from_bytes
        - Files API name (files/...) -> resolve to URI + mime and use Part.from_uri
        - gs:// URI -> Part.from_uri
        - http(s) URL -> download bytes and use Part.from_bytes
        - data: URI (base64) -> decode and use Part.from_bytes
        """
        if not identifier:
            return None
        ident = str(identifier).strip()

        # Local file
        if os.path.exists(ident):
            mime = self._guess_mime(ident)
            with open(ident, "rb") as f:
                return gtypes.Part.from_bytes(data=f.read(), mime_type=mime)

        # Files API
        if ident.startswith("files/"):
            try:
                f = self.client.files.get(name=ident)
                file_uri = getattr(f, "uri", None)
                mime = getattr(f, "mime_type", None) or self._guess_mime_from_uri(file_uri)
                if file_uri and mime:
                    return gtypes.Part.from_uri(file_uri=file_uri, mime_type=mime)
            except Exception:
                pass

        # gs://
        if ident.startswith("gs://"):
            mime = self._guess_mime_from_uri(ident) or "image/png"
            return gtypes.Part.from_uri(file_uri=ident, mime_type=mime)

        # http(s)
        if ident.startswith("http://") or ident.startswith("https://"):
            try:
                r = requests.get(ident, timeout=60)
                if r.status_code == 200:
                    mime = r.headers.get("Content-Type") or self._guess_mime_from_uri(ident) or "image/png"
                    return gtypes.Part.from_bytes(data=r.content, mime_type=mime)
            except Exception:
                return None

        # data:
        if ident.startswith("data:"):
            try:
                head, b64 = ident.split(",", 1)
                mime = head.split(";")[0][5:] if ";" in head else "image/png"
                return gtypes.Part.from_bytes(data=base64.b64decode(b64), mime_type=mime)
            except Exception:
                return None

        return None

    def _imagen_image_from_identifier(self, identifier: str) -> Optional[gtypes.Image]:
        """
        Build a gtypes.Image for Imagen edit:
        - Local path -> Image.from_file
        - Files API name -> resolve to URI; if gs:// use gcs_uri, otherwise download to temp and from_file
        - gs:// -> Image(gcs_uri=...)
        - http(s) -> download to temp file, then from_file
        """
        if not identifier:
            return None
        ident = str(identifier).strip()

        if os.path.exists(ident):
            return gtypes.Image.from_file(location=ident)

        if ident.startswith("files/"):
            try:
                f = self.client.files.get(name=ident)
                uri = getattr(f, "uri", None)
                if uri and uri.startswith("gs://"):
                    return gtypes.Image(gcs_uri=uri)
                if uri and (uri.startswith("http://") or uri.startswith("https://")):
                    tmp = self._download_to_temp(uri)
                    return gtypes.Image.from_file(location=tmp) if tmp else None
            except Exception:
                return None

        if ident.startswith("gs://"):
            return gtypes.Image(gcs_uri=ident)

        if ident.startswith("http://") or ident.startswith("https://"):
            tmp = self._download_to_temp(ident)
            return gtypes.Image.from_file(location=tmp) if tmp else None

        return None

    def _download_to_temp(self, url: str) -> Optional[str]:
        """Download URL to a temporary file and return its path."""
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                ext = ".png"
                ct = r.headers.get("Content-Type") or ""
                if "jpeg" in ct:
                    ext = ".jpg"
                elif "webp" in ct:
                    ext = ".webp"
                fd, path = tempfile.mkstemp(suffix=ext)
                with os.fdopen(fd, "wb") as f:
                    f.write(r.content)
                return path
        except Exception:
            return None
        return None

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
        """Derive aspect ratio from WxH across supported set."""
        try:
            from math import gcd
            tolerance = 0.08
            w_str, h_str = resolution.lower().replace("×", "x").split("x")
            w, h = int(w_str.strip()), int(h_str.strip())
            if w <= 0 or h <= 0:
                return None
            supported = {
                "1:1": 1 / 1,
                "2:3": 2 / 3,
                "3:2": 3 / 2,
                "3:4": 3 / 4,
                "4:3": 4 / 3,
                "4:5": 4 / 5,
                "5:4": 5 / 4,
                "9:16": 9 / 16,
                "16:9": 16 / 9,
                "21:9": 21 / 9,
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

    def _store_image_reference_imagen(self, generated_image_item: Any, fallback_path: Optional[str]) -> None:
        """
        Persist a reusable image reference to ctx.extra['image_id'].
        Prefer remote URI/name if provided by Imagen; fallback to the saved local path.
        """
        ref = None
        try:
            img = getattr(generated_image_item, "image", None) if generated_image_item else None
            if img:
                ref = getattr(img, "uri", None) or getattr(img, "url", None) or getattr(img, "name", None)
        except Exception:
            ref = None
        self._store_image_id(ref or fallback_path)

    def _store_image_id(self, value: Optional[str]) -> None:
        """
        Store image_id reference in ctx.extra and persist the context item.
        """
        if not value:
            return
        try:
            if not isinstance(self.ctx.extra, dict):
                self.ctx.extra = {}
            self.ctx.extra["image_id"] = str(value)
            self.window.core.ctx.update_item(self.ctx)
        except Exception:
            pass

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
        if ext in ('.heic', '.heif'):
            return 'image/heic'
        return 'image/png'

    def _guess_mime_from_uri(self, uri: Optional[str]) -> Optional[str]:
        """Best-effort MIME guess from URI or file extension."""
        if not uri:
            return None
        mime, _ = mimetypes.guess_type(uri)
        return mime or None

    # ---------- usage helpers (Google GenAI) ----------

    def _record_usage_google(self, response: Any) -> None:
        """
        Extract usage_metadata from Google GenAI response if present and store in ctx.
        Saves to:
          - ctx.set_tokens(prompt_token_count, candidates_token_count)
          - ctx.extra["usage"] = {...}
        """
        try:
            usage = getattr(response, "usage_metadata", None)
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

            p = _as_int(getattr(usage, "prompt_token_count", 0) or 0)
            c = _as_int(getattr(usage, "candidates_token_count", 0) or 0)
            t = _as_int(getattr(usage, "total_token_count", (p + c)) or (p + c))

            if self.ctx:
                self.ctx.set_tokens(p, c)

            if not isinstance(self.ctx.extra, dict):
                self.ctx.extra = {}

            self.ctx.extra["usage"] = {
                "vendor": "google",
                "model": str(self.model),
                "input_tokens": p,
                "output_tokens": c,
                "total_tokens": t,
                "source": "image",
            }
        except Exception:
            # best-effort; ignore failures
            pass

    def _cleanup(self):
        """Cleanup resources."""
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
        Append a negative prompt to the main text prompt when the provider has no native negative_prompt field.
        """
        base = (prompt or "").strip()
        neg = (negative or "").strip()
        if not neg:
            return base
        return (base + ("\n" if base else "") + f"Negative prompt: {neg}").strip()