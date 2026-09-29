"""Offline LlamaIndex LLM + embedding provider example.

It uses LlamaIndex mock classes already available in PyGPT, so it is safe for
learning the provider contract without API keys or network access.
"""

from pygpt_net.core.types import MODE_EMBEDDINGS, MODE_LLAMA_INDEX
from pygpt_net.provider.llms.base import BaseLLM


class ExampleLLM(BaseLLM):
    def __init__(self):
        super().__init__()
        self.id = "example_llm"
        self.name = "Example Mock LLM"
        self.description = "Offline tutorial provider using LlamaIndex MockLLM/MockEmbedding."
        self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def llama(self, window, model, stream=False):
        from llama_index.core.llms.mock import MockLLM

        # A real provider would build its SDK/LlamaIndex wrapper here using
        # model.id plus provider configuration returned by setup().
        return MockLLM(max_tokens=128)

    def llama_completion(self, window, model, stream=False):
        return self.llama(window, model, stream=stream)

    def get_embeddings_model(self, window, config=None):
        from llama_index.core.embeddings.mock_embed_model import MockEmbedding

        return MockEmbedding(embed_dim=8)
