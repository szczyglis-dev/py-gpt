import asyncio
import json
import httpx
from types import SimpleNamespace
from unittest.mock import AsyncMock
from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText
from openai import AsyncOpenAI
from llama_index.core.llms import ChatMessage
from pygpt_net.provider.llms.openai.responses_agent import AgentOpenAIResponses


def response(phase, text, ident='resp-final'):
    item = ResponseOutputMessage.model_construct(
        id='msg-'+ident, type='message', role='assistant', status='completed',
        phase=phase, content=[ResponseOutputText.model_construct(type='output_text', text=text, annotations=[])])
    return Response.model_construct(id=ident, status='completed', output=[item], usage=None)


def adapter():
    return AgentOpenAIResponses(model='gpt-4o', api_key='test-not-used', built_in_tools=[{'type': 'computer'}])


def test_tool_calls_and_results_serialize_without_message_roles():
    call = {'type': 'function_call', 'call_id': 'call-1',
            'name': 'read_file', 'arguments': '{"path":"test.txt"}'}
    messages = [ChatMessage(role='user', content='Read file'),
                ChatMessage(role='assistant', content='', additional_kwargs={'tool_calls': [call]}),
                ChatMessage(role='tool', content='File contents',
                            additional_kwargs={'tool_call_id': 'call-1'})]
    items = adapter()._serialize_messages(messages, {'store': True})
    assert items == [{'role': 'user', 'content': 'Read file'}, call,
                     {'type': 'function_call_output', 'call_id': 'call-1', 'output': 'File contents'}]


def test_original_output_replays_reasoning_and_calls_once_in_order():
    llm = adapter()
    raw = response('commentary', 'Checking')
    reasoning = {'id': 'rs-1', 'type': 'reasoning', 'summary': [], 'status': None}
    call = {'id': 'fc-1', 'type': 'function_call', 'call_id': 'call-1',
            'name': 'read_file', 'arguments': '{}'}
    raw.output = [reasoning, *raw.output, call]
    parsed = llm._parse_response_output(raw.output[1:2])
    parsed.raw = raw
    parsed.message.additional_kwargs['tool_calls'] = [call]
    parsed = llm._prepare_response(parsed)
    items = llm._serialize_messages([parsed.message, ChatMessage(
        role='tool', content='Contents', additional_kwargs={'tool_call_id': 'call-1'})], {'store': True})
    assert items[:3] == [{'type': 'item_reference', 'id': ident}
                         for ident in ('rs-1', raw.output[1].id, 'fc-1')]
    assert len(items) == 4
    assert items[-1]['type'] == 'function_call_output'


def test_phase_and_original_assistant_items_survive_history_roundtrip():
    llm = adapter()
    parsed = llm._parse_response_output(response('commentary','Checking screen').output)
    parsed.raw = response('commentary','Checking screen')
    parsed = llm._prepare_response(parsed)
    assert parsed.message.additional_kwargs['phase'] == 'commentary'
    items = llm._serialize_messages([ChatMessage(role='user',content='Task'), parsed.message], {'store':True})
    assert all(isinstance(item, dict) for item in items)
    assert items[0] == {'role': 'user', 'content': 'Task'}
    assert items[1] == {'type': 'item_reference', 'id': 'msg-resp-final'}
    assert parsed.message.additional_kwargs['responses_output'][0]['phase'] == 'commentary'
    assert all('phase' not in item for item in items if isinstance(item,dict) and item.get('role')=='user')


def test_commentary_continues_same_provider_response_without_new_user_instruction():
    async def scenario():
        llm = adapter()
        first = response('commentary','Checking screen', 'resp-working')
        parsed = llm._parse_response_output(first.output)
        parsed.raw = first
        parsed = llm._prepare_response(parsed)
        create = AsyncMock(return_value=response('final_answer','Done'))
        llm._aclient = SimpleNamespace(responses=SimpleNamespace(create=create))
        final = await llm._continue_computer_chain(parsed,{})
        kwargs = create.await_args.kwargs
        assert kwargs['previous_response_id']=='resp-working'
        assert kwargs['input']==[]
        assert create.await_count==1
        assert final.message.additional_kwargs['phase']=='final_answer'
        assert '_pygpt_computer_complete' not in final.raw
    asyncio.run(scenario())


def test_stateless_reasoning_has_only_input_fields_and_no_nulls():
    original = {'id': 'rs-1', 'type': 'reasoning', 'summary': [],
                'status': 'completed', 'encrypted_content': 'encrypted', 'extra_output': 'unused'}
    assert adapter()._history_input_item(original, False) == {
        'id': 'rs-1', 'type': 'reasoning', 'summary': [], 'encrypted_content': 'encrypted'}
    assert original['status'] == 'completed'


def test_real_sdk_serializes_history_as_references_without_output_metadata():
    async def scenario():
        llm = adapter()
        history = ChatMessage(role='assistant', content='Checking', additional_kwargs={
            'responses_stored': True,
            'responses_output': [
                {'id': 'rs-1', 'type': 'reasoning', 'summary': [], 'status': None},
                {'id': 'msg-1', 'type': 'message', 'role': 'assistant',
                 'phase': 'commentary', 'status': 'completed', 'content': []},
                {'id': 'fc-1', 'type': 'function_call', 'call_id': 'call-1',
                 'status': 'completed', 'name': 'read_file', 'arguments': '{}'},
                {'id': 'cu-1', 'type': 'computer_call', 'status': 'completed'},
                {'id': 'ws-1', 'type': 'web_search_call', 'status': 'completed'},
            ]})
        sent = []
        def handle(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200, json=response('final_answer', 'Done').model_dump())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False) as client:
            sdk = AsyncOpenAI(api_key='test-not-used', http_client=client, max_retries=0, timeout=3)
            llm._aclient = sdk
            await llm._achat([ChatMessage(role='user', content='Task'), history,
                             ChatMessage(role='tool', content='Contents',
                                         additional_kwargs={'tool_call_id': 'call-1'})])
        assert sent[0]['store'] is True
        assert sent[0]['input'] == [
            {'role': 'user', 'content': 'Task'},
            *[{'type': 'item_reference', 'id': ident}
              for ident in ('rs-1', 'msg-1', 'fc-1', 'cu-1', 'ws-1')],
            {'type': 'function_call_output', 'call_id': 'call-1', 'output': 'Contents'}]
    asyncio.run(scenario())


def test_computer_continuation_history_preserves_intermediate_items_and_screenshot():
    async def scenario():
        llm = adapter()
        first = response('commentary', 'Checking', 'resp-first')
        parsed = llm._parse_response_output(first.output)
        parsed.raw = first
        parsed = llm._prepare_response(parsed)
        create = AsyncMock(return_value=response('final_answer', 'Done'))
        llm._aclient = SimpleNamespace(responses=SimpleNamespace(create=create))
        screenshot = {'type': 'computer_call_output', 'call_id': 'cu-1',
                      'output': {'type': 'computer_screenshot', 'image_url': 'data:image/png;base64,AAAA'}}
        from unittest.mock import patch
        with patch.object(AgentOpenAIResponses, '_computer_calls', side_effect=[[{'id': 'cu-1'}], []]), \
             patch.object(AgentOpenAIResponses, '_execute_computer_call', new=AsyncMock(return_value=screenshot)):
            final = await llm._continue_computer_chain(parsed, {})
        items = llm._serialize_messages([final.message], {'store': True})
        assert items == [{'type': 'item_reference', 'id': 'msg-resp-first'}, screenshot,
                         {'type': 'item_reference', 'id': 'msg-resp-final'}]
    asyncio.run(scenario())


def test_final_answer_does_not_trigger_additional_provider_request():
    async def scenario():
        llm=adapter()
        raw=response('final_answer','Done')
        parsed=llm._parse_response_output(raw.output);parsed.raw=raw
        parsed=llm._prepare_response(parsed)
        create=AsyncMock()
        llm._aclient=SimpleNamespace(responses=SimpleNamespace(create=create))
        assert await llm._continue_computer_chain(parsed,{}) is parsed
        create.assert_not_awaited()
    asyncio.run(scenario())


def test_stream_preserves_terminal_phase_without_replaying_text_delta():
    async def scenario():
        llm=adapter()
        raw=response('final_answer','Done')
        async def events():
            yield SimpleNamespace(type='response.output_text.delta',delta='Done')
            yield SimpleNamespace(type='response.completed',response=raw)
        create=AsyncMock(return_value=events())
        llm._aclient=SimpleNamespace(responses=SimpleNamespace(create=create))
        stream=await llm._astream_chat([ChatMessage(role='user',content='Task')])
        output=[item async for item in stream]
        assert create.await_args.kwargs['input'] == [{'role': 'user', 'content': 'Task'}]
        assert ''.join(item.delta or '' for item in output)=='Done'
        assert output[-1].message.additional_kwargs['phase']=='final_answer'
        assert output[-1].raw['id']=='resp-final'
    asyncio.run(scenario())


def test_nonstream_request_contains_message_objects_for_system_and_user():
    async def scenario():
        llm = adapter()
        create = AsyncMock(return_value=response('final_answer', 'Done'))
        llm._aclient = SimpleNamespace(responses=SimpleNamespace(create=create))
        await llm._achat([ChatMessage(role='system', content='Instructions'),
                          ChatMessage(role='user', content='Task')])
        items = create.await_args.kwargs['input']
        assert all(isinstance(item, dict) for item in items)
        assert len(items) == 2
        assert items[1] == {'role': 'user', 'content': 'Task'}
    asyncio.run(scenario())
