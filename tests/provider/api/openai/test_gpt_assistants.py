#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import json
import pytest
from unittest.mock import MagicMock, patch
from pygpt_net.provider.api.openai.assistants import Assistants

@pytest.fixture
def fake_client():
    return MagicMock()

@pytest.fixture
def fake_window(fake_client):
    window = MagicMock()
    window.core.api.openai.get_client.return_value = fake_client
    return window

@pytest.fixture
def assistants_obj(fake_window):
    return Assistants(window=fake_window)

def test_get_client(assistants_obj, fake_window):
    client = MagicMock()
    fake_window.core.api.openai.get_client.return_value = client
    assert assistants_obj.get_client() is client

def test_log_with_callback(assistants_obj):
    callback = MagicMock()
    assistants_obj.log("test message", callback)
    callback.assert_called_once_with("test message")

def test_log_without_callback(assistants_obj, capsys):
    assistants_obj.log("test print")
    captured = capsys.readouterr().out.strip()
    assert captured == "test print"

def test_create(assistants_obj, fake_window):
    assistant = MagicMock()
    assistant.instructions = "inst"
    assistant.description = "desc"
    assistant.name = "name"
    assistant.model = "model"
    assistant.has_tool.side_effect = lambda x: False
    assistant.has_functions.return_value = False
    fake_result = MagicMock()
    fake_result.id = "assistant_id"
    fake_window.core.api.openai.get_client.return_value.beta.assistants.create.return_value = fake_result
    result = assistants_obj.create(assistant)
    fake_window.core.api.openai.get_client.return_value.beta.assistants.create.assert_called_once_with(
        instructions="inst",
        description="desc",
        name="name",
        tools=[],
        model="model",
        tool_resources={}
    )
    assert result.id == "assistant_id"

def test_update(assistants_obj, fake_window):
    assistant = MagicMock()
    assistant.id = "old_id"
    assistant.instructions = "inst"
    assistant.description = "desc"
    assistant.name = "name"
    assistant.model = "model"
    assistant.has_tool.side_effect = lambda x: False
    assistant.has_functions.return_value = False
    fake_result = MagicMock()
    fake_result.id = "updated_id"
    fake_window.core.api.openai.get_client.return_value.beta.assistants.update.return_value = fake_result
    result = assistants_obj.update(assistant)
    fake_window.core.api.openai.get_client.return_value.beta.assistants.update.assert_called_once_with(
        "old_id",
        instructions="inst",
        description="desc",
        name="name",
        tools=[],
        model="model",
        tool_resources={}
    )
    assert result.id == "updated_id"

def test_delete(assistants_obj, fake_window):
    fake_response = MagicMock()
    fake_response.id = "deleted_id"
    fake_window.core.api.openai.get_client.return_value.beta.assistants.delete.return_value = fake_response
    result = assistants_obj.delete("some_id")
    fake_window.core.api.openai.get_client.return_value.beta.assistants.delete.assert_called_once_with("some_id")
    assert result == "deleted_id"

def test_thread_create(assistants_obj, fake_window):
    fake_thread = MagicMock()
    fake_thread.id = "thread_id"
    fake_window.core.api.openai.get_client.return_value.beta.threads.create.return_value = fake_thread
    result = assistants_obj.thread_create()
    fake_window.core.api.openai.get_client.return_value.beta.threads.create.assert_called_once()
    assert result == "thread_id"

def test_thread_delete(assistants_obj, fake_window):
    fake_response = MagicMock()
    fake_response.id = "thread_deleted_id"
    fake_window.core.api.openai.get_client.return_value.beta.threads.delete.return_value = fake_response
    result = assistants_obj.thread_delete("thread1")
    fake_window.core.api.openai.get_client.return_value.beta.threads.delete.assert_called_once_with("thread1")
    assert result == "thread_deleted_id"

def test_msg_list(assistants_obj, fake_window):
    fake_list = MagicMock()
    fake_list.data = ["msg1", "msg2"]
    fake_window.core.api.openai.get_client.return_value.beta.threads.messages.list.return_value = fake_list
    result = assistants_obj.msg_list("thread1")
    fake_window.core.api.openai.get_client.return_value.beta.threads.messages.list.assert_called_once_with("thread1")
    assert result == ["msg1", "msg2"]

def test_msg_send_without_files(assistants_obj, fake_window):
    fake_message = MagicMock()
    fake_window.core.api.openai.get_client.return_value.beta.threads.messages.create.return_value = fake_message
    result = assistants_obj.msg_send("thread1", "hello", [])
    fake_window.core.api.openai.get_client.return_value.beta.threads.messages.create.assert_called_once_with(
        "thread1",
        role="user",
        content="hello"
    )
    assert result is fake_message

def test_msg_send_with_files(assistants_obj, fake_window):
    fake_message = MagicMock()
    fake_window.core.api.openai.get_client.return_value.beta.threads.messages.create.return_value = fake_message
    result = assistants_obj.msg_send("thread1", "hello", ["file1", "file2"])
    expected_attachments = [
        {"file_id": "file1", "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]},
        {"file_id": "file2", "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]},
    ]
    fake_window.core.api.openai.get_client.return_value.beta.threads.messages.create.assert_called_once_with(
        "thread1",
        role="user",
        content="hello",
        attachments=expected_attachments
    )
    assert result is fake_message

def test_get_tools_no_tools(assistants_obj):
    assistant = MagicMock()
    assistant.has_tool.side_effect = lambda x: False
    assistant.has_functions.return_value = False
    result = assistants_obj.get_tools(assistant)
    assert result == []

def test_get_tools_with_tools(assistants_obj):
    assistant = MagicMock()
    assistant.has_tool.side_effect = lambda x: x in ["code_interpreter", "file_search"]
    assistant.has_functions.return_value = True
    assistant.get_functions.return_value = [
        {"name": "func1", "params": '{"param": "value"}', "desc": "desc"}
    ]
    result = assistants_obj.get_tools(assistant)
    assert {"type": "code_interpreter"} in result
    assert {"type": "file_search"} in result
    function_tool = {"type": "function", "function": {"name": "func1", "parameters": {"param": "value"}, "description": "desc"}}
    assert function_tool in result

def test_get_tools_with_empty_function_name(assistants_obj):
    assistant = MagicMock()
    assistant.has_tool.side_effect = lambda x: False
    assistant.has_functions.return_value = True
    assistant.get_functions.return_value = [
        {"name": "", "params": '{"param": "value"}', "desc": "desc"}
    ]
    result = assistants_obj.get_tools(assistant)
    assert result == []

def test_get_tool_resources_positive(assistants_obj):
    assistant = MagicMock()
    assistant.has_tool.side_effect = lambda x: x == "file_search"
    assistant.vector_store = "store1"
    result = assistants_obj.get_tool_resources(assistant)
    assert result == {"file_search": {"vector_store_ids": ["store1"]}}

def test_get_tool_resources_negative(assistants_obj):
    assistant = MagicMock()
    assistant.has_tool.side_effect = lambda x: False
    assistant.vector_store = "store1"
    result = assistants_obj.get_tool_resources(assistant)
    assert result == {}

def test_run_create(assistants_obj, fake_window):
    fake_run = MagicMock()
    fake_run.id = "run_id"
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.create.return_value = fake_run
    result = assistants_obj.run_create("thread1", "assistant1", model="modelX", instructions="inst")
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.create.assert_called_once_with(
        thread_id="thread1", assistant_id="assistant1", instructions="inst", model="modelX"
    )
    assert result is fake_run

def test_run_create_without_instructions(assistants_obj, fake_window):
    fake_run = MagicMock()
    fake_run.id = "run_id"
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.create.return_value = fake_run
    result = assistants_obj.run_create("thread1", "assistant1", model="modelX")
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.create.assert_called_once_with(
        thread_id="thread1", assistant_id="assistant1", model="modelX"
    )
    assert result is fake_run

def test_run_create_stream(assistants_obj, fake_window):
    fake_run_final = MagicMock()
    fake_stream = MagicMock()
    fake_stream.get_final_run.return_value = fake_run_final
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_stream
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.stream.return_value = fake_cm
    signals = MagicMock()
    ctx = MagicMock()
    result = assistants_obj.run_create_stream(signals, ctx, "thread1", "assistant1", model="modelX", instructions="inst")
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.stream.assert_called_once()
    assert result is fake_run_final

def test_run_status(assistants_obj, fake_window):
    fake_run = MagicMock()
    fake_run.usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    fake_run.status = "completed"
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.retrieve.return_value = fake_run
    ctx = MagicMock()
    ctx.thread = "thread1"
    ctx.run_id = "run1"
    status = assistants_obj.run_status(ctx)
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.retrieve.assert_called_once_with(
        thread_id="thread1", run_id="run1"
    )
    assert ctx.input_tokens == 10
    assert ctx.output_tokens == 20
    assert ctx.total_tokens == 30
    assert status == "completed"

def test_run_get(assistants_obj, fake_window):
    fake_run = MagicMock()
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.retrieve.return_value = fake_run
    ctx = MagicMock()
    ctx.thread = "thread1"
    ctx.run_id = "run1"
    result = assistants_obj.run_get(ctx)
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.retrieve.assert_called_once_with(
        thread_id="thread1", run_id="run1"
    )
    assert result is fake_run

def test_run_stop(assistants_obj, fake_window):
    fake_run = MagicMock()
    fake_run.usage = {"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20}
    fake_run.status = "stopped"
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.cancel.return_value = fake_run
    ctx = MagicMock()
    ctx.thread = "thread1"
    ctx.run_id = "run1"
    status = assistants_obj.run_stop(ctx)
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.cancel.assert_called_once_with(
        thread_id="thread1", run_id="run1"
    )
    assert ctx.input_tokens == 5
    assert ctx.output_tokens == 15
    assert ctx.total_tokens == 20
    assert status == "stopped"

def test_run_submit_tool(assistants_obj, fake_window):
    fake_response = MagicMock()
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.submit_tool_outputs.return_value = fake_response
    ctx = MagicMock()
    ctx.thread = "thread1"
    ctx.run_id = "run1"
    outputs = [{"output": {"key": "value"}}, {"output": "string_output"}]
    result = assistants_obj.run_submit_tool(ctx, outputs)
    expected_outputs = [{"output": json.dumps({"key": "value"})}, {"output": "string_output"}]
    fake_window.core.api.openai.get_client.return_value.beta.threads.runs.submit_tool_outputs.assert_called_once_with(
        thread_id="thread1",
        run_id="run1",
        tool_outputs=expected_outputs
    )
    assert result is fake_response

def test_import_all(assistants_obj, fake_window):
    remote1 = MagicMock()
    remote1.id = "a1"
    remote1.name = "Assistant 1"
    remote1.description = "Desc 1"
    remote1.instructions = "Inst 1"
    remote1.model = "Model 1"
    remote1.metadata = {"v": 1}
    ts = MagicMock()
    ts.vector_store_ids = ["vstore1"]
    tr = MagicMock()
    tr.file_search = ts
    remote1.tool_resources = tr
    func_obj = MagicMock()
    func_obj.name = "func1"
    func_obj.parameters = {"p": "v"}
    func_obj.description = "Func desc"
    tool1 = MagicMock()
    tool1.type = "function"
    tool1.function = func_obj
    remote1.tools = [tool1]
    remote2 = MagicMock()
    remote2.id = "a2"
    remote2.name = "Assistant 2"
    remote2.description = "Desc 2"
    remote2.instructions = "Inst 2"
    remote2.model = "Model 2"
    remote2.metadata = {"v": 2}
    tr2 = MagicMock()
    tr2.file_search = None
    remote2.tool_resources = tr2
    remote2.tools = []
    response1 = MagicMock()
    response1.data = [remote1]
    response1.has_more = True
    response1.last_id = "a1"
    response2 = MagicMock()
    response2.data = [remote2]
    response2.has_more = False
    response2.last_id = None
    fake_window.core.api.openai.get_client.return_value.beta.assistants.list.side_effect = [response1, response2]
    callback = MagicMock()
    with patch("pygpt_net.provider.api.openai.assistants.AssistantItem", side_effect=lambda: MagicMock()) as FakeAssistantItem:
        items = {}
        result = assistants_obj.import_all(items, order="asc", limit=100, after=None, callback=callback)
    fake_window.core.api.openai.get_client.return_value.beta.assistants.list.assert_any_call(order="asc", limit=100)
    callback.assert_any_call("Imported assistant: a1")
    callback.assert_any_call("Imported assistant: a2")
    assert "a1" in result
    assert "a2" in result
    result["a1"].add_function.assert_called_once_with("func1", json.dumps({"p": "v"}), "Func desc")