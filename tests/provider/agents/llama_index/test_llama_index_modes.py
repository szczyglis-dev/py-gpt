import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
from llama_index.core.llms import ChatMessage
from llama_index.core.llms.mock import MockFunctionCallingLLM
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool
from workflows.errors import WorkflowCancelledByUser

from pygpt_net.core.agents.runners.llama_events import consume_handler
from pygpt_net.core.agents.compatibility import migrate_preset
from pygpt_net.core.agents.provider import Provider
from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.agents.llama_index.modes import ModeAgent, get_mode_agents
from pygpt_net.provider.agents.llama_index.workflow.events import StepEvent


def build(strategy, responses, options=None):
    provider = ModeAgent(strategy)
    preset = PresetItem()
    preset.extra = {provider.id: options or {}}
    preset.experts = []
    window = MagicMock()
    model = SimpleNamespace(id='test-model')
    seen = []
    replies = iter(responses)

    def respond(messages, **kwargs):
        seen.append(messages)
        value = next(replies)
        return value if isinstance(value, ChatMessage) else ChatMessage(role='assistant', content=value)

    window.core.idx.llm.get_agent.return_value = MockFunctionCallingLLM(response_generator=respond)
    kwargs = {'context': SimpleNamespace(preset=preset), 'model': model,
              'system_prompt': 'Help with the task.', 'max_iterations': 3, 'tools': []}
    return provider, window, kwargs, seen


def run(provider, window, kwargs, stop=None):
    output = []
    async def execute():
        workflow = provider.get_agent(window, kwargs)
        async def event(ev):
            output.append(ev)
        result = await consume_handler(workflow.run('User task', memory=ChatMemoryBuffer.from_defaults(
            chat_history=[ChatMessage(role='user', content='Earlier context')], token_limit=2000),
            on_stop=stop), event, stop or (lambda: False))
        return result
    return asyncio.run(execute()), output


@pytest.mark.parametrize('strategy,responses,options,answer,actors', [
    ('base', ['Answer'], {}, 'Answer', ['Agent']),
    ('feedback', ['Draft', '{"feedback":"Fix it","score":"fail"}', 'Improved',
                  '{"feedback":"Good","score":"pass"}'], {}, 'Improved',
     ['Agent', 'Evaluator', 'Agent', 'Evaluator', 'Final answer']),
    ('b2b', ['Proposal', 'Critique'], {'conversation': {'max_rounds': 1}}, 'Critique', ['Bot 1', 'Bot 2']),
    ('evolve', ['Weak', 'Strong', '{"answer_number":2}', '{"feedback":"Good","score":"pass"}'],
     {'base': {'num_parents': 2, 'max_generations': 2}}, 'Strong',
     ['Generation 1 · Candidate 1', 'Generation 1 · Candidate 2', 'Chooser', 'Evaluator', 'Final answer']),
    ('researcher', ['{"searches":[{"query":"source A"},{"query":"source B"}]}',
                    'Evidence A', 'Evidence B', 'Report'], {}, 'Report',
     ['Planner', 'Researcher', 'Researcher', 'Writer']),
])
def test_strategies_run_native_llama_workflows(strategy, responses, options, answer, actors):
    provider, window, kwargs, seen = build(strategy, responses, options)
    result, events = run(provider, window, kwargs)
    assert result == answer
    assert [event.meta['agent_name'] for event in events if isinstance(event, StepEvent)] == actors
    assert any('Earlier context' in str(message.content) for message in seen[0])
    visible = ''.join(event.delta for event in events if isinstance(event, AgentStream))
    assert '"score"' not in visible
    assert '"answer_number"' not in visible
    assert '"sub_tasks"' not in visible
    if strategy == 'feedback':
        assert 'Fix it' in str(seen[2])
    if strategy == 'evolve':
        assert 'Weak' not in str(seen[1])  # candidates have independent histories
        assert 'Strong' in str(seen[-1])
    if strategy == 'b2b':
        assert 'Proposal' in str(seen[1])
    if strategy == 'researcher':
        assert 'Evidence A' in str(seen[-1]) and 'Evidence B' in str(seen[-1])
    window.core.agents.provider.get_openai_model.assert_not_called()


def test_native_tools_are_executed_and_streamed():
    from llama_index.core.base.llms.types import ToolCallBlock, TextBlock
    provider, window, kwargs, seen = build('base', [
        ChatMessage(role='assistant', blocks=[TextBlock(text='Reading'),
            ToolCallBlock(tool_call_id='r1', tool_name='fs_read_file', tool_kwargs={'path':'a'})]), 'Done'])
    calls = []
    async def read_file(path: str):
        calls.append(path)
        return 'File contents'
    kwargs['tools'] = [FunctionTool.from_defaults(async_fn=read_file, name="fs_read_file")]
    result, events = run(provider, window, kwargs)
    assert result == 'Done' and calls == ['a']
    assert any(isinstance(event, ToolCallResult) for event in events)


def test_experts_use_llama_tools_and_return_to_the_parent():
    from llama_index.core.base.llms.types import ToolCallBlock
    provider, window, kwargs, _ = build('experts', [ChatMessage(role='assistant', blocks=[
        ToolCallBlock(tool_call_id='e1', tool_name='consult_expert_1', tool_kwargs={'query':'Analyze'})]),
        'Expert finding', 'Final synthesis'])
    expert = PresetItem()
    expert.name = 'Specialist'
    expert.prompt = 'Analyze carefully.'
    kwargs['context'].preset.experts = ['expert-id']
    window.core.presets.get_by_uuid.return_value = expert
    window.core.models.get.return_value = kwargs['model']
    result, events = run(provider, window, kwargs)
    assert result == 'Final synthesis'
    assert 'Specialist' in [event.meta['agent_name'] for event in events if isinstance(event, StepEvent)]
    assert any(isinstance(event, AgentStream) and event.delta for event in events)


def test_evolve_rejects_out_of_range_winner():
    p, w, kw, _ = build('evolve', ['A', 'B', '{"answer_number":3}'])
    with pytest.raises(Exception, match='nonexistent candidate'):
        run(p, w, kw)



def test_stop_prevents_next_bot_call():
    p, w, kw, seen = build('b2b', ['First'])
    with pytest.raises(WorkflowCancelledByUser):
        run(p, w, kw, stop=lambda: bool(seen))
    assert len(seen) == 1


def test_role_model_and_tool_permissions():
    p, w, kw, _ = build('feedback', [], {'feedback': {
        'model_overwrite': True, 'model':'review-model', 'allow_local_tools':False, 'allow_remote_tools':False}})
    w.core.models.get.return_value = SimpleNamespace(id='review-model')
    kw['tools'] = [FunctionTool.from_defaults(fn=lambda: 'ok', name='local')]
    workflow = p.get_agent(w, kw)
    role = p.build_role(w, kw, 'feedback', 'Evaluator', workflow=workflow, ctx=MagicMock())
    assert role.tools == []
    assert w.core.idx.llm.get_agent.call_args.kwargs['allow_remote_tools'] is False
    assert w.core.idx.llm.get_agent.call_args.args[0].id == 'review-model'


def test_registry_and_saved_preset_compatibility():
    registry = Provider()
    for provider in get_mode_agents():
        registry.register(provider.id, provider)
    for old in ('openai', 'react', 'openai_assistant'):
        assert registry.get(old).id == 'llama_agent_base'
        assert old not in registry.get_ids()
    preset = PresetItem()
    preset.agent_openai = True
    preset.agent_provider_openai = 'openai_agent_evolve'
    preset.extra = {'openai_agent_evolve': {'base': {'num_parents': 4}}}
    migrate_preset(preset)
    assert preset.agent_llama and preset.agent_provider == 'llama_agent_evolve'
    assert registry.get(preset.agent_provider).get_option(preset, 'base', 'num_parents') == 4
    assert preset.agent_provider_openai == 'openai_agent_evolve'


def test_evolve_improves_selected_candidate_in_next_generation():
    p, w, kw, seen = build('evolve', ['Weak', 'Selected', '{"answer_number":2}',
        '{"feedback":"Add evidence","score":"needs_improvement"}',
        'Improved A', 'Improved B', '{"answer_number":1}', '{"feedback":"Done","score":"pass"}'],
        {'base': {'num_parents': 2, 'max_generations': 2}})
    result, _ = run(p, w, kw)
    assert result == 'Improved A'
    for messages in seen[4:6]:
        assert 'Selected' in str(messages) and 'Add evidence' in str(messages)
    # Each candidate retains its OWN prior attempts, never the other candidate's.
    assert 'Weak' in str(seen[4])
    assert 'Weak' not in str(seen[5])


def test_migration_keeps_explicit_llama_choice_and_copies_options_independently():
    preset = PresetItem()
    preset.agent_openai = True
    preset.agent_provider_openai = 'openai_agent_evolve'
    preset.extra = {'openai_agent_evolve': {'base': {'num_parents': 4}}}
    migrate_preset(preset)
    preset.extra['llama_agent_evolve']['base']['num_parents'] = 2
    assert preset.extra['openai_agent_evolve']['base']['num_parents'] == 4
    preset.agent_provider = 'supervisor'
    migrate_preset(preset)
    assert preset.agent_provider == 'supervisor'


def test_feedback_limit_keeps_last_answer_and_reports_limit():
    from unittest.mock import AsyncMock
    from pygpt_net.provider.agents.llama_index.workflow.modes import Feedback
    p, w, kw, _ = build('feedback', [])
    kw['max_iterations'] = 1
    workflow = p.get_agent(w, kw)
    workflow.role = AsyncMock(side_effect=['Draft', Feedback(feedback='Improve', score='fail')])
    ctx = MagicMock()
    assert asyncio.run(workflow.feedback(ctx, 'Task')) == 'Draft'
    assert workflow.role.await_count == 2
    assert any(isinstance(call.args[0], AgentStream) and 'limit reached' in call.args[0].delta
               for call in ctx.write_event_to_stream.call_args_list)


def test_migration_does_not_copy_options_between_different_strategies():
    preset = PresetItem()
    preset.agent_openai = preset.agent_llama = True
    preset.agent_provider_openai = 'openai_agent_evolve'
    preset.agent_provider = 'llama_agent_base'
    preset.extra = {'openai_agent_evolve': {'base': {'prompt': 'Evolve prompt'}}}
    migrate_preset(preset)
    assert 'llama_agent_base' not in preset.extra
