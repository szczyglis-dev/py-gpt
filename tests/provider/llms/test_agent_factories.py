"""Provider selection must preserve native tools, credentials and continuation policy."""
import copy
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


def adapter(monkeypatch, module_name, class_name):
    module = ModuleType(module_name)
    factory = MagicMock(side_effect=lambda **kwargs: SimpleNamespace(
        options=kwargs, bind_computer_runtime=MagicMock(),
    ))
    setattr(module, class_name, factory)
    monkeypatch.setitem(sys.modules, module_name, module)
    return factory


def setup(provider, args=None):
    window = MagicMock()
    window.core.config.get.side_effect = lambda key, default=None: default
    window.core.models.get_reasoning_effort.return_value = "high"
    window.core.context_manager.configure_llm_for_rolling_context.side_effect = lambda llm: llm
    provider.parse_args = MagicMock(side_effect=lambda *a: copy.deepcopy(args or {}))
    provider.prepare_openai_compatible_args = MagicMock(side_effect=lambda *a: copy.deepcopy(args or {}))
    provider.inject_llamaindex_http_clients = MagicMock(side_effect=lambda args, config: args)
    provider.get_env_override = MagicMock(return_value="model-key")
    provider.get_config = MagicMock(side_effect=lambda key, default=None: "provider-key" if key == "api_key" else default)
    provider.log_llama_create = MagicMock()
    return window


@pytest.mark.parametrize("remote,computer", [(False, False), (True, False), (True, True)])
def test_openai_agent_always_uses_responses_and_preserves_remote_tool_policy(monkeypatch, remote, computer):
    from pygpt_net.provider.llms.openai.provider import OpenAILLM
    from pygpt_net.core.types import MODE_AGENT_V2, MODE_COMPUTER
    provider = OpenAILLM()
    window = setup(provider, {"model": "gpt-test", "include": ["existing"]})
    constructor = adapter(monkeypatch, "pygpt_net.provider.llms.openai.responses_agent", "AgentOpenAIResponses")
    window.core.api.openai.remote_tools.append_to_tools.return_value = [{"type": "web_search"}]
    llm = provider.llama_agent(window, SimpleNamespace(id="gpt-test"),
                               allow_remote_tools=remote, force_computer_use=computer)
    assert constructor.call_count == 1
    assert llm.options["additional_kwargs"]["reasoning"] == {"effort": "high"}
    if remote:
        assert llm.options["built_in_tools"] == [{"type": "web_search"}]
        assert llm.options["include"] == ["existing", "web_search_call.action.sources"]
        assert window.core.api.openai.remote_tools.append_to_tools.call_args.kwargs["mode"] == (
            MODE_COMPUTER if computer else MODE_AGENT_V2
        )
    else:
        assert "built_in_tools" not in llm.options
        window.core.api.openai.remote_tools.append_to_tools.assert_not_called()


@pytest.mark.parametrize("force", [False, True])
def test_anthropic_agent_keeps_beta_headers_and_computer_exclusivity(monkeypatch, force):
    from pygpt_net.provider.llms.anthropic.provider import AnthropicLLM
    provider = AnthropicLLM()
    window = setup(provider, {"tools": [{"type": "custom", "name": "local"}],
                              "default_headers": {"anthropic-beta": "user-beta"},
                              "additional_kwargs": {"extra_body": {"user": "value"}}})
    adapter(monkeypatch, "pygpt_net.provider.llms.anthropic.agent", "AgentAnthropic")
    remote = {"type": "computer_20251124", "name": "computer"}
    window.core.api.anthropic.remote_tools.build_remote_tools.return_value = [remote]
    window.core.api.anthropic.computer.supports_model.return_value = True
    window.core.api.anthropic.computer.get_tool.return_value = remote
    model = SimpleNamespace(id="claude-test", llama_index={})
    llm = provider.agents.create(window, model, force_computer_use=force)
    assert llm.options["api_key"] == "model-key"
    assert llm.options["tools"] == ([remote] if force else [{"type": "custom", "name": "local"}, remote])
    assert llm.options["default_headers"]["anthropic-beta"] == "user-beta,computer-use-2025-11-24"
    assert llm.options["additional_kwargs"]["extra_body"] == {"user": "value", "output_config": {"effort": "high"}}


@pytest.mark.parametrize("remote,force", [(False, False), (True, False), (False, True)])
def test_google_agent_keeps_remote_tools_thinking_and_model_environment(monkeypatch, remote, force):
    from pygpt_net.provider.llms.google.provider import GoogleLLM
    from pygpt_net.provider.llms.google import parameters
    provider = GoogleLLM()
    window = setup(provider, {"generation_config": {"temperature": 0.3}})
    adapter(monkeypatch, "pygpt_net.provider.llms.google.agent", "AgentGoogleGenAI")
    monkeypatch.setattr(parameters, "get_google_thinking_kwargs", lambda *a: {"thinking_budget": 1024})
    window.core.api.google.remote_tools.build_remote_tools.return_value = ["search"]
    window.core.api.google.remote_tools.supports_computer_use.return_value = True
    window.core.api.google.computer.get_tool.return_value = "computer"
    model = SimpleNamespace(id="gemini-test", llama_index={})
    llm = provider.agents.create(window, model, allow_remote_tools=remote, force_computer_use=force)
    assert llm.options["model"] == "models/gemini-test"
    assert llm.options["api_key"] == "model-key"
    assert llm.options["generation_config"].temperature == 0.3
    assert llm.options["generation_config"].thinking_config.thinking_budget == 1024
    assert llm.options["pygpt_remote_tools"] == (["computer"] if force else ["search"] if remote else [])
    window.core.api.google.setup_env.assert_called_once()


def test_ollama_agent_and_completion_share_native_options_but_not_tool_capability(monkeypatch):
    from pygpt_net.provider.llms.ollama.provider import OllamaLLM
    provider = OllamaLLM()
    window = setup(provider, {"timeout": 12, "api_base": "ignored", "api_key": "ignored"})
    adapter(monkeypatch, "pygpt_net.provider.llms.ollama.custom", "Ollama")
    adapter(monkeypatch, "pygpt_net.provider.llms.ollama.completion", "OllamaCompletion")
    window.core.models.prepare_client_args.return_value = {"base_url": "http://local:1234/v1/"}
    window.core.models.get_num_ctx.return_value = 8192
    model = SimpleNamespace(id="ollama-test", llama_index={}, tool_calls=True, get_ollama_model=lambda: "qwen3")
    agent = provider.agents.create(window, model)
    completion = provider.llama_completion(window, model)
    for llm in [agent, completion]:
        assert llm.options["base_url"] == "http://local:1234"
        assert llm.options["model"] == "qwen3"
        assert llm.options["request_timeout"] == 12
        assert llm.options["context_window"] == 8192
        assert llm.options["think"] == "high"
        assert "api_key" not in llm.options and "api_base" not in llm.options
    assert agent.options["is_function_calling_model"] is True
    assert completion.options["is_function_calling_model"] is False


@pytest.mark.parametrize("remote", [False, True])
def test_xai_agent_tools_choose_responses_without_changing_local_only_path(monkeypatch, remote):
    from pygpt_net.provider.llms.x_ai.provider import xAILLM
    provider = xAILLM()
    window = setup(provider, {"model": "grok-3", "max_tokens": 100})
    adapter(monkeypatch, "pygpt_net.provider.llms.x_ai.responses_agent", "AgentXAIResponses")
    window.core.api.xai.remote.build_for_responses.return_value = {"tools": [{"type": "web_search"}]}
    provider.llama = MagicMock(return_value="plain")
    model = SimpleNamespace(id="grok-3", ctx=4096)
    llm = provider.agents.create(window, model, allow_remote_tools=remote)
    if not remote:
        assert llm == "plain"
        provider.llama.assert_called_once_with(window=window, model=model, stream=False, remote_tools=False)
    else:
        assert llm.options["model"] == "grok-4.5-latest"
        assert llm.options["max_output_tokens"] == 100
        assert "max_tokens" not in llm.options
        assert llm.options["built_in_tools"] == [{"type": "web_search"}]


@pytest.mark.parametrize("kind", ["openai", "anthropic", "google"])
def test_llama_with_computer_runtime_binds_only_for_computer_capable_models(monkeypatch, kind):
    from pygpt_net.provider.llms.openai.provider import OpenAILLM
    from pygpt_net.provider.llms.anthropic.provider import AnthropicLLM
    from pygpt_net.provider.llms.google.provider import GoogleLLM
    provider = {"openai": OpenAILLM, "anthropic": AnthropicLLM, "google": GoogleLLM}[kind]()
    window = setup(provider)
    llm = SimpleNamespace(bind_computer_runtime=MagicMock())
    provider.agents.create = MagicMock(return_value=llm)
    provider.agents.computer_enabled = MagicMock(return_value=True)
    runtime = object()
    model = SimpleNamespace(id="model")
    assert provider.llama_with_computer_runtime(window, model, computer_runtime=runtime) is llm
    llm.bind_computer_runtime.assert_called_once_with(runtime)
    provider.agents.computer_enabled.return_value = False
    provider.llama = MagicMock(return_value="plain")
    assert provider.llama_with_computer_runtime(window, model, computer_runtime=runtime) == "plain"
    assert llm.bind_computer_runtime.call_count == 1
