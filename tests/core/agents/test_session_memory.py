import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from llama_index.core.llms import ChatMessage
from llama_index.core.llms.mock import MockFunctionCallingLLM
from llama_index.core.tools import FunctionTool
from llama_index.core.base.llms.types import ToolCallBlock

from pygpt_net.core.agents.agents import Agents
from pygpt_net.core.agents.session_memory import role_memory, memory_namespace
from pygpt_net.core.agents.runners.llama_events import consume_handler
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.agents.llama_index.supervisor_workflow import SupervisorAgent
from pygpt_net.provider.agents.llama_index.modes import ModeAgent


def setup():
    window = MagicMock()
    window.core.agents = Agents(window)
    preset = PresetItem()
    preset.uuid = 'preset-one'
    ctx = CtxItem()
    ctx.meta = CtxMeta(id=1)
    context = BridgeContext(ctx=ctx, preset=preset)
    return window, context


def execute(workflow, prompt):
    async def run():
        async def ignore(event):
            pass
        return await consume_handler(workflow.run(prompt), ignore, lambda: False)
    return asyncio.run(run())


def test_scoped_cache_isolates_roles_presets_workflows_and_conversations():
    window, context = setup()
    provider = ModeAgent('base')
    memory = role_memory(window, provider, context, 'worker')
    assert role_memory(window, provider, context, 'worker') is memory
    assert role_memory(window, provider, context, 'supervisor') is not memory
    assert role_memory(window, ModeAgent('feedback'), context, 'worker') is not memory
    context.preset.uuid = 'other-preset'
    assert role_memory(window, provider, context, 'worker') is not memory
    context.preset.uuid = 'preset-one'
    context.ctx.meta = CtxMeta(id=2)
    assert role_memory(window, provider, context, 'worker') is not memory
    context.ctx.meta = CtxMeta(id=1)  # reloaded object for the same conversation
    assert role_memory(window, provider, context, 'worker') is memory
    window.core.agents.clear_session_memory(1)
    assert role_memory(window, provider, context, 'worker') is not memory


def test_unsaved_meta_memory_survives_save_and_detached_calls_do_not_share():
    window, context = setup()
    core = window.core.agents
    meta = CtxMeta()
    value = core.get_session_memory(meta, 'flow', 'actor', list)
    meta.id = 99
    assert core.get_session_memory(meta, 'flow', 'actor', list) is value
    assert core.get_session_memory(CtxMeta(99), 'flow', 'actor', list) is value
    assert core.get_session_memory(None, 'flow', 'actor', list) is not core.get_session_memory(None, 'flow', 'actor', list)


def test_custom_provider_identity_uses_custom_id_not_base_provider_id():
    from pygpt_net.provider.agents.llama_index.flow_from_schema import Agent
    _, context = setup()
    one, two = Agent(), Agent()
    one.set_id('flow-one')
    two.set_id('flow-two')
    assert one.id == two.id
    assert memory_namespace(one, context) != memory_namespace(two, context)


def test_supervisor_worker_keeps_tool_history_across_turns_and_event_loops():
    window, context = setup()
    provider = SupervisorAgent()
    sup_seen, worker_seen = [], []
    sup_replies = iter(['{"action":"task","instruction":"Read"}', '{"action":"final","final_answer":"OK"}',
                        '{"action":"task","instruction":"Recall"}', '{"action":"final","final_answer":"OK"}',
                        '{"action":"task","instruction":"New chat"}', '{"action":"final","final_answer":"OK"}'])
    worker_replies = iter([ChatMessage(role='assistant', blocks=[ToolCallBlock(
        tool_call_id='r1', tool_name='fs_read_file', tool_kwargs={})]), 'Done', 'Remembered', 'New'])
    def sup_response(messages, **kwargs):
        sup_seen.append(messages)
        return ChatMessage(role='assistant', content=next(sup_replies))
    def worker_response(messages, **kwargs):
        worker_seen.append(messages)
        value = next(worker_replies)
        return value if isinstance(value, ChatMessage) else ChatMessage(role='assistant', content=value)
    supervisor = MockFunctionCallingLLM(response_generator=sup_response)
    worker = MockFunctionCallingLLM(response_generator=worker_response)
    window.core.idx.llm.get_agent.side_effect = lambda *a, **kw: worker if kw['allow_remote_tools'] else supervisor
    async def read_file():
        return 'Secret from the file: 4817'
    kwargs = {'context': context, 'model': SimpleNamespace(id='mock'),
              'tools':[FunctionTool.from_defaults(async_fn=read_file)], 'verbose':False}
    execute(provider.get_agent(window, kwargs), 'First turn')
    # Same meta id, new CtxItem/workflow instance, and a fresh asyncio.run loop.
    context.ctx = CtxItem()
    context.ctx.meta = CtxMeta(1)
    execute(provider.get_agent(window, kwargs), 'Second turn')
    assert '4817' in str(worker_seen[2])
    assert 'First turn' in str(sup_seen[2]) and 'Second turn' in str(sup_seen[2])
    context.ctx.meta = CtxMeta(2)
    execute(provider.get_agent(window, kwargs), 'Unrelated turn')
    assert '4817' not in str(worker_seen[3])
    assert 'First turn' not in str(sup_seen[4])


def test_modes_keep_role_memory_across_new_workflow_instances():
    window, context = setup()
    provider = ModeAgent('feedback')
    seen = []
    replies = iter(['Draft one', '{"feedback":"Good one","score":"pass"}',
                    'Draft two', '{"feedback":"Good two","score":"pass"}'])
    def response(messages, **kwargs):
        seen.append(messages)
        return ChatMessage(role='assistant', content=next(replies))
    window.core.idx.llm.get_agent.return_value = MockFunctionCallingLLM(response_generator=response)
    kwargs = {'context':context,'model':SimpleNamespace(id='mock'), 'max_iterations':2}
    assert execute(provider.get_agent(window, kwargs), 'First task') == 'Draft one'
    assert execute(provider.get_agent(window, kwargs), 'Second task') == 'Draft two'
    assert 'Draft one' in str(seen[2]) and 'Second task' in str(seen[2])
    assert 'Good one' in str(seen[3])
    assert 'Good one' not in str(seen[2])  # evaluator's private history stays separate


def test_workflow_state_snapshots_preserve_memory_writes():
    from workflows.context import Context
    from pygpt_net.core.agents.session_memory import WorkflowMemory
    from llama_index.core.agent.workflow import FunctionAgent
    memory = WorkflowMemory.from_defaults(token_limit=1000)
    async def run():
        context = Context(FunctionAgent(llm=MockFunctionCallingLLM()))
        await context.store.set('memory', memory)
        stored = await context.store.get('memory')
        await stored.aput(ChatMessage(role='user', content='remember this'))
        assert (await memory.aget_all())[0].content == 'remember this'
        assert await context.store.get('memory') is memory
    asyncio.run(run())


def test_custom_connected_memory_keeps_tool_messages_and_no_memory_stays_stateless():
    from pygpt_net.provider.agents.llama_index.flow_from_schema import Agent
    window, context = setup()
    provider = Agent()
    provider.set_id('custom-one')
    seen = []
    replies = iter([ChatMessage(role='assistant', blocks=[ToolCallBlock(
        tool_call_id='c1', tool_name='fs_read_file', tool_kwargs={})]), 'Done', 'Recall', 'Fresh', 'No memory'])
    def response(messages, **kwargs):
        seen.append(messages)
        value = next(replies)
        return value if isinstance(value, ChatMessage) else ChatMessage(role='assistant', content=value)
    llm = MockFunctionCallingLLM(response_generator=response)
    window.core.idx.llm.get_agent.return_value = llm
    async def read_file():
        return 'custom-private-value-123'
    schema = [
        {'id':'start', 'type':'start', 'slots':{'output':{'out':['worker']}}},
        {'id':'worker','type':'agent','slots':{'name':'Worker', 'instruction':'Help',
            'output':{'out':['end']}, 'memory':{'out':['mem']}}},
        {'id':'end', 'type':'end', 'slots':{}}, {'id':'mem', 'type':'memory', 'slots':{}},
    ]
    kwargs = {'context':context, 'schema':schema, 'llm':llm, 'model':None,
              'tools':[FunctionTool.from_defaults(async_fn=read_file)], 'verbose':False}
    execute(provider.get_agent(window, kwargs), 'First task')
    execute(provider.get_agent(window, kwargs), 'New task')
    assert 'custom-private-value-123' in str(seen[2])
    assert seen[2][-1].content == 'New task'
    # A different custom workflow with identical node ids must not share memory.
    provider.set_id('custom-two')
    execute(provider.get_agent(window, kwargs), 'Other flow')
    assert 'custom-private-value-123' not in str(seen[3])
    provider.set_id('custom-one')
    del schema[1]['slots']['memory']
    execute(provider.get_agent(window, kwargs), 'Disconnected memory')
    assert 'custom-private-value-123' not in str(seen[4])
    assert 'First task' not in str(seen[4])


def test_subtask_planner_executor_retains_its_own_tool_history():
    from pygpt_net.provider.agents.llama_index.planner_workflow import PlannerAgent
    window, context = setup()
    provider = PlannerAgent()
    context.preset.extra = {'planner': {'plan_refine': {'after_each_subtask': False}}}
    planning_inputs, execution_inputs = [], []
    replies = iter([ChatMessage(role='assistant', blocks=[ToolCallBlock(
        tool_call_id='p1', tool_name='fs_read_file', tool_kwargs={})]), 'Completed first', 'Completed second'])
    class PlannerLLM(MockFunctionCallingLLM):
        async def astructured_predict(self, output_cls, prompt, **kwargs):
            planning_inputs.append(kwargs)
            return output_cls(sub_tasks=[{'name':'work', 'input':kwargs['task'],
                                          'expected_output':'done','dependencies':[]}])
    def response(messages, **kwargs):
        execution_inputs.append(messages)
        value = next(replies)
        return value if isinstance(value, ChatMessage) else ChatMessage(role='assistant', content=value)
    llm = PlannerLLM(response_generator=response)
    window.core.idx.llm.get_agent.return_value = llm
    async def read_file():
        return 'planner-file-value-9001'
    kwargs = {'context':context, 'model':SimpleNamespace(id='mock'), 'llm':llm,
              'tools':[FunctionTool.from_defaults(async_fn=read_file)], 'verbose':False}
    execute(provider.get_agent(window, kwargs), 'First planner task')
    execute(provider.get_agent(window, kwargs), 'Second planner task')
    assert 'planner-file-value-9001' in str(execution_inputs[2])
    assert 'First planner task' in planning_inputs[1]['memory_context']
    assert 'Completed first' in planning_inputs[1]['memory_context']


def test_rewinding_or_deleting_context_invalidates_only_its_memories():
    from pygpt_net.core.ctx import Ctx
    window, context = setup()
    core = window.core.agents
    one = core.get_session_memory(CtxMeta(1), 'flow', 'worker', list)
    two = core.get_session_memory(CtxMeta(2), 'flow', 'worker', list)
    ctx = Ctx(window)
    ctx.provider = MagicMock()
    ctx.remove_items_from(1, 10)
    assert core.get_session_memory(CtxMeta(1), 'flow', 'worker', list) is not one
    assert core.get_session_memory(CtxMeta(2), 'flow', 'worker', list) is two
    ctx.remove(2)
    assert core.get_session_memory(CtxMeta(2), 'flow', 'worker', list) is not two
