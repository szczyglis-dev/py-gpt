# Example LLM / embeddings provider

This `llm` Add-on is intentionally offline: it returns LlamaIndex `MockLLM` and `MockEmbedding` objects, so a developer can test provider registration without credentials or network access.

## Try it

Install and restart PyGPT. The provider is then available to the LlamaIndex/embedding registries. The example shows the smallest useful implementations of `llama()`, `llama_completion()` and `get_embeddings_model()`.

For a production provider, construct the real SDK/LlamaIndex wrapper from the selected model and provider configuration. An external `BaseLLM` wrapper does not by itself create a new native Chat SDK bridge; see the Add-ons API notes on provider scope.
