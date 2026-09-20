#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from llama_index.core.base.llms.types import ImageBlock, MessageRole, TextBlock

import pygpt_net.core.agents_v2.context as context_module
import pygpt_net.core.agents_v2.runtime as runtime_module
from pygpt_net.core.agents_v2.artifacts import RuntimeArtifacts
from pygpt_net.core.agents_v2.context import RuntimeContext
from pygpt_net.core.agents_v2.contracts import RuntimeInput, RuntimeOutput
from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime
from pygpt_net.core.agents_v2.prompt_builder import RuntimePromptBuilder
from pygpt_net.core.agents_v2.status import RuntimeStatus
from pygpt_net.core.agents_v2.timeline import RuntimeTimeline
from pygpt_net.core.agents_v2.tool_history import RuntimeToolHistory
from pygpt_net.core.agents_v2.toolset import RuntimeToolset
from pygpt_net.core.agents_v2.workers import WorkerRuntime


def bare_runtime():
    runtime = AgentsV2Runtime.__new__(AgentsV2Runtime)
    runtime.window = MagicMock()
    runtime.context = SimpleNamespace(ctx=None, attachments={})
    runtime.model = None
    runtime.agent_definition = None
    runtime.strategy = SimpleNamespace(main_name="Primary Agent", main_description="Primary agent")
    runtime.index_id = None
    runtime.rag_context_text = ""
    runtime.verbose = MagicMock()
    runtime.verbose_log = MagicMock()
    runtime.verbose_text = MagicMock()
    runtime._actor_llms = {}
    runtime.workers = {}
    runtime._artifact_seen = {
        "files": set(), "images": set(), "urls": set(), "attachments": set()
    }
    runtime._artifact_delivery_seen = set()
    runtime._pending_artifacts = {
        "files": [], "images": [], "urls": [], "attachments": []
    }
    runtime.context_api = RuntimeContext(runtime)
    runtime.artifact_api = RuntimeArtifacts(runtime)
    return runtime



def test_agents_v2_runtime_output_returns_stable_snapshot():
    runtime = AgentsV2Runtime.__new__(AgentsV2Runtime)
    runtime.run_id = "run-1"
    runtime.agent_mode = runtime_module.AgentMode.PRIMARY_AGENT
    runtime.finished = True
    runtime.final_answer = "done"

    output = runtime.output()

    assert isinstance(output, RuntimeOutput)
    assert output.run_id == "run-1"
    assert output.agent_mode is runtime_module.AgentMode.PRIMARY_AGENT
    assert output.finished is True
    assert output.final_answer == "done"


def test_agents_v2_runtime_from_input_forwards_stable_contract(monkeypatch):
    captured = {}

    def fake_init(self, window, context, extra, signals, emitter):
        captured.update({
            "window": window,
            "context": context,
            "extra": extra,
            "signals": signals,
            "emitter": emitter,
        })

    monkeypatch.setattr(AgentsV2Runtime, "__init__", fake_init)
    data = RuntimeInput(
        window="window",
        context="context",
        extra={"x": 1},
        signals="signals",
        emitter="emitter",
    )

    runtime = AgentsV2Runtime.from_input(data)

    assert isinstance(runtime, AgentsV2Runtime)
    assert captured == {
        "window": "window",
        "context": "context",
        "extra": {"x": 1},
        "signals": "signals",
        "emitter": "emitter",
    }

def test_agents_v2_runtime_input_images_requires_image_capable_model_and_unique_existing_files(monkeypatch):
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_image_input=lambda: True)
    runtime.context.attachments = {
        "a": SimpleNamespace(path="/tmp/a.png"),
        "dup": SimpleNamespace(path="/tmp/a.png"),
        "text": SimpleNamespace(path="/tmp/a.txt"),
        "missing": SimpleNamespace(path="/tmp/missing.png"),
    }
    monkeypatch.setattr(context_module.os.path, "isfile", lambda path: path != "/tmp/missing.png")
    monkeypatch.setattr(context_module, "is_image", lambda path: path.endswith(".png"))

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
    monkeypatch.setattr(context_module, "is_image", lambda path: path.endswith(".png"))

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
    monkeypatch.setattr(
        runtime_module, "AgentsV2VerboseLogger",
        lambda window, run_id, agent_mode=None: MagicMock(),
    )
    monkeypatch.setattr(runtime_module, "WorkerToolFactory", lambda runtime: SimpleNamespace(runtime=runtime))
    monkeypatch.setattr(AgentsV2Runtime, "_persist_input_images", lambda self: None)
    monkeypatch.setattr(AgentsV2Runtime, "_build_shared_context", lambda self: "shared")
    monkeypatch.setattr(AgentsV2Runtime, "_build_runtime_system_context", lambda self: "runtime")
    monkeypatch.setattr(AgentsV2Runtime, "_seed_artifact_seen", lambda self: None)
    monkeypatch.setattr(AgentsV2Runtime, "_make_tool_ctx", lambda self, actor_id: actor_ctx)

    window = MagicMock()
    window.core.agents_v2.editor.resolve_selection.return_value = (
        "chat", runtime_module.AgentMode.PRIMARY_AGENT, None
    )
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
    assert runtime.workflow_final_requested is False
    assert runtime.workflow_final_stream_started is False
    assert runtime.workflow_final_hint == ""
    assert isinstance(runtime.timeline, RuntimeTimeline)
    assert isinstance(runtime.tool_history, RuntimeToolHistory)
    assert isinstance(runtime.context_api, RuntimeContext)
    assert isinstance(runtime.status_api, RuntimeStatus)
    assert isinstance(runtime.artifact_api, RuntimeArtifacts)
    assert isinstance(runtime.worker_api, WorkerRuntime)
    assert isinstance(runtime.toolset_api, RuntimeToolset)
    assert isinstance(runtime.prompt_api, RuntimePromptBuilder)
    actor_ctx.set_input.assert_called_once_with("prompt", "orchestrator")
    actor_ctx.set_output.assert_called_once_with("", "Primary Agent")


def test_agents_v2_runtime_build_agent_prefers_function_calling_and_disables_parallel_for_ollama(monkeypatch):
    captured = {}

    class FakeFunctionAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class FakeReactAgent:
        def __init__(self, **kwargs):
            raise AssertionError("ReActAgent should not be used")

    monkeypatch.setattr(context_module, "FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr(context_module, "ReActAgent", FakeReactAgent)
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_ollama=lambda: True)
    runtime.verbose = MagicMock()
    llm = SimpleNamespace(metadata=SimpleNamespace(is_function_calling_model=True))

    agent = runtime.build_agent("Worker", "desc", llm, "system", ["tool"])

    assert isinstance(agent, FakeFunctionAgent)
    assert captured["allow_parallel_tool_calls"] is False
    assert captured["tools"][0] == "tool"
    assert captured["tools"][1].metadata.name == "task_complete"


def test_agents_v2_runtime_build_agent_uses_react_for_non_function_calling_model(monkeypatch):
    captured = {}

    class FakeFunctionAgent:
        def __init__(self, **kwargs):
            raise AssertionError("FunctionAgent should not be used")

    class FakeReactAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(context_module, "FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr(context_module, "ReActAgent", FakeReactAgent)
    runtime = bare_runtime()
    runtime.model = SimpleNamespace(is_ollama=lambda: False)
    runtime.verbose = MagicMock()
    llm = SimpleNamespace(metadata=SimpleNamespace(is_function_calling_model=False))

    agent = runtime.build_agent("Worker", "desc", llm, "system", [])

    assert isinstance(agent, FakeReactAgent)
    assert "allow_parallel_tool_calls" not in captured


def test_agents_v2_runtime_collect_artifacts_stages_non_file_values_for_final_delivery():
    runtime = bare_runtime()
    main = SimpleNamespace(files=["existing"], images=[], urls=[], attachments=[])
    runtime.context.ctx = main
    runtime._artifact_seen = {
        "files": {json.dumps("existing")},
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

    assert main.files == ["existing"]
    assert main.images == []
    assert main.urls == []
    assert not hasattr(main, "results")
    assert worker.artifacts["files"] == []
    assert worker.artifacts["images"] == ["img.png"]
    assert worker.artifacts["urls"] == ["https://example.com"]
    assert runtime.pending_artifacts() == {
        "images": ["img.png"],
        "urls": ["https://example.com"],
    }
    runtime.window.core.ctx.update_item.assert_not_called()


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
    assert main.urls == []
    assert runtime.pending_artifacts() == {
        "urls": ["https://old", "https://new"],
    }


def test_agents_v2_project_rules_loads_agents_md_from_active_context_workdir(tmp_path):
    rules_file = tmp_path / "AGENTS.md"
    rules_file.write_text("  project rule  ", encoding="utf-8")
    runtime = bare_runtime()
    runtime.context.ctx = SimpleNamespace(id=77)
    runtime.window.core.filesystem.get_data_dir.return_value = str(tmp_path)
    runtime.window.core.security.is_in_workdir.return_value = True

    rules = runtime.context_api.load_project_rules()

    assert rules == "project rule"
    runtime.window.core.filesystem.get_data_dir.assert_called_once_with(ctx=runtime.context.ctx, create=False)
    runtime.window.core.security.is_in_workdir.assert_called_once_with(str(rules_file), ctx=runtime.context.ctx)
    runtime.verbose_text.assert_called_once_with("PROJECT RULES", "project rule")


def test_agents_v2_project_rules_rejects_agents_md_outside_active_workdir(tmp_path):
    rules_file = tmp_path / "AGENTS.md"
    rules_file.write_text("do not load", encoding="utf-8")
    runtime = bare_runtime()
    runtime.context.ctx = SimpleNamespace(id=11)
    runtime.window.core.filesystem.get_data_dir.return_value = str(tmp_path)
    runtime.window.core.security.is_in_workdir.return_value = False

    assert runtime.context_api.load_project_rules() == ""
    runtime.verbose_text.assert_not_called()
    runtime.verbose_log.assert_called()


def test_agents_v2_project_rules_missing_file_returns_empty(tmp_path):
    runtime = bare_runtime()
    runtime.window.core.filesystem.get_data_dir.return_value = str(tmp_path)
    assert runtime.context_api.load_project_rules() == ""
    runtime.window.core.security.is_in_workdir.assert_not_called()


def test_main_function_agent_promotes_runtime_image_blocks_after_tool_result(tmp_path):
    import asyncio

    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"x")
    image = ImageBlock(path=str(image_path))
    text = TextBlock(text="attached")
    result = SimpleNamespace(
        tool_output=SimpleNamespace(blocks=[text, image], content="attached"),
        tool_id="call-1",
        return_direct=False,
        tool_name="attach_runtime_file",
    )

    class Store:
        def __init__(self):
            self.value = []
        async def get(self, key, default=None):
            return list(self.value)
        async def set(self, key, value):
            self.value = value

    store = Store()
    ctx = SimpleNamespace(store=store)
    agent = SimpleNamespace(scratchpad_key="scratchpad")

    asyncio.run(context_module.MainFunctionAgent.handle_tool_call_results(agent, ctx, [result], memory=None))

    assert len(store.value) == 2
    tool_msg, user_msg = store.value
    assert tool_msg.role == MessageRole.TOOL
    assert tool_msg.blocks == [text]
    assert tool_msg.additional_kwargs["tool_call_id"] == "call-1"
    assert user_msg.role == MessageRole.USER
    assert isinstance(user_msg.blocks[0], TextBlock)
    assert image in user_msg.blocks[1:]
