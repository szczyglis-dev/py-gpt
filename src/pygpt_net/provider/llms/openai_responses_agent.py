#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import asyncio
import json
import warnings
from typing import Any, ClassVar, Sequence

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.openai import OpenAIResponses

from pygpt_net.provider.llms.agent_computer import (
    AgentComputerBridge,
    run_coroutine_sync,
    wait_for_computer_safety_confirmation,
)


class AgentOpenAIResponses(OpenAIResponses):
    """OpenAI Responses adapter used by Agents v2.

    Besides normal hosted-tool metadata handling, this adapter owns the local
    Computer Use continuation loop. LlamaIndex treats hosted tools as metadata,
    so without this bridge a ``computer_call`` is parsed but never executed.
    """

    MAX_COMPUTER_TURNS: ClassVar[int] = 1000

    _pygpt_urls: list[str] = PrivateAttr(default_factory=list)
    _pygpt_runtime: Any = PrivateAttr(default=None)

    def bind_computer_runtime(self, runtime):
        """Bind a PyGPT runtime that can execute provider-native Computer Use."""
        self._pygpt_runtime = runtime
        return self

    def bind_agents_v2_runtime(self, runtime):
        """Backward-compatible Agents v2 binder."""
        return self.bind_computer_runtime(runtime)

    @staticmethod
    def _get(value: Any, key: str, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    def _computer_enabled(self) -> bool:
        for tool in (getattr(self, "built_in_tools", None) or []):
            if self._get(tool, "type") == "computer":
                return True
        return False

    def _get_model_kwargs(self, **kwargs: Any):
        """Computer continuations require stored response IDs and ordered tool calls."""
        model_kwargs = super()._get_model_kwargs(**kwargs)
        if self._computer_enabled():
            # Computer Use is a stateful Responses loop. Store only requests for
            # runtimes where the computer hosted tool is actually enabled.
            model_kwargs["store"] = True
            # A simultaneous local function call + computer call would require
            # two independent outputs before a continuation can be submitted.
            model_kwargs["parallel_tool_calls"] = False
        return model_kwargs

    @staticmethod
    def _safe_dump(value: Any) -> Any:
        """Convert a Pydantic/SDK object to plain data without serializer noise."""
        if value is None or isinstance(value, (dict, list, str, int, float, bool)):
            return value

        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            try:
                # Pydantic v2 supports disabling serializer warnings explicitly.
                return model_dump(warnings=False)
            except TypeError:
                # Compatibility fallback for older Pydantic signatures.
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        return model_dump()
                except Exception:
                    pass
            except Exception:
                pass

        try:
            return dict(value)
        except Exception:
            pass
        try:
            data = getattr(value, "__dict__", None)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return value

    def _append_urls(self, urls) -> None:
        seen = set(self._pygpt_urls)
        for url in urls or []:
            if not isinstance(url, str):
                continue
            value = url.strip()
            if not value or value in seen:
                continue
            self._pygpt_urls.append(value)
            seen.add(value)

    def _capture_raw_urls(self, raw: Any) -> None:
        """Capture URLs from a Responses API event or final Response object."""
        if raw is None:
            return
        try:
            # Lazy import avoids coupling provider registration/import order to
            # the full OpenAI API package.
            from pygpt_net.provider.api.openai.utils import (
                extract_response_urls,
                extract_url_from_annotation,
                get_annotation_type,
            )

            response = getattr(raw, "response", None)
            if response is not None:
                self._append_urls(extract_response_urls(response))
            else:
                self._append_urls(extract_response_urls(raw))

            # Streaming Responses exposes citation annotations before the final
            # ResponseCompletedEvent. Keep them as an additional fallback.
            annotation = getattr(raw, "annotation", None)
            if annotation is not None and get_annotation_type(annotation) == "url_citation":
                url = extract_url_from_annotation(annotation)
                if url:
                    self._append_urls([url])
        except Exception:
            # URL capture is metadata-only and must never break agent execution.
            pass

    def _prepare_response(self, response: ChatResponse) -> ChatResponse:
        raw = getattr(response, "raw", None)
        self._capture_raw_urls(raw)

        try:
            from pygpt_net.provider.api.openai.utils import (
                extract_url_from_annotation,
                get_annotation_type,
            )

            for annotation in (response.additional_kwargs or {}).get("annotations", []) or []:
                if get_annotation_type(annotation) != "url_citation":
                    continue
                url = extract_url_from_annotation(annotation)
                if url:
                    self._append_urls([url])
        except Exception:
            pass

        # Crucial: AgentWorkflow will otherwise call raw.model_dump() itself and
        # trigger Pydantic serializer warnings for hosted web-search payloads.
        response.raw = self._safe_dump(raw)
        return response

    def pop_pygpt_urls(self) -> list[str]:
        """Return and clear URLs collected since the previous drain."""
        urls = list(self._pygpt_urls)
        self._pygpt_urls.clear()
        return urls

    def _raw_response(self, raw: Any) -> Any:
        """Return the final Response payload from a Response or streaming event."""
        if raw is None:
            return None
        nested = self._get(raw, "response")
        return nested if nested is not None else raw

    def _response_id(self, response: ChatResponse) -> str:
        payload = self._raw_response(getattr(response, "raw", None))
        value = self._get(payload, "id", "")
        return str(value or "")

    def _raw_output_items(self, response: ChatResponse) -> list[Any]:
        payload = self._raw_response(getattr(response, "raw", None))
        output = self._get(payload, "output", []) or []
        return list(output) if isinstance(output, (list, tuple)) else []

    def _computer_calls(self, response: ChatResponse) -> list[Any]:
        """Extract Computer Use calls from parsed metadata and final raw Responses payload."""
        calls = []
        seen = set()

        def append(item):
            if item is None or self._get(item, "type") != "computer_call":
                return
            call_id = str(self._get(item, "call_id", "") or self._get(item, "id", "") or id(item))
            if call_id in seen:
                return
            seen.add(call_id)
            calls.append(item)

        for item in (getattr(response, "additional_kwargs", None) or {}).get("built_in_tool_calls", []) or []:
            # Streaming integrations may put an event here rather than the call itself.
            append(self._get(item, "item", item))

        for item in self._raw_output_items(response):
            append(item)

        return calls

    def _runtime_ctx(self):
        runtime = self._pygpt_runtime
        if runtime is None:
            return None
        return getattr(getattr(runtime, "context", None), "ctx", None)

    def _check_stopped(self):
        runtime = self._pygpt_runtime
        if runtime is not None and runtime.is_stopped():
            raise asyncio.CancelledError("Agents v2 Computer Use cancelled")

    async def _computer_safety(self, call: Any) -> list[dict]:
        """Persist provider safety checks and return acknowledgements when allowed."""
        runtime = self._pygpt_runtime
        if runtime is None:
            return []
        ctx = self._runtime_ctx()
        if ctx is None:
            return []

        if not isinstance(getattr(ctx, "extra", None), dict):
            ctx.extra = {}

        computer_api = runtime.window.core.api.openai.computer
        computer_api.store_pending_safety_checks(ctx, call)
        security = runtime.window.core.security
        await wait_for_computer_safety_confirmation(runtime, ctx)

        if not security.can_acknowledge_computer_safety(ctx):
            return []
        checks = ctx.extra.get("pending_safety_checks") or []
        out = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            out.append({
                "id": check.get("id"),
                "code": check.get("code"),
                "message": check.get("message"),
            })
        return out

    async def _execute_computer_call(self, call: Any) -> dict:
        """Execute one ordered Computer Use action batch and return its screenshot output."""
        self._check_stopped()
        runtime = self._pygpt_runtime
        if runtime is None:
            raise RuntimeError("PyGPT Computer Use runtime is not bound to the OpenAI Responses adapter")

        window = runtime.window
        computer_api = window.core.api.openai.computer
        call_id = str(self._get(call, "call_id", "") or "")
        response_item_id = str(self._get(call, "id", "") or "")
        if not call_id:
            raise RuntimeError("OpenAI Computer Use returned a computer_call without call_id")

        acknowledgements = await self._computer_safety(call)
        actions = computer_api.get_actions(call)
        runtime.emit_runtime_status("status.agent_v2.tool", tool="computer_use")
        runtime.verbose.log("COMPUTER USE CALL", {
            "call_id": call_id,
            "id": response_item_id,
            "actions": self._safe_dump(actions),
        }, actor="orchestrator")

        # Reuse the shared executor used by Google/Anthropic so unsupported or
        # denied commands produce a concrete worker result instead of being
        # silently treated as successful.
        tool_calls = []
        tool_calls, _ = computer_api.handle_actions(
            id=response_item_id,
            call_id=call_id,
            actions=actions,
            tool_calls=tool_calls,
        )
        commands = []
        for tool_call in tool_calls:
            function = self._get(tool_call, "function", {}) or {}
            name = str(self._get(function, "name", "") or "")
            if not name:
                continue
            raw_args = self._get(function, "arguments", "{}")
            if isinstance(raw_args, str):
                try:
                    params = json.loads(raw_args or "{}")
                except Exception:
                    params = {}
            elif isinstance(raw_args, dict):
                params = dict(raw_args)
            else:
                params = {}
            commands.append({"cmd": name, "params": params})

        execution = await AgentComputerBridge(runtime).execute(
            commands,
            tool_label="computer_use",
            require_screenshot=True,
        )
        screenshot_b64 = execution.screenshot_b64

        execution_errors = []
        for response in execution.response if isinstance(execution.response, list) else [execution.response]:
            if not isinstance(response, dict):
                continue
            result = response.get("result")
            if isinstance(result, dict) and result.get("error"):
                execution_errors.append(str(result.get("error")))
            elif isinstance(result, str) and result.lower().startswith("error"):
                execution_errors.append(result)
        output = {
            "type": "computer_call_output",
            "call_id": call_id,
            "output": {
                "type": "computer_screenshot",
                "image_url": f"data:image/png;base64,{screenshot_b64}",
                "detail": "original",
            },
        }
        if acknowledgements:
            output["acknowledged_safety_checks"] = acknowledgements
        if execution_errors:
            # Internal marker only. _continue_computer_chain converts it to a
            # normal input_text item; it is never sent as part of the strict
            # computer_call_output schema.
            output["_pygpt_error"] = "\n".join(dict.fromkeys(execution_errors))
        try:
            window.core.security.clear_computer_safety(self._runtime_ctx())
        except Exception:
            pass
        return output

    async def _continue_computer_chain(
            self,
            response: ChatResponse,
            kwargs: dict[str, Any],
    ) -> ChatResponse:
        """Execute native Computer Use calls until the model stops requesting them.

        The continuation rule is intentionally narrow: submit another Responses
        request only when we have actually executed a ``computer_call`` and have
        a ``computer_call_output`` screenshot to return.  An assistant/message
        response with no computer call is already the result of that tool round
        and must be returned to FunctionAgent as-is.  In particular, never issue
        an extra empty-input continuation for ``phase=commentary``; doing so can
        make the model start a new Computer Use action after it has already
        reported success.
        """
        current = response
        for turn in range(self.MAX_COMPUTER_TURNS):
            calls = self._computer_calls(current)
            if not calls:
                return current

            previous_response_id = self._response_id(current)
            if not previous_response_id:
                raise RuntimeError("Unable to continue Computer Use: missing OpenAI response id")

            outputs = []
            for call in calls:
                outputs.append(await self._execute_computer_call(call))

            api_outputs = []
            for item in outputs:
                payload = dict(item)
                error = str(payload.pop("_pygpt_error", "") or "").strip()
                api_outputs.append(payload)
                if error:
                    api_outputs.append({
                        "role": "user",
                        "content": [{
                            "type": "input_text",
                            "text": f"[PyGPT Computer Use executor] Error: {error}",
                        }],
                    })

            self._check_stopped()
            model_kwargs = self._get_model_kwargs(**dict(kwargs or {}))
            model_kwargs["previous_response_id"] = previous_response_id
            # A forced tool choice from FunctionAgent must not leak into the
            # continuation. After receiving the screenshot the model is free to
            # return a normal assistant response instead of calling Computer Use
            # again.
            model_kwargs["tool_choice"] = "auto"

            runtime = self._pygpt_runtime
            if runtime is not None:
                runtime.verbose.log("COMPUTER USE CONTINUE", {
                    "turn": turn + 1,
                    "previous_response_id": previous_response_id,
                    "outputs": [
                        {"type": item.get("type"), "call_id": item.get("call_id")}
                        for item in outputs
                    ],
                }, actor="orchestrator")

            raw = await self._aclient.responses.create(
                input=api_outputs,
                stream=False,
                **model_kwargs,
            )
            parsed = self._parse_response_output(raw.output)
            parsed.raw = raw
            parsed.additional_kwargs["usage"] = getattr(raw, "usage", None)
            current = self._prepare_response(parsed)

        raise RuntimeError(
            f"Computer Use exceeded the safety limit of {self.MAX_COMPUTER_TURNS} continuation turns"
        )

    def _chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        """Sync LlamaIndex entry point used by Chat with Files.

        Reuse the authoritative async Computer Use continuation instead of
        implementing a second provider loop.
        """
        if not self._computer_enabled():
            return super()._chat(messages, **kwargs)
        return run_coroutine_sync(self._achat(messages, **kwargs))

    def _stream_chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ):
        if not self._computer_enabled():
            return super()._stream_chat(messages, **kwargs)

        # Computer actions require complete provider call objects before they can
        # be executed. Run only the provider-internal loop non-streaming, then
        # expose the final response through the normal synchronous stream API.
        response = run_coroutine_sync(self._achat(messages, **kwargs))

        def gen():
            if not getattr(response, "delta", None):
                try:
                    response.delta = str(response.message.content or "")
                except Exception:
                    pass
            yield response

        return gen()

    async def _achat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        response = await super()._achat(messages, **kwargs)
        response = self._prepare_response(response)
        if self._computer_enabled() and self._computer_calls(response):
            response = await self._continue_computer_chain(response, dict(kwargs))
        return response

    async def _astream_chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ):
        stream = await super()._astream_chat(messages, **kwargs)

        async def gen():
            last_response = None
            async for response in stream:
                prepared = self._prepare_response(response)
                last_response = prepared
                yield prepared

            # Upstream streaming currently exposes hosted Computer Use calls
            # inconsistently across versions. The final response.completed raw
            # payload still contains the computer_call, so inspect it after the
            # stream and continue locally when needed.
            if (
                    last_response is not None
                    and self._computer_enabled()
                    and self._computer_calls(last_response)
            ):
                final_response = await self._continue_computer_chain(last_response, dict(kwargs))
                if not getattr(final_response, "delta", None):
                    try:
                        final_response.delta = str(final_response.message.content or "")
                    except Exception:
                        pass
                yield final_response

        return gen()
