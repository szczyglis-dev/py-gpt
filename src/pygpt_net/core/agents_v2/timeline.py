#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.13 15:14:00                  #
# ================================================== #

from __future__ import annotations

from typing import Any, Optional

from llama_index.core.agent.workflow import AgentOutput, AgentStream, ToolCall, ToolCallResult

from .utils import tool_event_value, translated_status


class RuntimeTimeline:
    """Own durable actor partials, stream boundaries and final-answer resolution."""

    def __init__(self, runtime):
        self.runtime = runtime

    def _close_primary_stream_segment(self):
        """Close the current streamed Primary Agent prose segment, if any."""
        value = str(self.runtime._primary_stream_current or "")
        if value.strip():
            self.runtime._primary_stream_completed.append(value)
        self.runtime._primary_stream_current = ""

    def note_provider_tool_activity(
            self,
            tool_name: str,
            actor: str = "orchestrator",
            call_id: str = "",
    ):
        """Bridge a provider-native hosted tool boundary into the Agents v2 timeline.

        Hosted tools execute inside the provider Responses/GenerateContent call and
        therefore never become LlamaIndex ``ToolCall`` / ``ToolCallResult`` events.
        Without this callback, prose emitted before the hosted tool and the final
        answer emitted after it are appended to one CtxItemPart and later look like
        one synthetic final response.
        """
        actor = str(actor or "orchestrator")
        tool = str(tool_name or "remote_tool").strip() or "remote_tool"
        self.runtime.verbose.log("PROVIDER TOOL ACTIVITY", {
            "tool": tool,
            "call_id": str(call_id or ""),
        }, actor=actor)

        if actor != "orchestrator":
            worker = self.runtime.workers.get(actor)
            if worker is not None and self.runtime._show_tool_status(tool):
                self.runtime.emit_worker_status(
                    worker,
                    translated_status("status.agent_v2.tool", tool=tool),
                )
            return

        self.runtime._primary_tool_activity_seen = True
        had_prose = bool(str(self.runtime._primary_stream_current or "").strip())
        self.runtime._close_primary_stream_segment()
        if had_prose:
            # Flush the already streamed pre-tool prose and arm a durable partial
            # rotation. The next real AgentStream delta becomes a new sub-turn.
            self.runtime.emitter.mark_block_boundary()
            self.runtime._actor_needs_new_part["orchestrator"] = True
        if self.runtime._show_tool_status(tool):
            self.runtime.emit_runtime_status("status.agent_v2.tool", tool=tool)

    def primary_stream_final_output(self) -> str:
        """Return only prose streamed after the most recent tool boundary."""
        return str(self.runtime._primary_stream_current or "").strip()

    def verbose_event(self, event: Any, actor: str = "orchestrator"):
        actor = str(actor or "orchestrator")
        # AgentStream/AgentOutput carry the raw provider response. Capture source
        # metadata at this boundary instead of relying solely on a later LLM buffer
        # drain; this is the authoritative path for the user-facing Primary Agent.
        if isinstance(event, (AgentStream, AgentOutput)):
            self.runtime.collect_llm_artifacts(response=event, actor_id=actor)
        if isinstance(event, ToolCall):
            tool_name = str(tool_event_value(event, "tool_name", "name", "tool") or "").strip()
            if self.runtime._show_tool_status(tool_name):
                if actor == "orchestrator":
                    self.runtime.emit_runtime_status("status.agent_v2.tool", tool=tool_name)
                else:
                    worker = self.runtime.workers.get(actor)
                    if worker is not None:
                        self.runtime.emit_runtime_status("status.agent_v2.tool", worker=worker, tool=tool_name)
            # A local/function tool call is also a Primary Agent prose boundary.
            # Keep this runtime-side segmentation independent of DB/UI timing.
            if actor == "orchestrator":
                self.runtime._primary_tool_activity_seen = True
                self.runtime._close_primary_stream_segment()
            # A tool-only model pass stays in the current partial. The previous
            # result has nevertheless been consumed, so expose completed tasks
            # before persisting the next call under that same partial.
            self.runtime._promote_actor_tasks(actor)
            self.runtime.record_tool_call(event, actor=actor)
            self.runtime.verbose.log("TOOL CALL", event, actor=actor)
        elif isinstance(event, ToolCallResult):
            tool_name = str(tool_event_value(event, "tool_name", "name", "tool") or "").strip()
            self.runtime.record_tool_result(event, actor=actor)
            if actor == "orchestrator":
                self.runtime._actor_needs_new_part["orchestrator"] = True
                # A provider/model pass after a normal execution tool may spend
                # noticeable time before yielding the next event. Use only the
                # neutral request spinner here. Internal orchestration tools keep
                # the semantic worker/workflow status they emitted themselves.
                if self.runtime._show_tool_status(tool_name):
                    self.runtime.emitter.show_loading()
            # Do not synthesize ``Planning task...`` after worker tool results.
            # It falsely replaces the worker's actual progress on every tool
            # roundtrip. The next status must come from report_status(), another
            # real tool call, or the worker lifecycle (completed/failed/stopped).
            self.runtime.verbose.log("TOOL RESULT", event, actor=actor)
        elif isinstance(event, AgentStream):
            delta = getattr(event, "delta", None)
            if delta:
                # Only actual assistant prose can rotate a partial. Empty stream
                # bookkeeping events must not create DB rows.
                self.runtime._prepare_actor_response_part(actor)
                self.runtime._promote_actor_tasks(actor)
                if actor == "orchestrator":
                    self.runtime._primary_stream_current += str(delta)
                self.runtime.verbose.text("STREAM", delta, actor=actor)
            else:
                self.runtime.verbose.log("AGENT STREAM", event, actor=actor)
        else:
            self.runtime.verbose.log(event.__class__.__name__, event, actor=actor)

    def _actor_metadata(self, actor: str):
        actor = str(actor or "orchestrator")
        if actor == "orchestrator":
            return "orchestrator", self.runtime.main_agent_name, ""
        state = self.runtime.workers.get(actor)
        if state is None:
            return actor, actor, ""
        return state.id, state.name, str(state.current_task or "")

    def _actor_part(self, actor: str, create: bool = True):
        """Return the durable orchestrator partial associated with an actor.

        Workers never own durable partials. Their private LlamaIndex memory stays
        in RAM; any persisted worker tool calls/results are attached to the
        orchestrator partial from which that worker run was started.
        """
        actor = str(actor or "orchestrator")
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return None
        if actor != "orchestrator":
            part = self.runtime._worker_parent_parts.get(actor)
            if part is not None and part in (main.parts or []):
                return part
            return self.runtime._actor_parts.get("orchestrator") or (main.parts[-1] if main.parts else None)
        part = self.runtime._actor_parts.get(actor)
        if part is not None and part in (main.parts or []):
            return part
        if not create:
            return None
        return self.runtime._begin_actor_part(actor, reuse_initial=True)

    def _begin_actor_part(
            self,
            actor: str,
            reuse_initial: bool = False,
            extra: Optional[dict] = None,
            joiner: str = "",
    ):
        """Create a durable actor partial, optionally adopting the auto-created first row."""
        actor = str(actor or "orchestrator")
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return None
        if actor != "orchestrator":
            # Worker partials are intentionally not durable.
            return self.runtime._actor_part(actor, create=False)
        actor_id, agent_name, task_name = self.runtime._actor_metadata(actor)
        seq = int(self.runtime._actor_part_seq.get(actor, 0)) + 1
        self.runtime._actor_part_seq[actor] = seq
        payload = {
            "agents_v2_actor": actor_id,
            "agent_task": task_name,
            "agent_generation": seq,
        }
        if isinstance(extra, dict):
            payload.update(extra)

        part = None
        if reuse_initial:
            for candidate in main.parts or []:
                candidate_actor = str(getattr(candidate, "agent_id", "") or "")
                candidate_extra = candidate.extra if isinstance(candidate.extra, dict) else {}
                extra_actor = str(candidate_extra.get("agents_v2_actor", "") or "")
                # AGENT_V2_BEGIN is delivered through Qt while the runtime works
                # in its worker thread. Either side may label the auto-created
                # first part first. Adopt it when it is still empty and belongs
                # to this actor instead of creating a duplicate orchestrator row.
                actor_matches = (
                    not candidate_actor or candidate_actor == str(actor_id)
                ) and (
                    not extra_actor or extra_actor == str(actor_id)
                )
                if (actor_matches
                        and not (candidate.output or "")
                        and not (candidate.tasks or [])):
                    part = candidate
                    part.agent_id = actor_id
                    part.name = agent_name
                    if not isinstance(part.extra, dict):
                        part.extra = {}
                    part.extra.update(payload)
                    self.runtime.window.core.ctx.update_part(main, part, sync_item=False)
                    break
        if part is None:
            part = self.runtime.window.core.ctx.begin_part(
                main, agent_id=actor_id, name=agent_name, output="",
                extra=payload, joiner=joiner,
            )
        self.runtime._actor_parts[actor] = part
        return part

    def _prepare_actor_response_part(self, actor: str):
        """Rotate the orchestrator partial at the first event of its next LLM pass."""
        actor = str(actor or "orchestrator")
        main = getattr(self.runtime.context, "ctx", None)
        if actor != "orchestrator":
            # Worker prose is private and lives only in its in-memory Memory.
            return None
        if self.runtime._actor_needs_new_part.get(actor):
            previous = self.runtime._actor_part(actor, create=False)
            if previous is not None:
                self.runtime._promote_part_tasks(previous)
            self.runtime._actor_needs_new_part[actor] = False
            # A ToolCallResult marks a chronological boundary. Tool-only passes
            # keep using the current partial, but the first real prose after the
            # completed tool chain must live in a fresh partial so the WebView can
            # render: previous text/tool(s) -> new text.
            return self.runtime._begin_actor_part(
                actor, reuse_initial=False,
                extra={"agents_v2_orchestrator": True},
                joiner="\n\n",
            )
        part = self.runtime._actor_part(actor, create=True)
        if part is not None:
            if not isinstance(part.extra, dict):
                part.extra = {}
            part.extra.setdefault("agents_v2_orchestrator", True)
            if not str(part.output or "").strip() and part.tasks:
                part.extra.setdefault(
                    "text_after_tool_round",
                    self.runtime.window.core.ctx._part_max_tool_round(part),
                )
                self.runtime.window.core.ctx.update_part(main, part, sync_item=False)
        return part

    def actor_part_uuid(self, actor: str = "orchestrator", prepare_response: bool = False) -> Optional[str]:
        """Return the UUID used by the UI stream to target the same DB partial."""
        part = self.runtime._prepare_actor_response_part(actor) if prepare_response else self.runtime._actor_part(actor, create=True)
        return getattr(part, "uuid", None) if part is not None else None

    def _prepare_final_part(self):
        """Return/mark the durable orchestrator partial containing final answer."""
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return None
        previous = self.runtime._actor_part("orchestrator", create=True)
        self.runtime._promote_all_tasks()
        if previous is not None and (
                str(previous.output or "").strip()
                or bool(getattr(previous, "tasks", None))
        ):
            # Final prose after any visible work/tool activity is a new timeline
            # segment as well. Reusing a tool-only partial would place the final
            # answer above that tool after a reload.
            part = self.runtime._begin_actor_part(
                "orchestrator", reuse_initial=False,
                extra={"agents_v2_orchestrator": True, "agents_v2_final": True},
                joiner="\n\n",
            )
        else:
            part = previous
            if part is not None:
                if not isinstance(part.extra, dict):
                    part.extra = {}
                part.extra["agents_v2_orchestrator"] = True
                part.extra["agents_v2_final"] = True
                self.runtime.window.core.ctx.update_part(main, part, sync_item=False)
        self.runtime._actor_needs_new_part["orchestrator"] = False
        if part is not None:
            self.runtime._actor_parts["orchestrator"] = part
        return part

    def last_orchestrator_output(self) -> str:
        """Return the latest persisted orchestrator prose fragment only.

        This is intentionally not the composed parent output. Agents v2 may own
        several textual partials in one user turn, and folding them here would
        turn the whole working trace into a synthetic final answer.
        """
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return ""
        for part in reversed(getattr(main, "parts", None) or []):
            extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if extra.get("agents_v2_worker") is True or extra.get("provider_history") is False:
                continue
            value = str(getattr(part, "output", None) or "").strip()
            if value:
                return value
        return ""

    def primary_response_boundary_pending(self) -> bool:
        """Return True when the last completed tool round has no streamed prose yet.

        ``ToolCallResult`` arms this boundary and the first following ``AgentStream``
        delta consumes it by rotating to a fresh partial.  At handler completion a
        still-pending boundary therefore means that the terminal handler result is
        the only place where the post-tool final answer can exist.
        """
        return bool(self.runtime._actor_needs_new_part.get("orchestrator"))

    def _primary_prose_outputs(self) -> list[str]:
        """Return persisted Primary Agent prose in chronological order.

        Tool-only rows and worker-private data are intentionally ignored.  This is
        used only to de-aggregate terminal LlamaIndex results; it does not change
        what is kept in durable partial history.
        """
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return []
        values = []
        for part in getattr(main, "parts", None) or []:
            extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if extra.get("agents_v2_worker") is True or extra.get("provider_history") is False:
                continue
            actor_id = str(getattr(part, "agent_id", "") or extra.get("agents_v2_actor", "") or "")
            if actor_id and actor_id != "orchestrator":
                continue
            value = str(getattr(part, "output", None) or "").strip()
            if value:
                values.append(value)
        return values

    def _strip_primary_prose_prefix(self, terminal_text: str) -> str:
        """Remove already-streamed Primary Agent prose from an aggregate result.

        Some LlamaIndex agent/provider combinations return ``handler``'s terminal
        ``response.content`` as the concatenation of every assistant text pass in
        the run (progress prose before tools + the actual final answer).  Those
        earlier passes are already stored as separate ``CtxItemPart`` records.
        Persisting the aggregate as the final part duplicates them in both
        ``ctx_item.output`` and the restored conversation.

        Only exact chronological prefixes are removed.  If the terminal result is
        already just the final answer, it is left untouched.
        """
        original = str(terminal_text or "").strip()
        if not original:
            return ""
        remaining = original
        removed = False
        for value in self.runtime._primary_prose_outputs():
            prefix = str(value or "").strip()
            if not prefix:
                continue
            candidate = remaining.lstrip()
            if not candidate.startswith(prefix):
                break
            tail = candidate[len(prefix):].lstrip()
            # Never turn a valid terminal result into an empty answer.  This also
            # covers providers whose handler result is exactly the already-streamed
            # final prose.
            if not tail:
                break
            remaining = tail
            removed = True
        return remaining.strip() if removed and remaining.strip() else original

    def resolve_primary_final_output(self, terminal_text: str = "") -> str:
        """Choose the authoritative final answer for the Primary Agent turn.

        The runtime-side stream buffer is preferred because it is segmented at
        both ordinary LlamaIndex tool calls and provider-native hosted-tool
        boundaries. This avoids depending on the asynchronously persisted parent
        CtxItem, whose current output may temporarily be the full working trace.
        """
        terminal = str(terminal_text or "").strip()
        streamed = self.runtime.primary_stream_final_output()
        if streamed:
            return streamed

        last_output = self.runtime.last_orchestrator_output()
        if last_output and not self.runtime.primary_response_boundary_pending():
            return last_output

        if terminal:
            resolved = self.runtime._strip_primary_prose_prefix(terminal)
            if resolved:
                return resolved

        return last_output or terminal

    def detach_primary_final_suffix(self, final_answer: str) -> bool:
        """Repair a mixed last partial that already contains progress + final text.

        This is a defensive fallback for provider/event-order edge cases. If a
        hosted-tool boundary arrived too late for the live renderer, the final
        answer may already be the suffix of the current partial. Remove only that
        exact suffix so _prepare_final_part() can persist/replay it as its own
        authoritative final segment.
        """
        final = str(final_answer or "").strip()
        if not final:
            return False
        main = getattr(self.runtime.context, "ctx", None)
        part = self.runtime._actor_part("orchestrator", create=False)
        if main is None or part is None:
            return False
        current = str(getattr(part, "output", None) or "")
        stripped = current.strip()
        if not stripped or stripped == final or not stripped.endswith(final):
            return False
        prefix = stripped[:-len(final)].rstrip()
        if not prefix:
            return False
        part.set_output(prefix)
        if not isinstance(part.extra, dict):
            part.extra = {}
        part.extra.pop("agents_v2_final", None)
        self.runtime.window.core.ctx.update_part(main, part, sync_item=False)
        self.runtime.verbose.log("PRIMARY AGENT MIXED PART REPAIRED", {
            "part_uuid": getattr(part, "uuid", None),
            "progress_chars": len(prefix),
            "final_chars": len(final),
        })
        return True

    def mark_current_part_final(self):
        """Mark the current orchestrator partial as the authoritative final one."""
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return None
        part = self.runtime._actor_part("orchestrator", create=False)
        if part is None:
            return None
        self.runtime._promote_all_tasks()
        if not isinstance(part.extra, dict):
            part.extra = {}
        part.extra["agents_v2_orchestrator"] = True
        part.extra["agents_v2_final"] = True
        self.runtime.window.core.ctx.update_part(main, part, sync_item=False)
        self.runtime._actor_needs_new_part["orchestrator"] = False
        self.runtime._actor_parts["orchestrator"] = part
        return part

    def orchestrator_memory_output(self, final_answer: str = "") -> str:
        """Build compact persisted orchestrator memory for future turns."""
        return self.runtime.memory_store.compose_turn_output(
            getattr(self.runtime.context, "ctx", None),
            final_answer=final_answer or self.runtime.final_answer,
        )
