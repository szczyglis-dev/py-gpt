"""Lazy core facades must avoid creating execution engines during UI setup."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.agents.agents import Agents
from pygpt_net.core.agents_v2.agents import AgentsV2, _PromptPreviewRuntime
from pygpt_net.core.agents_v2.mode import AgentMode


@pytest.mark.parametrize('cls,attribute,module,symbol', [
    (Agents, 'memory', 'pygpt_net.core.agents.memory', 'Memory'),
    (Agents, 'runner', 'pygpt_net.core.agents.runner', 'Runner'),
    (AgentsV2, 'runner', 'pygpt_net.core.agents_v2.runner', 'Runner'),
    (AgentsV2, 'memory_store', 'pygpt_net.core.agents_v2.memory', 'AgentsV2MemoryStore'),
])
def test_facades_construct_services_once_on_first_access(cls, attribute, module, symbol):
    window = MagicMock()
    with patch(module+'.'+symbol) as factory:
        core = cls(window)
        factory.assert_not_called()
        assert getattr(core, attribute) is factory.return_value
        assert getattr(core, attribute) is factory.return_value
        factory.assert_called_once_with(window)


def test_v2_history_counter_fallback_and_empty_context():
    core = AgentsV2(MagicMock())
    assert core.count_current_history_tokens(None) == (0, 0)
    core.window.core.ctx.get_last_item.return_value = None
    core.window.core.ctx.get_items.return_value = []
    assert core.count_current_history_tokens('model') == (0, 0)
    ctx = SimpleNamespace(meta=object())
    core.window.core.ctx.get_items.return_value = [ctx]
    core._memory_store = MagicMock()
    core._memory_store.count_history_tokens.return_value = (5, 7)
    assert core.count_current_history_tokens('model', 3, 100) == (5, 7)
    core._memory_store.count_history_tokens.assert_called_once_with(ctx, model='model', used_tokens=3, max_tokens=100)


def test_prompt_preview_uses_selected_context_without_creating_runner():
    window = MagicMock()
    core = AgentsV2(window)
    assert core.build_main_system_prompt_preview('prompt', None) == 'prompt'
    window.core.attachments.get_all.side_effect = RuntimeError('not ready')
    window.controller.idx.get_current.side_effect = RuntimeError('not ready')
    with patch('pygpt_net.core.agents_v2.agents._PromptPreviewRuntime') as preview:
        preview.return_value.prompts.main.return_value = 'composed'
        assert core.build_main_system_prompt_preview('prompt', 'model', 'ctx') == 'composed'
    assert preview.call_args.kwargs['attachments'] == {}
    assert preview.call_args.kwargs['index_id'] is None
    assert preview.call_args.kwargs['ctx'] == 'ctx'
    assert core._runner is None


@pytest.mark.parametrize('mode', list(AgentMode))
def test_preview_runtime_shares_prompt_context_and_limits(mode):
    window = MagicMock()
    window.core.config.get.side_effect = lambda key, default=None: default
    window.core.agents_v2.editor.resolve_selection.return_value = ('id', mode, None)
    with patch('pygpt_net.core.agents_v2.context.RuntimeContext') as context, \
         patch('pygpt_net.core.agents_v2.prompts.agents_directory_exists', return_value=False):
        preview = _PromptPreviewRuntime(window, 'model', None, None, {}, '_', ' prompt ')
    assert preview.index_id is None and preview.bridge_system_prompt == 'prompt'
    assert preview.is_swarm_mode is (mode == AgentMode.SWARM)
    assert preview.max_workers_configured == 16
    window.core.config.get.return_value = None
    window.core.config.get.side_effect = lambda key, default=None: 'invalid'
    assert preview.max_workers_configured == 16
    window.core.config.get.side_effect = lambda key, default=None: -3
    assert preview.max_workers_configured == 0
    preview.verbose.log('anything')
    preview.verbose.text('anything')
    context.return_value.shared_context.assert_called_once()
