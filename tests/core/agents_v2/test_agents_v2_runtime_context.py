#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from llama_index.core.base.llms.types import ImageBlock, MessageRole, TextBlock

import pygpt_net.core.agents_v2.runtime as runtime_module
from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime


def bare_runtime():
    runtime = AgentsV2Runtime.__new__(AgentsV2Runtime)
    runtime.window = MagicMock()
    runtime.context = SimpleNamespace(ctx=None, attachments={})
    runtime.model = None
    runtime.index_id = None
    runtime.rag_context_text = ""
    runtime.verbose = MagicMock()
    runtime.verbose_log = MagicMock()
    runtime.verbose_text = MagicMock()
    return runtime


def test_agents_v2_runtime_input_images_requires_image_capable_model_and_unique_existing_files(monkeypatch):
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_image_input=lambda: True)
    runtime.context.attachments = {
        "a": SimpleNamespace(path="/tmp/a.png"),
        "dup": SimpleNamespace(path="/tmp/a.png"),
        "text": SimpleNamespace(path="/tmp/a.txt"),
        "missing": SimpleNamespace(path="/tmp/missing.png"),
    }
    monkeypatch.setattr(runtime_module.os.path, "isfile", lambda path: path != "/tmp/missing.png")
    monkeypatch.setattr(runtime_module, "is_image", lambda path: path.endswith(".png"))

    assert runtime._input_image_paths() == ["/tmp/a.png"]

    runtime.model = SimpleNamespace(is_image_input=lambda: False)
    assert runtime._input_image_paths() == []


def test_agents_v2_runtime_persist_input_images_updates_main_ctx_once():
    runtime = bare_runtime()
    main = SimpleNamespace(images=["existing"])
    runtime.context.ctx = main
    runtime._input_image_paths = MagicMock(return_value=["/tmp/a.png", "/tmp/b.png"])
    runtime.window.core.filesystem.make_local_list.return_value = ["local:a", "local:b"]

    runtime._persist_input_images()

    assert main.images == ["existing", "local:a", "local:b"]
    runtime.window.core.ctx.update_item.assert_called_once_with(main)


def test_agents_v2_runtime_persist_input_images_does_not_write_when_unchanged():
    runtime = bare_runtime()
    main = SimpleNamespace(images=["local:a"])
    runtime.context.ctx = main
    runtime._input_image_paths = MagicMock(return_value=["/tmp/a.png"])
    runtime.window.core.filesystem.make_local_list.return_value = ["local:a"]

    runtime._persist_input_images()

    runtime.window.core.ctx.update_item.assert_not_called()


def test_agents_v2_runtime_build_user_message_uses_native_image_blocks(tmp_path):
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_image_input=lambda: True)
    image_a = tmp_path / "a.png"
    image_b = tmp_path / "b.jpg"
    image_a.write_bytes(b"")
    image_b.write_bytes(b"")
    runtime._input_image_paths = MagicMock(return_value=[str(image_a), str(image_b)])

    message = runtime.build_user_message("hello")

    assert message.role == MessageRole.USER
    assert isinstance(message.blocks[0], TextBlock)
    assert message.blocks[0].text == "hello"
    assert all(isinstance(block, ImageBlock) for block in message.blocks[1:])
    assert [str(block.path) for block in message.blocks[1:]] == [str(image_a), str(image_b)]


def test_agents_v2_runtime_build_user_message_plain_model_uses_content():
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_image_input=lambda: False)

    message = runtime.build_user_message("hello")

    assert message.role == MessageRole.USER
    assert message.content == "hello"


def test_agents_v2_runtime_shared_context_contains_hidden_input_attachment_manifest_and_images(monkeypatch):
    runtime = bare_runtime()
    runtime.context.ctx = SimpleNamespace(hidden_input="extracted text", images=["local:a"])
    runtime.context.attachments = {
        "1": SimpleNamespace(
            path="/tmp/a.png",
            name="a.png",
            remote="remote-id",
            extra={},
        ),
        "2": SimpleNamespace(
            path="/tmp/doc.txt",
            filename="doc.txt",
            remote=None,
            extra={"native_files": True},
        ),
    }
    monkeypatch.setattr(runtime_module, "is_image", lambda path: path.endswith(".png"))

    text = runtime._build_shared_context()

    assert "extracted text" in text
    assert '"name": "a.png"' in text
    assert '"native": true' in text
    assert '"image": true' in text
    assert "Images associated with this turn: local:a" in text


def test_agents_v2_runtime_system_context_reads_filesystem_runtime_prompt_only():
    runtime = bare_runtime()
    runtime.context.ctx = SimpleNamespace(extra={
        "agents_v2_filesystem_context": "stale persisted value must be ignored",
        "other": "ignore",
    })
    plugin = MagicMock()
    plugin.get_option_value.return_value = True
    plugin.build_runtime_filesystem_context.return_value = " filesystem instructions "
    runtime.window.controller.plugins.is_enabled.return_value = True
    runtime.window.core.plugins.get.return_value = plugin
    runtime.window.core.command.is_cmd.return_value = True

    assert runtime._build_runtime_system_context() == "filesystem instructions"
    runtime.window.core.plugins.get.assert_called_once_with("cmd_files")
    plugin.build_runtime_filesystem_context.assert_called_once_with()


def test_agents_v2_runtime_prefetch_rag_context_uses_selected_index():
    runtime = bare_runtime()
    runtime.index_id = "idx-7"
    runtime.model = "model"
    runtime.has_rag_index = MagicMock(return_value=True)
    runtime.window.core.config.get.side_effect = lambda key, default=None: default
    runtime.window.core.idx.chat.query_retrieval.return_value = "  retrieved context  "

    result = runtime.prefetch_rag_context(" question ")

    assert result == "retrieved context"
    runtime.window.core.idx.chat.query_retrieval.assert_called_once_with(
        query="question",
        idx="idx-7",
        model="model",
    )


def test_agents_v2_runtime_prefetch_rag_context_respects_auto_retrieve_setting():
    runtime = bare_runtime()
    runtime.index_id = "idx-7"
    runtime.has_rag_index = MagicMock(return_value=True)
    runtime.window.core.config.get.return_value = False

    assert runtime.prefetch_rag_context("question") == ""
    runtime.window.core.idx.chat.query_retrieval.assert_not_called()



def test_agents_v2_runtime_init_reads_tool_chain_and_preset_capability_flags(monkeypatch):
    actor_ctx = MagicMock()
    monkeypatch.setattr(runtime_module, "AgentsV2VerboseLogger", lambda window, run_id: MagicMock())
    monkeypatch.setattr(runtime_module, "WorkerToolFactory", lambda runtime: SimpleNamespace(runtime=runtime))
    monkeypatch.setattr(AgentsV2Runtime, "_persist_input_images", lambda self: None)
    monkeypatch.setattr(AgentsV2Runtime, "_build_shared_context", lambda self: "shared")
    monkeypatch.setattr(AgentsV2Runtime, "_build_runtime_system_context", lambda self: "runtime")
    monkeypatch.setattr(AgentsV2Runtime, "_seed_artifact_seen", lambda self: None)
    monkeypatch.setattr(AgentsV2Runtime, "_make_tool_ctx", lambda self, actor_id: actor_ctx)

    window = MagicMock()
    values = {"agent.v2.show_tool_chain": True}
    window.core.config.get.side_effect = lambda key, default=None: values.get(key, default)
    preset = SimpleNamespace(
        agent_v2_allow_local_tools=False,
        agent_v2_allow_remote_tools=True,
        idx="_",
    )
    context = SimpleNamespace(
        model="model",
        preset=preset,
        idx="fallback-index",
        ctx=SimpleNamespace(input="input"),
        prompt="prompt",
    )

    runtime = AgentsV2Runtime(window, context, {}, SimpleNamespace(), MagicMock())

    assert runtime.return_tool_calls_to_main_ctx is True
    assert runtime.allow_local_tools is False
    assert runtime.allow_remote_tools is True
    assert runtime.index_id is None
    assert runtime.shared_context_text == "shared"
    assert runtime.runtime_system_context == "runtime"
    actor_ctx.set_input.assert_called_once_with("input", "orchestrator")
    actor_ctx.set_output.assert_called_once_with("", "Orchestrator")


def test_agents_v2_runtime_build_agent_prefers_function_calling_and_disables_parallel_for_ollama(monkeypatch):
    captured = {}

    class FakeFunctionAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class FakeReactAgent:
        def __init__(self, **kwargs):
            raise AssertionError("ReActAgent should not be used")

    monkeypatch.setattr(runtime_module, "FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr(runtime_module, "ReActAgent", FakeReactAgent)
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_ollama=lambda: True)
    runtime.verbose = MagicMock()
    llm = SimpleNamespace(metadata=SimpleNamespace(is_function_calling_model=True))

    agent = runtime.build_agent("Worker", "desc", llm, "system", ["tool"])

    assert isinstance(agent, FakeFunctionAgent)
    assert captured["allow_parallel_tool_calls"] is False
    assert captured["tools"] == ["tool"]


def test_agents_v2_runtime_build_agent_uses_react_for_non_function_calling_model(monkeypatch):
    captured = {}

    class FakeFunctionAgent:
        def __init__(self, **kwargs):
            raise AssertionError("FunctionAgent should not be used")

    class FakeReactAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(runtime_module, "FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr(runtime_module, "ReActAgent", FakeReactAgent)
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_ollama=lambda: False)
    runtime.verbose = MagicMock()
    llm = SimpleNamespace(metadata=SimpleNamespace(is_function_calling_model=False))

    agent = runtime.build_agent("Worker", "desc", llm, "system", [])

    assert isinstance(agent, FakeReactAgent)
    assert "allow_parallel_tool_calls" not in captured


def test_agents_v2_runtime_collect_artifacts_merges_only_new_durable_values():
    runtime = bare_runtime()
    main = SimpleNamespace(files=["existing"], images=[], urls=[], attachments=[])
    runtime.context.ctx = main
    runtime._artifact_seen = {
        "files": {runtime_module.json.dumps("existing")},
        "images": set(),
        "urls": set(),
        "attachments": set(),
    }
    source = SimpleNamespace(
        files=["existing", "new.txt"],
        images=["img.png"],
        urls=["https://example.com"],
        attachments=[],
        results={"must": "not copy"},
    )
    worker = SimpleNamespace(
        id="w01",
        artifacts={"files": [], "images": [], "urls": [], "attachments": []},
    )

    runtime.collect_artifacts(source, worker)

    assert main.files == ["existing", "new.txt"]
    assert main.images == ["img.png"]
    assert main.urls == ["https://example.com"]
    assert not hasattr(main, "results")
    assert worker.artifacts["files"] == ["new.txt"]
    runtime.window.core.ctx.update_item.assert_called_once_with(main)


def test_agents_v2_runtime_collect_llm_artifacts_deduplicates_provider_urls():
    runtime = bare_runtime()
    runtime._artifact_seen = {"files": set(), "images": set(), "urls": set(), "attachments": set()}
    main = SimpleNamespace(files=[], images=[], urls=[], attachments=[])
    tool_ctx = SimpleNamespace(files=[], images=[], urls=["https://old"], attachments=[])
    runtime.context.ctx = main
    runtime.orchestrator_actor = SimpleNamespace(id="orchestrator", tool_ctx=tool_ctx)
    llm = SimpleNamespace(pop_pygpt_urls=lambda: ["https://old", "https://new", "https://new"])

    runtime.collect_llm_artifacts(llm)

    assert tool_ctx.urls == ["https://old", "https://new"]
    assert main.urls == ["https://old", "https://new"]
