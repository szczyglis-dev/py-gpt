#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 16:00:00                  #
# ================================================== #

from __future__ import annotations

import json
from enum import Enum
from typing import Any


class AgentsV2Debug:
    """Realtime/post-run inspector for Chat with Agents (Agents v2)."""

    def __init__(self, window=None):
        self.window = window
        self.id = 'agents_v2'

    @staticmethod
    def _value(value: Any) -> str:
        """Render mutable/runtime values without requiring them to be JSON-native."""
        if isinstance(value, Enum):
            return str(value.value)
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return str(value)

    def _add(self, key: str, value: Any):
        self.window.core.debug.add(self.id, key, self._value(value))

    def _section(self, title: str):
        self._add(f'[{title}]', '')

    @staticmethod
    def _part(part):
        if part is None:
            return None
        return {
            'uuid': getattr(part, 'uuid', None),
            'id': getattr(part, 'id', None),
            'agent_id': getattr(part, 'agent_id', None),
            'name': getattr(part, 'name', None),
            'output': getattr(part, 'output', None),
            'extra': getattr(part, 'extra', None),
            'tasks': getattr(part, 'tasks', None),
        }

    def _workers(self, runtime):
        live = {}
        try:
            items = list(runtime.workers.items())
        except Exception:
            items = []
        for worker_id, state in items:
            try:
                live[worker_id] = {
                    **state.public_dict(include_result=True),
                    'instruction': state.instruction,
                    'system_prompt': state.system_prompt,
                    'stop_requested': state.stop_requested,
                    'task_done': bool(state.task.done()) if state.task is not None else None,
                    'task_cancelled': bool(state.task.cancelled()) if state.task is not None else None,
                }
            except Exception as exc:
                live[str(worker_id)] = {'debug_error': str(exc)}
        if live:
            return live
        snapshot = getattr(runtime, 'debug_cleanup_snapshot', None)
        if isinstance(snapshot, dict):
            return snapshot.get('workers', {})
        return {}

    def update(self):
        debug = self.window.core.debug
        runner = self.window.core.agents_v2.runner
        runtime = getattr(runner, 'current_runtime', None) or getattr(runner, 'last_runtime', None)

        debug.begin(self.id)
        self._section('RUNNER')
        self._add('active', getattr(runner, 'current_runtime', None) is not None)
        self._add('last_error', getattr(runner, 'last_error', None))

        if runtime is None:
            self._add('runtime', 'No Agents v2 run in this application session.')
            debug.end(self.id)
            return

        self._section('RUNTIME')
        self._add('run_id', getattr(runtime, 'run_id', None))
        self._add('agent_mode', getattr(runtime, 'agent_mode', None))
        strategy = getattr(runtime, 'strategy', None)
        self._add('strategy_mode', getattr(strategy, 'mode', None))
        self._add('tool_surface', getattr(strategy, 'tool_surface', None))
        self._add('main_agent_name', getattr(runtime, 'main_agent_name', None))
        self._add('model', getattr(getattr(runtime, 'model', None), 'id', None))
        self._add('provider', getattr(getattr(runtime, 'model', None), 'provider', None))
        preset = getattr(runtime, 'preset', None)
        self._add('preset', getattr(preset, 'name', None) or getattr(preset, 'id', None))
        self._add('index_id', getattr(runtime, 'index_id', None))
        self._add('sequence', getattr(runtime, 'sequence', None))
        self._add('finished', getattr(runtime, 'finished', None))
        snapshot = getattr(runtime, 'debug_cleanup_snapshot', {}) or {}
        self._add('kernel_stopped', runtime.is_stopped())
        self._add('stopped_at_cleanup', snapshot.get('stopped'))
        self._add('workflow_final_requested', getattr(runtime, 'workflow_final_requested', None))
        self._add('workflow_final_stream_started', getattr(runtime, 'workflow_final_stream_started', None))
        self._add('workflow_final_hint', getattr(runtime, 'workflow_final_hint', None))
        self._add('final_answer', getattr(runtime, 'final_answer', None))
        self._add('event_count', getattr(runtime, 'debug_event_count', None))
        self._add('event_types', getattr(runtime, 'debug_event_types', None))

        self._section('LIMITS / POLICIES')
        self._add('main_max_iterations_configured', runtime.main_max_iterations_configured)
        self._add('worker_max_iterations_configured', runtime.worker_max_iterations_configured)
        self._add('max_workers_configured', runtime.max_workers_configured)
        self._add('uses_workflow_finish', runtime.uses_workflow_finish)
        self._add('allow_local_tools', getattr(runtime, 'allow_local_tools', None))
        self._add('allow_remote_tools', getattr(runtime, 'allow_remote_tools', None))
        self._add('show_tool_chain', getattr(runtime, 'return_tool_calls_to_main_ctx', None))
        self._add('step_by_step', getattr(runtime, 'step_by_step_enabled', None))
        self._add('local_plugin_tool_names', sorted(getattr(runtime, '_local_plugin_tool_names', set())))

        self._section('CONTEXT / PROMPTS')
        self._add('rag_context_text', getattr(runtime, 'rag_context_text', None))
        self._add('shared_context_text', getattr(runtime, 'shared_context_text', None))
        self._add('runtime_system_context', getattr(runtime, 'runtime_system_context', None))
        self._add('bridge_system_prompt', getattr(runtime, 'bridge_system_prompt', None))
        try:
            self._add('main_agent_prompt', runtime.main_agent_prompt())
        except Exception as exc:
            self._add('main_agent_prompt', f'<debug error: {exc}>')
        context = getattr(runtime, 'context', None)
        self._add('input_prompt', getattr(context, 'prompt', None))
        self._add('context_system_prompt', getattr(context, 'system_prompt', None))
        self._add('attachments', getattr(context, 'attachments', None))
        self._add('file_ids', getattr(context, 'file_ids', None))
        main_ctx = getattr(context, 'ctx', None)
        self._add('ctx_input', getattr(main_ctx, 'input', None))
        self._add('ctx_output', getattr(main_ctx, 'output', None))
        self._add('ctx_results', getattr(main_ctx, 'results', None))
        self._add('ctx_extra', getattr(main_ctx, 'extra', None))

        self._section('WORKERS / SWARM')
        self._add('workers', self._workers(runtime))
        self._add('swarm_expected_workers', getattr(runtime, 'swarm_expected_workers', None))
        self._add('swarm_created_workers', getattr(runtime, 'swarm_created_workers', None))
        self._add('swarm_launched_workers', getattr(runtime, 'swarm_launched_workers', None))
        self._add('swarm_worker_numbers', dict(getattr(runtime, '_swarm_worker_numbers', {})) or snapshot.get('swarm_worker_numbers', {}))
        self._add('worker_parent_parts', {
            str(k): getattr(v, 'uuid', None)
            for k, v in getattr(runtime, '_worker_parent_parts', {}).items()
        } or snapshot.get('worker_parent_parts', {}))
        self._add('stored_worker_context_runs', list(getattr(runtime, '_stored_worker_context_runs', set())) or snapshot.get('stored_worker_context_runs', []))

        self._section('TIMELINE / PARTIALS')
        self._add('ctx_parts', [self._part(part) for part in (getattr(main_ctx, 'parts', None) or [])])
        self._add('primary_stream_current', getattr(runtime, '_primary_stream_current', None))
        self._add('primary_stream_completed', getattr(runtime, '_primary_stream_completed', None))
        self._add('primary_tool_activity_seen', getattr(runtime, '_primary_tool_activity_seen', None))
        self._add('actor_parts', {
            str(actor): self._part(part)
            for actor, part in getattr(runtime, '_actor_parts', {}).items()
        })
        self._add('actor_needs_new_part', getattr(runtime, '_actor_needs_new_part', None))
        self._add('actor_part_seq', getattr(runtime, '_actor_part_seq', None))

        self._section('TOOLS / TASKS')
        self._add('main_tool_calls', getattr(runtime, '_main_tool_calls', None))
        self._add('main_tool_call_seq', getattr(runtime, '_main_tool_call_seq', None))
        self._add('persisted_tool_tasks', getattr(runtime, '_persisted_tool_tasks', None))
        self._add('actor_llms', {
            str(actor): type(llm).__name__
            for actor, llm in getattr(runtime, '_actor_llms', {}).items()
        })
        self._add('artifact_seen', getattr(runtime, '_artifact_seen', None))

        self._section('STATUS')
        self._add('status_seq', getattr(runtime, '_status_seq', None))
        self._add('status_events', getattr(runtime, 'status_events', None))
        self._add('last_swarm_status_at', getattr(runtime, '_last_swarm_status_at', None))
        reporter = getattr(runtime, '_swarm_reporter_task', None)
        self._add('swarm_reporter_task', {
            'exists': reporter is not None,
            'done': reporter.done() if reporter is not None else None,
            'cancelled': reporter.cancelled() if reporter is not None else None,
        })

        self._section('EMITTER / STREAM')
        emitter = getattr(runtime, 'emitter', None)
        if emitter is not None:
            for name in (
                '_begun', '_first_chunk', '_finished', 'text', 'status_text',
                '_pending_part_uuid', '_last_emitted_part_uuid', 'final_started',
                '_status_hold_until', '_pending_status', '_pending_chunk',
                '_last_stream_emit', '_stream_emit_interval', '_stream_emit_chars',
                '_final_stream_enabled', '_final_stream_chunk_chars', '_final_stream_delay',
            ):
                self._add(name, getattr(emitter, name, None))
        else:
            self._add('emitter', None)

        debug.end(self.id)
