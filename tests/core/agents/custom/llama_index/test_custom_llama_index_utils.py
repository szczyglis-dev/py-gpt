from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.agents.custom.llama_index.utils as utils


def test_sanitize_input_items_removes_server_ids_without_mutating_original():
    original = [{
        "id": "msg",
        "message_id": "mid",
        "role": "user",
        "content": [{"id": "part", "type": "input_text", "text": "hello"}],
    }]
    result = utils.sanitize_input_items(original)
    assert "id" not in result[0]
    assert "message_id" not in result[0]
    assert "id" not in result[0]["content"][0]
    assert original[0]["id"] == "msg"


def test_content_to_str_and_strip_role_prefixes():
    assert utils.content_to_str("x") == "x"
    assert utils.content_to_str([{"text": "a"}, {"type": "image"}, {"text": 2}]) == "a\n2"
    assert utils.content_to_str(None) == ""
    assert utils.strip_role_prefixes(" Assistant: hello ") == "hello"
    assert utils.strip_role_prefixes("plain") == "plain"


def test_make_option_getter_uses_default_for_missing_or_error():
    base = SimpleNamespace(get_option=MagicMock(side_effect=["value", "", RuntimeError("x")]))
    getter = utils.make_option_getter(base, object())
    assert getter("a", "b", "default") == "value"
    assert getter("a", "b", "default") == "default"
    assert getter("a", "b", "default") == "default"
    assert utils.make_option_getter(base, None)("a", "b", "default") == "default"


def test_resolve_node_runtime_applies_option_schema_and_extra_prompt():
    default_model = object()
    selected_model = object()
    window = SimpleNamespace(core=SimpleNamespace(models=SimpleNamespace(get=MagicMock(return_value=selected_model))))
    node = SimpleNamespace(id="agent_1", instruction="node prompt", role="schema role")
    values = {
        ("agent_1", "model"): "model-id",
        ("agent_1", "prompt"): "custom prompt",
        ("agent_1", "role"): "custom role",
        ("agent_1", "allow_local_tools"): False,
        ("agent_1", "allow_remote_tools"): True,
    }
    getter = lambda section, key, default=None: values.get((section, key), default)

    runtime = utils.resolve_node_runtime(
        window=window,
        node=node,
        option_get=getter,
        default_model=default_model,
        base_prompt="base",
        system_prompt_extra="extra",
        schema_allow_local=True,
        schema_allow_remote=False,
        default_allow_local=True,
        default_allow_remote=False,
    )
    assert runtime.model is selected_model
    assert runtime.instructions == "custom prompt\n\nextra"
    assert runtime.role == "custom role"
    assert runtime.allow_local_tools is False
    assert runtime.allow_remote_tools is True


def test_patch_last_assistant_output_replaces_only_last_assistant():
    items = [
        {"role": "assistant", "content": "first"},
        {"role": "user", "content": "q"},
        {"id": "x", "role": "assistant", "content": "old"},
    ]
    result = utils.patch_last_assistant_output(items, "new")
    assert result[0]["content"] == "first"
    assert result[-1] == {"role": "assistant", "content": [{"type": "output_text", "text": "new"}]}


def test_extract_agent_text_handles_common_shapes():
    assert utils.extract_agent_text("plain") == "plain"
    ret = SimpleNamespace(response=SimpleNamespace(message=SimpleNamespace(content="answer")))
    assert utils.extract_agent_text(ret) == "answer"
    ret = SimpleNamespace(response=SimpleNamespace(message=None, text="text answer"))
    assert utils.extract_agent_text(ret) == "text answer"


def test_resolve_llm_uses_index_agent_and_preserves_remote_tool_policy():
    get_agent = MagicMock(return_value="llm")
    window = SimpleNamespace(core=SimpleNamespace(idx=SimpleNamespace(llm=SimpleNamespace(get_agent=get_agent))))
    model = SimpleNamespace(name="m")
    runtime = object()
    assert utils.resolve_llm(window, model, "base", True, runtime, False) == "llm"
    get_agent.assert_called_once_with(
        model,
        stream=True,
        allow_remote_tools=False,
        computer_runtime=None,
    )


def test_chat_message_helpers_return_empty_when_llama_index_is_unavailable(monkeypatch):
    monkeypatch.setattr(utils, "ChatMessage", None)
    monkeypatch.setattr(utils, "MessageRole", None)
    assert utils.to_li_chat_messages([{"role": "user", "content": "x"}]) == []
    assert utils.single_user_msg("x") == []


def test_coerce_li_tools_returns_empty_without_llama_index(monkeypatch):
    monkeypatch.setattr(utils, "BaseTool", object)
    assert utils.coerce_li_tools([lambda: None]) == []
