#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.10 15:55:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
import base64
import json
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence

from llama_index.core.base.llms.types import ChatMessage, MessageRole

from pygpt_net.item.ctx import CtxItem


class _AsyncThreadLock:
    """Event-loop independent async context manager around one threading lock.

    Chat with Files invokes LlamaIndex synchronously from a bridge worker, while
    the provider Computer Use adapters run their continuation loops as coroutines.
    A regular ``asyncio.Lock`` would become tied to the first temporary event
    loop. This lock can therefore be reused safely across multiple sync LLM calls.
    """

    def __init__(self):
        self._lock = threading.RLock()

    async def __aenter__(self):
        self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()
        return False


class _ComputerRuntimeVerbose:
    """Minimal logger matching the Agents v2 runtime logger contract."""

    def __init__(self, window):
        self.window = window

    def log(self, label: str, value: Any = None, actor: str = None) -> None:
        try:
            suffix = f" [{actor}]" if actor else ""
            self.window.core.debug.info(f"[computer]{suffix} {label}: {value}")
        except Exception:
            pass


class ComputerRuntime:
    """Small runtime adapter for provider-native Computer Use outside Agents v2.

    Provider adapters only need access to the PyGPT window/context, a serialized
    desktop lock, stop state and logging/status hooks. Keeping this contract tiny
    lets Chat with Files and legacy agent workflows reuse the exact same provider
    continuation adapters and Computer Use executor without importing the Agents v2
    orchestration runtime.
    """

    def __init__(self, window, context):
        self.window = window
        self.context = context
        self.model = getattr(context, "model", None)
        self.local_tool_lock = _AsyncThreadLock()
        self.verbose = _ComputerRuntimeVerbose(window)

    def for_model(self, model):
        """Return a lightweight child runtime for another model, sharing the desktop lock."""
        child = ComputerRuntime(self.window, self.context)
        child.model = model
        child.local_tool_lock = self.local_tool_lock
        child.verbose = self.verbose
        return child

    def is_stopped(self) -> bool:
        try:
            return bool(self.window.controller.kernel.stopped())
        except Exception:
            return False

    def emit_runtime_status(self, key: str, **kwargs) -> None:
        # Agents v2 has a dedicated partial/status renderer. Legacy/regular modes
        # do not, so keep this hook transient and diagnostic instead of persisting
        # an Agents-v2-specific status block in the normal chat context.
        self.verbose.log("STATUS", {"key": key, "args": kwargs})


# Backward-compatible name used by older Chat with Files callers/plugins.
LlamaIndexComputerRuntime = ComputerRuntime


@dataclass
class ProviderComputerTurn:
    """Final result of a provider-native Computer Use turn."""

    output: str = ""
    response_id: Optional[str] = None


def _response_id(response: Any) -> Optional[str]:
    """Best-effort extraction of a provider response ID from a LlamaIndex reply."""
    raw = getattr(response, "raw", None)
    if raw is None:
        return None
    if isinstance(raw, dict):
        nested = raw.get("response")
        payload = nested if nested is not None else raw
        if isinstance(payload, dict):
            value = payload.get("id")
        else:
            value = getattr(payload, "id", None)
    else:
        nested = getattr(raw, "response", None)
        payload = nested if nested is not None else raw
        value = getattr(payload, "id", None)
    value = str(value or "").strip()
    return value or None


def _collect_llm_urls(context, llm) -> None:
    """Bridge provider-native URL artifacts back to the current PyGPT context."""
    ctx = getattr(context, "ctx", None)
    pop_urls = getattr(llm, "pop_pygpt_urls", None)
    if ctx is None or not callable(pop_urls):
        return
    try:
        urls = pop_urls() or []
    except Exception:
        return
    if not isinstance(getattr(ctx, "urls", None), list):
        ctx.urls = []
    seen = set(ctx.urls)
    for url in urls:
        value = str(url or "").strip()
        if value and value not in seen:
            ctx.urls.append(value)
            seen.add(value)


async def run_provider_computer_turn(
        window,
        context,
        model,
        prompt: str,
        *,
        history: Optional[Sequence[ChatMessage]] = None,
        system_prompt: str = "",
        runtime=None,
        llm=None,
) -> Optional[ProviderComputerTurn]:
    """Run one direct provider-native Computer Use turn when it is configured.

    The provider registry decides whether the selected model/provider has an active
    Computer Use adapter. If not, ``None`` is returned without issuing an LLM call,
    so callers can continue their normal workflow unchanged. This is intentionally
    provider-agnostic: OpenAI, Google and Anthropic all reuse the same LlamaIndex
    adapter contract and :class:`AgentComputerBridge` executor.
    """
    if window is None or context is None or model is None:
        return None

    if runtime is None:
        runtime = ComputerRuntime(window, context)

    if llm is None:
        llm = window.core.idx.llm.get(
            model=model,
            stream=False,
            computer_runtime=runtime,
        )
    binder = getattr(llm, "bind_computer_runtime", None)
    if not callable(binder):
        return None
    binder(runtime)

    messages = list(history or [])
    system_text = str(system_prompt or "").strip()
    if system_text:
        has_system = any(
            getattr(item, "role", None) == MessageRole.SYSTEM
            for item in messages
            if isinstance(item, ChatMessage)
        )
        if not has_system:
            messages.insert(0, ChatMessage(role=MessageRole.SYSTEM, content=system_text))

    messages.append(ChatMessage(
        role=MessageRole.USER,
        content=str(prompt or ""),
    ))

    response = await llm.achat(messages)
    _collect_llm_urls(context, llm)

    message = getattr(response, "message", None)
    content = getattr(message, "content", None) if message is not None else None
    if content is None:
        content = str(response or "")
    return ProviderComputerTurn(
        output=str(content or ""),
        response_id=_response_id(response),
    )



OPENAI_AGENT_COMPUTER_TOOL_NAME = "pygpt_computer_use"


def build_openai_agent_computer_tool(
        window,
        context,
        model,
        *,
        runtime=None,
        system_prompt: str = "",
):
    """Build an OpenAI Agents SDK FunctionTool backed by provider-native CU.

    Legacy OpenAI-agent workflows can run Google/Anthropic models through the
    Agents SDK compatibility layer, but provider-native Computer Use cannot pass
    through that Chat-Completions-shaped transport. Expose one outer remote tool
    whose callback runs the existing LlamaIndex provider continuation adapter.

    OpenAI GPT models are deliberately skipped: the legacy OpenAI agent provider
    already uses the SDK's native ComputerTool/LocalComputer path for them.
    """
    if window is None or context is None or model is None:
        return None
    try:
        if model.is_gpt():
            return None
    except Exception:
        pass

    shared_runtime = runtime or ComputerRuntime(window, context)
    runtime_for_model = getattr(shared_runtime, "for_model", None)
    if callable(runtime_for_model):
        shared_runtime = runtime_for_model(model)

    try:
        llm = window.core.idx.llm.get(
            model=model,
            stream=False,
            computer_runtime=shared_runtime,
        )
    except Exception as exc:
        try:
            window.core.debug.log(exc)
        except Exception:
            pass
        return None

    binder = getattr(llm, "bind_computer_runtime", None)
    if not callable(binder):
        return None
    binder(shared_runtime)

    try:
        from agents import FunctionTool, RunContextWrapper
    except Exception:
        return None

    async def invoke(run_ctx: RunContextWrapper[Any], args: str) -> str:
        try:
            payload = json.loads(args or "{}")
        except Exception:
            payload = {}
        task = str(payload.get("task") or "").strip()
        if not task:
            return json.dumps({
                "error": "Missing required Computer Use task.",
                "tool": OPENAI_AGENT_COMPUTER_TOOL_NAME,
            }, ensure_ascii=False)

        result = await run_provider_computer_turn(
            window=window,
            context=context,
            model=model,
            prompt=task,
            system_prompt=system_prompt or getattr(context, "system_prompt", ""),
            runtime=shared_runtime,
            llm=llm,
        )
        if result is None:
            return json.dumps({
                "error": "Computer Use is not enabled for this provider/model.",
                "tool": OPENAI_AGENT_COMPUTER_TOOL_NAME,
            }, ensure_ascii=False)
        return result.output or "Computer Use task completed."

    return FunctionTool(
        name=OPENAI_AGENT_COMPUTER_TOOL_NAME,
        description=(
            "Use the user's computer through the provider-native Computer Use "
            "runtime. Call this when the task requires viewing the screen or "
            "interacting with the desktop. Pass a concise, self-contained task."
        ),
        params_json_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The self-contained desktop task to perform.",
                },
            },
            "required": ["task"],
            "additionalProperties": False,
        },
        on_invoke_tool=invoke,
    )

def run_coroutine_sync(awaitable):
    """Run one provider continuation coroutine from a synchronous LlamaIndex call.

    BridgeWorker normally has no asyncio loop, in which case ``asyncio.run`` is
    sufficient. The helper-thread fallback also makes the adapter safe if a future
    caller invokes the same synchronous LlamaIndex API while an event loop is
    already running in that thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result_queue = queue.Queue(maxsize=1)

    def runner():
        try:
            result_queue.put((True, asyncio.run(awaitable)))
        except BaseException as exc:
            result_queue.put((False, exc))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    ok, value = result_queue.get()
    if ok:
        return value
    raise value


async def wait_for_computer_safety_confirmation(runtime, ctx) -> None:
    """Pause one provider-native Computer Use round until the user confirms it.

    The same helper is used by Chat with Files and Agents v2.  It deliberately
    keeps the provider coroutine alive instead of aborting the continuation with
    an exception, so the exact pending provider call can be acknowledged and
    resumed after the user approves the Yes/No confirmation dialog.
    """
    if runtime is None or ctx is None:
        return
    security = runtime.window.core.security
    if not security.should_halt_computer(ctx):
        return

    resumed = threading.Event()
    runtime.window.controller.chat.command.pause_for_safety_confirmation(
        ctx,
        resume_callback=resumed.set,
    )
    while not resumed.is_set():
        if runtime.is_stopped():
            raise asyncio.CancelledError(
                "Computer Use cancelled while waiting for safety confirmation"
            )
        await asyncio.sleep(0.05)

    if runtime.is_stopped():
        raise asyncio.CancelledError("Computer Use cancelled")
    if not security.can_acknowledge_computer_safety(ctx):
        raise asyncio.CancelledError("Computer Use safety confirmation was rejected by the user")


@dataclass
class AgentComputerExecution:
    """Result of one native Computer Use action batch executed by PyGPT."""

    response: Any = None
    screenshot_path: Optional[str] = None
    screenshot_b64: Optional[str] = None


class AgentComputerBridge:
    """Execute provider-native Computer Use actions through cmd_mouse_control.

    Provider adapters need a small bridge because Computer Use is a
    client-side provider tool: the model emits an action, PyGPT executes it,
    then the provider requires a screenshot/tool result in a continuation
    request.  FunctionAgent must never see those provider-native calls as normal
    app tools, otherwise it either cannot resolve their names or loses the
    provider-specific continuation metadata.
    """

    def __init__(self, runtime):
        self.runtime = runtime

    def _check_stopped(self) -> None:
        runtime = self.runtime
        if runtime is not None and runtime.is_stopped():
            import asyncio
            raise asyncio.CancelledError("Computer Use cancelled")

    @staticmethod
    def _normalize_cmds(cmds: Iterable[dict]) -> list[dict]:
        out = []
        for item in cmds or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("cmd") or "").strip()
            if not name:
                continue
            params = item.get("params")
            if not isinstance(params, dict):
                params = {}
            out.append({"cmd": name, "params": dict(params)})
        return out

    @staticmethod
    def _last_existing_path(values, filesystem=None) -> Optional[str]:
        for value in reversed(list(values or [])):
            raw = str(value or "").strip()
            if not raw:
                continue
            candidates = []
            if filesystem is not None:
                try:
                    candidates.append(filesystem.to_workdir(raw, auto_prefix=False))
                except Exception:
                    pass
            candidates.append(raw)
            for candidate in candidates:
                if candidate and os.path.isfile(candidate):
                    return candidate
        return None

    @classmethod
    def _response_attachment_paths(cls, value: Any) -> list[str]:
        """Extract transport-only attachment paths embedded in plugin replies."""
        out = []

        def walk(node):
            if isinstance(node, dict):
                marker = node.get("agent_runtime_attachments")
                if isinstance(marker, (list, tuple)):
                    for entry in marker:
                        if isinstance(entry, dict):
                            path = entry.get("path")
                        else:
                            path = entry
                        if path:
                            out.append(str(path))
                for key, child in node.items():
                    if key != "agent_runtime_attachments":
                        walk(child)
            elif isinstance(node, (list, tuple)):
                for child in node:
                    walk(child)

        walk(value)
        return out

    @staticmethod
    def _capture_snapshot(runtime) -> tuple[Optional[str], dict[str, tuple[int, int]]]:
        """Snapshot the capture directory for a screenshot transport fallback."""
        try:
            directory = runtime.window.controller.painter.common.get_capture_dir()
        except Exception:
            return None, {}
        if not directory or not os.path.isdir(directory):
            return directory, {}
        state = {}
        try:
            for entry in os.scandir(directory):
                if not entry.is_file():
                    continue
                try:
                    stat = entry.stat()
                    state[entry.path] = (int(stat.st_mtime_ns), int(stat.st_size))
                except OSError:
                    continue
        except OSError:
            return directory, {}
        return directory, state

    @staticmethod
    def _new_capture_path(
            directory: Optional[str],
            before: dict[str, tuple[int, int]],
            started_ns: int,
    ) -> Optional[str]:
        """Return the newest image created/updated by the just-finished action."""
        if not directory or not os.path.isdir(directory):
            return None
        candidates = []
        try:
            for entry in os.scandir(directory):
                if not entry.is_file():
                    continue
                if not entry.name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                try:
                    stat = entry.stat()
                except OSError:
                    continue
                signature = (int(stat.st_mtime_ns), int(stat.st_size))
                changed = before.get(entry.path) != signature
                # Some filesystems expose coarse mtimes; changed/new is the main
                # discriminator and this timestamp guard rejects old captures.
                recent = int(stat.st_mtime_ns) >= started_ns - 2_000_000_000
                if changed and recent:
                    candidates.append((int(stat.st_mtime_ns), entry.path))
        except OSError:
            return None
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]


    @staticmethod
    def _encode_file(path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        try:
            with open(path, "rb") as handle:
                return base64.b64encode(handle.read()).decode("ascii")
        except Exception:
            return None

    def _capture_direct(self) -> tuple[Optional[str], Optional[str]]:
        """Capture a transport screenshot exactly like the working OpenAI agent path.

        Provider-native Computer Use must not depend on cmd_mouse_control's delayed
        reply screenshot. That path is controlled by the plugin's ``allow_screenshot``
        option and a Qt timer, while OpenAI Agents v2 already captures explicitly
        after executing the action batch. Google and Anthropic need the same contract.
        """
        runtime = self.runtime
        if runtime is None:
            return None, None
        window = runtime.window
        try:
            plugin = window.core.plugins.get("cmd_mouse_control")
        except Exception:
            plugin = None

        try:
            window.controller.attachment.clear_silent()
        except Exception:
            pass

        path = None
        try:
            is_sandbox = bool(plugin is not None and plugin.is_sandbox())
        except Exception:
            is_sandbox = False

        try:
            capture = window.controller.painter.capture
            if is_sandbox:
                path = capture.screenshot_playwright(
                    page=getattr(plugin, "page", None),
                    silent=True,
                    append_to_ctx=False,
                    attach_cursor=True,
                    cursor_position=(
                        getattr(plugin, "pointer_x", 0),
                        getattr(plugin, "pointer_y", 0),
                    ),
                )
            else:
                path = capture.screenshot(
                    attach_cursor=True,
                    silent=True,
                    append_to_ctx=False,
                )
        except Exception:
            path = None

        try:
            window.controller.attachment.clear_silent()
        except Exception:
            pass

        path = str(path) if path else None
        return path, self._encode_file(path)

    async def _settle_before_direct_capture(self, commands: list[dict]) -> None:
        """Match the working OpenAI adapter's post-action GUI settle delay."""
        action_names = {
            str(item.get("cmd") or "").strip().lower()
            for item in commands or []
            if isinstance(item, dict)
        }
        needs_settle = any(
            name not in {"", "get_screenshot", "screenshot", "take_screenshot", "wait", "wait_5_seconds"}
            for name in action_names
        )
        if not needs_settle:
            return

        delay_ms = 1000.0
        try:
            plugin = self.runtime.window.core.plugins.get("cmd_mouse_control")
            delay_ms = float(getattr(plugin, "SLEEP_TIME", 1000) or 0)
        except Exception:
            pass
        delay = max(0.0, delay_ms / 1000.0)
        if delay:
            await asyncio.sleep(delay)

    def _execute_direct(self, commands: list[dict]) -> list[dict]:
        """Execute canonical Computer Use commands synchronously through cmd_mouse_control.

        This intentionally mirrors the working OpenAI Agents v2 Computer Use path.
        Provider-native Computer Use is already a trusted/explicit local-computer
        transport and must not be routed through the generic Agents-v2 plugin RPC:
        that path is designed for ordinary model tools and introduces an extra Qt
        dispatch/continuation layer between the provider action and the desktop.

        A private worker is used instead of ``Plugin.handle_call()`` only so we can
        collect its real response payloads for Google/Anthropic tool_result/function
        responses. Execution semantics remain the same as handle_call(): synchronous,
        one cmd_mouse_control worker, and no plugin-generated screenshot (the bridge
        captures the transport screenshot explicitly afterwards when required).
        """
        runtime = self.runtime
        window = runtime.window
        plugin = window.core.plugins.get("cmd_mouse_control")
        if plugin is None:
            raise RuntimeError("Computer Use plugin 'cmd_mouse_control' is not available")

        prepared = []
        for command in commands:
            item = {
                "cmd": str(command.get("cmd") or ""),
                "params": dict(command.get("params") or {}),
            }
            # Exactly the same contract as Plugin.handle_call(): the provider loop
            # owns screenshot timing, so the action worker must not schedule one.
            item["params"]["no_screenshot"] = True
            prepared.append(item)

        screenshot_names = {"get_screenshot", "screenshot", "take_screenshot"}
        executable = [item for item in prepared if item["cmd"].lower() not in screenshot_names]
        executed_responses: list[dict] = []
        errors: list[Any] = []

        if executable:
            worker = plugin.get_worker()
            worker.from_defaults(plugin)
            worker.cmds = executable
            worker.ctx = CtxItem()

            # Worker.run() normally publishes through Qt/plugin reply handling. For
            # the provider bridge we need the actual synchronous result but must not
            # create a second chat/plugin reply. Capture it locally instead.
            worker.reply_more = lambda value, extra_data=None: executed_responses.extend(value or [])
            worker.reply = lambda value, extra_data=None: executed_responses.append(value) if value is not None else None
            worker.error = lambda err: errors.append(err)
            worker.run()

        if errors:
            raise RuntimeError(str(errors[-1]))

        # Reconstruct one response per provider action. Screenshot requests are not
        # sent through the plugin worker because the bridge captures one authoritative
        # transport screenshot immediately afterwards (the same rule OpenAI uses).
        responses: list[dict] = []
        response_iter = iter(executed_responses)
        for item in prepared:
            if item["cmd"].lower() in screenshot_names:
                responses.append({
                    "request": {"cmd": item["cmd"]},
                    "result": {"result": "success", "no_screenshot": True},
                })
                continue
            try:
                responses.append(next(response_iter))
            except StopIteration:
                raise RuntimeError(
                    f"Computer Use command produced no execution result: {item['cmd']}"
                )

        # More worker responses than submitted commands indicate a broken mapper or
        # worker contract; fail loudly instead of associating results with wrong calls.
        try:
            extra = next(response_iter)
        except StopIteration:
            extra = None
        if extra is not None:
            raise RuntimeError("Computer Use worker returned more results than actions")

        return responses

    async def execute(
            self,
            cmds: Iterable[dict],
            *,
            tool_label: str = "computer_use",
            require_screenshot: bool = False,
    ) -> AgentComputerExecution:
        runtime = self.runtime
        if runtime is None:
            raise RuntimeError("PyGPT Computer Use runtime is not bound to the adapter")

        self._check_stopped()
        commands = self._normalize_cmds(cmds)
        if not commands:
            raise RuntimeError("Computer Use returned no executable action")

        runtime.emit_runtime_status("status.agent_v2.tool", tool=tool_label)
        runtime.verbose.log("COMPUTER USE ACTIONS", commands, actor="orchestrator")

        # Match OpenAI's known-good Agents v2 path: execute the canonical actions
        # directly through cmd_mouse_control while holding the desktop lock. Keep
        # the lock through the optional settle + screenshot so no worker can mutate
        # the desktop between the provider action and the image returned for it.
        async with runtime.local_tool_lock:
            response = self._execute_direct(commands)
            self._check_stopped()

            screenshot_path = None
            screenshot_b64 = None
            if require_screenshot:
                await self._settle_before_direct_capture(commands)
                screenshot_path, screenshot_b64 = self._capture_direct()
                if not screenshot_b64:
                    raise RuntimeError(
                        "Computer Use action executed, but PyGPT could not capture the transport screenshot"
                    )

        runtime.verbose.log("COMPUTER USE RESULT", {
            "commands": [item.get("cmd") for item in commands],
            "response": response,
            "screenshot": screenshot_path or "",
        }, actor="orchestrator")

        return AgentComputerExecution(
            response=response,
            screenshot_path=screenshot_path,
            screenshot_b64=screenshot_b64,
        )
