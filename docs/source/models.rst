Models
======

Built-in models
---------------

PyGPT has a preconfigured list of models (as of 2026-08-15):

- ``bielik-11b-v2.3-instruct:Q4_K_M`` (Ollama)
- ``claude-fable-5`` (Anthropic)
- ``claude-haiku-4-5`` (Anthropic)
- ``claude-opus-4-5`` (Anthropic)
- ``claude-opus-5`` (Anthropic)
- ``claude-sonnet-4-5`` (Anthropic)
- ``claude-sonnet-5`` (Anthropic)
- ``codellama`` (Ollama)
- ``computer-use-preview`` (OpenAI)
- ``deep-research-max-preview-04-2026`` (Google)
- ``deep-research-preview-04-2026`` (Google)
- ``deep-research-pro-preview-12-2025`` (Google)
- ``deepseek-r1:1.5b`` (Ollama)
- ``deepseek-r1:14b`` (Ollama)
- ``deepseek-r1:7b`` (Ollama)
- ``deepseek-v4-flash`` (DeepSeek)
- ``deepseek-v4-pro`` (DeepSeek)
- ``gemini-2.5-computer-use-preview-10-2025`` (Google)
- ``gemini-2.5-flash`` (Google)
- ``gemini-2.5-flash-image`` (Google)
- ``gemini-2.5-flash-native-audio-latest`` (Google, real-time)
- ``gemini-2.5-pro`` (Google)
- ``gemini-3-flash-preview`` (Google)
- ``gemini-3-pro-image`` (Google)
- ``gemini-3.1-flash-image`` (Google)
- ``gemini-3.1-flash-lite-image`` (Google)
- ``gemini-3.1-flash-live-preview`` (Google, real-time)
- ``gemini-3.1-pro-preview`` (Google)
- ``gemini-3.5-flash`` (Google)
- ``gemini-3.5-flash-lite`` (Google)
- ``gemini-3.6-flash`` (Google)
- ``gpt-3.5-turbo`` (OpenAI)
- ``gpt-3.5-turbo-instruct`` (OpenAI)
- ``gpt-4`` (OpenAI)
- ``gpt-4-turbo`` (OpenAI)
- ``gpt-4.1`` (OpenAI)
- ``gpt-4.1-mini`` (OpenAI)
- ``gpt-4.1-nano`` (OpenAI)
- ``gpt-4o`` (OpenAI)
- ``gpt-4o-mini`` (OpenAI)
- ``gpt-5`` (OpenAI)
- ``gpt-5-mini`` (OpenAI)
- ``gpt-5-nano`` (OpenAI)
- ``gpt-5.2`` (OpenAI)
- ``gpt-5.6-sol`` (OpenAI)
- ``gpt-5.6-luna`` (OpenAI)
- ``gpt-5.6-terra`` (OpenAI)
- ``gpt-image-1`` (OpenAI)
- ``gpt-image-1.5`` (OpenAI)
- ``gpt-image-2`` (OpenAI)
- ``gpt-oss:20b`` (OpenAI - via Ollama and HuggingFace Router)
- ``gpt-oss:120b`` (OpenAI - via Ollama and HuggingFace Router)
- ``gpt-realtime`` (OpenAI, real-time)
- ``gpt-realtime-2.1`` (OpenAI, real-time)
- ``gpt-realtime-2.1-mini`` (OpenAI, real-time)
- ``grok-2-image-1212`` (xAI)
- ``grok-2-vision`` (xAI)
- ``grok-3-mini`` (xAI)
- ``grok-3-mini-fast`` (xAI)
- ``grok-4.3`` (xAI)
- ``grok-4.5`` (xAI)
- ``grok-4.6`` (xAI)
- ``grok-imagine-image`` (xAI)
- ``grok-imagine-image-quality-latest`` (xAI)
- ``grok-imagine-video`` (xAI)
- ``grok-imagine-video-1.5`` (xAI)
- ``imagen-4.0-generate-001`` (Google)
- ``llama2-uncensored`` (Ollama)
- ``llama3.1`` (Ollama)
- ``llama3.1:70b`` (Ollama)
- ``llama3.3:70b`` (Ollama)
- ``mistral`` (Ollama)
- ``mistral-large`` (Ollama)
- ``mistral-small3.1`` (Ollama)
- ``nano-banana-pro-preview`` (Google)
- ``o1`` (OpenAI)
- ``o1-pro`` (OpenAI)
- ``o3`` (OpenAI)
- ``o3-deep-research`` (OpenAI)
- ``o3-mini`` (OpenAI)
- ``o3-pro`` (OpenAI)
- ``o4-mini`` (OpenAI)
- ``o4-mini-deep-research`` (OpenAI)
- ``qwen2:7b`` (Ollama)
- ``qwen2.5-coder:7b`` (Ollama)
- ``qwen3:8b`` (Ollama)
- ``qwen3:30b-a3b`` (Ollama)
- ``sonar`` (Perplexity)
- ``sonar-deep-research`` (Perplexity)
- ``sonar-pro`` (Perplexity)
- ``sonar-reasoning-pro`` (Perplexity)
- ``sora-2`` (OpenAI)
- ``sora-2-pro`` (OpenAI)
- ``veo-3.1-fast-generate-preview`` (Google)
- ``veo-3.1-generate-preview`` (Google)
- ``veo-3.1-lite-generate-preview`` (Google)

All models are specified in the configuration file ``models.json``, which you can customize. 
This file is located in your working directory. You can add new models provided directly by ``OpenAI API`` (or compatible), ``Google Gen AI API``, ``Anthropic API``, ``xAI API``, and those supported by ``LlamaIndex`` or ``Ollama`` to this file. LlamaIndex-specific configuration is stored in the ``llama_index`` key.

You can import new models by manually editing ``models.json`` or by using the model importer in the ``Config -> Models -> Import`` menu.

.. tip::
    The models on the list are sorted by provider, not by manufacturer. A model from a particular manufacturer may be available through different providers (e.g., OpenAI models can be provided by the ``OpenAI API`` or by ``OpenRouter``). If you want to use a specific model through a particular provider, you need to configure the provider in ``Config -> Models -> Edit``, or import it directly via ``Config -> Models -> Import``.

.. tip::
    Anthropic and Deepseek API providers use VoyageAI for embeddings (Chat with Files and attachments RAG), so you must also configure the Voyage API key if you want to use embeddings from these providers.

Adding a custom model
---------------------

You can add your own models. See the section ``Extending PyGPT / Adding a new model`` for more info.

There is built-in support for those LLM providers:

* ``Anthropic``
* ``Azure OpenAI`` (native SDK)
* ``Deepseek API``
* ``Eden AI``
* ``Forge``
* ``Google`` (native SDK)
* ``HuggingFace API``
* ``HuggingFace Router`` (wrapper for OpenAI compatible ChatCompletions)
* ``LiteLLM``
* ``Local models`` (OpenAI API compatible)
* ``Mistral AI``
* ``Ollama``
* ``OpenAI`` (native SDK)
* ``OpenRouter``
* ``Perplexity``
* ``xAI`` (native SDK)

Per-model API base and API key
------------------------------

The Models Editor provides two optional fields in ``Advanced`` settings, directly after ``Tool calls``:

* ``API base`` - model-specific API base URL.
* ``API key`` - model-specific API key.

When these fields are non-empty, normal OpenAI-compatible Chat requests use them instead of the
provider/global API endpoint or key for that model. For the ``Local models (OpenAI API compatible)``
provider, the same values are also passed to the LlamaIndex ``OpenAILike`` wrapper
(``API base`` -> ``api_base``, ``API key`` -> ``api_key``).

Leave either field empty to keep the normal provider/global value for that field. This is especially
useful when multiple local/OpenAI-compatible servers are configured at the same time, because each model
can point to its own server without changing the global OpenAI configuration.

LlamaIndex ``**kwargs`` and ``ENV`` fields remain available for provider-specific advanced parameters.
Built-in provider wrappers normally reuse the API keys configured in ``Config -> Settings -> API Keys``
when an explicit key is not supplied in the model's LlamaIndex arguments.

How to use local or non-GPT models
----------------------------------

Llama 3, Mistral, DeepSeek, Qwen, gpt-oss, and other local models
``````````````````````````````````````````````````````````````````

How to use locally installed Llama 3, DeepSeek, Mistral, etc. models:

1) Choose a working mode: ``Chat`` or ``Chat with Files``.

2) On the models list - select, edit, or add a new model (with ``ollama`` provider). You can edit the model settings through the menu ``Config -> Models -> Edit``, then configure the model parameters in the ``advanced`` section.

3) Download and install Ollama from here: https://github.com/ollama/ollama

For example, on Linux:

.. code-block:: sh

    $ curl -fsSL https://ollama.com/install.sh | sh

4) Run the model (e.g. Llama 3) locally on your machine. For example, on Linux:

.. code-block:: sh

    $ ollama run llama3.1

5) Return to PyGPT and select the correct model from models list to chat with selected model using Ollama running locally.

**Example available models:**

- ``llama3.1``
- ``codellama``
- ``mistral``
- ``llama2-uncensored``
- ``deepseek-r1``

etc.

You can add more models by editing the models list.

**Real-time importer**

You can also import models in real-time from a running Ollama instance using the ``Config -> Models -> Import...`` tool.

**Custom Ollama endpoint**

The default endpoint for Ollama is: http://localhost:11434

You can change it globally by setting the environment variable ``OLLAMA_API_BASE`` in ``Settings -> General -> Advanced -> Application environment``.

You can also change the "base_url" for a specific model in its configuration:

``Config -> Models -> Edit``, then in the ``Advanced -> [LlamaIndex] ENV Vars`` section add the variable:

NAME: ``OLLAMA_API_BASE``
VALUE: ``http://my_endpoint.com:11434``

**List of all models supported by Ollama:**

https://ollama.com/library

https://github.com/ollama/ollama

**IMPORTANT:** Remember to define the correct model name in the **kwargs list in the model settings.

Using local embeddings
```````````````````````
Refer to: https://docs.llamaindex.ai/en/stable/examples/embeddings/ollama_embedding/

You can use an Ollama instance for embeddings. Simply select the ``ollama`` provider in:

.. code-block:: sh

    Config -> Settings -> Indexes / LlamaIndex -> Embeddings -> Embeddings provider

Define parameters like model name and Ollama base URL in the Embeddings provider **kwargs list, e.g.:

- name: ``model_name``, value: ``llama3.1``, type: ``str``

- name: ``base_url``, value: ``http://localhost:11434``, type: ``str``


Provider configuration for LlamaIndex
````````````````````````````````````````

Built-in LlamaIndex wrappers use the provider selected in the model configuration. In most cases the
provider API key is read automatically from ``Config -> Settings -> API Keys`` when it is not supplied
explicitly in ``Advanced -> [LlamaIndex] LLM provider extra **kwargs``.

Typical model configuration therefore only needs the model name in LlamaIndex arguments. Provider-specific
arguments can still be added when required by a custom endpoint or integration.

Examples:

* ``Google`` uses the configured Google API key by default.
* ``Anthropic`` uses the configured Anthropic API key by default.
* ``xAI`` uses the configured xAI API key and endpoint by default.
* ``Mistral AI`` uses the configured Mistral API key by default.
* ``Perplexity`` uses the configured Perplexity API key by default.
* ``HuggingFace API`` uses the configured HuggingFace token by default.
* ``DeepSeek`` and ``Anthropic`` use the configured VoyageAI key for their default embeddings integration.

For ``Local models (OpenAI API compatible)``, prefer the per-model ``API base`` and ``API key`` fields
described above. Advanced LlamaIndex arguments can still be used for options such as ``is_chat_model``,
``context_window``, or backend-specific parameters.
