"""Embedding constructor logs reflect normalized SDK arguments."""
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize("provider_name", ["openai", "ollama"])
@pytest.mark.parametrize("legacy_entry", [False, True])
def test_embedding_creation_logs_final_options_once(monkeypatch, provider_name, legacy_entry):
    from pygpt_net.provider.llms.openai.provider import OpenAILLM
    from pygpt_net.provider.llms.ollama.provider import OllamaLLM

    provider = {"openai": OpenAILLM, "ollama": OllamaLLM}[provider_name]()
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "llama.idx.embeddings.timeout": 12,
    }.get(key, default)
    logger = MagicMock()
    window = SimpleNamespace(core=SimpleNamespace(config=config, api=SimpleNamespace(logger=logger)))
    args = {"model_name": "embedding-test"}
    provider.parse_args = MagicMock(return_value=dict(args))
    provider.prepare_openai_compatible_embedding_args = MagicMock(return_value=dict(args))
    provider.inject_llamaindex_embedding_http_clients = lambda options, cfg: {**options, "http_client": "configured-client"}
    provider.get_env_override = MagicMock(return_value=None)

    sdk_module = ModuleType(f"llama_index.embeddings.{provider_name}")
    constructor_name = {"openai": "OpenAIEmbedding", "ollama": "OllamaEmbedding"}[provider_name]
    constructor = MagicMock(return_value=object())
    setattr(sdk_module, constructor_name, constructor)
    monkeypatch.setitem(sys.modules, sdk_module.__name__, sdk_module)

    method = provider.get_embeddings_model if legacy_entry else provider.llama_embeddings
    assert method(window, config=[]) is constructor.return_value
    constructor.assert_called_once()
    options = constructor.call_args.kwargs
    logger.log_input.assert_called_once_with(
        type="llama_index.embeddings.create",
        provider=provider.id,
        kwargs=options,
        model="embedding-test",
        path=constructor_name,
    )
    if provider_name == "ollama":
        assert options["base_url"] == "http://localhost:11434"
        assert options["client_kwargs"]["timeout"] == 12
    else:
        assert options["http_client"] == "configured-client"
