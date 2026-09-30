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

    def setup(self):
        # Fields with use_locale=True are translated from this Add-on's own
        # locale/ directory. BaseLLM.get_name() also uses provider.name there.
        return {
            "openai_compatible": False,
            "settings": {
                "extra": {
                    "mock_max_tokens": {
                        "type": "int",
                        "default": 128,
                        "min": 16,
                        "max": 4096,
                        "label": "settings.mock_max_tokens.label",
                        "description": "settings.mock_max_tokens.description",
                        "use_locale": True,
                    },
                },
            },
            "remote_tools": {},
        }

    def llama(self, window, model, stream=False):
        from llama_index.core.llms.mock import MockLLM

        # A real provider would build its SDK/LlamaIndex wrapper here using
        # model.id plus provider configuration returned by setup().
        max_tokens = int(self.get_config("mock_max_tokens", 128) or 128)
        return MockLLM(max_tokens=max_tokens)

    def llama_completion(self, window, model, stream=False):
        return self.llama(window, model, stream=stream)

    def get_embeddings_model(self, window, config=None):
        from llama_index.core.embeddings.mock_embed_model import MockEmbedding

        return MockEmbedding(embed_dim=8)
