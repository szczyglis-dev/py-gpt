import asyncio
from unittest.mock import MagicMock

from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.agents.base import BaseAgent


def make_agent():
    agent = BaseAgent()
    agent.id = "agent"
    agent.mode = "agent-mode"
    return agent


def options():
    return {
        "__prompt__": "Default prompt",
        "section": {
            "options": {
                "enabled": {"default": True},
                "limit": {"default": 5},
                "nullable": {"default": None},
            }
        },
    }


def test_initial_state_and_mode():
    agent = BaseAgent()
    assert agent.id == ""
    assert agent.type == ""
    assert agent.mode == ""
    assert agent.name == ""
    assert agent.custom_id is None
    assert agent.custom_options is None
    assert agent.custom_schema is None
    assert agent.get_mode() == ""


def test_setters_and_custom_options():
    agent = make_agent()
    schema = [{"name": "x"}]
    opts = options()
    agent.set_id("custom")
    agent.set_schema(schema)
    agent.set_options(opts)
    assert agent.custom_id == "custom"
    assert agent.custom_schema is schema
    assert agent.get_options() is opts


def test_get_options_defaults_to_empty_and_base_agent_is_abstract_by_noop():
    agent = make_agent()
    assert agent.get_options() == {}
    assert agent.get_agent(object(), {}) is None
    assert asyncio.run(agent.run(object())) is None


def test_get_default_and_default_prompt():
    agent = make_agent()
    agent.set_options(options())
    assert agent.get_default("section", "enabled") is True
    assert agent.get_default("section", "limit") == 5
    assert agent.get_default("missing", "limit") is None
    assert agent.get_default("section", "missing") is None
    assert agent.get_default_prompt() == "Default prompt"
    agent.set_options({})
    assert agent.get_default_prompt() == ""


def test_get_option_returns_none_for_missing_preset(capsys):
    agent = make_agent()
    assert agent.get_option(None, "section", "limit") is None
    assert "No preset provided" in capsys.readouterr().out


def test_get_option_uses_defaults_for_missing_or_null_values():
    agent = make_agent()
    agent.set_options(options())
    preset = PresetItem()

    preset.extra = None
    assert agent.get_option(preset, "section", "limit") == 5
    preset.extra = {}
    assert agent.get_option(preset, "section", "limit") == 5
    preset.extra = {"agent": {}}
    assert agent.get_option(preset, "section", "limit") == 5
    preset.extra = {"agent": {"section": {}}}
    assert agent.get_option(preset, "section", "limit") == 5
    preset.extra = {"agent": {"section": {"limit": None}}}
    assert agent.get_option(preset, "section", "limit") == 5


def test_get_option_uses_preset_value_and_custom_agent_id():
    agent = make_agent()
    agent.set_options(options())
    preset = PresetItem()
    preset.extra = {"custom": {"section": {"limit": 11}}}
    agent.set_id("custom")
    assert agent.get_option(preset, "section", "limit") == 11
