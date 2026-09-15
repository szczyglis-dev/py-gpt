#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.15 21:20:00                  #
# ================================================== #

from __future__ import annotations

import copy
import html
from typing import List, Optional

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from pygpt_net.core.context_manager.constants import SOURCE_ITEM_KWARG

from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.types import MODE_AGENT_V2


_HISTORY_SEGMENTS_KEY = "_pygpt_agents_v2_history_segments"


class OrchestratorMemoryStore:
    """Project the root conversation into Primary-Agent-facing history.

    Agents v2 used to persist a second, preset-specific hidden ``ctx_item`` for
    every visible conversation turn.  History is now conversation-scoped instead:
    one durable root ``ctx_item`` is the source of truth regardless of which
    Primary Agent preset handled a previous turn.

    ``preset`` parameters are intentionally retained on the public methods for
    compatibility with existing callers, but they no longer select or create a
    separate memory stream.
    """

    def __init__(self, window):
        self.window = window

    @staticmethod
    def _worker_context_records(part) -> list:
        """Return normalized worker finals stored on one orchestrator partial."""
        extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
        values = extra.get("worker_context")
        legacy = False
        if not isinstance(values, list):
            values = extra.get("worker_outputs")
            legacy = True
        if not isinstance(values, list):
            return []

        result = []
        for value in values:
            if not isinstance(value, dict):
                continue
            output = value.get("output")
            if output is None and legacy:
                output = value.get("output_text")
            created_at = value.get("created_at")
            if created_at is None and legacy:
                created_at = value.get("output_created_at")
            try:
                created_at = int(created_at or 0)
            except (TypeError, ValueError):
                created_at = 0
            record = {
                "id": str(value.get("id") or (value.get("worker_id") if legacy else "") or ""),
                "name": str(value.get("name") or (value.get("worker_name") if legacy else "") or ""),
                "input": str(value.get("input") or (value.get("task") if legacy else "") or ""),
                "output": str(output or ""),
                "created_at": created_at,
            }
            result.append(record)
        result.sort(key=lambda item: item["created_at"])
        return result

    @staticmethod
    def _worker_context_block(record: dict) -> str:
        """Return a model-only runtime envelope for one delegated worker result.

        The wrapper is intentionally explicit about provenance. On a restored
        conversation this block is replayed as a separate USER-role history
        message, not as Primary-Agent prose, so the model can distinguish a real
        historical worker result from text it generated itself.
        """
        output = str(record.get("output") or "").strip()
        if not output:
            return ""
        name = html.escape(str(record.get("name") or record.get("id") or "Worker"), quote=True)
        return (
            '<agents_runtime_context type="worker_result">\n'
            f'<worker_context name="{name}" source="delegated_agent">\n'
            f'{output}\n'
            '</worker_context>\n'
            '</agents_runtime_context>'
        )

    def _compose_source_history_segments(self, source: Optional[CtxItem]) -> list[dict]:
        """Rebuild ordered Primary-Agent and worker-result segments for one turn.

        Worker results are kept as their own segment so ``load_history`` can
        replay them as hidden/runtime USER inputs between assistant prose chunks.
        Adjacent segments of the same kind are merged to avoid unnecessary
        same-role message fragmentation for provider adapters.
        """
        if source is None:
            return []
        parts = list(getattr(source, "parts", None) or [])
        if not parts:
            return []

        def part_key(part):
            try:
                created = int(getattr(part, "created_at", 0) or 0)
            except (TypeError, ValueError):
                created = 0
            try:
                row_id = int(getattr(part, "id", 0) or 0)
            except (TypeError, ValueError):
                row_id = 0
            return created, row_id

        segments: list[dict] = []

        def append(kind: str, content: str):
            value = str(content or "").strip()
            if not value:
                return
            if segments and segments[-1].get("kind") == kind:
                segments[-1]["content"] = (
                    str(segments[-1].get("content") or "").rstrip()
                    + "\n\n"
                    + value
                )
            else:
                segments.append({"kind": kind, "content": value})

        for part in sorted(parts, key=part_key):
            extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if extra.get("provider_history") is False or extra.get("agents_v2_worker") is True:
                continue

            text = str(getattr(part, "output", None) or "").strip()
            if text:
                append("assistant", text)

            for record in self._worker_context_records(part):
                block = self._worker_context_block(record)
                if block:
                    append("worker", block)

        return segments

    def _compose_source_history(self, source: Optional[CtxItem]) -> str:
        """Return a flattened snapshot for token/window helpers.

        Actual provider replay is segmented by ``load_history``; this flattened
        value exists only because generic ctx history/token helpers operate on one
        assistant output string per durable turn.
        """
        return "\n\n".join(
            str(segment.get("content") or "").strip()
            for segment in self._compose_source_history_segments(source)
            if str(segment.get("content") or "").strip()
        ).strip()

    @staticmethod
    def _row_id(item: CtxItem) -> int:
        try:
            return int(getattr(item, "id", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _project_source_item(self, item: CtxItem) -> Optional[CtxItem]:
        """Return a disposable Primary-Agent history row from one root ctx item.

        Normal modes replay their ordinary final input/output. Completed Agents
        v2 turns keep ordered model-only segments so worker results can later be
        replayed as separate runtime inputs instead of being flattened into
        assistant-authored prose. An interrupted Agents v2 turn is USER-only.
        """
        if item is None or getattr(item, "hidden", False) or getattr(item, "internal", False):
            return None

        history_segments = []
        mode = str(getattr(item, "mode", "") or "")
        if mode == MODE_AGENT_V2:
            extra = item.extra if isinstance(getattr(item, "extra", None), dict) else {}
            try:
                durable_final = str(item.get_agents_v2_final_output() or "").strip()
            except Exception:
                durable_final = ""
            completed = extra.get("response_final") is True or bool(durable_final)
            if completed:
                history_segments = self._compose_source_history_segments(item)
                output = "\n\n".join(
                    str(segment.get("content") or "").strip()
                    for segment in history_segments
                    if str(segment.get("content") or "").strip()
                ).strip()
                if not output:
                    output = durable_final
                if not output:
                    # Compatibility with completed records whose parent output was
                    # persisted before durable final partials became the source of truth.
                    output = str(getattr(item, "output", None) or "").strip()
                if output and not history_segments:
                    history_segments = [{"kind": "assistant", "content": output}]
            else:
                # Preserve a stopped/interrupted request as USER-only history.
                # Any transient partial output from an unfinished workflow is not
                # authoritative and must not be replayed as an assistant answer.
                output = ""
        else:
            try:
                output = item.final_output
            except Exception:
                output = getattr(item, "output", None)

        clone = copy.copy(item)
        clone.parts = []
        clone.active_part = None
        clone.output = output
        # The projection is conversation-scoped and checkpoint filtering is done
        # using the durable source item id. Prevent generic history helpers from
        # inferring a second meta/checkpoint from a projected row.
        clone.meta = None
        clone.meta_id = None
        clone.extra = copy.deepcopy(item.extra) if isinstance(getattr(item, "extra", None), dict) else {}
        if history_segments:
            clone.extra[_HISTORY_SEGMENTS_KEY] = copy.deepcopy(history_segments)
        source_id = self._row_id(item)
        if source_id > 0:
            clone.extra["agents_v2_source_item_id"] = source_id
        return clone

    def _projected_items(
            self,
            master_ctx: CtxItem,
            preset=None,
            create_meta: bool = False,
            exclude_source_id: int = 0,
    ) -> List[CtxItem]:
        """Return model-facing history from the root conversation only.

        ``preset`` and ``create_meta`` are compatibility arguments. They are
        deliberately ignored: changing the Primary Agent must never fork or filter
        conversation history, and reading/token-counting history must never create
        an Agents v2 child meta.
        """
        del preset, create_meta

        meta = getattr(master_ctx, "meta", None) if master_ctx is not None else None
        meta_id = getattr(meta, "id", None)
        if meta_id is None:
            return []

        try:
            source_items = list(self.window.core.ctx.provider.load(meta_id) or [])
        except Exception as exc:
            self.window.core.debug.log(exc)
            source_items = []

        try:
            exclude_source_id = int(exclude_source_id or 0)
        except (TypeError, ValueError):
            exclude_source_id = 0

        projected = []
        sequence = 0
        for source in source_items:
            source_id = self._row_id(source)
            if exclude_source_id > 0 and source_id == exclude_source_id:
                continue
            clone = self._project_source_item(source)
            if clone is None:
                continue
            projected.append((source_id, sequence, clone))
            sequence += 1

        # Provider order is normally chronological already, but sorting by the
        # durable root row id makes mixed-mode replay deterministic after reload.
        projected.sort(key=lambda entry: (entry[0], entry[1]))
        items = [entry[2] for entry in projected]
        return self.window.core.context_manager.filter_agents_v2_items(items, master_ctx)

    def count_history_tokens(
            self,
            master_ctx: CtxItem,
            preset=None,
            model=None,
            used_tokens: int = 0,
            max_tokens: int = 0,
    ) -> tuple[int, int]:
        """Count exactly the root-conversation history replayed by Agents v2."""
        if master_ctx is None or model is None:
            return 0, 0
        items = self._projected_items(master_ctx, preset)
        if not items:
            return 0, 0

        model_id = str(getattr(model, "id", "") or "")
        notes_tokens = 0
        try:
            manager = self.window.core.context_manager
            if manager.enabled():
                notes = manager.notes_for_model(master_ctx, model=model)
                if notes:
                    notes_tokens = int(self.window.core.tokens.from_text(notes, model_id) or 0)
        except Exception as exc:
            self.window.core.debug.log(exc)
        if max_tokens > 0:
            items = self.window.core.ctx.get_history(
                items,
                model_id,
                MODE_AGENT_V2,
                int(used_tokens or 0) + notes_tokens,
                int(max_tokens or 0),
                ignore_first=False,
            )

        from_ctx = self.window.core.tokens.from_ctx
        total = notes_tokens + sum(from_ctx(item, MODE_AGENT_V2, model_id) for item in items)
        return len(items), total

    @staticmethod
    def _projected_source_id(item: CtxItem) -> int:
        extra = getattr(item, "extra", None) or {}
        if not isinstance(extra, dict):
            return 0
        try:
            return int(extra.get("agents_v2_source_item_id") or 0)
        except (TypeError, ValueError):
            return 0

    def _messages_from_projected_item(self, item: CtxItem) -> List[ChatMessage]:
        """Convert one projected root turn to provider-facing chat messages.

        Historical worker results are injected as USER-role runtime context. They
        never become visible/persisted chat items; this is only the model-facing
        replay shape. The durable source marker stays on the final message of a
        completed turn so rolling context checkpoints advance only after the
        whole turn has been flushed.
        """
        messages: List[ChatMessage] = []
        if item.final_input:
            messages.append(ChatMessage(role=MessageRole.USER, content=str(item.final_input)))

        extra = getattr(item, "extra", None) or {}
        segments = extra.get(_HISTORY_SEGMENTS_KEY) if isinstance(extra, dict) else None
        source_id = self._projected_source_id(item)
        source_kwargs = {SOURCE_ITEM_KWARG: source_id} if source_id > 0 else {}

        if isinstance(segments, list) and segments:
            valid = []
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                kind = str(segment.get("kind") or "").strip()
                content = str(segment.get("content") or "").strip()
                if kind not in {"assistant", "worker"} or not content:
                    continue
                valid.append((kind, content))

            for index, (kind, content) in enumerate(valid):
                is_last = index == len(valid) - 1
                kwargs = source_kwargs if is_last else {}
                if kind == "worker":
                    # USER is the most portable provider role for a historical
                    # runtime injection. The wrapper/system policy carries its
                    # non-user provenance; TOOL would require a replayed tool_call.
                    messages.append(ChatMessage(
                        role=MessageRole.USER,
                        content=content,
                        additional_kwargs=kwargs,
                    ))
                else:
                    messages.append(ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=content,
                        additional_kwargs=kwargs,
                    ))
            if valid:
                return messages

        output = str(getattr(item, "output", None) or "").strip()
        if output:
            messages.append(ChatMessage(
                role=MessageRole.ASSISTANT,
                content=output,
                additional_kwargs=source_kwargs,
            ))
        return messages

    def load_history(self, master_ctx: CtxItem, preset=None, model=None, current_input: str = "") -> List[ChatMessage]:
        """Load one continuous conversation for any Primary Agent preset.

        The current root ``ctx_item`` is already durable when Runner starts, so it
        is excluded from replay and sent separately as the current user request.
        All earlier root turns are shared across Primary Agents and conversation
        modes.
        """
        items = self._projected_items(
            master_ctx,
            preset,
            exclude_source_id=self._row_id(master_ctx),
        )

        if model is not None and items:
            try:
                model_id = model.id
                # ``from_user`` expects (system_prompt, input_prompt). This
                # history-window estimate has no system prompt available yet,
                # but the current user input must still be counted as USER.
                used_tokens = self.window.core.tokens.from_user("", current_input or "")
                # Advanced Agents v2 injects compact continuation notes through
                # rolling Memory rather than the system prompt. Reserve that
                # space while selecting the initial replay tail.
                try:
                    manager = self.window.core.context_manager
                    if manager.enabled():
                        notes = manager.notes_for_model(master_ctx, model=model)
                        if notes:
                            used_tokens += int(self.window.core.tokens.from_text(notes, model_id) or 0)
                except Exception as exc:
                    self.window.core.debug.log(exc)
                max_tokens = int(self.window.core.config.get("max_total_tokens") or 0)
                model_ctx = int(getattr(model, "ctx", 0) or 0)
                if model_ctx > 0 and (max_tokens <= 0 or max_tokens > model_ctx):
                    max_tokens = model_ctx
                if max_tokens > 0:
                    items = self.window.core.ctx.get_history(
                        items,
                        model_id,
                        MODE_AGENT_V2,
                        used_tokens,
                        max_tokens,
                        ignore_first=False,
                    )
            except Exception as exc:
                self.window.core.debug.log(exc)

        messages: List[ChatMessage] = []
        for item in items:
            messages.extend(self._messages_from_projected_item(item))
        return messages

    @staticmethod
    def compose_turn_output(master_ctx: CtxItem, final_answer: str = "") -> str:
        """Compatibility helper returning the authoritative final text.

        Turn output is no longer persisted in a second Agents v2 memory row; the
        durable root ctx_item/partials are the only source of conversation state.
        """
        final = str(final_answer or "").strip()
        if final:
            return final
        if master_ctx is None:
            return ""
        try:
            value = master_ctx.get_agents_v2_final_output()
        except Exception:
            value = None
        return str(value or "").strip()

    @staticmethod
    def begin_turn(master_ctx: CtxItem, preset=None, user_input: str = ""):
        """Compatibility no-op: the root ctx_item already persists the user turn."""
        del preset, user_input
        return master_ctx

    @staticmethod
    def complete_turn(item: CtxItem, assistant_output: str):
        """Compatibility no-op: normal response lifecycle finalizes the root item."""
        del item, assistant_output

    @staticmethod
    def append_turn(master_ctx: CtxItem, preset=None, user_input: str = "", assistant_output: str = ""):
        """Compatibility no-op kept for callers from older Agents v2 revisions."""
        del preset, user_input, assistant_output
        return master_ctx



# Semantic name for the Primary Agent flow; keep aliases for compatibility.
PrimaryAgentMemoryStore = OrchestratorMemoryStore
AgentsV2MemoryStore = OrchestratorMemoryStore
