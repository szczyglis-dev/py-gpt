#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.16 09:00:00                  #
# ================================================== #

from __future__ import annotations

import json
import threading
from typing import Iterable, Optional

from pygpt_net.core.types import MODE_AGENT_V2, MODE_CHAT

from .budget import ContextBudget
from .store import ContextMemoryStore


class ContextManager:
    """High-level continuous context management shared by Chat and Agents v2."""

    def __init__(self, window=None):
        self.window = window
        self.store = ContextMemoryStore(window)
        self._pending = set()
        self._lock = threading.Lock()
        self._notes_lock = threading.Lock()

    def enabled(self) -> bool:
        return bool(self.window.core.config.get("context.advanced.enabled", False))

    def get_notes_max_chars(self) -> int:
        try:
            return max(1000, int(self.window.core.config.get("context.advanced.notes_max_chars") or 24000))
        except (TypeError, ValueError):
            return 24000

    def limit_notes(self, text: str, preserve_tail: bool = False) -> str:
        value = str(text or "").strip()
        max_chars = self.get_notes_max_chars()
        if len(value) <= max_chars:
            return value
        if not preserve_tail:
            return value[:max_chars].rstrip()
        # Manual append memory is intentionally newline-oriented. When the hard
        # safety ceiling is reached retain stable goals/constraints from the
        # beginning and the newest progress from the tail instead of silently
        # discarding the note the model/user just appended.
        head = max(500, int(max_chars * 0.60))
        tail = max(500, max_chars - head - 32)
        return (value[:head].rstrip() + "\n…\n" + value[-tail:].lstrip()).strip()


    def clip_text_to_tokens(
            self,
            text: str,
            model_id: str,
            max_tokens: int,
            preserve_tail: bool = True,
    ) -> str:
        """Bound text by the model tokenizer without requiring token decoding.

        Continuation notes are stored with a character safety ceiling, but dense
        code/CJK text can use far more tokens per character than English.  This
        second guard is applied at provider boundaries and maintenance calls.
        """
        value = str(text or "").strip()
        try:
            max_tokens = int(max_tokens or 0)
        except (TypeError, ValueError):
            max_tokens = 0
        if not value or max_tokens <= 0:
            return "" if max_tokens <= 0 else value

        def count(candidate: str) -> int:
            try:
                return max(0, int(self.window.core.tokens.from_text(candidate, model_id) or 0))
            except Exception:
                return max(0, len(candidate) // 4)

        tokens = count(value)
        if tokens <= max_tokens:
            return value

        # First jump close to the measured ratio, then monotonically shrink.
        # Keeping both ends preserves stable goals/constraints and newest state.
        ratio = max(0.02, min(0.98, max_tokens / max(1, tokens)))
        keep_chars = max(64, int(len(value) * ratio * 0.92))
        while keep_chars >= 64:
            if preserve_tail and keep_chars >= 128:
                head = max(32, int(keep_chars * 0.62))
                tail = max(32, keep_chars - head)
                candidate = (value[:head].rstrip() + "\n…\n" + value[-tail:].lstrip()).strip()
            else:
                candidate = value[:keep_chars].rstrip()
            if count(candidate) <= max_tokens:
                return candidate
            keep_chars = int(keep_chars * 0.82)
        # Extremely small/dense budgets: return the largest safe prefix we can.
        lo, hi = 0, min(len(value), 256)
        best = ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if count(candidate) <= max_tokens:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return best.rstrip()

    def notes_for_model(self, ctx=None, meta=None, model=None, max_tokens: int = 0) -> str:
        """Return canonical notes clipped to a safe share of one model window."""
        notes = self.get_notes(ctx, meta)
        if not notes:
            return ""
        if model is None:
            try:
                model = self.window.core.models.from_defaults()
            except Exception:
                return self.limit_notes(notes, preserve_tail=True)
        model_id = str(getattr(model, "id", "") or "gpt-4")
        if max_tokens <= 0:
            budget = ContextBudget.build(self.window, model)
            if budget.input_limit <= 0:
                return self.limit_notes(notes, preserve_tail=True)
            # Notes are a continuity aid, not the active transcript. Keep a hard
            # share limit so small-window models still have room for current work.
            max_tokens = max(256, min(8192, int(budget.input_limit * 0.18)))
        return self.clip_text_to_tokens(
            self.limit_notes(notes, preserve_tail=True),
            model_id,
            max_tokens,
            preserve_tail=True,
        )

    def _tokenizer_fn(self, model_id: str):
        """Return a zero-allocation len()-compatible tokenizer for LlamaIndex Memory."""
        model_id = str(model_id or "gpt-4")

        def tokenize(text):
            try:
                count = int(self.window.core.tokens.from_text(str(text or ""), model_id) or 0)
            except Exception:
                count = max(0, len(str(text or "")) // 4)
            # Memory only calls len(tokenizer_fn(...)); range avoids allocating
            # a Python list containing hundreds of thousands of token ids.
            return range(max(0, count))

        return tokenize

    def _tool_tokens(self, tools, model_id: str) -> int:
        """Conservatively estimate the provider-visible tool-schema budget."""
        total = 0
        for tool in list(tools or []):
            try:
                metadata = getattr(tool, "metadata", None)
                if metadata is None:
                    payload = str(tool)
                else:
                    params = None
                    getter = getattr(metadata, "get_parameters_dict", None)
                    if callable(getter):
                        try:
                            params = getter()
                        except Exception:
                            params = None
                    if params is None:
                        params = getattr(metadata, "fn_schema", None)
                    payload = json.dumps({
                        "name": getattr(metadata, "name", ""),
                        "description": getattr(metadata, "description", ""),
                        "parameters": params,
                    }, ensure_ascii=False, default=str)
                total += int(self.window.core.tokens.from_text(payload, model_id) or 0)
            except Exception:
                total += 128
        # Function/tool protocol framing differs by provider. Keep a small
        # additional reserve rather than pretending JSON alone is exact.
        return total + (len(list(tools or [])) * 24)

    def configure_llm_for_rolling_context(self, llm):
        """Make a LlamaIndex LLM compatible with client-side rolling memory.

        Stateful Responses adapters can otherwise retain a server-side chain
        after ``SafeAgentMemory`` has compacted its local FIFO. That makes the
        provider context grow invisibly and defeats local rollover. In advanced
        mode the local Memory object is authoritative, so generic response-id
        tracking is disabled and Responses truncation is left on as a final
        provider-side safety net. Explicit Computer Use continuations still pass
        their own previous_response_id for the immediately required tool round.
        """
        if not self.enabled() or llm is None:
            return llm
        try:
            if hasattr(llm, "track_previous_responses"):
                llm.track_previous_responses = False
        except Exception as exc:
            self.window.core.debug.log(exc)
        try:
            if hasattr(llm, "_previous_response_id"):
                llm._previous_response_id = None
        except Exception:
            pass
        try:
            if hasattr(llm, "truncation"):
                llm.truncation = "auto"
        except Exception as exc:
            self.window.core.debug.log(exc)
        return llm

    def configure_maintenance_llm(self, llm, max_output_tokens: int):
        """Best-effort cap for side-effect-free context maintenance calls.

        PyGPT supports several LlamaIndex adapters with different output-limit
        fields.  A rolling-summary call must not inherit a very large global
        output setting (for example 64k on an 8k/16k model), otherwise the
        maintenance request itself can exceed the provider context window.
        Keep this adapter-local and conservative instead of forwarding unknown
        kwargs through ``achat()``.
        """
        if llm is None:
            return llm
        try:
            limit = max(128, int(max_output_tokens or 0))
        except (TypeError, ValueError):
            limit = 1024

        # OpenAI Chat / Anthropic / LiteLLM and compatible adapters.
        for attr in ("max_tokens", "max_output_tokens"):
            try:
                if not hasattr(llm, attr):
                    continue
                current = getattr(llm, attr, None)
                try:
                    current_int = int(current or 0)
                except (TypeError, ValueError):
                    current_int = 0
                if current_int <= 0 or current_int > limit:
                    setattr(llm, attr, limit)
            except Exception as exc:
                try:
                    self.window.core.debug.log(exc)
                except Exception:
                    pass

        # llama-index GoogleGenAI keeps GenerateContentConfig as an internal
        # normalized dictionary. Do not overwrite thinking/tool settings; only
        # cap the response budget used by the maintenance model pass.
        try:
            if hasattr(llm, "_generation_config"):
                raw = getattr(llm, "_generation_config", None)
                if raw is None:
                    cfg = {}
                elif isinstance(raw, dict):
                    cfg = dict(raw)
                else:
                    try:
                        cfg = raw.model_dump(exclude_none=True)
                    except Exception:
                        cfg = {}
                current = cfg.get("max_output_tokens")
                try:
                    current_int = int(current or 0)
                except (TypeError, ValueError):
                    current_int = 0
                if current_int <= 0 or current_int > limit:
                    cfg["max_output_tokens"] = limit
                    setattr(llm, "_generation_config", cfg)
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass
        return llm

    def agent_memory_limit(self, model, system_prompt: str = "", tools=None) -> int:
        """Return the safe LlamaIndex Memory ceiling for one agent actor.

        The memory ceiling is intentionally below the provider input ceiling: the
        agent system prompt and tool schemas are re-sent outside LlamaIndex Memory
        on every model pass and therefore must be reserved separately.
        """
        if model is None:
            return 40000
        budget = ContextBudget.build(self.window, model)
        if budget.input_limit <= 0:
            return 40000
        model_id = str(getattr(model, "id", "") or "gpt-4")
        system_tokens = int(self.window.core.tokens.from_text(str(system_prompt or ""), model_id) or 0)
        tool_tokens = self._tool_tokens(tools, model_id)
        protocol_reserve = max(1024, int(budget.effective_limit * 0.025))
        available = budget.input_limit - system_tokens - tool_tokens - protocol_reserve
        # Never reproduce the previous 128k hard cap: large-context models may
        # safely retain hundreds of thousands of tokens between rollovers.
        return max(2048, int(available))

    def build_agent_memory(
            self,
            runtime,
            *,
            actor_id: str,
            system_prompt: str,
            tools,
            persistent: bool = False,
    ):
        """Create bounded rolling memory for one Agents v2 actor.

        The Primary Agent uses a persistent continuation block backed by
        ``memory_ctx``. Workers use the same rolling summary algorithm only in
        RAM so unfinished specialist scratch state never overwrites canonical
        conversation notes.
        """
        from .agent_memory import ContinuationSummaryBlock, SafeAgentMemory

        model = runtime.model
        model_id = str(getattr(model, "id", "") or "gpt-4")
        available_limit = self.agent_memory_limit(model, system_prompt, tools)
        threshold = min(95, max(20, int(self.window.core.config.get("context.advanced.threshold") or 75)))
        target = min(threshold - 5, max(10, int(self.window.core.config.get("context.advanced.target") or 45)))

        # LlamaIndex Memory uses ``token_limit * chat_history_token_ratio`` as
        # the FIFO waterfall threshold, while ``token_limit`` itself remains the
        # ceiling for short-term history + memory blocks. Keep the full safe
        # provider budget as the physical limit so the protected continuation
        # summary has explicit headroom, and use the configured threshold only
        # for the short-term queue. ``token_flush_size`` is sized to move the
        # queue from the threshold toward the configured target in one batch.
        token_limit = max(2048, int(available_limit))
        threshold_tokens = max(1024, int(token_limit * threshold / 100.0))
        target_tokens = max(512, int(token_limit * target / 100.0))
        flush_size = max(512, threshold_tokens - target_tokens)
        ratio = max(0.05, min(0.95, threshold / 100.0))

        configured_chars = self.get_notes_max_chars()
        actor_summary_chars = min(
            configured_chars,
            max(2000, int(available_limit * 0.08 * 4)),
        )
        actor_summary_tokens = max(256, min(8192, int(available_limit * 0.12)))
        summary_input_tokens = max(1024, int(available_limit * 0.24))
        initial_summary = (
            self.notes_for_model(
                runtime.context.ctx,
                model=model,
                max_tokens=actor_summary_tokens,
            )
            if persistent else ""
        )
        # Context compaction is an internal maintenance pass. Never expose
        # provider-native web/computer/search tools to this auxiliary LLM; a
        # summary operation must stay side-effect free and deterministic.
        summary_llm = runtime.get_llm(
            stream=False,
            actor_id=f"{actor_id}:context-memory",
            allow_remote_tools=False,
        )
        summary_llm = self.configure_maintenance_llm(
            summary_llm,
            actor_summary_tokens,
        )
        block = ContinuationSummaryBlock(
            name="pygpt_continuation",
            description="Compact rolling state for context-window continuation.",
            priority=0,
            manager=self,
            ctx=runtime.context.ctx if persistent else None,
            llm=summary_llm,
            persistent=bool(persistent),
            max_chars=actor_summary_chars,
            model_id=model_id,
            max_tokens=actor_summary_tokens,
            summary_input_tokens=summary_input_tokens,
            summary=str(initial_summary or ""),
        )
        memory = SafeAgentMemory.from_defaults(
            session_id=f"agents_v2_{runtime.run_id}_{actor_id}_rolling",
            token_limit=token_limit,
            memory_blocks=[block],
            tokenizer_fn=self._tokenizer_fn(model_id),
            chat_history_token_ratio=ratio,
            token_flush_size=flush_size,
            # Conservative multimodal estimates: correctness/safety beats
            # squeezing the final few percent out of the context window.
            image_token_size_estimate=4096,
            audio_token_size_estimate=8192,
            video_token_size_estimate=16384,
        )
        try:
            memory.document_token_size_estimate = 8192
            memory.single_message_ratio = max(0.25, min(0.70, target / max(1.0, float(threshold))))
        except Exception:
            pass
        runtime.verbose_log("CONTEXT MEMORY CREATED", {
            "actor": actor_id,
            "persistent": bool(persistent),
            "available_input_limit": available_limit,
            "token_limit": token_limit,
            "waterfall_threshold": threshold_tokens,
            "target_tokens": target_tokens,
            "flush_size": flush_size,
            "summary_max_chars": actor_summary_chars,
            "summary_max_tokens": actor_summary_tokens,
            "summary_input_tokens": summary_input_tokens,
        })
        return memory

    def build_agent_tools(self, ctx):
        if not self.enabled():
            return []
        from .tools import build_context_tools
        return build_context_tools(self, ctx)

    @staticmethod
    def _meta_id(ctx=None, meta=None) -> Optional[int]:
        if meta is None and ctx is not None:
            meta = getattr(ctx, "meta", None)
        value = getattr(meta, "id", None) if meta is not None else None
        if value in (None, 0, "") and ctx is not None:
            value = getattr(ctx, "meta_id", None)
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def get(self, ctx=None, meta=None) -> dict:
        meta_id = self._meta_id(ctx, meta)
        if meta_id is None:
            return {
                "id": None, "meta_id": None, "updated_at": 0, "last_item_id": 0,
                "generation": 0, "revision": 0, "content": "",
            }
        try:
            return self.store.get(meta_id)
        except Exception as exc:
            self.window.core.debug.log(exc)
            return {
                "id": None, "meta_id": meta_id, "updated_at": 0, "last_item_id": 0,
                "generation": 0, "revision": 0, "content": "",
            }

    def get_notes(self, ctx=None, meta=None) -> str:
        return self.get(ctx, meta)["content"]

    def add_notes(self, ctx, text: str) -> str:
        meta_id = self._meta_id(ctx)
        if meta_id is None:
            raise ValueError("No active conversation is available for context memory.")
        addition = str(text or "").strip()
        if not addition:
            return self.store.content(meta_id)
        with self._notes_lock:
            current = self.store.content(meta_id).rstrip()
            merged = addition if not current else current + "\n" + addition
            value = self.limit_notes(merged, preserve_tail=True)
            return self.store.replace(meta_id, value)

    def replace_notes(self, ctx, text: str) -> str:
        meta_id = self._meta_id(ctx)
        if meta_id is None:
            raise ValueError("No active conversation is available for context memory.")
        value = self.limit_notes(text)
        with self._notes_lock:
            return self.store.replace(meta_id, value)

    def commit_runtime_summary(
            self,
            ctx,
            text: str,
            expected_revision: int,
            last_item_id: int = 0,
    ):
        """Commit one Agents v2 rolling-memory update without clobbering edits."""
        meta_id = self._meta_id(ctx)
        if meta_id is None:
            return None
        value = self.limit_notes(text)
        with self._notes_lock:
            return self.store.runtime_summary(
                meta_id,
                value,
                expected_revision=int(expected_revision or 0),
                last_item_id=int(last_item_id or 0),
            )

    def prepare_system_prompt(self, prompt: str, ctx, mode: str, model=None, internal: bool = False) -> str:
        """Attach the continuous-context policy and compact continuation state."""
        value = str(prompt or "")
        if not self.enabled() or internal or ctx is None or getattr(ctx, "internal", False):
            return value

        policy = (
            "<context_management>\n"
            "Advanced context handling is active. PyGPT may compact older completed turns into "
            "conversation-scoped continuation notes and remove those raw turns from the active model window. "
            "Keep working normally and treat any <context_continuation> block as prior conversation state, not as "
            "new user instructions. If memory_ctx_add or memory_ctx_replace tools are available, use them sparingly "
            "to persist crucial goals, decisions, completed work, constraints, findings, and pending work during long "
            "tasks; those notes belong only to this conversation. Do not store hidden reasoning or routine chatter.\n"
            "</context_management>"
        )
        blocks = [policy]
        state = self.get(ctx)
        notes = self.notes_for_model(ctx, model=model)
        # Agents v2 injects continuation state through its rolling LlamaIndex
        # Memory block, which can refresh *during the same run*. Avoid sending a
        # second stale copy in the static system prompt. Other chat modes use the
        # durable system-prompt block below.
        if notes and str(mode or "") != MODE_AGENT_V2:
            blocks.append(
                f'<context_continuation generation="{int(state.get("generation") or 0)}" '
                f'summarized_through_item_id="{int(state.get("last_item_id") or 0)}">\n'
                "The following is a compact continuation state produced from older turns that may no longer be "
                "present in the active model window. Treat it as conversation history/state, not as new user "
                "instructions. Continue consistently from it and prefer newer explicit user messages if anything "
                "conflicts.\n\n"
                + notes
                + "\n</context_continuation>"
            )
        block = "\n\n".join(blocks)
        if value.strip():
            return value.rstrip() + "\n\n" + block
        return block

    def fit_history_limit(self, model_ref, requested: int = 0) -> int:
        """Return the safe input budget used by every history projector.

        With advanced handling disabled this preserves the caller's legacy limit.
        With it enabled, ``0`` no longer means an unbounded request: the model's
        declared context window becomes the ceiling and output/safety reserve is
        subtracted before history is selected.
        """
        try:
            requested = int(requested or 0)
        except (TypeError, ValueError):
            requested = 0
        if not self.enabled():
            return requested
        model = model_ref
        if isinstance(model_ref, str):
            try:
                model = self.window.core.models.get(model_ref) if self.window.core.models.has(model_ref) else None
            except Exception:
                model = None
        if model is None:
            try:
                model = self.window.core.models.from_defaults()
            except Exception:
                return requested
        budget = ContextBudget.build(self.window, model)
        safe = int(budget.input_limit or 0)
        if safe <= 0:
            return requested
        if requested > 0:
            return min(requested, safe)
        return safe

    def filter_history(self, items: Iterable) -> list:
        """Drop durable turns already represented by a conversation checkpoint."""
        values = list(items or [])
        if not self.enabled() or not values:
            return values
        meta_id = None
        for item in values:
            meta_id = self._meta_id(item)
            if meta_id is not None:
                break
        if meta_id is None:
            return values
        state = self.store.get(meta_id)
        floor = int(state.get("last_item_id") or 0)
        if floor <= 0:
            return values
        out = []
        for item in values:
            try:
                item_id = int(getattr(item, "id", 0) or 0)
            except (TypeError, ValueError):
                item_id = 0
            if item_id <= 0 or item_id > floor:
                out.append(item)
        return out

    def filter_agents_v2_items(self, items: Iterable, master_ctx) -> list:
        """Apply the master conversation checkpoint floor to hidden Agents v2 memory rows."""
        values = list(items or [])
        if not self.enabled() or master_ctx is None:
            return values
        state = self.get(master_ctx)
        floor = int(state.get("last_item_id") or 0)
        if floor <= 0:
            return values
        out = []
        for item in values:
            extra = getattr(item, "extra", None) or {}
            source_id = extra.get("agents_v2_source_item_id") if isinstance(extra, dict) else None
            try:
                source_id = int(source_id or 0)
            except (TypeError, ValueError):
                source_id = 0
            if source_id <= 0 or source_id > floor:
                out.append(item)
        return out

    def mark_request_generation(self, ctx):
        if not self.enabled() or ctx is None or getattr(ctx, "internal", False):
            return
        state = self.get(ctx)
        if not isinstance(getattr(ctx, "extra", None), dict):
            ctx.extra = {}
        ctx.extra["context_generation"] = int(state.get("generation") or 0)

    def should_break_server_chain(self, history, ctx) -> bool:
        """Return True once after a checkpoint so stateful APIs start a compact chain."""
        if not self.enabled() or ctx is None:
            return False
        current_generation = int(self.get(ctx).get("generation") or 0)
        if current_generation <= 0:
            return False
        for item in reversed(list(history or [])):
            if not getattr(item, "msg_id", None):
                continue
            extra = getattr(item, "extra", None) or {}
            try:
                item_generation = int(extra.get("context_generation", 0) or 0) if isinstance(extra, dict) else 0
            except (TypeError, ValueError):
                item_generation = 0
            return item_generation < current_generation
        return False

    def _item_tokens(self, item, model_id: str, mode: str) -> int:
        try:
            if str(getattr(item, "mode", "") or mode) == MODE_AGENT_V2:
                user = str(getattr(item, "final_input", None) or "")
                assistant = self._assistant_snapshot(item)
                return int(self.window.core.tokens.from_text(user + "\n" + assistant, model_id) or 0)
            return int(self.window.core.tokens.from_ctx(item, mode or MODE_CHAT, model_id) or 0)
        except Exception:
            return 0

    def _assistant_snapshot(self, item) -> str:
        """Return the assistant state used by advanced-context checkpoints.

        For Chat with Agents this follows the same history-restore policy as the
        live Agents v2 replay path, so token accounting, checkpoint thresholds and
        continuation notes never silently reintroduce a full workflow when the user
        selected final-response-only history.
        """
        if str(getattr(item, "mode", "") or "") == MODE_AGENT_V2 \
                and not bool(self.window.core.config.get("agent.v2.restore_full_history", True)):
            try:
                final = item.get_agents_v2_response_output()
                if final is None or not str(final).strip():
                    final = item.get_agents_v2_final_output()
            except Exception:
                final = None
            if final is not None and str(final).strip():
                return str(final).strip()

        chunks = []
        for part in list(getattr(item, "parts", None) or []):
            text = str(getattr(part, "output", None) or "").strip()
            if text:
                chunks.append(text)
            extra = getattr(part, "extra", None) or {}
            if isinstance(extra, dict):
                workers = extra.get("worker_context") or []
                if isinstance(workers, list):
                    for worker in workers:
                        if not isinstance(worker, dict):
                            continue
                        result = str(worker.get("result") or worker.get("output") or "").strip()
                        if result:
                            name = str(worker.get("name") or worker.get("worker") or "worker").strip()
                            chunks.append(f"[{name}] {result}")
        if chunks:
            return "\n\n".join(chunks)
        try:
            value = item.get_agents_v2_response_output()
        except Exception:
            value = None
        if value:
            return str(value).strip()
        # hidden_output is one-turn provider/runtime context and must not become
        # durable continuation memory merely because CtxItem.final_output exposes
        # it to model-facing history.
        return str(getattr(item, "output", None) or "").strip()

    def _checkpoint_plan(self, ctx) -> Optional[dict]:
        if not self.enabled() or ctx is None or getattr(ctx, "internal", False) or getattr(ctx, "sub_call", False):
            return None
        meta_id = self._meta_id(ctx)
        if meta_id is None:
            return None
        model = None
        model_id = str(getattr(ctx, "model", "") or "")
        if model_id and self.window.core.models.has(model_id):
            model = self.window.core.models.get(model_id)
        if model is None:
            model = self.window.core.models.from_defaults()
            model_id = str(getattr(model, "id", "") or "")
        budget = ContextBudget.build(self.window, model)
        if budget.input_limit <= 0:
            return None

        state = self.store.get(meta_id)
        floor = int(state.get("last_item_id") or 0)
        items = list(self.window.core.ctx.provider.load(meta_id) or [])
        candidates = []
        total = 0
        mode = str(getattr(ctx, "mode", None) or self.window.core.config.get("mode") or MODE_CHAT)
        for item in items:
            if getattr(item, "internal", False) or getattr(item, "hidden", False):
                continue
            try:
                item_id = int(getattr(item, "id", 0) or 0)
            except (TypeError, ValueError):
                item_id = 0
            if item_id <= floor:
                continue
            cost = max(1, self._item_tokens(item, model_id, mode))
            candidates.append((item, cost))
            total += cost

        notes_tokens = 0
        if state.get("content"):
            try:
                notes_tokens = int(self.window.core.tokens.from_text(str(state["content"]), model_id) or 0)
            except Exception:
                notes_tokens = max(1, len(str(state["content"])) // 4)
        if total + notes_tokens < budget.checkpoint_tokens:
            return None

        # Keep the newest tail around the target size and compress everything
        # before it. If one completed turn alone is huge, it may also be rolled
        # into notes so the next turn can still start safely.
        tail = 0
        cut_index = len(candidates)
        for idx in range(len(candidates) - 1, -1, -1):
            cost = candidates[idx][1]
            if tail > 0 and tail + cost > budget.target_tail_tokens:
                cut_index = idx + 1
                break
            tail += cost
            cut_index = idx
        to_summary = candidates[:cut_index]
        if not to_summary and candidates and total > budget.checkpoint_tokens:
            to_summary = candidates[:1]
        if not to_summary:
            return None

        last_item = to_summary[-1][0]
        snapshot = self.build_snapshot([item for item, _ in to_summary])
        if not snapshot.strip():
            return None
        return {
            "meta_id": meta_id,
            "model_id": model_id,
            "revision": int(state.get("revision") or 0),
            "existing_notes": str(state.get("content") or ""),
            "last_item_id": int(getattr(last_item, "id", 0) or 0),
            "snapshot": snapshot,
            "budget": budget,
        }

    def build_snapshot(self, items: Iterable) -> str:
        chunks = []
        for item in items or []:
            # Do not persist hidden_input (RAG payload / one-turn runtime
            # context) into continuation memory. Preserve the user's durable
            # message and the useful assistant/workflow state only.
            user = str(getattr(item, "final_input", None) or "").strip()
            assistant = self._assistant_snapshot(item)
            if not user and not assistant:
                continue
            item_id = getattr(item, "id", None)
            chunks.append(f"<turn id=\"{item_id}\">\nUser:\n{user}\n\nAssistant:\n{assistant}\n</turn>")
        return "\n\n".join(chunks)

    def build_checkpoint_input(self, existing_notes: str, snapshot: str) -> str:
        current = str(existing_notes or "").strip() or "(empty)"
        return (
            "<existing_continuation_notes>\n" + current + "\n</existing_continuation_notes>\n\n"
            "<conversation_segment_to_compact>\n" + str(snapshot or "").strip()
            + "\n</conversation_segment_to_compact>"
        )

    def split_checkpoint_snapshot(self, snapshot: str, model_id: str, max_tokens: int) -> list[str]:
        """Split a checkpoint source into token-bounded sequential chunks."""
        value = str(snapshot or "").strip()
        if not value:
            return []
        max_tokens = max(128, int(max_tokens or 0))

        def count(text):
            try:
                return max(1, int(self.window.core.tokens.from_text(text, model_id) or 0))
            except Exception:
                return max(1, len(text) // 4)

        total_tokens = count(value)
        if total_tokens <= max_tokens:
            return [value]

        # Start from the measured chars/token ratio, then shrink individual
        # candidates when multilingual/code-heavy text tokenizes more densely.
        chars_per_token = max(0.5, len(value) / max(1, total_tokens))
        soft_chars = max(256, int(max_tokens * chars_per_token * 0.90))
        chunks = []
        pos = 0
        length = len(value)
        while pos < length:
            end = min(length, pos + soft_chars)
            if end < length:
                # Prefer completed turn/XML boundaries, then paragraph/newline.
                window = value[pos:end]
                cuts = [
                    window.rfind("</turn>"),
                    window.rfind("\n\n"),
                    window.rfind("\n"),
                ]
                cut = max(cuts)
                if cut > max(128, len(window) // 3):
                    if window[cut:cut + 7] == "</turn>":
                        cut += 7
                    end = pos + cut
            candidate = value[pos:end].strip()
            while candidate and count(candidate) > max_tokens and len(candidate) > 128:
                end = pos + max(128, int((end - pos) * 0.78))
                candidate = value[pos:end].strip()
            if candidate and count(candidate) > max_tokens:
                # Dense text can still exceed the token cap even at 128 chars.
                # Binary-search a safe character boundary rather than emitting an
                # oversized maintenance chunk.
                lo, hi = pos + 1, end
                safe_end = pos
                while lo <= hi:
                    mid = (lo + hi) // 2
                    probe = value[pos:mid].strip()
                    if probe and count(probe) <= max_tokens:
                        safe_end = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1
                end = safe_end
                candidate = value[pos:end].strip() if end > pos else ""
            if not candidate:
                # One codepoint can theoretically tokenize above an extremely
                # small synthetic budget. Make progress and let the exact prompt
                # headroom guard decide the output allowance.
                end = min(length, pos + 1)
                candidate = value[pos:end]
            chunks.append(candidate)
            pos = end
        return chunks or [value]

    @staticmethod
    def clean_checkpoint_output(text: str) -> str:
        value = str(text or "").strip()
        if value.startswith("```") and value.endswith("```"):
            lines = value.splitlines()
            if len(lines) >= 2:
                value = "\n".join(lines[1:-1]).strip()
        return value

    def on_ctx_end(self, ctx):
        plan = self._checkpoint_plan(ctx)
        if plan is None:
            return
        meta_id = plan["meta_id"]
        with self._lock:
            if meta_id in self._pending:
                return
            self._pending.add(meta_id)
        try:
            from .checkpoint import ContextCheckpointWorker
            worker = ContextCheckpointWorker(self, plan)
            self.window.threadpool.start(worker)
        except Exception:
            self.finish_checkpoint(meta_id)
            raise

    def finish_checkpoint(self, meta_id):
        try:
            meta_id = int(meta_id)
        except (TypeError, ValueError):
            return
        with self._lock:
            self._pending.discard(meta_id)
