from types import SimpleNamespace
from unittest.mock import patch

from pygpt_net.core.agents_v2.editor import AgentEditor, CUSTOM_AGENTS_CONFIG_KEY
from pygpt_net.core.agents_v2.mode import AgentMode
from pygpt_net.core.agents_v2.prompts import (
    CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY,
    CUSTOM_PRIMARY_PROMPT_CONFIG_KEY,
    CUSTOM_STEP_BY_STEP_PROMPT_CONFIG_KEY,
    CUSTOM_SWARM_PROMPT_CONFIG_KEY,
    ORCHESTRATOR_BASE_PROMPT,
    STEP_BY_STEP_RULES,
)


class ConfigStub:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.set_calls = []

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.set_calls.append((key, value))
        self.values[key] = value


def make_editor(values=None):
    config = ConfigStub(values)
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    return AgentEditor(window), config


def test_agents_v2_editor_normalizes_builtin_ids_and_aliases():
    assert AgentEditor.normalize_builtin_id("chat") == "chat"
    assert AgentEditor.normalize_builtin_id(" primary-agent ") == "chat"
    assert AgentEditor.normalize_builtin_id("swarm_mode") == "swarm"
    assert AgentEditor.normalize_builtin_id(AgentMode.ORCHESTRATOR) == "orchestrator"
    assert AgentEditor.normalize_builtin_id("custom-id") == ""
    assert AgentEditor.normalize_builtin_id(None) == ""


def test_agents_v2_editor_filters_and_normalizes_custom_rows():
    editor, _ = make_editor({
        CUSTOM_AGENTS_CONFIG_KEY: [
            None,
            {"id": "", "name": "empty"},
            {"id": "chat", "name": "reserved"},
            {"id": "a1", "name": " First ", "system_prompt": 123},
            {"id": "a1", "name": "duplicate"},
            {"id": "a2", "step_by_step_prompt": " steps "},
        ]
    })

    assert editor.get_custom_agents() == [
        {
            "id": "a1",
            "name": "First",
            "system_prompt": "123",
            "step_by_step_prompt": "",
        },
        {
            "id": "a2",
            "name": "",
            "system_prompt": "",
            "step_by_step_prompt": " steps ",
        },
    ]


def test_agents_v2_editor_lists_builtins_before_custom_agents():
    editor, _ = make_editor({
        CUSTOM_AGENTS_CONFIG_KEY: [{"id": "custom", "name": "Custom"}],
    })

    rows = editor.get_agents()

    assert [row["id"] for row in rows] == ["chat", "orchestrator", "swarm", "custom"]
    assert all(row["built_in"] for row in rows[:3])
    assert rows[3]["built_in"] is False
    assert rows[3]["runtime_mode"] is AgentMode.ORCHESTRATOR


def test_agents_v2_editor_resolves_builtin_custom_and_unknown_selection():
    editor, _ = make_editor({
        CUSTOM_AGENTS_CONFIG_KEY: [{
            "id": "custom",
            "name": "Custom",
            "system_prompt": "system",
            "step_by_step_prompt": "steps",
        }],
    })

    assert editor.resolve_selection("primary") == ("chat", AgentMode.PRIMARY_AGENT, None)
    assert editor.resolve_selection("swarm") == ("swarm", AgentMode.SWARM, None)

    agent_id, mode, definition = editor.resolve_selection("custom")
    assert agent_id == "custom"
    assert mode is AgentMode.ORCHESTRATOR
    assert definition["name"] == "Custom"
    assert definition["built_in"] is False

    assert editor.resolve_selection("missing") == ("chat", AgentMode.PRIMARY_AGENT, None)


def test_agents_v2_editor_editable_values_read_builtin_overrides():
    editor, _ = make_editor({
        CUSTOM_PRIMARY_PROMPT_CONFIG_KEY: "primary override",
        CUSTOM_STEP_BY_STEP_PROMPT_CONFIG_KEY: "shared steps",
    })

    row = editor.editable_values("chat")

    assert row["built_in"] is True
    assert row["system_prompt"] == "primary override"
    assert row["step_by_step_prompt"] == "shared steps"
    assert editor.editable_values("missing") is None


def test_agents_v2_editor_create_save_and_delete_custom_agent():
    editor, config = make_editor()

    with patch("pygpt_net.core.agents_v2.editor.editor.uuid.uuid4", return_value="uuid-1"):
        agent_id = editor.create("  My agent  ")

    assert agent_id == "uuid-1"
    assert config.values[CUSTOM_AGENTS_CONFIG_KEY][0]["name"] == "My agent"

    assert editor.save(agent_id, " Renamed ", "system", "steps") is True
    row = editor.get(agent_id)
    assert row["name"] == "Renamed"
    assert row["system_prompt"] == "system"
    assert row["step_by_step_prompt"] == "steps"

    assert editor.save("missing", "x", "y", "z") is False
    assert editor.delete("chat") is False
    assert editor.delete("missing") is False
    assert editor.delete(agent_id) is True
    assert editor.get(agent_id) is None


def test_agents_v2_editor_builtin_save_uses_legacy_prompt_keys():
    editor, config = make_editor()

    assert editor.save("chat", "ignored name", "primary", "steps") is True
    assert editor.save("orchestrator", "ignored name", "orch", "steps2") is True
    assert editor.save("swarm", "ignored name", "swarm", "steps3") is True

    assert (CUSTOM_PRIMARY_PROMPT_CONFIG_KEY, "primary") in config.set_calls
    assert (CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY, "orch") in config.set_calls
    assert (CUSTOM_SWARM_PROMPT_CONFIG_KEY, "swarm") in config.set_calls
    assert config.values[CUSTOM_STEP_BY_STEP_PROMPT_CONFIG_KEY] == "steps3"


def test_agents_v2_editor_default_prompts_cover_custom_workflows():
    editor, _ = make_editor()

    assert editor.get_default_main_prompt("custom") == str(ORCHESTRATOR_BASE_PROMPT)
    assert editor.get_default_step_by_step_prompt("custom") == str(STEP_BY_STEP_RULES)
