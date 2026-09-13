#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.mode import AgentMode
from pygpt_net.core.agents_v2.prompt_builder import RuntimePromptBuilder
from pygpt_net.core.agents_v2.strategy import get_agent_strategy


def make_runtime():
    runtime = SimpleNamespace(
        bridge_system_prompt="plugin prompt",
        preset=SimpleNamespace(prompt="preset prompt"),
        agent_mode=AgentMode.PRIMARY_AGENT,
        model=SimpleNamespace(id="model-x"),
        allow_local_tools=True,
        allow_remote_tools=False,
        index_id="idx-1",
        rag_context_text="retrieved",
        shared_context_text="attachments",
        max_workers_configured=4,
        is_swarm_mode=False,
        runtime_system_context="filesystem instructions",
        strategy=get_agent_strategy(AgentMode.PRIMARY_AGENT),
    )
    runtime._rag_prompt_context = MagicMock(return_value="<rag_context>retrieved</rag_context>")
    return runtime


def test_compose_agent_system_prompt_includes_capabilities_runtime_rag_and_bridge_prompt():
    runtime = make_runtime()
    builder = RuntimePromptBuilder(runtime)

    prompt = builder.compose_agent_system_prompt(base_prompt="role prompt")

    assert prompt.startswith("role prompt\n\n<runtime_capabilities>")
    assert "agent_mode=primary_agent" in prompt
    assert "selected_model=model-x" in prompt
    assert "allow_local_tools=True" in prompt
    assert "allow_remote_tools=False" in prompt
    assert "rag_index=idx-1" in prompt
    assert "max_parallel_workers=4" in prompt
    assert "<runtime_environment>\nfilesystem instructions\n</runtime_environment>" in prompt
    assert "<rag_context>retrieved</rag_context>" in prompt
    assert "<additional_system_prompt>\nplugin prompt\n</additional_system_prompt>" in prompt


def test_compose_agent_system_prompt_uses_preset_fallback_and_does_not_duplicate_runtime_context():
    runtime = make_runtime()
    runtime.bridge_system_prompt = ""
    runtime.runtime_system_context = "runtime block"
    runtime.preset.prompt = "preset prompt with runtime block"
    builder = RuntimePromptBuilder(runtime)

    prompt = builder.compose_agent_system_prompt()

    assert "preset prompt with runtime block" in prompt
    assert "<runtime_environment>" not in prompt
    assert prompt.count("runtime block") == 1


def test_compose_agent_system_prompt_honors_explicit_additional_prompt():
    runtime = make_runtime()
    builder = RuntimePromptBuilder(runtime)

    prompt = builder.compose_agent_system_prompt(
        base_prompt="base",
        additional_system_prompt="explicit",
    )

    assert "<additional_system_prompt>\nexplicit\n</additional_system_prompt>" in prompt
    assert "plugin prompt" not in prompt
    assert "preset prompt" not in prompt
