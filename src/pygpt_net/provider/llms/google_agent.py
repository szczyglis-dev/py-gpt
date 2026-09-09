#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.09 18:40:00                  #
# ================================================== #

from __future__ import annotations

import base64
import inspect
from typing import Any, ClassVar, Sequence

from google.genai import types
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.google_genai.utils import (
    adelete_uploaded_files,
    chat_from_gemini_response,
    prepare_chat_params,
)

from pygpt_net.provider.llms.agent_computer import AgentComputerBridge
from pygpt_net.provider.llms.google_capture import PyGPTGoogleGenAI


class AgentGoogleGenAI(PyGPTGoogleGenAI):
    """Google GenAI adapter used by Agents v2.

    Google Computer Use is a client-side tool.  LlamaIndex can describe it to
    Gemini but does not execute the action/screenshot continuation itself, so
    this adapter owns that loop and returns only the final/local-tool response
    to FunctionAgent.
    """

    MAX_COMPUTER_TURNS: ClassVar[int] = 1000

    _pygpt_runtime: Any = PrivateAttr(default=None)

    def bind_agents_v2_runtime(self, runtime):
        self._pygpt_runtime = runtime
        return self

    @staticmethod
    def _get(value: Any, key: str, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    @classmethod
    def _tool_has_field(cls, tool: Any, field: str) -> bool:
        value = cls._get(tool, field, None)
        return value is not None

    def _computer_enabled(self) -> bool:
        return any(
            self._tool_has_field(tool, "computer_use")
            for tool in (self._pygpt_remote_tools or [])
        )

    @staticmethod
    def _same_object(value: Any, candidates: list[Any]) -> bool:
        return any(value is candidate for candidate in candidates)

    @staticmethod
    def _without_server_side_invocations(tool_config):
        """Preserve function-calling config while removing Gemini server-tool circulation."""
        if tool_config is None:
            return None
        if isinstance(tool_config, dict):
            data = dict(tool_config)
            data.pop("include_server_side_tool_invocations", None)
            return data or None
        try:
            data = tool_config.model_dump(exclude_none=True)
        except Exception:
            data = None
        if isinstance(data, dict):
            data.pop("include_server_side_tool_invocations", None)
            try:
                return types.ToolConfig(**data) if data else None
            except Exception:
                pass
        try:
            tool_config.include_server_side_tool_invocations = False
        except Exception:
            pass
        return tool_config

    def _prepare_chat_with_tools(self, *args, **kwargs):
        prepared = super()._prepare_chat_with_tools(*args, **kwargs)
        if not self._computer_enabled():
            return prepared

        # The Generate Content Computer Use endpoint currently rejects
        # computer_use + google_search in the same request.  Match normal PyGPT
        # Chat by keeping provider-native Computer Use exclusive from other
        # provider built-ins, while retaining Agents v2 custom/local functions
        # (which Gemini explicitly supports alongside Computer Use).
        remote = list(self._pygpt_remote_tools or [])
        all_tools = prepared.get("tools") or []
        if not isinstance(all_tools, list):
            all_tools = [all_tools]
        local_tools = [tool for tool in all_tools if not self._same_object(tool, remote)]
        computer_tools = [tool for tool in remote if self._tool_has_field(tool, "computer_use")]
        prepared["tools"] = [*computer_tools, *local_tools]

        # include_server_side_tool_invocations is for built-in server tools +
        # custom function circulation. Computer Use itself is client-side and
        # already uses function_call/function_response context circulation.
        cleaned = self._without_server_side_invocations(prepared.get("tool_config"))
        if cleaned is None:
            prepared.pop("tool_config", None)
        else:
            prepared["tool_config"] = cleaned
        return prepared

    def _runtime_ctx(self):
        runtime = self._pygpt_runtime
        if runtime is None:
            return None
        return getattr(getattr(runtime, "context", None), "ctx", None)

    def _computer_api(self):
        runtime = self._pygpt_runtime
        if runtime is None:
            raise RuntimeError("Agents v2 runtime is not bound to the Google adapter")
        return runtime.window.core.api.google.computer

    def _computer_calls(self, raw_response: Any) -> tuple[list[dict], bool]:
        """Return native Computer Use calls and whether any custom call is mixed in."""
        computer = self._computer_api()
        calls = []
        custom_found = False
        for name, args, call_id in computer._iter_function_calls(raw_response):
            local_name, local_args = computer._map_function(name, args or {})
            if not local_name:
                custom_found = True
                continue
            calls.append({
                "id": str(call_id or ""),
                "name": str(name or ""),
                "args": dict(args or {}),
                "local_name": local_name,
                "local_args": local_args,
            })
        return calls, custom_found

    @staticmethod
    def _response_for_index(response: Any, index: int) -> dict:
        value = response
        if isinstance(response, list):
            value = response[index] if 0 <= index < len(response) else (response[-1] if response else None)
        if isinstance(value, dict):
            nested = value.get("result")
            if isinstance(nested, dict):
                out = dict(nested)
            elif nested is not None:
                out = {"result": nested}
            else:
                out = dict(value)
            status = str(out.get("result", "") or "").lower()
            out.setdefault("ok", status not in {"error", "failed", "failure"})
            return out
        if value is None:
            return {"ok": True}
        text = str(value)
        return {"ok": not text.lower().startswith("error"), "result": text}

    def _record_google_safety(self, calls: list[dict]) -> None:
        ctx = self._runtime_ctx()
        if ctx is None:
            return
        computer = self._computer_api()
        for call in calls:
            computer._record_safety_decision(ctx, call.get("name") or "", call.get("args") or {})
        security = self._pygpt_runtime.window.core.security
        if security.should_halt_computer(ctx):
            if not isinstance(getattr(ctx, "extra", None), dict):
                ctx.extra = {}
            ctx.extra["computer_safety_waiting"] = True
            raise RuntimeError(
                "Computer Use paused by security policy. Confirm the pending operation in chat before continuing."
            )

    def _safety_acknowledgement(self) -> bool:
        ctx = self._runtime_ctx()
        if ctx is None or not isinstance(getattr(ctx, "extra", None), dict):
            return False
        if not ctx.extra.get("computer_safety_decisions"):
            return False
        try:
            return bool(self._pygpt_runtime.window.core.security.can_acknowledge_computer_safety(ctx))
        except Exception:
            return False

    @staticmethod
    def _screenshot_response_part(screenshot_b64: str):
        data = base64.b64decode(screenshot_b64)
        blob = types.FunctionResponseBlob(mime_type="image/png", data=data)
        return types.FunctionResponsePart(inline_data=blob)

    def _function_response_part(
            self,
            call: dict,
            response: dict,
            screenshot_part,
    ):
        payload = dict(response or {"ok": True})
        if self._safety_acknowledgement():
            payload["safety_acknowledgement"] = True
        kwargs = {
            "name": call.get("name") or "",
            "response": payload,
            "parts": [screenshot_part],
        }
        call_id = call.get("id") or None
        try:
            fr = types.FunctionResponse(id=call_id, **kwargs) if call_id \
                else types.FunctionResponse(**kwargs)
            return types.Part(function_response=fr)
        except Exception:
            # Compatibility with google-genai versions where id is not yet
            # accepted by FunctionResponse/Part.from_function_response.
            return types.Part.from_function_response(
                name=kwargs["name"],
                response=payload,
                parts=kwargs["parts"],
            )

    async def _execute_computer_calls(self, calls: list[dict]):
        self._record_google_safety(calls)
        commands = [
            {"cmd": call["local_name"], "params": dict(call.get("local_args") or {})}
            for call in calls
        ]
        execution = await AgentComputerBridge(self._pygpt_runtime).execute(
            commands,
            tool_label="computer_use",
            require_screenshot=True,
        )
        screenshot_part = self._screenshot_response_part(execution.screenshot_b64)
        return [
            self._function_response_part(
                call,
                self._response_for_index(execution.response, index),
                screenshot_part,
            )
            for index, call in enumerate(calls)
        ]

    @staticmethod
    def _chat_from_gemini(raw_response: Any) -> ChatResponse:
        """Convert one non-stream Gemini response across LlamaIndex versions.

        Newer llama-index-llms-google-genai requires the mutable
        ``existing_content`` accumulator explicitly; older releases accepted
        only the response. Keep Agents v2 compatible with both APIs.
        """
        try:
            params = inspect.signature(chat_from_gemini_response).parameters
        except (TypeError, ValueError):
            params = {}
        if "existing_content" in params or len(params) >= 2:
            return chat_from_gemini_response(raw_response, [])
        return chat_from_gemini_response(raw_response)

    async def _achat_with_computer(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        generation_config = {
            **(self._generation_config or {}),
            **kwargs.pop("generation_config", {}),
        }
        params = {**kwargs, "generation_config": generation_config}
        next_msg, chat_kwargs, file_api_names = await prepare_chat_params(
            self.model,
            messages,
            self.file_mode,
            self._client,
            **params,
        )
        chat = self._client.aio.chats.create(**chat_kwargs)

        try:
            payload = next_msg.parts if isinstance(next_msg, types.Content) else next_msg
            raw = await chat.send_message(payload)
            self._capture_urls(raw)

            for turn in range(self.MAX_COMPUTER_TURNS + 1):
                calls, custom_found = self._computer_calls(raw)
                if not calls:
                    return self._chat_from_gemini(raw)

                if custom_found:
                    # This should not occur with the default non-parallel Agents v2
                    # tool policy. Returning the provider response is safer than
                    # submitting an incomplete continuation that omits a custom
                    # function result.
                    runtime = self._pygpt_runtime
                    if runtime is not None:
                        runtime.verbose.log(
                            "GOOGLE COMPUTER USE MIXED CALLS",
                            {"computer_calls": calls},
                            actor="orchestrator",
                        )
                    return self._chat_from_gemini(raw)

                if turn >= self.MAX_COMPUTER_TURNS:
                    break

                runtime = self._pygpt_runtime
                if runtime is not None:
                    runtime.verbose.log("GOOGLE COMPUTER USE", {
                        "turn": turn + 1,
                        "calls": calls,
                    }, actor="orchestrator")

                response_parts = await self._execute_computer_calls(calls)
                raw = await chat.send_message(response_parts)
                self._capture_urls(raw)

            raise RuntimeError(
                f"Google Computer Use exceeded the safety limit of {self.MAX_COMPUTER_TURNS} continuation turns"
            )
        finally:
            if self.file_mode in ("fileapi", "hybrid"):
                await adelete_uploaded_files(file_api_names, self._client)

    async def _achat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        if not self._computer_enabled():
            return await super()._achat(messages, **kwargs)
        return await self._achat_with_computer(messages, **kwargs)

    async def _astream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any):
        if not self._computer_enabled():
            return await super()._astream_chat(messages, **kwargs)

        # Computer Use actions need a complete FunctionCall before local
        # execution. Agents v2 handles final answer streaming at runtime level,
        # so keep only the provider-internal computer loop non-streaming.
        response = await self._achat_with_computer(messages, **kwargs)

        async def gen():
            if not getattr(response, "delta", None):
                try:
                    response.delta = str(response.message.content or "")
                except Exception:
                    pass
            yield response

        return gen()
