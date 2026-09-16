from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.agents import AgentsV2
from pygpt_net.core.agents_v2.mode import AgentMode
from pygpt_net.core.agents_v2.prompt_builder import RuntimePromptBuilder
from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime
from pygpt_net.core.agents_v2.strategy import get_agent_strategy


def make_runtime(definition=None, step_by_step=False):
    runtime = SimpleNamespace(
        agent_id="custom-id" if definition else "chat",
        agent_definition=definition,
        bridge_system_prompt="",
        preset=SimpleNamespace(prompt=""),
        agent_mode=AgentMode.ORCHESTRATOR if definition else AgentMode.PRIMARY_AGENT,
        model=SimpleNamespace(id="model-x"),
        allow_local_tools=True,
        allow_remote_tools=True,
        index_id=None,
        rag_context_text="",
        shared_context_text="",
        max_workers_configured=4,
        is_swarm_mode=False,
        runtime_system_context="",
        step_by_step_enabled=step_by_step,
        project_rules_loaded=True,
        project_rules_text="",
        context_api=SimpleNamespace(load_project_rules=MagicMock(return_value="")),
        window=SimpleNamespace(
            core=SimpleNamespace(
                config=SimpleNamespace(get=MagicMock(return_value="")),
            ),
        ),
        strategy=get_agent_strategy(AgentMode.ORCHESTRATOR if definition else AgentMode.PRIMARY_AGENT),
    )
    runtime._rag_prompt_context = MagicMock(return_value="")
    return runtime


def test_agents_v2_profiles_custom_prompt_uses_independent_system_and_steps():
    runtime = make_runtime({
        "id": "custom-id",
        "name": "Research lead",
        "system_prompt": "Custom system",
        "step_by_step_prompt": "Custom steps",
    }, step_by_step=True)

    prompt = RuntimePromptBuilder(runtime).main_agent_prompt()

    assert prompt.startswith("Custom system\n\nCustom steps")
    assert "agent_profile=custom-id" in prompt
    assert "agent_mode=orchestrator" in prompt


def test_agents_v2_profiles_custom_prompt_does_not_add_steps_when_disabled():
    runtime = make_runtime({
        "id": "custom-id",
        "name": "Research lead",
        "system_prompt": "Custom system",
        "step_by_step_prompt": "Custom steps",
    }, step_by_step=False)

    prompt = RuntimePromptBuilder(runtime).main_agent_prompt()

    assert prompt.startswith("Custom system")
    assert "Custom steps" not in prompt


def test_agents_v2_profiles_runtime_name_and_description_use_custom_definition():
    runtime = object.__new__(AgentsV2Runtime)
    runtime.agent_definition = {"name": "My workflow"}
    runtime.strategy = get_agent_strategy(AgentMode.ORCHESTRATOR)

    assert runtime.main_agent_name == "My workflow"
    assert runtime.main_agent_description == "Custom Chat with Agents workflow"

    runtime.agent_definition = {"name": ""}
    assert runtime.main_agent_name == "Custom Agent"

    runtime.agent_definition = None
    assert runtime.main_agent_name == runtime.strategy.main_name
    assert runtime.main_agent_description == runtime.strategy.main_description


def test_agents_v2_profiles_wrapper_exposes_editor_and_memory_store():
    window = SimpleNamespace()
    agents = AgentsV2(window)

    assert agents.window is window
    assert agents.editor.window is window
    assert agents.memory_store.window is window
