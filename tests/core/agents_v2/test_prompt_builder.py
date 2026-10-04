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
        step_by_step_enabled=False,
        window=SimpleNamespace(
            core=SimpleNamespace(
                config=SimpleNamespace(get=MagicMock(return_value="")),
            ),
        ),
        strategy=get_agent_strategy(AgentMode.PRIMARY_AGENT),
    )
    runtime.inputs = SimpleNamespace()
    runtime.inputs.rag_prompt = MagicMock(return_value="<rag_context>retrieved</rag_context>")
    return runtime


def test_compose_agent_system_prompt_includes_capabilities_runtime_rag_and_bridge_prompt():
    runtime = make_runtime()
    builder = RuntimePromptBuilder(runtime)

    prompt = builder.compose(base_prompt="role prompt")

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

    prompt = builder.compose()

    assert "preset prompt with runtime block" in prompt
    assert "<runtime_environment>" not in prompt
    assert prompt.count("runtime block") == 1


def test_compose_agent_system_prompt_honors_explicit_additional_prompt():
    runtime = make_runtime()
    builder = RuntimePromptBuilder(runtime)

    prompt = builder.compose(
        base_prompt="base",
        additional_system_prompt="explicit",
    )

    assert "<additional_system_prompt>\nexplicit\n</additional_system_prompt>" in prompt
    assert "plugin prompt" not in prompt
    assert "preset prompt" not in prompt


def test_builtin_prompt_slots_honor_overrides_without_injecting_policy():
    runtime = make_runtime()
    builder = RuntimePromptBuilder(runtime)
    runtime.window.core.config.get.side_effect = lambda key, default=None: ' custom role ' if key.startswith('prompt.') else default
    assert builder._compose_main('base').startswith('base')
    assert builder._configured_main_prompt('default', 'override') == 'default'
    runtime.window.core.config.get.side_effect = lambda key, default=None: ' custom role '
    for method in (builder.primary, builder.orchestrator, builder.swarm):
        prompt = method()
        assert prompt.startswith('custom role')
        assert '<workflow_progress_policy>' not in prompt


def test_all_stock_domain_presets_compose_once_in_each_builtin_mode():
    import json
    from pathlib import Path
    from pygpt_net.core.agents_v2.prompts import AGENT_RUNTIME_POLICY, STEP_BY_STEP_RULES

    root = Path(__file__).resolve().parents[3] / 'src/pygpt_net/data/config/presets'
    runtime = make_runtime()
    runtime.window.core.config.get.side_effect = lambda key, default=None: default
    builder = RuntimePromptBuilder(runtime)
    for file in root.glob('*agent_v2*.json'):
        domain = json.loads(file.read_text())['prompt']
        runtime.bridge_system_prompt = domain
        for method in (builder.primary, builder.orchestrator, builder.swarm):
            prompt = method()
            assert prompt.count(domain) == 1, (file.name, method.__name__)
            assert prompt.count(AGENT_RUNTIME_POLICY) == 1
            assert prompt.count(STEP_BY_STEP_RULES) == 1
            assert prompt.count('# Autonomous completion contract') == 1
            assert prompt.count('# User-visible workflow progress') == 1
            assert 'After each meaningful stage' in prompt
            assert 'Report refinements explicitly' in prompt
            assert 'are required before starting each meaningful activity' in prompt
            assert 'Normal progress messages never replace these activity statuses' in prompt
            assert 'never replace the introduction' in prompt
            assert 'first required tool/delegation action in the same model pass' in prompt
            assert '<step_by_step_rules>' not in prompt
            assert '<step_by_step_brief>' not in prompt
            assert '<additional_system_prompt>' in prompt


def test_builtin_workflow_is_independent_of_preset_and_domain_prompts_do_not_own_it():
    import json
    from pathlib import Path
    from pygpt_net.core.agents_v2.prompts import WORKFLOW_PROGRESS_POLICY

    runtime = make_runtime()
    runtime.bridge_system_prompt = ''
    runtime.preset.prompt = ''
    runtime.window.core.config.get.side_effect = lambda key, default=None: default
    builder = RuntimePromptBuilder(runtime)
    for method in (builder.primary, builder.orchestrator, builder.swarm):
        assert WORKFLOW_PROGRESS_POLICY in method()
    root = Path(__file__).resolve().parents[3] / 'src/pygpt_net/data/config/presets'
    for file in root.glob('*agent_v2*.json'):
        domain = json.loads(file.read_text())['prompt']
        for runtime_instruction in ('workflow_status', 'report_status', 'workflow_finish',
                                    'task_complete', '## Progress communication'):
            assert runtime_instruction not in domain, file.name
