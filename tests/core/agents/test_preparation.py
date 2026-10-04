"""Policies shared by legacy full workflows and quick expert calls."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.agents.preparation import AgentPreparation, PreparedAgentCall
from pygpt_net.core.types import AGENT_MODE_WORKFLOW
from pygpt_net.item.ctx import CtxItem


@pytest.fixture
def preparation():
    window = MagicMock()
    window.core.config.get.side_effect = lambda key, default=None: default
    return AgentPreparation(window, {'system-agent'}, 'Retrieved context:')


def context():
    return SimpleNamespace(ctx=CtxItem(), prompt='question', system_prompt='instructions',
                           mode='agent_llama', preset=None, model=SimpleNamespace(id='model'),
                           is_expert_call=True, stream=True)


@pytest.mark.parametrize('once', [False, True])
def test_provider_validation_and_registry_namespace(preparation, once):
    ctx = context()
    registry = preparation.window.core.agents.provider
    args = ('missing',) if once else ('missing', ctx.mode)
    registry.has.return_value = False
    with pytest.raises(Exception, match='Agent not found: missing'):
        preparation._get_provider('missing', ctx, once, validate=True)
    registry.has.assert_called_once_with(*args)
    registry.get.assert_not_called()
    registry.has.return_value = True
    assert preparation._get_provider('available', ctx, once, validate=True) is registry.get.return_value


@pytest.mark.parametrize('once,workflow,visible', [(True, False, False), (False, True, True), (False, False, None)])
def test_session_visibility(preparation, once, workflow, visible):
    provider = MagicMock()
    provider.get_mode.return_value = AGENT_MODE_WORKFLOW if workflow else 'other'
    ctx, signals = context(), MagicMock()
    with patch('pygpt_net.core.agents.preparation.LlamaSession') as session:
        result = preparation._create_session(provider, ctx, {}, signals, once)
    if visible is None:
        assert result is None
        session.assert_not_called()
    elif visible:
        session.assert_called_once_with(preparation.window, ctx, {}, signals)
    else:
        session.assert_called_once_with(preparation.window, ctx, {}, signals, visible=False)


@pytest.mark.parametrize('once', [False, True])
def test_input_markers(preparation, once):
    ctx = context().ctx
    preparation._mark_input(ctx, once)
    assert ctx.agent_call is True
    assert ctx.extra['agent_input'] is True
    assert ctx.extra.get('agent_output', False) is once


@pytest.mark.parametrize('workflow', [False, True])
def test_build_agent_uses_composed_prompt_only_for_workflows(preparation, workflow):
    provider = MagicMock()
    provider.get_mode.return_value = AGENT_MODE_WORKFLOW if workflow else 'other'
    provider.get_system_prompt_extra.return_value = 'extracted'
    kwargs = {'system_prompt': 'composed'}
    assert preparation._build_agent(provider, kwargs) is provider.get_agent.return_value
    assert kwargs['system_prompt_extra'] == ('composed' if workflow else 'extracted')
    provider.get_agent.assert_called_once_with(preparation.window, kwargs)


def test_system_message_is_prepended_without_replacing_history(preparation):
    history = ['previous']
    preparation._append_system_message('other', 'prompt', history)
    preparation._append_system_message('system-agent', '', history)
    assert history == ['previous']
    preparation._append_system_message('system-agent', 'prompt', history)
    assert history[0].content == 'prompt'
    assert history[0].role.value == 'system'
    assert history[1] == 'previous'


@pytest.mark.parametrize('idx', [None, '', '_'])
def test_retrieval_is_skipped_without_selected_index(preparation, idx):
    ctx = context()
    assert preparation._append_retrieved_context(ctx, idx) == 'question'
    preparation.window.core.idx.chat.query_retrieval.assert_not_called()


def test_retrieval_preserves_existing_hidden_context(preparation):
    ctx = context()
    preparation.window.core.idx.chat.query_retrieval.return_value = 'evidence'
    assert preparation._append_retrieved_context(ctx, 'index') == 'question\n\nRetrieved context:\nevidence'
    assert ctx.ctx.hidden_input == 'Retrieved context:\nevidence'
    preparation._append_retrieved_context(ctx, 'index')
    assert ctx.ctx.hidden_input == 'Retrieved context:\nevidence\nevidence'
    preparation.window.core.idx.chat.query_retrieval.return_value = ''
    assert preparation._append_retrieved_context(ctx, 'index') == 'question'


@pytest.mark.parametrize('once', [False, True])
def test_index_override_policy(preparation, once):
    ctx = context()
    ctx.preset = SimpleNamespace(idx='preset-index')
    extra = {'agent_idx': 'explicit-index'}
    assert preparation._select_index(ctx, extra, once) == ('explicit-index' if once else 'preset-index')
    assert extra['agent_idx'] == ('explicit-index' if once else 'preset-index')


@pytest.mark.parametrize('once,is_cmd', [(False, False), (False, True), (True, False), (True, True)])
def test_tool_selection_respects_command_policy(preparation, once, is_cmd):
    factory = MagicMock()
    factory.prepare.return_value = ['tool']
    factory.get_function_tools.return_value = ['function']
    factory.get_plugin_tools.return_value = ['plugin']
    factory.get_plugin_specs.return_value = ['spec']
    factory.get_retriever_tool.return_value = 'retriever'
    result = preparation._prepare_tools(context(), {}, factory, is_cmd, once)
    assert result['tools'] == (['tool'] if is_cmd else [])
    if not once:
        assert result['function_tools'] == (['function'] if is_cmd else [])
        assert result['retriever_tool'] == 'retriever'
    else:
        factory.get_function_tools.assert_not_called()
    explicit = ['explicit']
    assert preparation._prepare_tools(context(), {'agent_tools': explicit}, factory, False, True)['tools'] is explicit


def test_model_and_tool_factory_bind_shared_session(preparation):
    ctx, session, computer = context(), MagicMock(), MagicMock()
    preparation.window.core.agents.tools.cmd_blacklist = ['private']
    with patch('pygpt_net.core.agents.preparation.ComputerRuntime', return_value=computer):
        actual_computer, llm = preparation._prepare_model(ctx, session)
    assert actual_computer is computer
    session.bind_llm.assert_called_once_with(llm)
    with patch('pygpt_net.core.agents.preparation.Tools') as factory:
        tools = preparation._prepare_tool_factory(ctx, session, computer, 'idx')
    factory.assert_called_once_with(preparation.window, executor=session.execute_plugin)
    assert tools.cmd_blacklist == ['private']
    assert tools.cmd_blacklist is not preparation.window.core.agents.tools.cmd_blacklist
    tools.set_context.assert_called_once_with(ctx)
    tools.set_computer_runtime.assert_called_once_with(computer)
    tools.set_idx.assert_called_once_with('idx')


def test_prepared_call_exposes_only_execution_arguments():
    ctx = context()
    prepared = PreparedAgentCall('id', 'provider', 'agent', ctx, 'prompt', 'signals', True,
                                None, [], 'llm', {}, False, False)
    assert prepared.execution_kwargs() == dict(agent='agent', ctx=ctx.ctx, prompt='prompt', signals='signals', verbose=True)


@pytest.mark.parametrize('once', [False, True])
def test_complete_preparation_preserves_quick_call_policies(preparation, once):
    ctx, signals = context(), MagicMock()
    provider = MagicMock()
    provider.get_mode.return_value = AGENT_MODE_WORKFLOW
    session, factory = MagicMock(), MagicMock()
    preparation._get_provider = MagicMock(return_value=provider)
    preparation._create_session = MagicMock(return_value=session)
    preparation._system_prompt = MagicMock(return_value='composed')
    preparation._prepare_model = MagicMock(return_value=('computer', 'llm'))
    preparation._prepare_tool_factory = MagicMock(return_value=factory)
    preparation._prepare_tools = MagicMock(return_value={'tools': ['tool']})
    preparation._build_agent = MagicMock(return_value='agent')
    preparation.window.core.command.is_cmd.return_value = True
    extra = {'agent_history': ['explicit']}
    result = preparation.prepare(ctx, extra, signals, 'id', False, once=once)
    assert result.agent == 'agent' and result.llm == 'llm'
    assert result.session is session
    assert result.is_expert_call is once
    assert result.agent_kwargs['system_prompt'] == 'composed'
    assert result.agent_kwargs['input_builder'] is session.build_worker_message
    if once:
        assert result.history is extra['agent_history'] and result.stream is False
        factory.get_plugin_tools.assert_called_once_with(ctx, extra, force=True)
    else:
        assert result.history is preparation.window.core.agents.memory.prepare.return_value


def test_system_prompt_preserves_composed_history_for_continuations(preparation):
    ctx = context()
    provider = MagicMock()
    provider.get_mode.return_value = AGENT_MODE_WORKFLOW
    with patch('pygpt_net.core.agents.preparation.agents_directory_exists', return_value=True), \
         patch('pygpt_net.core.agents.preparation.append_agents_directory_support', return_value='directory prompt'), \
         patch('pygpt_net.core.agents.preparation.BaseAgent.append_security_rule', side_effect=lambda value: value+' secure'):
        assert preparation._system_prompt(provider, ctx, False) == 'directory prompt secure'
    assert ctx.ctx.agents_v2_system_prompt == 'directory prompt'
