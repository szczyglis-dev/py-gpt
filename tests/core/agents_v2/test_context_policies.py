"""RAG guidance and model callbacks use the selected actor and runtime policy."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.agents_v2.context import RuntimeContext


def test_rag_guidance_and_invalid_index_errors():
    runtime = MagicMock()
    runtime.index_id = None
    inputs = RuntimeContext(runtime)
    assert not inputs.has_index() and inputs.rag_prompt() == ''
    runtime.index_id = 'docs'
    runtime.rag_context_text = 'evidence'
    runtime.window.core.idx.is_valid.return_value = True
    assert inputs.has_index()
    assert 'docs' in inputs.rag_prompt() and 'evidence' in inputs.rag_prompt()
    runtime.window.core.idx.is_valid.side_effect = ValueError('bad index')
    assert not inputs.has_index()
    runtime.window.core.debug.log.assert_called_once()


def test_llm_binding_rolling_context_and_memory_bounds():
    runtime = MagicMock()
    runtime.allow_remote_tools = True
    runtime.model = SimpleNamespace(ctx=10000)
    runtime.window.core.config.get.return_value = 3000
    inputs = RuntimeContext(runtime)
    llm = inputs.llm(stream=True, actor_id='w', allow_remote_tools=False)
    runtime.window.core.idx.llm.get_agent.assert_called_once_with(model=runtime.model, stream=True, allow_remote_tools=False)
    llm.bind_agents_v2_runtime.assert_called_once_with(runtime, actor_id='w')
    llm.bind_agents_v2_actor.assert_called_once_with('w')
    assert inputs.actor_llms['w'] is llm
    assert inputs.memory_limit() == 3000
    runtime.window.core.config.get.return_value = 1
    assert inputs.memory_limit() == 2048
    runtime.model.ctx = 0
    runtime.window.core.config.get.return_value = 0
    assert inputs.memory_limit() == 40000
    llm.bind_agents_v2_runtime.reset_mock()
    llm.bind_agents_v2_runtime.side_effect = [TypeError('old adapter'), None]
    assert inputs.llm(actor_id='old') is llm
    assert llm.bind_agents_v2_runtime.call_args.args == (runtime,)


def test_both_function_agents_promote_tool_images_to_user_messages():
    import asyncio
    from unittest.mock import AsyncMock
    from llama_index.core.base.llms.types import ImageBlock, TextBlock
    from pygpt_net.core.agents_v2.context import MainFunctionAgent, RuntimeImageFunctionAgent
    for cls in (MainFunctionAgent, RuntimeImageFunctionAgent):
        ctx = SimpleNamespace(store=SimpleNamespace(get=AsyncMock(return_value=[]), set=AsyncMock()))
        image = ImageBlock(image=b'image')
        result = SimpleNamespace(tool_id='call', tool_name='capture', return_direct=False,
                                 tool_output=SimpleNamespace(blocks=[TextBlock(text='screen'), image], content='screen'))
        agent = SimpleNamespace(scratchpad_key='scratchpad')
        asyncio.run(cls.handle_tool_call_results(agent, ctx, [result], None))
        messages = ctx.store.set.call_args.args[1]
        assert [m.role.value for m in messages] == ['tool', 'user']
        assert messages[0].additional_kwargs['tool_call_id'] == 'call'
        assert not any(isinstance(b, ImageBlock) for b in messages[0].blocks)
        assert any(isinstance(b, ImageBlock) for b in messages[1].blocks)
