"""Regression coverage for the shared legacy LlamaIndex execution timeline."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from llama_index.core.agent.workflow import AgentStream, AgentOutput, ToolCall, ToolCallResult
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolOutput
from llama_index.core.workflow import StopEvent
from workflows.errors import WorkflowCancelledByUser

from pygpt_net.core.agents.runners.llama_session import LlamaSession, result_text
from pygpt_net.core.agents.runners.llama_workflow import LlamaWorkflow
from pygpt_net.core.agents.runners.llama_events import forward_handler
from pygpt_net.core.agents.tools import Tools
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.ctx import Ctx
from pygpt_net.core.events import KernelEvent
from pygpt_net.controller.chat.response import Response
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.provider.agents.llama_index.workflow.events import StepEvent


def stream(text, name="Agent"):
    return AgentStream(delta=text, response=text, current_agent_name=name, tool_calls=[], raw={})


def call(key, name="read", **args):
    return ToolCall(tool_id=key, tool_name=name, tool_kwargs=args)


def result(key, text="", name="read"):
    return ToolCallResult(tool_id=key, tool_name=name, tool_kwargs={},
                          tool_output=ToolOutput(content=text, tool_name=name, raw_input={}, raw_output=text),
                          return_direct=False)


def setup(streaming=True, visible=True):
    window = MagicMock()
    window.controller.kernel.stopped.return_value = False
    window.core.command.is_tool_hidden.return_value = False
    window.core.config.get.side_effect = lambda key, default=None: default
    window.core.ctx = Ctx(window)
    window.core.ctx.provider = MagicMock()
    ctx = CtxItem()
    ctx.id = 42
    ctx.mode = "agent_llama"
    ctx.meta = CtxMeta()
    ctx.input = "question"
    context = BridgeContext(ctx=ctx, mode=ctx.mode, stream=streaming)
    signals = SimpleNamespace(response=MagicMock())
    session = LlamaSession(window, context, {}, signals, visible=visible)
    session.emitter._final_stream_delay = 0
    return window, ctx, signals, session


def events(signals):
    return [c.args[0] for c in signals.response.emit.call_args_list]


def deliver(window, signals):
    """Consume the Qt queue only AFTER the worker finished (worst-case latency)."""
    ui = Response(window)
    for event in events(signals):
        d = event.data
        if event.name == KernelEvent.AGENT_V2_BEGIN:
            ui.agent_v2_begin(d['context'], d['extra'])
        elif event.name == KernelEvent.AGENT_V2_APPEND:
            ui.agent_v2_append(d['context'], d['extra'], d['chunk'], d['begin'], d['part_begin'], d['part_uuid'])
        elif event.name == KernelEvent.AGENT_V2_END:
            ui.agent_v2_end(d['context'], d['extra'], d['final_answer'], d['artifacts'])


def test_delayed_ui_keeps_text_tool_text_order_and_single_final():
    window, ctx, signals, session = setup()

    async def run():
        session.emitter.begin()
        await session.event(stream("Checking."))
        await session.event(call("a", path="a"))
        await session.event(call("b", path="b"))
        await session.event(result("b", "second"))
        await session.event(result("a", "first"))
        await session.event(stream("The answer."))
        await session.finish("The answer.")
    asyncio.run(run())
    deliver(window, signals)
    assert len(ctx.parts) == 2
    assert [p.output for p in ctx.parts] == ["Checking.", "The answer."]
    assert [t.tool_call_id for t in ctx.parts[0].tasks] == ["a", "b"]
    assert [t.tool_output for t in ctx.parts[0].tasks] == ["first", "second"]
    assert ctx.final_output == "The answer."
    assert ctx.input == "question"
    assert window.core.ctx.should_persist_parts(ctx)
    assert len([e for e in events(signals) if e.name == KernelEvent.AGENT_V2_END]) == 1
    window.controller.agent.llama.on_finish.assert_called_once_with(ctx)


@pytest.mark.parametrize("streaming", [True, False])
def test_terminal_only_result_is_visible_and_final(streaming):
    window, ctx, signals, session = setup(streaming)
    asyncio.run(session.finish({"final_answer": "No deltas required."}))
    deliver(window, signals)
    assert ctx.final_output == "No deltas required."
    assert len(ctx.parts) == 1
    assert ctx.parts[0].output == "No deltas required."


def test_empty_steps_do_not_allocate_rows_and_names_follow_real_segments():
    window, ctx, signals, session = setup()
    async def run():
        for _ in range(3):
            await session.event(StepEvent(name="start", meta={"agent_name": "First"}))
        await session.event(stream("One", "First"))
        await session.event(StepEvent(name="next", meta={"agent_name": "Second"}))
        await session.event(stream("Two", "Second"))
        await session.finish("Two")
    asyncio.run(run())
    deliver(window, signals)
    assert [(p.name, p.output) for p in ctx.parts] == [("First", "One"), ("Second", "Two")]


def test_final_aggregate_does_not_repeat_earlier_prose():
    window, ctx, signals, session = setup()
    async def run():
        await session.event(stream("Working"))
        await session.event(call("a"))
        await session.event(result("a"))
        await session.event(stream("Done"))
        await session.finish("Working\n\nDone")
    asyncio.run(run())
    deliver(window, signals)
    assert [p.output for p in ctx.parts] == ["Working", "Done"]
    assert ctx.final_output == "Done"


def test_quick_call_never_streams_or_persists_on_parent():
    window, ctx, signals, session = setup(visible=False)
    async def run():
        await session.event(stream("answer"))
        await session.finish("answer")
    asyncio.run(run())
    assert ctx.output == "answer"
    assert ctx.parts == []
    assert events(signals) == []


def test_plugin_results_wait_for_reply_and_use_private_contexts():
    window, ctx, signals, session = setup()
    tool_contexts = []
    async def run():
        loop = asyncio.get_running_loop()
        def handle(event):
            if event.name != KernelEvent.AGENT_V2_TOOL_EXEC:
                return
            request = event.data['request']
            tool_contexts.append(request['ctx'])
            def complete():
                request['ctx'].files.append('file.txt')
                request['result'] = {'value': request['cmds'][0]['params']['n']}
                request['done'].set()
            loop.call_later(.01, complete)
        signals.response.emit.side_effect = handle
        return await asyncio.gather(session.execute_plugin('read', {'n': 1}),
                                    session.execute_plugin('read', {'n': 2}))
    assert [json.loads(value) for value in asyncio.run(run())] == [{"value": 1}, {"value": 2}]
    assert len({id(c) for c in tool_contexts}) == 2
    assert all(c is not ctx and c.hidden and not c.async_disabled for c in tool_contexts)
    # Reading a file inside a private tool context must not implicitly attach
    # it to the final agent response. Files are exported only through the
    # explicit delivery-files path.
    assert all(c.files == ['file.txt'] for c in tool_contexts)
    assert session.artifacts.values['files'] == []
    assert ctx.files == []


class Handler:
    def __init__(self, values=(), final="done", error=None, wait=False):
        self.values = values
        self.final = final
        self.error = error
        self.wait = wait
        self.cancelled = False
        self.cancel_signal = asyncio.Event()
    async def stream_events(self):
        for value in self.values:
            yield value
        if self.wait:
            await self.cancel_signal.wait()
            raise WorkflowCancelledByUser()
    async def cancel_run(self):
        self.cancelled = True
        self.cancel_signal.set()
    def __await__(self):
        async def get():
            if self.error:
                raise self.error
            return self.final
        return get().__await__()


def test_nested_stop_event_does_not_terminate_parent_stream():
    parent = MagicMock()
    async def run():
        return await forward_handler(Handler([stream("hello"), StopEvent(result="child")]), parent, lambda: False)
    final, text = asyncio.run(run())
    assert (final, text) == ("done", "hello")
    assert all(not isinstance(c.args[0], StopEvent) for c in parent.write_event_to_stream.call_args_list)


def test_stop_cancels_child_while_waiting_without_events():
    async def run():
        child = Handler(wait=True)
        stopped = False
        async def stop():
            nonlocal stopped
            await asyncio.sleep(.01)
            stopped = True
        task = asyncio.create_task(stop())
        with pytest.raises(WorkflowCancelledByUser):
            await asyncio.wait_for(forward_handler(child, MagicMock(), lambda: stopped), .5)
        await task
        assert child.cancelled
    asyncio.run(run())


def test_terminal_errors_are_not_reported_as_success():
    async def run():
        child = Handler([stream("partial")], error=ValueError("failure"))
        with pytest.raises(ValueError, match="failure"):
            await forward_handler(child, MagicMock(), lambda: False)
        assert child.cancelled
    asyncio.run(run())


def test_tool_schema_validation_and_async_dispatch():
    window = MagicMock()
    window.core.command.get_functions.return_value = [
        {'name': 'read', 'desc': 'read', 'params': '{"type":"object","required":["path"],"properties":{"path":{"type":"string"}}}'}]
    calls = []
    async def execute(name, args):
        calls.append((name, args))
        return 'ok'
    tool = Tools(window, executor=execute).get_plugin_functions(CtxItem())[0]
    async def run():
        assert (await tool.acall(arguments={'path': 'a'})).content == 'ok'
        assert 'Missing required' in (await tool.acall()).content
    asyncio.run(run())
    assert calls == [('read', {'path': 'a'})]
    window.controller.plugins.apply_cmds_all.assert_not_called()


def test_native_function_agent_runs_real_tool_loop():
    from llama_index.core.agent.workflow import FunctionAgent
    from llama_index.core.llms.mock import MockFunctionCallingLLM
    from llama_index.core.base.llms.types import ToolCallBlock, TextBlock
    from llama_index.core.memory import ChatMemoryBuffer
    from llama_index.core.tools import FunctionTool
    from llama_index.core.workflow import Context
    window, ctx, signals, session = setup()
    seen = []
    def response(messages, **kwargs):
        seen.append(messages)
        if not any(str(m.role) == 'MessageRole.TOOL' or m.role == 'tool' for m in messages):
            return ChatMessage(role='assistant', blocks=[TextBlock(text='Checking.'),
                ToolCallBlock(tool_call_id='read-1', tool_name='read', tool_kwargs={'path': 'file'})])
        return ChatMessage(role='assistant', content='Verified.')
    async def read(path: str):
        return 'content of ' + path
    async def run():
        agent = FunctionAgent(llm=MockFunctionCallingLLM(response_generator=response),
                              tools=[FunctionTool.from_defaults(async_fn=read)])
        runner = LlamaWorkflow(window)
        runner.is_stopped = lambda: False
        await runner.run_agent(agent, Context(agent), 'question', ChatMemoryBuffer.from_defaults(token_limit=1000),
                               item_ctx=ctx, signals=signals, session=session)
    asyncio.run(run())
    deliver(window, signals)
    assert ctx.final_output == 'Verified.'
    assert ctx.parts[0].tasks[0].tool_output == 'content of file'
    assert len(seen) == 2


def test_openai_workflow_wrapper_passes_prompt_and_memory_to_current_li_api():
    from llama_index.core.llms.mock import MockFunctionCallingLLM
    from llama_index.core.memory import ChatMemoryBuffer
    from pygpt_net.provider.agents.llama_index.workflow.openai import OpenAIWorkflowAgent
    seen = []
    def response(messages, **kwargs):
        seen.extend(messages)
        return ChatMessage(role='assistant', content='wrapper result')
    async def run():
        workflow = OpenAIWorkflowAgent(tools=[], llm=MockFunctionCallingLLM(response_generator=response))
        memory = ChatMemoryBuffer.from_defaults(token_limit=1000, chat_history=[ChatMessage(role='user', content='old')])
        return await asyncio.wait_for(forward_handler(workflow.run('new', memory=memory), MagicMock(), lambda: False), 5)
    final, streamed = asyncio.run(run())
    assert result_text(final) == streamed == 'wrapper result'
    assert any(m.content == 'new' for m in seen)
    assert any(m.content == 'old' for m in seen)




def test_custom_flow_streams_routes_and_keeps_current_input_and_history():
    from llama_index.core.llms.mock import MockFunctionCallingLLM
    from pygpt_net.core.agents.custom.llama_index.runner import DynamicFlowWorkflowLI
    seen = []
    def response(messages, **kwargs):
        seen.append(messages)
        answer = '{"route":"b","content":"handoff text"}' if len(seen) == 1 else 'Final result'
        return ChatMessage(role='assistant', content=answer)
    llm = MockFunctionCallingLLM(response_generator=response)
    schema = [
        {'id':'start', 'type':'start', 'slots':{'output':{'out':['a']}}},
        {'id':'a','type':'agent','slots':{'name':'Router','instruction':'route', 'output':{'out':['b','end']}}},
        {'id':'b','type':'agent','slots':{'name':'Writer','instruction':'write','output':{'out':['end']},
                                       'memory':{'out':['mem']}}},
        {'id':'end','type':'end','slots':{}},
        {'id':'mem','type':'memory','slots':{}},
    ]
    window = MagicMock()
    workflow = DynamicFlowWorkflowLI(
        window=window, logger=None, schema=schema, initial_messages=[ChatMessage(role='user',content='old question'),
        ChatMessage(role='assistant',content='old answer')], preset=None, default_model=None,
        option_get=lambda section,key,default=None: default, router_stream_mode='realtime',
        allow_local_tools_default=True,allow_remote_tools_default=True,max_iterations=5,
        llm=llm,tools=[],stream=True,base_prompt='', verbose=False,
    )
    parent = MagicMock()
    async def run():
        return await forward_handler(workflow.run('new question'), parent, lambda: False)
    final, streamed = asyncio.run(run())
    assert result_text(final) == 'Final result'
    assert streamed == 'handoff textFinal result'
    assert [m.content for m in seen[0] if m.role == 'user'] == ['old question', 'new question']
    assert any(m.content == 'old answer' for m in seen[0])
    assert any(m.content == 'handoff text' for m in seen[1])
    assert workflow.mem.get('mem').items[-1].content == 'Final result'


def test_error_without_stream_terminal_does_not_hang():
    async def run():
        child = Handler(wait=True, error=ValueError('silent error'))
        with pytest.raises(ValueError, match='silent error'):
            await asyncio.wait_for(forward_handler(child, MagicMock(), lambda: False), .5)
        assert child.cancelled
    asyncio.run(run())


def test_interrupted_work_does_not_become_final_answer():
    window, ctx, signals, session = setup()
    async def run():
        await session.event(stream('partial'))
        window.controller.kernel.stopped.return_value = True
        session.abort()
    asyncio.run(run())
    window.controller.kernel.stopped.return_value = True
    deliver(window, signals)
    assert ctx.extra.get('response_final') is not True
    assert ctx.extra.get('response_interrupted') is True
    assert ctx.get_agents_v2_final_output() is None
    assert ctx.parts[0].output == 'partial'


def test_completed_legacy_timeline_is_rendered_with_shared_preferences():
    from pygpt_net.core.render.web.renderer import Renderer
    window, ctx, signals, session = setup(streaming=False)
    async def run():
        await session.append('first')
        session.boundary('Next')
        await session.append('final')
        await session.finish('final')
    asyncio.run(run())
    deliver(window, signals)
    renderer = Renderer(window)
    renderer.helpers.pre_format_text = lambda value, **kwargs: value
    renderer.helpers.post_format_text = lambda value: value
    timeline = renderer.timeline.build_partial_timeline(ctx, include_workflow_statuses=False, include_tool_calls=False)
    assert [item['text'] for item in timeline] == ['first', 'final']
    assert renderer.agents.display_full_agent_workflow_for_ctx(ctx) is True
    # Old legacy rows retain their old layout and storage policy.
    old = CtxItem()
    old.mode = 'agent_llama'
    assert renderer.agents.display_full_agent_workflow_for_ctx(old) is False
    assert window.core.ctx.should_persist_parts(old) is False


def test_initial_runtime_part_is_promoted_to_durable_storage():
    window, ctx, signals, session = setup(streaming=False)
    ctx.extra.pop('agent_timeline')
    initial = window.core.ctx.ensure_part(ctx)
    assert initial.id is None
    window.core.ctx.provider.append_part.reset_mock()
    ctx.extra['agent_timeline'] = True
    asyncio.run(session.append('answer'))
    assert session.part is initial
    window.core.ctx.provider.append_part.assert_called_once_with(initial)


@pytest.mark.parametrize('call_id', ['', 'reused'])
def test_missing_or_reused_child_tool_ids_keep_distinct_results(call_id):
    window, ctx, signals, session = setup(streaming=False)
    async def run():
        await session.event(call(call_id))
        await session.event(result(call_id, 'first'))
        await session.event(call(call_id))
        await session.event(result(call_id, 'second'))
        await session.finish('done')
    asyncio.run(run())
    tasks = [task for part in ctx.parts for task in part.tasks]
    assert len(tasks) == 2
    assert [t.tool_output for t in tasks] == ['first', 'second']
    assert tasks[0].tool_call_id != tasks[1].tool_call_id


def test_planner_progress_does_not_duplicate_final_answer():
    from llama_index.core.llms.mock import MockFunctionCallingLLM
    from pygpt_net.provider.agents.llama_index.workflow.planner import PlannerWorkflow
    from pygpt_net.core.agents.runners.llama_events import consume_handler
    class PlannerLLM(MockFunctionCallingLLM):
        async def astructured_predict(self, output_cls, prompt, **kwargs):
            return output_cls(sub_tasks=[{'name':'work','input':'do work',
                                         'expected_output':'answer','dependencies':[]}])
    window, ctx, signals, session = setup()
    async def run():
        llm = PlannerLLM(response_generator=lambda *a, **kw: ChatMessage(role='assistant',content='Task result'))
        workflow = PlannerWorkflow(tools=[], llm=llm, refine_after_each_subtask=False)
        terminal = await consume_handler(workflow.run('question'), session.event, lambda: False)
        await session.finish(terminal)
    asyncio.run(run())
    deliver(window, signals)
    assert ctx.final_output == 'Task result'
    assert sum((part.output or '').count('Task result') for part in ctx.parts) == 1


def test_supervisor_streams_worker_and_hides_control_json():
    from llama_index.core.agent.workflow import FunctionAgent
    from llama_index.core.llms.mock import MockFunctionCallingLLM
    from llama_index.core.memory import ChatMemoryBuffer
    from pygpt_net.provider.agents.llama_index.workflow.supervisor import SupervisorWorkflow
    from pygpt_net.core.agents.runners.llama_events import consume_handler
    window, ctx, signals, session = setup()
    async def run():
        replies = iter(['{"action":"task","instruction":"Do work"}',
                        '{"action":"final","final_answer":"Verified result"}'])
        supervisor = FunctionAgent(name='Supervisor', llm=MockFunctionCallingLLM(
            response_generator=lambda *a, **kw: ChatMessage(role='assistant',content=next(replies))))
        worker = FunctionAgent(name='Worker', llm=MockFunctionCallingLLM(
            response_generator=lambda *a, **kw: ChatMessage(role='assistant',content='Worker result')))
        workflow = SupervisorWorkflow(supervisor=supervisor, worker=worker,
                                      worker_memory=ChatMemoryBuffer.from_defaults(token_limit=2000),verbose=False)
        terminal = await consume_handler(workflow.run('question', memory=ChatMemoryBuffer.from_defaults(token_limit=2000)),
                                         session.event, lambda: False)
        await session.finish(terminal)
    asyncio.run(run())
    deliver(window, signals)
    assert ctx.final_output == 'Verified result'
    assert [part.name for part in ctx.parts] == ['Supervisor', 'Worker', 'Supervisor']
    assert 'Worker result' in ctx.compose_output()
    assert '"action"' not in ctx.compose_output()


def test_saved_legacy_timeline_restores_final_and_ordered_tool_history():
    window, ctx, signals, session = setup(streaming=False)
    async def run():
        await session.append('Working')
        await session.event(call('read'))
        await session.event(result('read', 'tool result'))
        await session.finish('Final answer')
    asyncio.run(run())
    deliver(window, signals)
    restored = CtxItem()
    restored.from_dict(ctx.to_dict())
    assert restored.mode == 'agent_llama'
    assert restored.final_output == 'Final answer'
    assert [p.output for p in restored.parts] == ['Working', 'Final answer']
    assert restored.parts[0].tasks[0].tool_output == 'tool result'
    assert window.core.ctx.should_persist_parts(restored)


def test_supervisor_prose_is_available_before_json_is_complete():
    from pygpt_net.core.agents.custom.llama_index.router_streamer import RealtimeRouterStreamerLI
    stream = RealtimeRouterStreamerLI(fields=('instruction', 'final_answer', 'question'))
    assert stream.handle_delta('{"action":"final","instruction":"","final_an') == ''
    assert stream.handle_delta('swer":"Hello') == 'Hello'
    assert stream.handle_delta(' world\\n') == ' world\n'
    assert stream.handle_delta('done","reasoning":"control"}') == 'done'
    assert stream.handle_delta(' trailing control') == ''


def test_router_stream_decodes_split_escapes_without_control_json():
    from pygpt_net.core.agents.custom.llama_index.router_streamer import RealtimeRouterStreamerLI
    stream = RealtimeRouterStreamerLI()
    chunks = ['{"route":"next","content":"A', '\\', '"B', '\\u01', '42', '"}']
    assert ''.join(stream.handle_delta(chunk) for chunk in chunks) == 'A"Bł'


def test_legacy_chat_policy_delivers_text_to_renderer_before_workflow_finishes():
    from pygpt_net.controller.chat.text import Text
    from pygpt_net.core.events import RenderEvent

    window, ctx, signals, session = setup(streaming=False)
    # This is the actual chat entry policy, not the streaming=True test shortcut.
    assert Text(window).is_stream('agent_llama') is False
    ui = Response(window)

    def dispatch(event):
        d = event.data
        if event.name == KernelEvent.AGENT_V2_BEGIN:
            ui.agent_v2_begin(d['context'], d['extra'])
        elif event.name == KernelEvent.AGENT_V2_APPEND:
            ui.agent_v2_append(d['context'], d['extra'], d['chunk'],
                               d['begin'], d['part_begin'], d['part_uuid'])

    signals.response.emit.side_effect = dispatch

    async def run():
        session.emitter.begin()
        for name, text in [('Supervisor', 'Read the file.'), ('Worker', 'Here is the translation.')]:
            await session.event(stream(text, name))
            # The normal emitter timer must deliver while the workflow is alive.
            await asyncio.sleep(0.06)
            rendered = [c.args[0] for c in window.dispatch.call_args_list
                        if c.args[0].name == RenderEvent.STREAM_APPEND]
            assert any(event.data['chunk'] == text for event in rendered)
            assert not session.finished
        assert not any(event.name == KernelEvent.AGENT_V2_END for event in events(signals))
        assert session.context.stream is False  # generic chat lifecycle stays disabled

    asyncio.run(run())


@pytest.mark.parametrize("named_tool", [False, True])
def test_worker_tool_before_first_prose_owns_its_partial(named_tool):
    window, ctx, signals, session = setup()

    async def run():
        await session.event(stream("Delegating.", "Supervisor"))
        tool = call("worker-read", path="notes.txt")
        if named_tool:
            tool = tool.model_copy(update={"current_agent_name": "Worker"})
        else:
            await session.event(StepEvent(name="worker", meta={"agent_name": "Worker"}))
        await session.event(tool)
        await session.event(result("worker-read", "notes"))
        await session.event(stream("Checked.", "Worker"))
        await session.finish("Checked.")

    asyncio.run(run())
    deliver(window, signals)
    supervisor = next(p for p in ctx.parts if p.name == "Supervisor")
    worker = next(p for p in ctx.parts if p.tasks)
    assert supervisor.tasks == []
    assert worker.name == "Worker"
    assert worker.tasks[0].tool_output == "notes"
    assert worker.tasks[0].agent_id == "orchestrator"


def test_forwarded_child_tools_keep_display_actor_without_text():
    parent = MagicMock()
    child = Handler(values=[call("x"), result("x", "done")])
    asyncio.run(forward_handler(child, parent, lambda: False, name="Worker"))
    assert [c.args[0].current_agent_name for c in parent.write_event_to_stream.call_args_list] == ["Worker", "Worker"]


def test_tool_status_carries_worker_owner_even_when_ui_is_delayed():
    window, ctx, signals, session = setup()

    async def run():
        await session.event(stream("Delegating.", "Supervisor"))
        await session.event(StepEvent(name="worker", meta={"agent_name": "Worker"}))
        await session.event(call("worker-read"))
        await session.event(result("worker-read", "notes"))
        await session.event(stream("Checked.", "Worker"))
        await session.event(stream("Done.", "Supervisor"))
        await session.finish("Done.")

    asyncio.run(run())
    tool_status = next(e for e in events(signals)
                      if e.name == KernelEvent.AGENT_V2_STATUS and e.data.get("owner"))
    owner = tool_status.data["owner"]
    tool_part = next(p for p in ctx.parts if p.tasks)
    assert ctx.get_active_part().name == "Supervisor"
    assert owner == {"part_uuid": tool_part.uuid, "agent_name": "Worker", "placement": "before"}
    Response(window).agent_v2_status(session.context, {}, tool_status.data["status"], owner=owner)
    assert window.dispatch.call_args.args[0].data["owner"] == owner


@pytest.mark.parametrize('outcome', ['success', 'stopped', 'cancelled', 'error'])
def test_workflow_entrypoint_terminal_lifecycle(outcome):
    from unittest.mock import AsyncMock, patch
    window, ctx, signals, session = setup()
    workflow = LlamaWorkflow(window)
    workflow.set_busy = MagicMock()
    workflow.set_idle = MagicMock()
    workflow.set_error = MagicMock()
    session.emitter.begin = MagicMock()
    session.abort = MagicMock()
    monitor = MagicMock()
    workflow.is_stopped = MagicMock(return_value=outcome == 'stopped')
    async def run_agent(*args, **kwargs):
        if outcome == 'error':
            raise RuntimeError('provider failed')
        if outcome == 'cancelled':
            raise asyncio.CancelledError()
        session.final_answer = 'done'
        return ctx
    workflow.run_agent = AsyncMock(side_effect=run_agent)
    with patch('pygpt_net.core.agents.runners.llama_workflow.Context'):
        result = asyncio.run(workflow.run(MagicMock(), ctx, 'task', signals, session=session, workflow_bridge=monitor))
    assert result is (outcome != 'error')
    if outcome == 'success':
        monitor.finish.assert_called_once_with('done')
        session.abort.assert_not_called()
        workflow.set_idle.assert_not_called()
    else:
        session.abort.assert_called_once()
        workflow.set_idle.assert_called_once_with(signals)
        if outcome == 'error':
            assert ctx.extra['error'] == 'provider failed'
            monitor.fail.assert_called_once()
        else:
            monitor.stop.assert_called_once()


def test_hidden_workflow_entrypoint_and_session_helpers():
    from unittest.mock import AsyncMock, patch
    window, ctx, signals, session = setup()
    workflow = LlamaWorkflow(window)
    workflow.is_stopped = MagicMock(return_value=False)
    workflow.run_agent = AsyncMock(return_value=ctx)
    with patch('pygpt_net.core.agents.runners.llama_workflow.Context'):
        assert asyncio.run(workflow.run_once(MagicMock(), ctx, 'task', signals, session=session)) is ctx
    assert workflow.run_agent.call_args.kwargs['flush'] is False
    hidden = workflow._session(ctx, signals, visible=False)
    assert hidden.visible is False
    assert hidden.build_worker_message('request')
    llm = MagicMock()
    hidden.bind_llm(llm)
    assert hidden.llm is llm
    assert workflow._tool_output_to_text(SimpleNamespace(content=' output ')) == 'output'
    assert workflow._tool_output_to_text(None) == ''


def test_session_component_tool_history_and_visibility_contracts():
    from pygpt_net.core.agents.runners.session_components import SessionStatus, SessionToolHistory
    from unittest.mock import patch
    window, ctx, signals, session = setup()
    status = SessionStatus(session)
    assert status.show_tool('read') is True
    window.core.command.is_tool_hidden.return_value = True
    assert status.show_tool('read') is False
    history = SessionToolHistory(session)
    assert history.register_plugin('read') is None
    with patch.object(history, 'persist_call', return_value='call') as call, \
         patch.object(history, 'persist_result') as result:
        assert history.record_local_call('read', {'path': 'x'}) == 'call'
        history.record_local_result('call', 'read', 'output')
    call.assert_called_once_with('read', {'path': 'x'}, 'orchestrator')
    result.assert_called_once_with('output', 'orchestrator', 'read', 'call')
