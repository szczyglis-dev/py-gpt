#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

import os
from typing import Optional, Dict, Any, List, Tuple

from google.genai import types as gtypes
from google.genai.types import Content, Part

from pygpt_net.core.types import MODE_CHAT, MODE_AUDIO, MODE_COMPUTER, MODE_RESEARCH
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

    def send(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ):
        """
        Call Google GenAI for chat / multimodal / audio / computer use.

        :param context: BridgeContext with prompt, model, history, mode, etc.
        :param extra: Extra parameters (not used currently)
        :return: Response object or generator (if streaming)
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
                temperature=self.window.core.config.get('temperature'),
                top_p=self.window.core.config.get('top_p'),
                max_output_tokens=context.max_tokens if context.max_tokens else None,
            )
            trans_resp = client.models.generate_content(
                model=transcribe_model,
                contents=trans_inputs,
                config=trans_cfg,
            )
            transcribed_text = self.extract_text(trans_resp).strip()
            if transcribed_text:
                prompt = transcribed_text
                ctx.input = transcribed_text
                try:
                    if isinstance(ctx.extra, dict):
                        ctx.extra["transcription"] = transcribed_text
                except Exception:
                    pass
            ctx.is_audio = False
            multimodal_ctx.is_audio_input = False

        # ---------------------- REGULAR CHAT/COMPUTER PATH ----------------------
        inputs = self.build_input(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            history=context.history,
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
            mode=mode,
        )

        # Best-effort input tokens estimate
        self.reset_tokens()
        count_msgs = self._build_count_messages(prompt, system_prompt, model, context.history, mode)
        self.input_tokens += self.window.core.tokens.from_messages(count_msgs, model.id)

        # Tools -> merge app-defined tools with remote tools
        base_tools = self.window.core.api.google.tools.prepare(model, functions)
        remote_tools = self.window.core.api.google.remote_tools.build_remote_tools(model)

        # Note: Combining native (remote) tools with function declarations is documented as Live API-only.
        if base_tools:
            remote_tools = []
        tools = (base_tools or []) + (remote_tools or [])

        # Enable Computer Use tool in computer mode (use the official Tool/ComputerUse object)
        if mode == MODE_COMPUTER or (model and isinstance(model.id, str) and "computer-use" in model.id.lower()):
            tool = self.window.core.api.google.computer.get_tool()
            tools = [tool]  # reset tools to only Computer Use (multiple tools not supported together)

        # Some models cannot use tools; keep behavior for image-only models
        if model and isinstance(model.id, str) and "-image" in model.id:
            tools = None

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

            inputs = [Content(role="user", parts=[Part.from_text(text=str(prompt or ""))])]

            # Remove params not used by TTS flow
            for key in ("temperature", "top_p", "max_output_tokens", "system_instruction", "tools"):
                if key in cfg_kwargs:
                    del cfg_kwargs[key]

            # Voice selection (case-sensitive name)
            voice_name = "Kore"
            try:
                tmp = self.window.core.plugins.get_option("audio_output", "google_genai_tts_voice")
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
        cfg = gtypes.GenerateContentConfig(**cfg_kwargs)
        params = dict(model=model.id, contents=inputs, config=cfg)

        if mode == MODE_RESEARCH:

            # Deep Research does not support audio inputs; if an audio snippet is present, transcribe it to text first.
            if has_audio_input:
                try:
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
                        temperature=self.window.core.config.get('temperature'),
                        top_p=self.window.core.config.get('top_p'),
                        max_output_tokens=context.max_tokens if context.max_tokens else None,
                    )
                    trans_resp = client.models.generate_content(
                        model=transcribe_model,
                        contents=trans_inputs,
                        config=trans_cfg,
                    )
                    transcribed_text = self.extract_text(trans_resp).strip()
                    if transcribed_text:
                        prompt = (str(prompt or "").strip() + "\n\n" + transcribed_text).strip() if prompt else transcribed_text
                        ctx.input = transcribed_text
                        try:
                            if isinstance(ctx.extra, dict):
                                ctx.extra["transcription"] = transcribed_text
                        except Exception:
                            pass
                except Exception:
                    pass
                # Ensure we don't send raw audio to Interactions API
                if multimodal_ctx:
                    multimodal_ctx.is_audio_input = False

            # Build single-turn multimodal input for Interactions API (no full chat history)
            research_parts = self._build_user_parts(
                content=str(prompt),
                attachments=attachments,
                multimodal_ctx=multimodal_ctx,
            )
            interactions_input = self._parts_to_interactions_input(research_parts)

            # Try to continue context with the last completed interaction (server-side state)
            prev_interaction_id, last_event_id, last_status = self._find_last_interaction_state(
                history=context.history,
                ctx=ctx,
            )
            try:
                if ctx.extra is None:
                    ctx.extra = {}
                if prev_interaction_id:
                    ctx.extra["previous_interaction_id"] = prev_interaction_id
                if last_event_id:
                    ctx.extra["google_last_event_id"] = last_event_id
                if last_status:
                    ctx.extra["google_interaction_status"] = last_status
            except Exception:
                pass

            # Deep Research agent must use background=True; stream=True enables live progress updates.
            create_kwargs: Dict[str, Any] = {
                "agent": model.id,
                "input": interactions_input if interactions_input else (str(prompt or "") or " "),
                "background": True,
                "stream": stream,
                "agent_config": {
                    "type": "deep-research",
                    "thinking_summaries": "auto"
                }
            }

            # Continue conversation on server using previous_interaction_id if available
            if prev_interaction_id:
                create_kwargs["previous_interaction_id"] = prev_interaction_id

            # Do not pass custom tools here; Deep Research manages its own built-in tools.
            return client.interactions.create(**create_kwargs)

        if stream and mode != MODE_AUDIO:
            return client.models.generate_content_stream(**params)
        else:
            return client.models.generate_content(**params)

    def unpack_response(
            self,
            mode: str,
            response, ctx: CtxItem
    ):
        """
        Unpack non-streaming response from Google GenAI and set context.

        :param mode: MODE_CHAT, MODE_AUDIO or MODE_COMPUTER
        :param response: Response object
        :param ctx: CtxItem to set output, audio_output, tokens, tool_calls
        """
        if mode == MODE_AUDIO:
            audio_bytes, mime = self.window.core.api.google.audio.extract_first_audio_part(response)
            if audio_bytes:
                if mime == "audio/pcm" or (isinstance(mime, str) and mime.startswith("audio/")):
                    wav_b64 = self.window.core.api.google.audio.pcm16_to_wav_base64(audio_bytes, rate=24000)
                    ctx.audio_output = wav_b64
                    ctx.is_audio = True
                txt = self.extract_text(response)
                ctx.output = txt or "..."
            else:
                ctx.output = self.extract_text(response)
            try:
                usage = getattr(response, "usage_metadata", None)
                if usage:
                    p = getattr(usage, "prompt_token_count", 0) or 0
                    c = getattr(usage, "candidates_token_count", 0) or 0
                    ctx.set_tokens(p, c)
            except Exception:
                pass
            return

        # ---- chat / computer ----
        ctx.output = self.extract_text(response) or ""

        # 1) Extract tool calls and store in ctx.tool_calls (backward-compatible shape)
        calls = self.extract_tool_calls(response)
        if calls:
            ctx.tool_calls = calls

        # 2) In MODE_COMPUTER: capture raw model parts (with thought_signature) for next FunctionResponse turn
        #    and translate Computer Use calls into plugin commands now.
        if mode == MODE_COMPUTER:
            candidate = None
            try:
                cands = getattr(response, "candidates", None) or []
                if cands:
                    candidate = cands[0]
            except Exception:
                pass

            if candidate and getattr(candidate, "content", None):
                parts = getattr(candidate.content, "parts", None) or []
                dump = self._dump_model_parts(parts)
                if dump:
                    if ctx.extra is None:
                        ctx.extra = {}
                    ctx.extra["prev_model_parts"] = dump

            tool_calls: List[dict] = []
            try:
                tool_calls, has_calls = self.window.core.api.google.computer.handle_stream_chunk(
                    ctx=ctx,
                    chunk=response,
                    tool_calls=tool_calls,
                )
            except Exception as e:
                has_calls = False
                print(f"Gemini computer-use mapping error: {e}")

            if has_calls and tool_calls:
                ctx.force_call = True
                self.window.core.debug.info("[chat] Google tool calls found, unpacking...")
                self.window.core.command.unpack_tool_calls_chunks(ctx, tool_calls)

            if calls:
                if ctx.extra is None:
                    ctx.extra = {}
                ctx.extra["function_response_required"] = True
                ctx.extra["function_response_source"] = "ctx.tool_calls"
                ctx.extra["function_response_reason"] = "computer_use"

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

        # Download Files API file_data parts if present
        try:
            self._maybe_download_response_files(response, ctx)
        except Exception:
            pass

    def extract_text(self, response) -> str:
        """
        Extract output text.

        Prefer response.text (Python SDK), then fallback to parts[].text.

        :param response: Response object
        :return: Extracted text
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
            try:
                if hasattr(obj, "to_json_dict"):
                    return obj.to_json_dict()
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
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
                    "arguments": args_dict,
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
                        "id": getattr(fn, "id", "") or "",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": args_dict,
                        }
                    })
        except Exception:
            pass

        return out

    def build_input(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
            mode: str = MODE_CHAT,
    ) -> List[Content]:
        """
        Build Google GenAI contents list

        :param prompt: User prompt
        :param system_prompt: System prompt/instruction
        :param model: ModelItem
        :param history: List of CtxItem for history
        :param attachments: Dict of AttachmentItem for images/screenshots
        :param multimodal_ctx: MultimodalContext for audio
        :param mode: MODE_CHAT / MODE_AUDIO / MODE_COMPUTER
        :return: List of Content
        """
        # FunctionResponse turn for Computer Use (strictly immediate after functionCall)
        if mode == MODE_COMPUTER and self.window.core.config.get('use_context'):
            hist = self.window.core.ctx.get_history(
                history,
                model.id,
                MODE_CHAT,
                self.window.core.tokens.from_user(prompt, system_prompt),
                self._fit_ctx(model),
            )
            fr_contents = self._build_function_responses_from_history(hist, attachments)
            if fr_contents:
                return fr_contents

        # Build conversation history first to detect "first input"
        items: List[CtxItem] = []
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                MODE_CHAT if model and MODE_CHAT in model.mode else MODE_CHAT,
                self.window.core.tokens.from_user(prompt, system_prompt),
                self._fit_ctx(model),
            )

        is_first_turn = (len(items) == 0)
        is_sandbox = bool(self.window.core.config.get("remote_tools.computer_use.sandbox", False))

        contents: List[Content] = []

        # Append conversation history (text only)
        for item in items:
            if item.final_input:
                contents.append(Content(role="user", parts=[Part.from_text(text=str(item.final_input))]))
            if item.final_output:
                contents.append(Content(role="model", parts=[Part.from_text(text=str(item.final_output))]))

        # Current user message:
        # - In MODE_COMPUTER attach initial screenshot only on the very first turn
        if mode == MODE_COMPUTER:
            initial_attachments = {}
            if is_first_turn and not attachments and not is_sandbox:
                self.window.controller.attachment.clear_silent()
                self.window.controller.painter.capture.screenshot(attach_cursor=True, silent=True)
                initial_attachments = self.window.core.attachments.get_all(mode)
            send_attachments = initial_attachments if initial_attachments else attachments
            parts = self._build_user_parts(
                content=str(prompt),
                attachments=send_attachments,
                multimodal_ctx=multimodal_ctx,
            )
        else:
            parts = self._build_user_parts(
                content=str(prompt),
                attachments=attachments,
                multimodal_ctx=multimodal_ctx,
            )
        contents.append(Content(role="user", parts=parts))

        return contents

    def _build_function_responses_from_history(
            self,
            history: Optional[List[CtxItem]],
            attachments: Optional[Dict[str, AttachmentItem]],
    ) -> Optional[List[Content]]:
        """
        Build FunctionResponse contents for the immediate next turn after executing
        Computer Use function calls. It reconstructs the last user -> model(functionCall) turn
        and returns [user_content, model_function_call_content, tool_function_response_content].
        """
        if not self.window.core.config.get('use_context') or not history:
            return None

        last_item = history[-1]
        if not getattr(last_item, "extra", None):
            return None
        if not last_item.extra.get("function_response_required"):
            return None

        # 1) Find the user message that started the current turn (previous item's input)
        prior_user_text = ""
        if len(history) >= 2:
            prev = history[-2]
            if getattr(prev, "final_input", None):
                prior_user_text = str(prev.final_input)

        if not prior_user_text and getattr(last_item, "input", None):
            prior_user_text = str(last_item.input)

        if not prior_user_text:
            prior_user_text = "..."

        user_content = Content(role="user", parts=[Part.from_text(text=prior_user_text)])

        # 2) Rebuild the model functionCall content with thought_signature preserved
        raw_parts = last_item.extra.get("prev_model_parts", [])
        model_parts = self._rehydrate_model_parts(raw_parts)
        if not model_parts:
            model_parts = self._rehydrate_from_tool_calls(getattr(last_item, "tool_calls", []))
        # append also text part if not empty
        if getattr(last_item, "final_output", None):
            output_text = str(last_item.final_output).strip()
            if output_text:
                model_parts.append(Part.from_text(text=output_text))

        model_fc_content = Content(role="model", parts=model_parts)

        # 3) Build a single tool content with N FunctionResponse parts (one per functionCall)
        screenshot_part = self._screenshot_function_response_part(attachments)
        fr_parts: List[Part] = []
        for p in model_parts:
            if getattr(p, "function_call", None):
                fn = p.function_call
                fr = Part.from_function_response(
                    name=fn.name,
                    response=self._minimal_tool_response(last_item),
                    parts=[screenshot_part] if screenshot_part else None
                )
                fr_parts.append(fr)

        if not fr_parts:
            return None

        tool_content = Content(role="tool", parts=fr_parts)

        return [user_content, model_fc_content, tool_content]

    def _rehydrate_from_tool_calls(self, calls: List[dict]) -> List[Part]:
        """
        Fallback rehydration when prev_model_parts are unavailable (no thought signatures).
        """
        parts: List[Part] = []
        for c in calls or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") != "function":
                continue
            fn = c.get("function") or {}
            name = fn.get("name")
            args = fn.get("arguments") or {}
            if not name:
                continue
            parts.append(Part.from_function_call(name=name, args=args))
        return parts

    def _dump_model_parts(self, parts: List[Part]) -> List[dict]:
        """
        Dump model parts into a JSON-serializable structure, preserving thought_signature.
        """
        out: List[dict] = []
        for p in parts or []:
            ts = getattr(p, "thought_signature", None)
            if getattr(p, "function_call", None):
                fn = p.function_call
                name = getattr(fn, "name", "") or ""
                args = getattr(fn, "args", {}) or {}
                out.append({
                    "type": "function_call",
                    "name": name,
                    "args": args,
                    "thought_signature": ts,
                })
            elif getattr(p, "text", None):
                out.append({"type": "text", "text": str(p.text)})
        return out

    def _rehydrate_model_parts(self, raw_parts: List[dict]) -> List[Part]:
        """
        Recreate SDK Part objects from dumped parts, including thought_signature on the Part.
        """
        parts: List[Part] = []
        for it in raw_parts or []:
            t = (it.get("type") or "").lower()
            if t == "function_call":
                name = it.get("name")
                args = it.get("args") or {}
                ts = it.get("thought_signature")
                if name:
                    parts.append(Part(function_call=gtypes.FunctionCall(name=name, args=args),
                                      thought_signature=ts))
            elif t == "text":
                parts.append(Part.from_text(text=str(it.get("text", ""))))
        return parts

    def _screenshot_function_response_part(
            self,
            attachments: Optional[Dict[str, AttachmentItem]]
    ) -> Optional[gtypes.FunctionResponsePart]:
        """
        Build FunctionResponsePart with inlineData PNG/JPEG screenshot from attachments.
        """
        if not attachments:
            return None

        chosen_path = None
        for _, att in attachments.items():
            if not att or not att.path:
                continue
            p = att.path
            if isinstance(p, str) and os.path.exists(p):
                ext = os.path.splitext(p)[1].lower()
                if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"):
                    chosen_path = p
                    if ext == ".png":
                        break

        if not chosen_path:
            return None

        try:
            with open(chosen_path, "rb") as f:
                data = f.read()
            blob = gtypes.FunctionResponseBlob(
                mime_type="image/png" if chosen_path.lower().endswith(".png") else "image/jpeg",
                data=data,
            )
            return gtypes.FunctionResponsePart(inline_data=blob)
        except Exception:
            return None

    @staticmethod
    def _minimal_tool_response(item: CtxItem) -> Dict[str, Any]:
        """
        Construct a minimal structured payload for FunctionResponse.response.
        """
        resp: Dict[str, Any] = {"ok": True}
        try:
            if item and item.extra and isinstance(item.extra, dict):
                outputs = item.extra.get("tool_output")
                if isinstance(outputs, list) and len(outputs) > 0:
                    last = outputs[-1]
                    if isinstance(last, dict):
                        if "result" in last and isinstance(last["result"], dict):
                            resp = last["result"]
                        if "error" in last:
                            resp["error"] = last["error"]
        except Exception:
            pass
        return resp

    def _extract_inline_images_and_links(
            self,
            response, ctx: CtxItem
    ) -> None:
        """
        Extract inline image parts (Gemini image output) and file links.
        """
        images: list[str] = []
        urls: list[str] = []

        try:
            cands = getattr(response, "candidates", None) or []
            for cand in cands:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []
                for p in parts:
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

                    fdata = getattr(p, "file_data", None)
                    if fdata:
                        uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                        mime = (getattr(fdata, "mime_type", "") or "").lower()
                        if uri and mime.startswith("image/"):
                            if uri.startswith("http://") or uri.startswith("https://"):
                                urls.append(uri)
        except Exception:
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
        """
        Return raw bytes from SDK part.inline_data.data which can be bytes or base64 string.
        """
        try:
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            if isinstance(data, str):
                import base64
                return base64.b64encode(bytes()) if data == "" else base64.b64decode(data)
        except Exception:
            return None
        return None

    def _build_user_parts(
            self,
            content: str,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
    ) -> List[Part]:
        """
        Build user message parts (text + images + audio)
        """
        self.window.core.api.google.vision.reset()
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
            mode: str = MODE_CHAT,
    ) -> List[dict]:
        """
        Build simple messages structure for local token estimation
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
        """
        return self.input_tokens

    @staticmethod
    def _supports_tts(model_id: Optional[str]) -> bool:
        """
        Heuristic check if the model supports native TTS.
        """
        if not model_id:
            return False
        mid = model_id.lower()
        return ("-tts" in mid) or ("native-audio" in mid)

    @staticmethod
    def _find_last_interaction_state(
            history: Optional[List[CtxItem]],
            ctx: CtxItem,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Resolve last known Interactions state:
        - previous_interaction_id: to continue conversation context
        - last_event_id: to resume streaming (not used here, but returned for completeness)
        - last_status: last known status string if available

        Looks at current ctx.extra first, then scans history from newest to oldest.
        """
        prev_interaction_id: Optional[str] = None
        last_event_id: Optional[str] = None
        last_status: Optional[str] = None

        try:
            if getattr(ctx, "extra", None) and isinstance(ctx.extra, dict):
                prev_interaction_id = (
                    ctx.extra.get("previous_interaction_id")
                    or ctx.extra.get("google_interaction_id")
                    or ctx.extra.get("google_last_interaction_id")
                )
                last_event_id = ctx.extra.get("google_last_event_id")
                last_status = ctx.extra.get("google_interaction_status")
        except Exception:
            pass

        if not prev_interaction_id and history:
            for item in reversed(history or []):
                ex = getattr(item, "extra", None)
                if not ex or not isinstance(ex, dict):
                    continue
                prev_interaction_id = (
                    ex.get("previous_interaction_id")
                    or ex.get("google_interaction_id")
                    or ex.get("google_last_interaction_id")
                    or prev_interaction_id
                )
                last_event_id = ex.get("google_last_event_id") or last_event_id
                last_status = ex.get("google_interaction_status") or last_status
                if prev_interaction_id and last_event_id:
                    break

        return prev_interaction_id, last_event_id, last_status

    @staticmethod
    def _mime_to_interactions_type(mime: str) -> Optional[str]:
        """
        Map MIME type to Interactions input type.
        """
        if not mime:
            return None
        m = mime.lower()
        if m.startswith("image/"):
            return "image"
        if m.startswith("audio/"):
            return "audio"
        if m.startswith("video/"):
            return "video"
        return None

    @staticmethod
    def _ensure_base64(data) -> Optional[str]:
        """
        Return base64 string from raw bytes or a base64 string.
        """
        try:
            if data is None:
                return None
            if isinstance(data, str):
                return data
            if isinstance(data, (bytes, bytearray)):
                import base64
                return base64.b64encode(bytes(data)).decode("utf-8")
        except Exception:
            return None
        return None

    def _parts_to_interactions_input(self, parts: List[Part]) -> List[Dict[str, Any]]:
        """
        Convert Responses API Part list into Interactions API input payload.
        """
        out: List[Dict[str, Any]] = []

        for p in parts or []:
            # Text
            t = getattr(p, "text", None)
            if t is not None:
                s = str(t).strip()
                if s:
                    out.append({"type": "text", "text": s})
                continue

            # Inline data (images/audio/video)
            inline = getattr(p, "inline_data", None)
            if inline:
                mime = (getattr(inline, "mime_type", "") or "").lower()
                typ = self._mime_to_interactions_type(mime)
                data = getattr(inline, "data", None)
                b64 = self._ensure_base64(data)
                if typ and b64:
                    out.append({"type": typ, "data": b64, "mime_type": mime})
                continue

            # File references (prefer URIs from Gemini Files API)
            fdata = getattr(p, "file_data", None)
            if fdata:
                uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                mime = (getattr(fdata, "mime_type", "") or "").lower()
                typ = self._mime_to_interactions_type(mime)
                if typ and uri:
                    out.append({"type": typ, "uri": uri})
                continue

        return out

    def _maybe_download_response_files(self, response, ctx: CtxItem) -> None:
        """
        Inspect non-stream response parts for Files API references and download them.
        """
        try:
            cands = getattr(response, "candidates", None) or []
            if not cands:
                return
            first = cands[0]
            content = getattr(first, "content", None)
            parts = getattr(content, "parts", None) or []
        except Exception:
            parts = []

        if not parts:
            return

        downloaded: List[str] = []
        for p in parts:
            fdata = getattr(p, "file_data", None)
            if not fdata:
                continue
            try:
                uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                prefer = getattr(fdata, "file_name", None) or getattr(fdata, "display_name", None)
                if not uri or not isinstance(uri, str):
                    continue
                # Only Gemini Files API refs are supported for direct download
                save_path = self.window.core.api.google.store.download_to_dir(uri, prefer_name=prefer)
                if save_path:
                    downloaded.append(save_path)
            except Exception:
                continue

        if downloaded:
            downloaded = self.window.core.filesystem.make_local_list(downloaded)
            if not isinstance(ctx.files, list):
                ctx.files = []
            for path in downloaded:
                if path not in ctx.files:
                    ctx.files.append(path)
            images = []
            for path in downloaded:
                ext = os.path.splitext(path)[1].lower().lstrip(".")
                if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                    images.append(path)
            if images:
                if not isinstance(ctx.images, list):
                    ctx.images = []
                ctx.images += images