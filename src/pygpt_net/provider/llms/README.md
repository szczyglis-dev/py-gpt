# LLM provider structure

Providers use composition: a provider describes its identity and configuration,
while its components own request policy and agent adapter construction.

| Module | Responsibility |
| --- | --- |
| `provider.py` | Provider registration, capabilities, regular models and embeddings. |
| `agents.py` | Agent adapter selection, native tools and Computer Use continuations. |
| `parameters.py` | Shared credentials, endpoints, reasoning and request configuration. |
| Adapter modules (`agent.py`, `responses_agent.py`, `completion.py`, `capture.py`, etc.) | SDK transport, streaming, tool loops and response capture. |

## Adding or extending agent support

Set `agents_class` on the provider to a subclass of `ProviderAgents` and implement
`create()`. Override `computer_enabled()` when the provider supports Computer Use.
The common `agents.bind_computer_use()` selects the continuation adapter and binds its
runtime. Provider-specific request loops belong in an adapter module, not in
`provider.py` or the factory.

`BaseLLM` exposes the application-facing `llama_agent()` and
`llama_with_computer_runtime()` entry points, delegating directly to its agent
component.
Providers without a dedicated agent adapter use the default component, which
creates their regular LlamaIndex model. SDK imports remain lazy so registering
providers does not load every optional SDK.

OpenAI, Anthropic, Google, Ollama and xAI have dedicated agent components.
OpenAI, Anthropic, Google and Ollama also share parameter policy between regular
models and agent adapters. Mistral's chat and embedding transport adapters live
in separate modules.

>= v2.8.38:
Embedding providers implement `llama_embeddings()`. The inherited
`get_embeddings_model()` is a compatibility entry point for older callers and
forwards to `llama_embeddings()`; application code uses the new name directly.
