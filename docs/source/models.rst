Models
======

Built-in models
---------------

PyGPT has built-in support for models (as of 2025-07-26):

- ``bielik-11b-v2.3-instruct:Q4_K_M`` (Ollama)
- ``chatgpt-4o-latest`` (OpenAI)
- ``claude-3-5-sonnet-20240620`` (Anthropic)
- ``claude-3-7-sonnet`` (Anthropic)
- ``claude-3-opus`` (Anthropic)
- ``claude-3-opus`` (Anthropic)
- ``claude-opus-4-0`` (Anthropic)
- ``claude-sonnet-4-0`` (Anthropic)
- ``codellama`` (Ollama)
- ``codex-mini`` (OpenAI)
- ``dall-e-2`` (OpenAI)
- ``dall-e-3`` (OpenAI)
- ``deepseek-chat`` (DeepSeek)
- ``deepseek-r1:1.5b`` (Ollama)
- ``deepseek-r1:14b`` (Ollama)
- ``deepseek-r1:32b`` (Ollama)
- ``deepseek-r1:7b`` (Ollama)
- ``deepseek-reasoner`` (DeepSeek)
- ``gemini-1.5-flash`` (Google)
- ``gemini-1.5-pro`` (Google)
- ``gemini-2.0-flash-exp`` (Google)
- ``gemini-2.5-flash`` (Google)
- ``gemini-2.5-pro`` (Google)
- ``gpt-3.5-turbo`` (OpenAI)
- ``gpt-3.5-turbo-16k`` (OpenAI)
- ``gpt-3.5-turbo-instruct`` (OpenAI)
- ``gpt-4`` (OpenAI)
- ``gpt-4-32k`` (OpenAI)
- ``gpt-4-turbo`` (OpenAI)
- ``gpt-4-vision-preview`` (OpenAI)
- ``gpt-4.1`` (OpenAI)
- ``gpt-4.1-mini`` (OpenAI)
- ``gpt-4.1-nano`` (OpenAI)
- ``gpt-4o`` (OpenAI)
- ``gpt-4o-audio-preview`` (OpenAI)
- ``gpt-4o-mini`` (OpenAI)
- ``gpt-5`` (OpenAI)
- ``gpt-5-mini`` (OpenAI)
- ``gpt-5-nano`` (OpenAI)
- ``gpt-image-1`` (OpenAI)
- ``gpt-oss:20b`` (OpenAI - via Ollama and HuggingFace Router)
- ``gpt-oss:120b`` (OpenAI - via Ollama and HuggingFace Router)
- ``grok-2-vision`` (xAI)
- ``grok-3`` (xAI)
- ``grok-3-fast`` (xAI)
- ``grok-3-mini`` (xAI)
- ``grok-3-mini-fast`` (xAI)
- ``grok-4`` (xAI)
- ``llama2-uncensored`` (Ollama)
- ``llama3.1`` (Ollama)
- ``llama3.1:70b`` (Ollama)
- ``mistral`` (Ollama)
- ``mistral-large`` (Ollama)
- ``mistral-small3.1`` (Ollama)
- ``o1`` (OpenAI)
- ``o1-mini`` (OpenAI)
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
- ``r1`` (Perplexity)
- ``sonar`` (Perplexity)
- ``sonar-deep-research`` (Perplexity)
- ``sonar-pro`` (Perplexity)
- ``sonar-reasoning`` (Perplexity)
- ``sonar-reasoning-pro`` (Perplexity)

All models are specified in the configuration file ``models.json``, which you can customize. 
This file is located in your working directory. You can add new models provided directly by ``OpenAI API`` (or compatible) and those supported by ``LlamaIndex`` or ``Ollama`` to this file. Configuration for LlamaIndex in placed in ``llama_index`` key.

**Tip**: Anthropic and Deepseek API providers use VoyageAI for embeddings, so you must also configure the Voyage API key if you want to use embeddings from these providers.

Adding a custom model
---------------------

You can add your own models. See the section ``Extending PyGPT / Adding a new model`` for more info.

There is built-in support for those LLM providers:

* ``Anthropic``
* ``Azure OpenAI``
* ``Deepseek API``
* ``Google``
* ``HuggingFace API``
* ``HuggingFace Router`` (wrapper for OpenAI compatible ChatCompletions)
* ``Local models`` (OpenAI API compatible)
* ``Mistral AI``
* ``Ollama``
* ``OpenAI``
* ``OpenRouter``
* ``Perplexity``
* ``xAI``

How to use local or non-GPT models
----------------------------------

Llama 3, Mistral, DeepSeek, and other local models
```````````````````````````````````````````````````

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


Google Gemini, Anthropic Claude, xAI Grok, etc.
```````````````````````````````````````````````
If you want to use non-OpenAI models in ``Chat with Files`` and ``Agents (LlamaIndex)`` modes, then remember to configure the required parameters like API keys in the model config fields. ``Chat`` mode works via OpenAI SDK (compatible API), ``Chat with Files`` and ``Agents (LlamaIndex)`` modes works via LlamaIndex.

**Google Gemini**

Required ENV:

- GOOGLE_API_KEY = {api_key_google}

Required **kwargs:

- model

**Anthropic Claude**

Required ENV:

- ANTHROPIC_API_KEY = {api_key_anthropic}

Required **kwargs:

- model

**xAI Grok** (Chat mode only)

Required ENV:

- OPENAI_API_KEY = {api_key_xai}
- OPENAI_API_BASE = {api_endpoint_xai}

Required **kwargs:

- model

**Mistral AI**

Required ENV:

- MISTRAL_API_KEY = {api_key_mistral}

Required **kwargs:

- model

**Perplexity**

Required ENV:

- PPLX_API_KEY = {api_key_perplexity}

Required **kwargs:

- model

**HuggingFace API** (Chat with Files mode only)

Required ENV:

- HUGGING_FACE_TOKEN = {api_key_hugging_face}

Required **kwargs:

- model_name | model
- token
- provider = auto


