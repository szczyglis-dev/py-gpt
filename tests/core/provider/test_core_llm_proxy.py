from types import SimpleNamespace

import pygpt_net.core.provider.llm as llm_module
from pygpt_net.core.provider.llm import LlamaIndexLLMProxy


def model(provider="openai", model_id="model-x", **kwargs):
    data = {
        "id": model_id,
        "provider": provider,
        "ctx": 0,
        "mode": ["chat"],
        "llama_index": {},
        "reasoning_effort": False,
        "tool_calls": False,
    }
    data.update(kwargs)
    return SimpleNamespace(**data)


def test_core_llm_proxy_resolves_provider_and_model_name_variants():
    proxy = LlamaIndexLLMProxy()

    item = model(provider="openai", model_id="fallback")
    item.get_provider = lambda: "anthropic"
    item.llama_index = {"args": {"model": " exact-model "}}
    assert proxy._provider_id(item) == "anthropic"
    assert proxy._model_name(item) == "exact-model"

    item.llama_index = {"args": [{"name": "x", "value": "skip"}, {"name": "model", "value": "list-model"}]}
    assert proxy._model_name(item) == "list-model"

    item.llama_index = {}
    assert proxy._model_name(item) == "fallback"


def test_core_llm_proxy_registry_helpers_mutate_supported_containers():
    module = SimpleNamespace(
        mapping={},
        values=set(),
        names=[],
        invalid=object(),
    )

    assert LlamaIndexLLMProxy._registry_add(module, "mapping", "m", 10) is True
    assert module.mapping == {"m": 10}
    assert LlamaIndexLLMProxy._registry_add(module, "mapping", "m", 20) is False

    assert LlamaIndexLLMProxy._registry_add(module, "values", "m", 10) is True
    assert LlamaIndexLLMProxy._registry_add(module, "names", "m", 10) is True
    assert LlamaIndexLLMProxy._registry_add(module, "invalid", "m", 10) is False
    assert LlamaIndexLLMProxy._registry_contains(module, "mapping", "m") is True
    assert LlamaIndexLLMProxy._registry_contains(module, "invalid", "m") is False


def test_core_llm_proxy_prepare_openai_extends_model_chat_and_reasoning_registries(monkeypatch, capsys):
    utils = SimpleNamespace(
        ALL_AVAILABLE_MODELS={"old": 1},
        CHAT_MODELS={},
        O1_MODELS=set(),
        OPENAI_REASONING_MODELS=[],
        REASONING_MODELS={},
    )
    monkeypatch.setattr(llm_module, "import_module", lambda name: utils)
    monkeypatch.setattr(llm_module, "is_openai_reasoning_model_id", lambda name: False)

    item = model(model_id="gpt-new", ctx=200000, reasoning_effort=True)
    proxy = LlamaIndexLLMProxy()

    assert proxy.prepare(item) is True
    assert utils.ALL_AVAILABLE_MODELS["gpt-new"] == 200000
    assert utils.CHAT_MODELS["gpt-new"] == 200000
    assert "gpt-new" in utils.O1_MODELS
    assert "gpt-new" in utils.OPENAI_REASONING_MODELS
    assert utils.REASONING_MODELS["gpt-new"] == 200000
    assert "gpt-new" in capsys.readouterr().out

    assert proxy.prepare(item) is False
    assert capsys.readouterr().out == ""


def test_core_llm_proxy_prepare_anthropic_installs_tool_calling_proxy(monkeypatch):
    utils = SimpleNamespace(
        CLAUDE_MODELS={},
        ANTHROPIC_MODELS={},
        is_function_calling_model=lambda name: name == "legacy",
    )
    base = SimpleNamespace(is_function_calling_model=utils.is_function_calling_model)

    def fake_import(name):
        if name == "llama_index.llms.anthropic.utils":
            return utils
        if name == "llama_index.llms.anthropic.base":
            return base
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(llm_module, "import_module", fake_import)
    monkeypatch.setattr(LlamaIndexLLMProxy, "_anthropic_function_calling_models", set())

    proxy = LlamaIndexLLMProxy()
    item = model(provider="anthropic", model_id="claude-new", ctx=240000, tool_calls=True)

    assert proxy.prepare(item) is True
    assert utils.CLAUDE_MODELS["claude-new"] == 240000
    assert utils.ANTHROPIC_MODELS["claude-new"] == 240000
    assert utils.is_function_calling_model("claude-new") is True
    assert utils.is_function_calling_model("legacy") is True
    assert base.is_function_calling_model("claude-new") is True
    assert getattr(utils, "_pygpt_function_calling_proxy") is True


def test_core_llm_proxy_prepare_returns_false_for_native_or_unsupported_paths(monkeypatch):
    proxy = LlamaIndexLLMProxy()

    assert proxy.prepare(None) is False
    assert proxy.prepare(model(provider="ollama")) is False
    assert proxy.prepare(model(provider="google")) is False
    assert proxy.prepare(model(provider="x_ai")) is False

    monkeypatch.setattr(llm_module, "import_module", lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)))
    assert proxy.prepare(model(provider="openai")) is False
    assert proxy.prepare(model(provider="anthropic")) is False


def test_core_llm_proxy_context_and_chat_helpers_handle_invalid_metadata(monkeypatch):
    proxy = LlamaIndexLLMProxy()
    item = model(ctx="bad", mode=["completion"])
    assert proxy._context_window(item, 128000) == 128000
    assert proxy._has_chat_mode(item) is False

    item.has_mode = lambda mode: (_ for _ in ()).throw(RuntimeError("broken"))
    item.mode = ["chat"]
    assert proxy._has_chat_mode(item) is True

    monkeypatch.setattr(llm_module, "is_openai_reasoning_model_id", lambda name: name == "o-new")
    assert proxy._is_reasoning_model(item, "o-new") is True
