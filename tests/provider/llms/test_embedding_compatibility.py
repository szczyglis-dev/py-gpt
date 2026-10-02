"""Legacy embedding callers use the provider's new constructor hook."""
import pytest

from pygpt_net.provider.llms.base import BaseLLM


class EmbeddingProvider(BaseLLM):
    def llama_embeddings(self, window, config=None):
        self.embedding_request = (window, config)
        return self.embedding


@pytest.mark.parametrize("config", [None, [{"name": "model", "value": "embedding-test"}]])
@pytest.mark.parametrize("keywords", [False, True])
def test_legacy_embedding_entry_point_dispatches_to_new_provider_hook(config, keywords):
    provider = EmbeddingProvider()
    provider.embedding = object()
    window = object()
    if keywords:
        result = provider.get_embeddings_model(window=window, config=config)
    else:
        result = provider.get_embeddings_model(window, config)
    assert result is provider.embedding
    assert provider.embedding_request[0] is window
    assert provider.embedding_request[1] is config
