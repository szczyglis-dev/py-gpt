"""Inline experts use the shared tool runtime without leaking chat rendering events."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pygpt_net.core.agents_v2.expert import (ExpertAgentBridge, _ExpertEmitter, _ExpertStatus,
                                           _ExpertHistory, _RuntimeSignalsProxy)
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.types import TOOL_EXPERT_CALL_NAME


@pytest.mark.parametrize('preset,user,expected', [(' preset ', '', 'preset'), ('', ' user ', 'user'),
    ('preset', 'user', 'user\n\n<additional_user_system_instruction>\npreset\n</additional_user_system_instruction>')])
def test_prompt_composition(preset, user, expected):
    assert ExpertAgentBridge.compose_system_prompt(preset, user) == expected


def test_headless_signals_only_forward_plugin_execution():
    signals = SimpleNamespace(event=MagicMock())
    proxy = _RuntimeSignalsProxy(signals)
    emitter = _ExpertEmitter(MagicMock(), {}, proxy)
    emitter._emit(KernelEvent.AGENT_V2_TOOL_EXEC, request='tool')
    assert signals.event.emit.call_count == 1
    assert signals.event.emit.call_args.args[0].name == KernelEvent.AGENT_V2_TOOL_EXEC
    emitter._emit(KernelEvent.AGENT_V2_BEGIN)
    emitter.show_loading()
    assert signals.event.emit.call_count == 1
    rt = MagicMock()
    status = _ExpertStatus(rt)
    status.emit('progress')
    status.worker(MagicMock(), 'progress')
    rt.emitter.status.assert_not_called()
    history = _ExpertHistory(rt)
    assert history.record_local_call('read', {})
    history.record_local_result('id', 'read', 'result')
    history.record_call(MagicMock())
    history.record_result(MagicMock())
    history.export()
    rt.window.core.ctx.update_part.assert_not_called()


def test_history_respects_context_switch_and_model_limit():
    window = MagicMock()
    bridge = ExpertAgentBridge(window, MagicMock())
    context = SimpleNamespace(model=SimpleNamespace(id='m', ctx=1024), history=['stored'])
    window.core.config.get.side_effect = lambda key: {'use_context': False, 'max_total_tokens': 4096}.get(key)
    assert bridge._history(context, 'request') == []
    window.core.ctx.get_history.assert_not_called()
    window.core.config.get.side_effect = lambda key: {'use_context': True, 'max_total_tokens': 4096}.get(key)
    window.core.models.get_num_ctx.side_effect = ValueError('unknown')
    window.core.tokens.from_user.return_value = 7
    window.core.ctx.get_history.return_value = [SimpleNamespace(final_input='Q', output='A'),
                                               SimpleNamespace(final_input='', output='')]
    messages = bridge._history(context, 'request')
    assert [m.content for m in messages] == ['Q', 'A']
    window.core.ctx.get_history.assert_called_once_with(['stored'], 'm', 'expert', 7, 1024, ignore_first=True)


@pytest.mark.parametrize('fail', [False, True])
def test_expert_call_excludes_recursive_expert_tool_and_cleans_up(fail):
    window = MagicMock()
    bridge = ExpertAgentBridge(window, MagicMock())
    bridge._history = MagicMock(return_value=[])
    ctx = SimpleNamespace(preset=SimpleNamespace(name='Expert', description='Specialist'), system_prompt='instruction')
    rt = MagicMock()
    rt.workers.cleanup = AsyncMock()
    rt.inputs.message.return_value = 'input'
    rt.model = SimpleNamespace(id='m', provider='openai')
    rt.main_max_iterations = 10
    agent = rt.inputs.agent.return_value
    async def execute():
        if fail:
            raise RuntimeError('provider failure')
        return 'answer'
    agent.run.side_effect = lambda **kwargs: execute()
    with patch('pygpt_net.core.agents_v2.expert._ExpertRuntime', return_value=rt):
        if fail:
            with pytest.raises(RuntimeError, match='provider failure'):
                bridge.call(ctx, 'task')
        else:
            assert bridge.call(ctx, 'task') == 'answer'
    assert rt.return_tool_calls_to_main_ctx is False
    rt.tool_factory.build_orchestrator.assert_called_once_with(rt.primary_actor, exclude={TOOL_EXPERT_CALL_NAME})
    rt.workers.cleanup.assert_awaited_once()


def test_expert_runtime_replaces_status_and_history_after_shared_setup():
    from pygpt_net.core.agents_v2.expert import _ExpertRuntime
    with patch('pygpt_net.core.agents_v2.expert.AgentsV2Runtime.__init__', return_value=None):
        rt = _ExpertRuntime()
    assert isinstance(rt.status, _ExpertStatus)
    assert isinstance(rt.tool_history, _ExpertHistory)
