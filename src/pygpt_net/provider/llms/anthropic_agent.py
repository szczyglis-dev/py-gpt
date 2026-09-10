#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.09 18:30:00                  #
# ================================================== #

from __future__ import annotations

import json
from typing import Any, ClassVar, Sequence

from llama_index.core.base.llms.types import ChatMessage, ChatResponse, LLMMetadata, MessageRole
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.anthropic.utils import (
    anthropic_modelname_to_contextsize,
    is_function_calling_model,
    messages_to_anthropic_messages,
)

from pygpt_net.provider.llms.agent_computer import AgentComputerBridge, run_coroutine_sync


class AgentAnthropic(Anthropic):
    """Anthropic adapter used by Agents v2.

    LlamaIndex can forward provider-native Anthropic tools, but Computer Use is
    client-side and therefore cannot be left to FunctionAgent as a normal tool
    call.  This adapter executes Anthropic Computer Use calls through PyGPT and
    performs the provider-specific ``tool_result`` continuation internally.
    """

    MAX_COMPUTER_TURNS: ClassVar[int] = 1000

    _pygpt_runtime: Any = PrivateAttr(default=None)

    def __init__(self, *args, proxy: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        if not proxy:
            return

        # Match the proxy behavior used by the regular PyGPT Anthropic LLM.
        from anthropic import DefaultHttpxClient
        self._client = self._client.with_options(
            http_client=DefaultHttpxClient(proxy=proxy)
        )

        import httpx
        try:
            async_http = httpx.AsyncClient(proxy=proxy)  # httpx >= 0.28
        except TypeError:
            async_http = httpx.AsyncClient(proxies=proxy)  # httpx <= 0.27
        self._aclient = self._aclient.with_options(http_client=async_http)

    def bind_computer_runtime(self, runtime):
        self._pygpt_runtime = runtime
        return self

    def bind_agents_v2_runtime(self, runtime):
        return self.bind_computer_runtime(runtime)

    @staticmethod
    def _metadata_aliases(model_name: str) -> list[str]:
        """Return conservative aliases for future/custom Anthropic model IDs.

        LlamaIndex keeps a hard-coded context-window table and can therefore
        reject a valid provider model before the first API request. PyGPT's
        models.json is updated independently, so Agents v2 must not depend on
        that table being newer than the selected model.
        """
        value = str(model_name or "").strip()
        aliases = []
        current = value
        while current:
            head, sep, tail = current.rpartition("-")
            if not sep or not tail.isdigit():
                break
            current = head
            if current and current not in aliases:
                aliases.append(current)
        return aliases

    @property
    def metadata(self) -> LLMMetadata:
        try:
            return super().metadata
        except ValueError:
            # Prefer PyGPT's own model metadata. This is the authoritative value
            # for models already present in models.json even when the installed
            # llama-index integration has not learned the ID yet.
            context_window = 0
            runtime = self._pygpt_runtime
            model_item = getattr(runtime, "model", None) if runtime is not None else None
            try:
                context_window = int(getattr(model_item, "ctx", 0) or 0)
            except Exception:
                context_window = 0

            # If the PyGPT model did not specify ctx, map versioned aliases such
            # as claude-fable-5-1 -> claude-fable-5 before using a safe default.
            if context_window <= 0:
                for alias in self._metadata_aliases(self.model):
                    try:
                        context_window = int(anthropic_modelname_to_contextsize(alias))
                        break
                    except ValueError:
                        continue

            if context_window <= 0:
                context_window = 200000

            return LLMMetadata(
                context_window=context_window,
                num_output=self.max_tokens,
                is_chat_model=True,
                model_name=self.model,
                is_function_calling_model=is_function_calling_model(self.model),
            )

    @staticmethod
    def _get(value: Any, key: str, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    def _configured_computer_type(self) -> str:
        for tool in (getattr(self, "tools", None) or []):
            if not isinstance(tool, dict):
                continue
            tool_type = str(tool.get("type") or "")
            if tool_type in {
                "computer_20250124",
                "computer_20251124",
                "computer_toolset_20260801",
            }:
                return tool_type
        return ""

    def _computer_enabled(self) -> bool:
        return bool(self._configured_computer_type())

    def _runtime_ctx(self):
        runtime = self._pygpt_runtime
        if runtime is None:
            return None
        return getattr(getattr(runtime, "context", None), "ctx", None)

    def _computer_api(self):
        runtime = self._pygpt_runtime
        if runtime is None:
            raise RuntimeError("PyGPT Computer Use runtime is not bound to the Anthropic adapter")
        return runtime.window.core.api.anthropic.computer

    def _prepare_chat_with_tools(self, *args, **kwargs):
        prepared = super()._prepare_chat_with_tools(*args, **kwargs)
        if not self._computer_enabled():
            return prepared

        # Computer Use has its own client-side continuation. Do not allow the
        # model to emit an unrelated local function in the same provider turn,
        # because both results would have to be submitted atomically.
        tool_choice = prepared.get("tool_choice")
        if isinstance(tool_choice, dict):
            tool_choice = dict(tool_choice)
            tool_choice["disable_parallel_tool_use"] = True
            prepared["tool_choice"] = tool_choice
        return prepared

    def _is_computer_call(self, name: str, toolset_name: str) -> bool:
        computer = self._computer_api()
        name = str(name or "")
        toolset_name = str(toolset_name or "")
        if toolset_name == "computer":
            # Stable computer_toolset members are provider-owned. Treat future
            # member names as Computer Use too, so PyGPT can return an explicit
            # unsupported-action tool_result instead of leaking them to FunctionAgent.
            return True
        if name in computer.COMPUTER_TOOL_NAMES:
            return True
        if self._configured_computer_type() == "computer_toolset_20260801":
            return name in computer.TOOLSET_MEMBER_NAMES and toolset_name in ("", "computer")
        return False

    def _computer_calls(self, raw_response: Any) -> list[dict]:
        computer = self._computer_api()
        out = []
        for block in computer.get_field(raw_response, "content", []) or []:
            if computer.get_field(block, "type", "") != "tool_use":
                continue
            name = str(computer.get_field(block, "name", "") or "")
            toolset_name = str(computer.get_field(block, "toolset_name", "") or "")
            if not self._is_computer_call(name, toolset_name):
                continue
            if (
                    not toolset_name
                    and self._configured_computer_type() == "computer_toolset_20260801"
                    and name in computer.TOOLSET_MEMBER_NAMES
            ):
                # Compatibility with SDK builds that deserialize the stable
                # member but do not expose its toolset_name field yet.
                toolset_name = "computer"
            out.append({
                "id": str(computer.get_field(block, "id", "") or ""),
                "name": name,
                "toolset_name": toolset_name,
                "input": computer.to_plain(computer.get_field(block, "input", {}) or {}),
            })
        return out

    @staticmethod
    def _json_args(value: Any) -> dict:
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value or "{}")
                return dict(parsed) if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def _mapped_commands(self, call: dict) -> list[dict]:
        computer = self._computer_api()
        record = {
            "id": call.get("id") or "",
            "call_id": call.get("id") or "",
            "type": "function",
            "function": {
                "name": call.get("name") or "computer",
                "arguments": json.dumps(call.get("input") or {}, ensure_ascii=False),
            },
        }
        if call.get("toolset_name"):
            record["toolset_name"] = call["toolset_name"]
        mapped = computer.rewrite_tool_calls([record], ctx=self._runtime_ctx())
        commands = []
        for item in mapped or []:
            function = item.get("function") or {}
            name = str(function.get("name") or "")
            if not name:
                continue
            commands.append({
                "cmd": name,
                "params": self._json_args(function.get("arguments") or {}),
            })
        return commands

    @staticmethod
    def _result_payload(response: Any) -> Any:
        """Return the last useful cmd_mouse_control result from an Agents v2 RPC."""
        if isinstance(response, list):
            for item in reversed(response):
                if item is not None:
                    return item
            return None
        return response

    @classmethod
    def _result_text(cls, response: Any) -> tuple[str, bool]:
        value = cls._result_payload(response)
        if value is None:
            return "OK", False
        if isinstance(value, dict):
            result = value.get("result", value)
            if isinstance(result, dict):
                error = result.get("error")
                if error:
                    return str(error), True
                status = str(result.get("result", "") or "").lower()
                if status in {"error", "failed", "failure"}:
                    return json.dumps(result, ensure_ascii=False, default=str), True
                if status == "success" or result.get("ok") is True:
                    return "OK", False
                return json.dumps(result, ensure_ascii=False, default=str), False
            text = str(result)
            return text or "OK", text.lower().startswith("error")
        text = str(value)
        return text or "OK", text.lower().startswith("error")

    @classmethod
    def _cursor_text(cls, response: Any) -> str:
        value = cls._result_payload(response)
        if isinstance(value, dict):
            nested = value.get("result", value)
            if isinstance(nested, dict):
                x = nested.get("mouse_x")
                y = nested.get("mouse_y")
                if x is not None and y is not None:
                    try:
                        return f"X={int(x)}, Y={int(y)}"
                    except Exception:
                        return f"X={x}, Y={y}"
        text, _ = cls._result_text(response)
        return text

    @staticmethod
    def _image_block(screenshot_b64: str) -> dict:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot_b64,
            },
        }

    async def _execute_computer_calls(self, calls: list[dict]) -> list[dict]:
        bridge = AgentComputerBridge(self._pygpt_runtime)
        result_blocks = []
        legacy_images = []
        has_toolset = any(str(call.get("toolset_name") or "") == "computer" for call in calls)
        toolset_failed = False

        for call in calls:
            name = str(call.get("name") or "computer")
            toolset_name = str(call.get("toolset_name") or "")

            # Stable computer_toolset batches are ordered and stop after the first
            # failing action. Anthropic still requires one tool_result for every
            # emitted tool_use, so explicitly mark later calls as not executed.
            if toolset_name == "computer" and toolset_failed:
                result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": str(call.get("id") or ""),
                    "toolset_name": "computer",
                    "content": [{
                        "type": "text",
                        "text": "Not executed: an earlier computer action in this turn failed.",
                    }],
                    "is_error": True,
                })
                continue

            commands = self._mapped_commands(call)
            if not commands:
                text = f"Unsupported Computer Use action: {name}"
                is_error = True
                execution = None
            else:
                needs_image = (
                    (toolset_name == "computer" and name in {"screenshot", "zoom"})
                    or (not has_toolset and any(cmd.get("cmd") == "get_screenshot" for cmd in commands))
                )
                execution = await bridge.execute(
                    commands,
                    tool_label="computer_use",
                    require_screenshot=needs_image,
                )
                text, is_error = self._result_text(execution.response)
                if toolset_name == "computer" and name == "cursor_position" and not is_error:
                    text = self._cursor_text(execution.response)

            screenshot_b64 = execution.screenshot_b64 if execution is not None else None
            if toolset_name == "computer" and name in {"screenshot", "zoom"} and screenshot_b64 and not is_error:
                content = [self._image_block(screenshot_b64)]
            else:
                content = [{"type": "text", "text": text or "OK"}]

            result = {
                "type": "tool_result",
                "tool_use_id": str(call.get("id") or ""),
                "content": content,
            }
            if toolset_name:
                result["toolset_name"] = toolset_name
            if is_error:
                result["is_error"] = True
            result_blocks.append(result)

            if toolset_name == "computer" and is_error:
                toolset_failed = True

            # Preserve the working Chat protocol for legacy computer_20xxxxxx:
            # screenshots are separate user image blocks, not toolset results.
            if not has_toolset and screenshot_b64:
                legacy_images.append(self._image_block(screenshot_b64))

        return result_blocks + legacy_images

    def _parse_response(self, raw_response: Any) -> ChatResponse:
        blocks, citations = self._get_blocks_and_tool_calls_and_thinking(raw_response)
        usage = self._get(raw_response, "usage")
        if usage is not None:
            try:
                usage = usage.model_dump()
            except Exception:
                try:
                    usage = dict(usage)
                except Exception:
                    pass
        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                blocks=blocks,
                additional_kwargs={
                    "usage": usage,
                    "stop_reason": self._get(raw_response, "stop_reason"),
                },
            ),
            raw=self._computer_api().to_plain(raw_response),
            additional_kwargs={"citations": citations},
        )

    async def _achat_with_computer(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        anthropic_messages, system_prompt = messages_to_anthropic_messages(
            messages, self.cache_idx, self.model
        )
        all_kwargs = self._get_all_kwargs(**kwargs)
        all_kwargs.pop("stream", None)

        for turn in range(self.MAX_COMPUTER_TURNS + 1):
            raw = await self._aclient.messages.create(
                messages=anthropic_messages,
                system=system_prompt,
                stream=False,
                **all_kwargs,
            )
            calls = self._computer_calls(raw)
            if not calls:
                return self._parse_response(raw)

            if turn >= self.MAX_COMPUTER_TURNS:
                break

            runtime = self._pygpt_runtime
            if runtime is not None:
                runtime.verbose.log("ANTHROPIC COMPUTER USE", {
                    "turn": turn + 1,
                    "calls": calls,
                }, actor="orchestrator")

            # Echo the exact assistant content, including thinking/signatures and
            # server-side tool blocks, before returning client tool results.
            assistant_content = self._computer_api().to_plain(
                self._get(raw, "content", []) or []
            )
            result_content = await self._execute_computer_calls(calls)
            anthropic_messages.append({"role": "assistant", "content": assistant_content})
            anthropic_messages.append({"role": "user", "content": result_content})

            # A FunctionAgent-forced local tool choice applies only to its first
            # model request. Once a computer result is supplied, let Claude decide
            # whether to call Computer Use again or return normal/local-tool output.
            all_kwargs.pop("tool_choice", None)

        raise RuntimeError(
            f"Anthropic Computer Use exceeded the safety limit of {self.MAX_COMPUTER_TURNS} continuation turns"
        )

    def chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        """Sync Chat with Files entry point backed by the shared async loop."""
        if not self._computer_enabled():
            return super().chat(messages, **kwargs)
        return run_coroutine_sync(self._achat_with_computer(messages, **kwargs))

    def stream_chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ):
        if not self._computer_enabled():
            return super().stream_chat(messages, **kwargs)

        response = run_coroutine_sync(self._achat_with_computer(messages, **kwargs))

        def gen():
            if not getattr(response, "delta", None):
                try:
                    response.delta = str(response.message.content or "")
                except Exception:
                    pass
            yield response

        return gen()

    async def achat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        if not self._computer_enabled():
            return await super().achat(messages, **kwargs)
        return await self._achat_with_computer(messages, **kwargs)

    async def astream_chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ):
        if not self._computer_enabled():
            return await super().astream_chat(messages, **kwargs)

        # Computer Use needs completed tool_use blocks before local execution.
        # Agents v2 streams its authoritative final answer separately, so keep
        # this provider-internal loop non-streaming and yield one final response.
        response = await self._achat_with_computer(messages, **kwargs)

        async def gen():
            if not getattr(response, "delta", None):
                try:
                    response.delta = str(response.message.content or "")
                except Exception:
                    pass
            yield response

        return gen()
