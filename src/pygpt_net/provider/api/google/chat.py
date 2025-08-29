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

from google.genai import types as gtypes
from google.genai.types import Content, Part

from pygpt_net.core.types import MODE_CHAT, MODE_AUDIO
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


class Chat:
    def __init__(self, window=None):
        """
        Chat wrapper for Google GenAI.
        """
        self.window = window
        self.input_tokens = 0

    def send(self, context: BridgeContext, extra: Optional[Dict[str, Any]] = None):
        """
        Call Google GenAI for chat / multimodal / audio.
        """
        prompt = context.prompt
        stream = context.stream
        system_prompt = context.system_prompt
        model = context.model
        functions = context.external_functions
        attachments = context.attachments
        multimodal_ctx = context.multimodal_ctx
        mode = context.mode
        ctx = context.ctx or CtxItem()

        client = self.window.core.api.google.get_client(context.mode, model)

        # Detect audio-input present
        has_audio_input = bool(
            multimodal_ctx
            and getattr(multimodal_ctx, "is_audio_input", False)
            and getattr(multimodal_ctx, "audio_data", None)
        )

        # ------------- TRANSCRIPTION PATH (audio input -> text -> feed to TTS) -------------
        if mode == MODE_AUDIO and has_audio_input:
            # Build minimal transcription request: [instruction text, audio part]
            transcribe_model = self.window.core.config.get("google_audio.transcribe_model", "gemini-2.5-flash")
            transcribe_prompt = self.window.core.config.get("google_audio.transcribe_prompt", "Transcribe this audio clip to text.")
            audio_part = self.window.core.api.google.audio.build_part(multimodal_ctx)
            trans_inputs = [
                Content(role="user", parts=[
                    Part.from_text(text=transcribe_prompt),
                    audio_part,
                ])
            ]
            trans_cfg = gtypes.GenerateContentConfig(
                # Keep minimal; no tools/system for transcription
                temperature=self.window.core.config.get('temperature'),
                top_p=self.window.core.config.get('top_p'),
                max_output_tokens=context.max_tokens if context.max_tokens else None,
            )

            # Always non-stream here (we immediately need the text for TTS)
            trans_resp = client.models.generate_content(
                model=transcribe_model,
                contents=trans_inputs,
                config=trans_cfg,
            )
            transcribed_text = self.extract_text(trans_resp).strip()
            if transcribed_text:
                # Feed transcription into TTS as the final prompt
                prompt = transcribed_text
                ctx.input = transcribed_text
                try:
                    # optional: store for debugging/UX
                    if isinstance(ctx.extra, dict):
                        ctx.extra["transcription"] = transcribed_text
                except Exception:
                    pass
            ctx.is_audio = False  # transcription is text
            multimodal_ctx.is_audio_input = False  # disable audio input for TTS below

        # ---------------------- REGULAR CHAT PATH (or no-audio in MODE_AUDIO) ----------------------
        # Build contents for chat/multimodal (will be overridden for TTS below)
        inputs = self.build_input(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            history=context.history,
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
        )

        # Best-effort input tokens estimate
        self.reset_tokens()
        count_msgs = self._build_count_messages(prompt, system_prompt, model, context.history)
        self.input_tokens += self.window.core.tokens.from_messages(count_msgs, model.id)

        # Tools -> merge app-defined tools with remote tools
        base_tools = self.window.core.api.google.tools.prepare(model, functions)
        remote_tools = self.window.core.api.google.build_remote_tools(model)
        if base_tools:
            remote_tools = [] # do not mix local and remote tools
        tools = (base_tools or []) + (remote_tools or [])

        # Sampling
        temperature = self.window.core.config.get('temperature')
        top_p = self.window.core.config.get('top_p')
        max_tokens = context.max_tokens if context.max_tokens else None

        # Base config
        cfg_kwargs: Dict[str, Any] = dict(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt if system_prompt else None,
            tools=tools if tools else None,
        )

        # ---------- AUDIO MODE (output TTS) ----------
        if mode == MODE_AUDIO:
            stream = False  # TTS non-stream in this app
            supports_tts = self._supports_tts(model.id)

            # Force minimal single-turn input for TTS (text only), using prompt possibly replaced by transcription
            inputs = [Content(role="user", parts=[Part.from_text(text=str(prompt or ""))])]

            # Remove params not used by TTS flow (and that sometimes cause issues)
            for key in ("temperature", "top_p", "max_output_tokens", "system_instruction", "tools"):
                if key in cfg_kwargs:
                    del cfg_kwargs[key]

            # Voice selection (case-sensitive name)
            voice_name = "Kore"
            try:
                tmp = self.window.core.plugins.get_option("audio_output", "google_voice_native")
                if tmp:
                    name = str(tmp).strip()
                    mapping = {"kore": "Kore", "puck": "Puck", "charon": "Charon", "verse": "Verse", "legend": "Legend"}
                    voice_name = mapping.get(name.lower(), name)
            except Exception:
                pass

            if supports_tts:
                cfg_kwargs["response_modalities"] = ["AUDIO"]
                cfg_kwargs["speech_config"] = gtypes.SpeechConfig(
                    voice_config=gtypes.VoiceConfig(
                        prebuilt_voice_config=gtypes.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                )
            # else: fallback to text-only below

        cfg = gtypes.GenerateContentConfig(**cfg_kwargs)
        params = dict(model=model.id, contents=inputs, config=cfg)

        if stream and mode != MODE_AUDIO:
            return client.models.generate_content_stream(**params)
        else:
            return client.models.generate_content(**params)

    def unpack_response(self, mode: str, response, ctx: CtxItem):
        """
        Unpack non-streaming response from Google GenAI and set context.
        """
        if mode == MODE_AUDIO:
            # Prefer audio if present
            audio_bytes, mime = self.window.core.api.google.audio.extract_first_audio_part(response)
            if audio_bytes:
                # Google returns PCM16 24kHz mono for TTS; wrap to WAV (base64) for UI compatibility
                # https://ai.google.dev/gemini-api/docs/speech-generation
                if mime == "audio/pcm" or mime.startswith("audio/"):
                    wav_b64 = self.window.core.api.google.audio.pcm16_to_wav_base64(audio_bytes, rate=24000)
                    ctx.audio_output = wav_b64
                    ctx.is_audio = True
                # Text transcript is typically not present for TTS; still try:
                txt = self.extract_text(response)
                ctx.output = txt or "..."
            else:
                # No audio present -> fallback to text
                ctx.output = self.extract_text(response)

            # Usage
            try:
                usage = getattr(response, "usage_metadata", None)
                if usage:
                    p = getattr(usage, "prompt_token_count", 0) or 0
                    c = getattr(usage, "candidates_token_count", 0) or 0
                    ctx.set_tokens(p, c)
            except Exception:
                pass

            return  # audio path done

        # ---- regular chat/completion ----
        ctx.output = self.extract_text(response)

        # Extract function calls
        calls = self.extract_tool_calls(response)
        if calls:
            ctx.tool_calls = calls

        # Usage if available
        try:
            usage = getattr(response, "usage_metadata", None)
            if usage:
                p = getattr(usage, "prompt_token_count", 0) or 0
                c = getattr(usage, "candidates_token_count", 0) or 0
                ctx.set_tokens(p, c)
        except Exception:
            pass

        # Best-effort: inline images / links (image-output in chat)
        try:
            self._extract_inline_images_and_links(response, ctx)
        except Exception:
            pass

    def extract_text(self, response) -> str:
        """
        Extract output text.
        """
        txt = getattr(response, "text", None) or getattr(response, "output_text", None)
        if txt:
            return str(txt).strip()
        try:
            cands = getattr(response, "candidates", None) or []
            if cands:
                parts = getattr(cands[0], "content", None)
                parts = getattr(parts, "parts", None) or []
                out = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        out.append(str(t))
                return "".join(out).strip()
        except Exception:
            pass
        return ""

    def extract_tool_calls(self, response) -> List[dict]:
        """
        Extract tool calls in a format compatible with app's tool execution.
        Prefer response.function_calls (Python SDK), then fallback to parts[].function_call.
        Returns arguments as a Python dict (not a JSON string).

        :param response: Response object
        :return: List of tool calls
        """
        def _to_plain_dict(obj):
            # Convert pydantic/genai objects to plain dict recursively
            try:
                if hasattr(obj, "to_json_dict"):
                    return obj.to_json_dict()
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()  # pydantic v2
                if hasattr(obj, "to_dict"):
                    return obj.to_dict()
            except Exception:
                pass
            if isinstance(obj, dict):
                return {k: _to_plain_dict(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_to_plain_dict(x) for x in obj]
            return obj

        out: List[dict] = []

        # 1) response.function_calls
        fcs = getattr(response, "function_calls", None) or []
        for fc in fcs:
            name = getattr(fc, "name", "") or ""
            args_obj = getattr(fc, "args", {}) or {}
            args_dict = _to_plain_dict(args_obj) or {}
            # if str, try to parse
            if isinstance(args_dict, str):
                try:
                    import json
                    args_dict = json.loads(args_dict)
                except Exception:
                    args_dict = {}
            out.append({
                "id": getattr(fc, "id", "") or "",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": args_dict,  # <--- DICT, not string
                }
            })

        if out:
            return out

        # 2) Fallback: candidates -> parts[].function_call
        try:
            cands = getattr(response, "candidates", None) or []
            for cand in cands:
                parts = getattr(getattr(cand, "content", None), "parts", None) or []
                for part in parts:
                    fn = getattr(part, "function_call", None)
                    if not fn:
                        continue
                    name = getattr(fn, "name", "") or ""
                    args_obj = getattr(fn, "args", {}) or {}
                    args_dict = _to_plain_dict(args_obj) or {}
                    if isinstance(args_dict, str):
                        try:
                            import json
                            args_dict = json.loads(args_dict)
                        except Exception:
                            args_dict = {}
                    out.append({
                        "id": "",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": args_dict,  # <--- DICT
                        }
                    })
        except Exception:
            pass

        return out

    def _extract_inline_images_and_links(self, response, ctx: CtxItem) -> None:
        """
        Extract inline image parts (Gemini image output) and file links.
        - Saves inline_data (image/*) bytes to files and appends paths to ctx.images.
        - Appends HTTP(S) image URIs from file_data to ctx.urls.
        """
        images: list[str] = []
        urls: list[str] = []

        try:
            cands = getattr(response, "candidates", None) or []
            for cand in cands:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    # Inline image bytes (image preview / image generation in chat)
                    blob = getattr(p, "inline_data", None)
                    if blob:
                        mime = (getattr(blob, "mime_type", "") or "").lower()
                        if mime.startswith("image/"):
                            data = getattr(blob, "data", None)
                            if data:
                                img_bytes = self._ensure_bytes(data)
                                if img_bytes:
                                    img_path = self.window.core.image.gen_unique_path(ctx)
                                    with open(img_path, "wb") as f:
                                        f.write(img_bytes)
                                    images.append(img_path)

                    # File data URI (may contain http/https or gs://)
                    fdata = getattr(p, "file_data", None)
                    if fdata:
                        uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                        mime = (getattr(fdata, "mime_type", "") or "").lower()
                        if uri and mime.startswith("image/"):
                            # Store only as URL; downloading is out of scope here.
                            if uri.startswith("http://") or uri.startswith("https://"):
                                urls.append(uri)
        except Exception:
            # Best-effort only
            pass

        if images:
            if not isinstance(ctx.images, list):
                ctx.images = []
            ctx.images.extend(images)

        if urls:
            if ctx.urls is None:
                ctx.urls = []
            ctx.urls.extend(urls)

    @staticmethod
    def _ensure_bytes(data) -> bytes | None:
        """Return raw bytes from SDK part.inline_data.data which can be bytes or base64 string."""
        try:
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            if isinstance(data, str):
                import base64
                return base64.b64decode(data)
        except Exception:
            return None
        return None

    def build_input(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
    ) -> List[Content]:
        """
        Build Google GenAI contents list

        :param prompt: User prompt
        :param system_prompt: System prompt/instruction
        :param model: ModelItem
        :param history: List of CtxItem for history
        :param attachments: Dict of AttachmentItem for images
        :param multimodal_ctx: MultimodalContext for audio
        :return: List of Content
        """
        contents: List[Content] = []

        # System instruction is passed separately (system_instruction),
        # so we do not build an explicit system role part here.

        # Append conversation history
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                MODE_CHAT if model and MODE_CHAT in model.mode else MODE_CHAT,
                self.window.core.tokens.from_user(prompt, system_prompt),
                self._fit_ctx(model),
            )
            for item in items:
                if item.final_input:
                    contents.append(Content(role="user", parts=[Part.from_text(text=str(item.final_input))]))
                if item.final_output:
                    contents.append(Content(role="model", parts=[Part.from_text(text=str(item.final_output))]))

        # Current user message with multimodal parts
        parts = self._build_user_parts(
            content=str(prompt),
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
        )
        contents.append(Content(role="user", parts=parts))

        return contents

    def _build_user_parts(
            self,
            content: str,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
    ) -> List[Part]:
        """
        Build user message parts (text + images + audio)

        :param content: User text content
        :param attachments: Dict of AttachmentItem for images
        :param multimodal_ctx: MultimodalContext for audio
        :return: List of Part
        """
        parts: List[Part] = []
        if content:
            parts.append(Part.from_text(text=str(content)))

        if attachments:
            img_parts = self.window.core.api.google.vision.build_parts(content, attachments)
            parts.extend(img_parts)

        if multimodal_ctx and multimodal_ctx.is_audio_input and multimodal_ctx.audio_data:
            audio_format = (multimodal_ctx.audio_format or "wav").lower()
            mime = f"audio/{audio_format}"
            parts.append(Part.from_bytes(data=multimodal_ctx.audio_data, mime_type=mime))

        return parts

    def _fit_ctx(self, model: ModelItem) -> int:
        """
        Fit to max model tokens (best-effort, uses model.ctx if present)

        :param model: ModelItem
        :return: max context tokens
        """
        max_ctx_tokens = self.window.core.config.get('max_total_tokens')
        if model and model.ctx and 0 < model.ctx < max_ctx_tokens:
            max_ctx_tokens = model.ctx
        return max_ctx_tokens

    def _build_count_messages(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
    ) -> List[dict]:
        """
        Build simple messages structure for local token estimation

        :param prompt: User prompt
        :param system_prompt: System prompt/instruction
        :param model: ModelItem
        :param history: List of CtxItem for history
        :return: List of messages dicts with 'role' and 'content' keys
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if self.window.core.config.get('use_context'):
            used_tokens = self.window.core.tokens.from_user(prompt, system_prompt)
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                MODE_CHAT,
                used_tokens,
                self._fit_ctx(model),
            )
            for item in items:
                if item.final_input:
                    messages.append({"role": "user", "content": str(item.final_input)})
                if item.final_output:
                    messages.append({"role": "assistant", "content": str(item.final_output)})

        messages.append({"role": "user", "content": str(prompt)})
        return messages


    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Get input tokens counter (estimated before sending)

        :return: input tokens count
        """
        return self.input_tokens

    @staticmethod
    def _supports_tts(model_id: Optional[str]) -> bool:
        """
        Heuristic check if the model supports native TTS.
        - Official TTS models contain '-tts' in id (e.g. 'gemini-2.5-flash-preview-tts').
        - Future/preview names may contain 'native-audio'.
        """
        if not model_id:
            return False
        mid = model_id.lower()
        return ("-tts" in mid) or ("native-audio" in mid)