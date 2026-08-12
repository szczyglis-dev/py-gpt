#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.12 16:30:00                  #
# ================================================== #

import mimetypes
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types as gtypes
from PySide6.QtCore import QObject, Signal, QRunnable, Slot
import base64, datetime, os, requests, tempfile

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.types import MODE_IMAGE
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

DEFAULT_GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"

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
        worker.client = self.window.core.api.google.get_client(mode=MODE_IMAGE, model=model)
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
        self.model = DEFAULT_GEMINI_IMAGE_MODEL
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
        self.DEFAULT_GEMINI_IMAGE_MODEL = DEFAULT_GEMINI_IMAGE_MODEL

        # Canonical Gemini image dimensions. These are also used to infer the
        # image_size token without sending unsupported sizing options to models
        # with fixed output size (e.g. Gemini 2.5 Flash Image / Flash Lite Image).
        self._GEMINI_1K = {
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
        self._GEMINI_31_FLASH_1K_EXTRA = {
            "512x2048",   # 1:4
            "384x3072",   # 1:8
            "2048x512",   # 4:1
            "3072x384",   # 8:1
        }
        # Keep the historical Nano Banana Pro alias dimensions working.
        # PyGPT exposed these before the stable Gemini 3 Pro model ids landed.
        self._NANO_BANANA_PRO_LEGACY_1K = {
            "1024x1024",
            "832x1248", "1248x832",
            "864x1184", "1184x864",
            "896x1152", "1152x896",
            "768x1344", "1344x768",
            "1536x672",
        }
        self._GEMINI_31_FLASH_512 = {
            "512x512",
            "256x1024",
            "192x1536",
            "424x632",
            "632x424",
            "448x600",
            "1024x256",
            "600x448",
            "464x576",
            "576x464",
            "1536x192",
            "384x688",
            "688x384",
            "792x168",
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

            # Remix path: if image_id provided, use the native edit/remix path
            # for the selected image model family.
            if self.image_id:
                self.signals.status.emit(trans('img.status.generating') + " (remix): " + (self.input_prompt or "") + "...")
                if self._is_imagen_generate(self.model):
                    if not self._using_vertex():
                        raise RuntimeError(
                            "Imagen remix/edit requires Vertex AI. Use a Gemini image model for editing "
                            "with the Gemini Developer API."
                        )

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
                        cfg_kwargs.pop("negative_prompt", None)
                        cfg = gtypes.EditImageConfig(**cfg_kwargs)

                    resp = self.client.models.edit_image(
                        model="imagen-3.0-capability-001",
                        prompt=self.input_prompt or "",
                        reference_images=[raw_ref, mask_ref],
                        config=cfg,
                    )
                    self._record_usage_google_safe(resp)

                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: min(self.num, self.imagen_max_num)]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)
                    if not paths:
                        raise RuntimeError("Google Imagen returned no image data.")
                    self._store_image_reference_imagen(imgs[0] if imgs else None, paths[0])

                else:
                    ref_part = self._image_part_from_identifier(self.image_id)
                    if not ref_part:
                        raise RuntimeError(
                            "Invalid image_id for remix. Provide a valid local path, Files API name, "
                            "http(s) URL, or gs:// URI."
                        )
                    resp = self._gemini_generate_content(
                        prompt=self.input_prompt or "",
                        model_id=self.model,
                        resolution=self.resolution,
                        extra_parts=[ref_part],
                    )
                    self._record_usage_google_safe(resp)
                    paths.extend(self._save_gemini_response(resp, self.num))
                    self._store_image_id(paths[0])

                if self.inline:
                    self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
                else:
                    self.signals.finished.emit(self.ctx, paths, self.input_prompt)
                return  # remix path finished

            # Normal paths
            self.signals.status.emit(trans('img.status.generating') + f": {self.input_prompt}...")

            if self.mode == Image.MODE_EDIT:
                # Attachments switch Imagen models to edit mode. Imagen editing is
                # available through Vertex AI; Gemini image models use generate_content.
                if self._is_imagen_generate(self.model):
                    if not self._using_vertex():
                        raise RuntimeError(
                            "Imagen image editing requires Vertex AI. Use a Gemini image model for "
                            "image-to-image editing with the Gemini Developer API."
                        )
                    resp = self._imagen_edit(self.input_prompt, self.attachments, self.num)
                    self._record_usage_google_safe(resp)

                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: self.num]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)
                    if not paths:
                        raise RuntimeError("Google Imagen returned no image data.")
                    self._store_image_reference_imagen(imgs[0] if imgs else None, paths[0])
                else:
                    resp = self._gemini_edit(self.input_prompt, self.attachments, self.num)
                    self._record_usage_google_safe(resp)
                    paths.extend(self._save_gemini_response(resp, self.num))
                    self._store_image_id(paths[0])

            else:
                # GENERATE. Imagen has a dedicated generate_images API on both
                # Gemini Developer API and Vertex AI; Gemini image models use generate_content.
                if self._is_imagen_generate(self.model):
                    num = min(self.num, self.imagen_max_num)
                    resp = self._imagen_generate(self.input_prompt, num, self.resolution)
                    self._record_usage_google_safe(resp)

                    imgs = getattr(resp, "generated_images", None) or []
                    for idx, gi in enumerate(imgs[: num]):
                        data = self._extract_imagen_bytes(gi)
                        p = self._save(idx, data)
                        if p:
                            paths.append(p)
                    if not paths:
                        raise RuntimeError("Google Imagen returned no image data.")
                    self._store_image_reference_imagen(imgs[0] if imgs else None, paths[0])
                else:
                    resp = self._gemini_generate_image(self.input_prompt, self.model, self.resolution)
                    self._record_usage_google_safe(resp)
                    paths.extend(self._save_gemini_response(resp, self.num))
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

    def _gemini_supports_variable_image_size(self, model_id: str) -> bool:
        """Return True only for Gemini image models that accept image_size."""
        mid = (model_id or "").lower().split("/")[-1]
        return (
            mid.startswith("gemini-3.1-flash-image")
            or mid.startswith("gemini-3-pro-image")
            or mid.startswith("nano-banana-pro")
            or mid.startswith("nb-pro")
        )

    def _is_gemini_31_flash_image(self, model_id: str) -> bool:
        mid = (model_id or "").lower().split("/")[-1]
        return mid.startswith("gemini-3.1-flash-image")

    def _is_nano_banana_pro_alias(self, model_id: str) -> bool:
        mid = (model_id or "").lower().split("/")[-1]
        return mid.startswith("nano-banana-pro") or mid.startswith("nb-pro")

    def _infer_gemini_image_size_for_dims(self, model_id: str, w: int, h: int) -> Optional[str]:
        """Infer the API image_size token from a canonical UI WxH value."""
        if not self._gemini_supports_variable_image_size(model_id):
            return None

        dims = f"{w}x{h}"
        if self._is_gemini_31_flash_image(model_id) and dims in self._GEMINI_31_FLASH_512:
            return "512"

        if self._is_nano_banana_pro_alias(model_id):
            base = set(self._NANO_BANANA_PRO_LEGACY_1K)
        else:
            base = set(self._GEMINI_1K)
            if self._is_gemini_31_flash_image(model_id):
                base.update(self._GEMINI_31_FLASH_1K_EXTRA)

        if dims in base:
            return "1K"
        if (w % 2 == 0) and (h % 2 == 0) and f"{w // 2}x{h // 2}" in base:
            return "2K"
        if (w % 4 == 0) and (h % 4 == 0) and f"{w // 4}x{h // 4}" in base:
            return "4K"
        return None

    def _build_gemini_image_config(self, model_id: str, resolution: str) -> Optional[gtypes.ImageConfig]:
        """Build a model-aware ImageConfig for Gemini native image generation."""
        try:
            aspect = self._aspect_from_resolution(resolution)
            cfg = gtypes.ImageConfig()
            if aspect:
                cfg.aspect_ratio = aspect

            # Do not send image_size to fixed-size Gemini image models. The old
            # code treated every gemini-* id as Nano Banana Pro, which could make
            # otherwise valid requests fail for Flash / Flash Lite variants.
            if self._gemini_supports_variable_image_size(model_id):
                w_str, h_str = resolution.lower().replace("×", "x").split("x")
                w, h = int(w_str.strip()), int(h_str.strip())
                image_size = self._infer_gemini_image_size_for_dims(model_id, w, h)
                if image_size:
                    cfg.image_size = image_size
            return cfg
        except Exception:
            return None

    def _attachment_image_parts(self) -> List[gtypes.Part]:
        """Build image Parts from current attachments for Gemini models."""
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

    def _gemini_config_error(self, exc: Exception) -> bool:
        """Best-effort detection of SDK/API errors caused by image config fields."""
        msg = str(exc).lower()
        markers = (
            "imagesize", "image_size", "imageconfig", "image_config",
            "aspect_ratio", "aspect ratio", "unrecognized", "unsupported",
            "unknown name", "cannot find field", "invalid argument",
        )
        return any(marker in msg for marker in markers)

    def _gemini_config_without_size(self, cfg: Optional[gtypes.ImageConfig]) -> Optional[gtypes.ImageConfig]:
        if not cfg:
            return None
        try:
            cfg2 = gtypes.ImageConfig()
            aspect = getattr(cfg, "aspect_ratio", None)
            if aspect:
                cfg2.aspect_ratio = aspect
            return cfg2
        except Exception:
            return None

    def _gtype_has_field(self, cls: Any, field: str) -> bool:
        """Return True when a google-genai Pydantic type exposes the given field."""
        try:
            fields = getattr(cls, "model_fields", None) or getattr(cls, "__fields__", None) or {}
            return field in fields
        except Exception:
            return False

    def _gemini_response_format(self, model_id: str, resolution: str) -> Dict[str, Any]:
        """Build the current Python SDK response_format payload for an image output."""
        image: Dict[str, Any] = {}
        aspect = self._aspect_from_resolution(resolution)
        if aspect:
            image["aspect_ratio"] = aspect

        try:
            w_str, h_str = resolution.lower().replace("×", "x").split("x")
            w, h = int(w_str.strip()), int(h_str.strip())
            image_size = self._infer_gemini_image_size_for_dims(model_id, w, h)
            if image_size:
                image["image_size"] = image_size
        except Exception:
            pass

        return {"image": image}

    def _gemini_generate_content(
            self,
            prompt: str,
            model_id: str,
            resolution: str,
            extra_parts: Optional[List[gtypes.Part]] = None
    ):
        """Call Gemini native image generation/editing with SDK-version fallbacks."""
        cfg = self._build_gemini_image_config(model_id, resolution)
        contents: List[Any] = [prompt or ""]
        if extra_parts:
            contents.extend(extra_parts)

        supports_response_format = self._gtype_has_field(gtypes.GenerateContentConfig, "response_format")

        def _do_call(icfg: Optional[gtypes.ImageConfig], use_response_format: bool = False):
            kwargs: Dict[str, Any] = {"response_modalities": ["IMAGE"]}
            if use_response_format and supports_response_format:
                kwargs["response_format"] = self._gemini_response_format(model_id, resolution)
            elif icfg is not None:
                kwargs["image_config"] = icfg
            return self.client.models.generate_content(
                model=model_id or self.DEFAULT_GEMINI_IMAGE_MODEL,
                contents=contents,
                config=gtypes.GenerateContentConfig(**kwargs),
            )

        response = None
        last_error: Optional[Exception] = None

        # Current Python SDK/docs use response_format. Older google-genai versions
        # expose image_config instead, so preserve both paths without requiring a
        # forced dependency upgrade.
        strategies = []
        if supports_response_format:
            strategies.append((cfg, True))
        strategies.append((cfg, False))

        cfg_no_size = self._gemini_config_without_size(cfg)
        if cfg_no_size is not None:
            strategies.append((cfg_no_size, False))
        strategies.append((None, False))

        seen = set()
        for icfg, use_response_format in strategies:
            signature = (
                bool(use_response_format),
                getattr(icfg, "aspect_ratio", None) if icfg else None,
                getattr(icfg, "image_size", None) if icfg else None,
            )
            if signature in seen:
                continue
            seen.add(signature)
            try:
                response = _do_call(icfg, use_response_format=use_response_format)
                break
            except Exception as exc:
                last_error = exc
                if not self._gemini_config_error(exc):
                    raise

        if response is None:
            if last_error is not None:
                raise last_error
            raise RuntimeError("Google Gemini image request failed before a response was returned.")

        # A successfully accepted but empty image response used to be silently
        # treated as success in PyGPT. Retry once without optional image sizing
        # unless Google explicitly blocked the request, then surface a real error.
        if (
                not self._gemini_response_has_image(response)
                and cfg is not None
                and not self._gemini_response_is_blocked(response)
        ):
            try:
                fallback = _do_call(None, use_response_format=False)
                if self._gemini_response_has_image(fallback) or self._gemini_response_is_blocked(fallback):
                    response = fallback
            except Exception:
                pass

        return response

    def _gemini_generate_image(self, prompt: str, model_id: str, resolution: str):
        """Gemini text-to-image, with optional image attachments as references."""
        return self._gemini_generate_content(
            prompt=prompt,
            model_id=model_id,
            resolution=resolution,
            extra_parts=self._attachment_image_parts(),
        )

    def _gemini_edit(self, prompt: str, attachments: Dict[str, Any], num: int):
        """Gemini image-to-image editing via native generate_content."""
        paths = self._collect_attachment_paths(attachments)
        if len(paths) == 0:
            raise RuntimeError("No attachment provided for edit mode.")

        parts: List[gtypes.Part] = []
        for img_path in paths:
            try:
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                parts.append(gtypes.Part.from_bytes(data=img_bytes, mime_type=self._guess_mime(img_path)))
            except Exception:
                continue
        if not parts:
            raise RuntimeError("No readable image attachment provided for edit mode.")

        return self._gemini_generate_content(
            prompt=prompt,
            model_id=self.model,
            resolution=self.resolution,
            extra_parts=parts,
        )

    def _gemini_response_parts(self, response: Any) -> List[Any]:
        """Return response parts across current and older google-genai response shapes."""
        try:
            parts = getattr(response, "parts", None)
            if parts:
                return list(parts)
        except Exception:
            pass

        parts: List[Any] = []
        for cand in getattr(response, "candidates", None) or []:
            try:
                parts.extend(getattr(getattr(cand, "content", None), "parts", None) or [])
            except Exception:
                continue
        return parts

    def _extract_gemini_part_bytes(self, part: Any) -> Optional[bytes]:
        """Extract image bytes from a Gemini response part."""
        try:
            if bool(getattr(part, "thought", False)):
                return None
        except Exception:
            pass

        try:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None) if inline else None
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            if isinstance(data, str):
                return base64.b64decode(data)
        except Exception:
            pass

        # Newer SDKs expose Part.as_image(); keep this as a secondary path so
        # parsing remains compatible if inline_data internals change.
        try:
            as_image = getattr(part, "as_image", None)
            if callable(as_image):
                img = as_image()
                data = getattr(img, "image_bytes", None) if img else None
                if isinstance(data, (bytes, bytearray)):
                    return bytes(data)
                if isinstance(data, str):
                    return base64.b64decode(data)
        except Exception:
            pass
        return None

    def _gemini_response_has_image(self, response: Any) -> bool:
        return any(self._extract_gemini_part_bytes(part) for part in self._gemini_response_parts(response))

    def _gemini_response_is_blocked(self, response: Any) -> bool:
        """Detect safety/content blocking so a blocked request is not retried unnecessarily."""
        try:
            feedback = getattr(response, "prompt_feedback", None)
            block_reason = getattr(feedback, "block_reason", None) if feedback else None
            if block_reason and str(block_reason).upper() not in ("BLOCK_REASON_UNSPECIFIED", "NONE", "0"):
                return True
        except Exception:
            pass
        for cand in getattr(response, "candidates", None) or []:
            try:
                reason = str(getattr(cand, "finish_reason", "") or "").upper()
                if any(x in reason for x in ("SAFETY", "BLOCKLIST", "PROHIBITED", "SPII", "RECITATION")):
                    return True
            except Exception:
                continue
        return False

    def _gemini_no_image_error(self, response: Any) -> RuntimeError:
        details: List[str] = []
        try:
            feedback = getattr(response, "prompt_feedback", None)
            reason = getattr(feedback, "block_reason", None) if feedback else None
            if reason:
                details.append(f"block_reason={reason}")
        except Exception:
            pass

        for cand in getattr(response, "candidates", None) or []:
            try:
                reason = getattr(cand, "finish_reason", None)
                message = getattr(cand, "finish_message", None)
                if reason:
                    details.append(f"finish_reason={reason}")
                if message:
                    details.append(str(message))
            except Exception:
                continue

        texts: List[str] = []
        for part in self._gemini_response_parts(response):
            try:
                text = getattr(part, "text", None)
                if text:
                    texts.append(str(text).strip())
            except Exception:
                continue
        if texts:
            details.append("response=" + " ".join(texts)[:500])

        suffix = (" Details: " + "; ".join(dict.fromkeys(details))) if details else ""
        return RuntimeError("Google Gemini returned no image data." + suffix)

    def _save_gemini_response(self, response: Any, max_images: int) -> List[str]:
        """Save image parts from a Gemini response; never silently accept an empty response."""
        data_items: List[bytes] = []
        for part in self._gemini_response_parts(response):
            data = self._extract_gemini_part_bytes(part)
            if data:
                data_items.append(data)
                if len(data_items) >= max(1, int(max_images or 1)):
                    break

        if not data_items:
            raise self._gemini_no_image_error(response)

        paths: List[str] = []
        for idx, data in enumerate(data_items):
            p = self._save(idx, data)
            if p:
                paths.append(p)
        if not paths:
            raise RuntimeError("Gemini returned image data, but PyGPT could not save the generated image.")
        return paths

    def _record_usage_google_safe(self, response: Any) -> None:
        try:
            self._record_usage_google(response)
        except Exception:
            pass

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
            normalized = resolution.lower().replace("×", "x").replace(" ", "")
            # Google's published 512px table currently lists 792x168 for 21:9,
            # which does not reduce mathematically to 21:9. Preserve the API
            # semantic ratio for that canonical value instead of guessing from WxH.
            canonical = {
                "792x168": "21:9",
            }
            if normalized in canonical:
                return canonical[normalized]

            w_str, h_str = normalized.split("x")
            w, h = int(w_str.strip()), int(h_str.strip())
            if w <= 0 or h <= 0:
                return None
            supported = {
                "1:1": 1 / 1,
                "1:4": 1 / 4,
                "1:8": 1 / 8,
                "2:3": 2 / 3,
                "3:2": 3 / 2,
                "3:4": 3 / 4,
                "4:1": 4 / 1,
                "4:3": 4 / 3,
                "4:5": 4 / 5,
                "5:4": 5 / 4,
                "8:1": 8 / 1,
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
            self.ctx.extra["image_id"] = self.window.core.filesystem.make_local(str(value))
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