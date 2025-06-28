Models
======

Built-in models
---------------

PyGPT has built-in support for models (as of 2025-06-27):

- ``bielik-11b-v2.3-instruct:Q4_K_M``
- ``chatgpt-4o-latest``
- ``claude-3-5-sonnet-20240620``
- ``claude-3-7-sonnet``
- ``claude-3-opus``
- ``claude-3-opus``
- ``claude-opus-4-0``
- ``claude-sonnet-4-0``
- ``codellama``
- ``dall-e-2``
- ``dall-e-3``
- ``deepseek-chat``
- ``deepseek-r1:1.5b``
- ``deepseek-r1:14b``
- ``deepseek-r1:32b``
- ``deepseek-r1:670b``
- ``deepseek-r1:7b``
- ``deepseek-r1:671b``
- ``deepseek-reasoner``
- ``deepseek-v3:671b``
- ``gemini-1.5-flash``
- ``gemini-1.5-pro``
- ``gemini-2.0-flash-exp``
- ``gemini-2.5-flash``
- ``gemini-2.5-pro``
- ``gpt-3.5-turbo``
- ``gpt-3.5-turbo-1106``
- ``gpt-3.5-turbo-16k``
- ``gpt-3.5-turbo-instruct``
- ``gpt-4``
- ``gpt-4-0125-preview``
- ``gpt-4-1106-preview``
- ``gpt-4-32k``
- ``gpt-4-turbo``
- ``gpt-4-turbo-2024-04-09``
- ``gpt-4-turbo-preview``
- ``gpt-4-vision-preview``
- ``gpt-4.1``
- ``gpt-4.1-mini``
- ``gpt-4.5-preview``
- ``gpt-4o``
- ``gpt-4o-2024-11-20``
- ``gpt-4o-audio-preview``
- ``gpt-4o-mini``
- ``grok-3``
- ``grok-3-fast``
- ``grok-3-mini``
- ``grok-3-mini-fast``
- ``llama2-uncensored``
- ``llama3.1``
- ``llama3.1:405b``
- ``llama3.1:70b``
- ``mistral``
- ``mistral-large``
- ``o1``
- ``o1-mini``
- ``o1-pro``
- ``o3``
- ``o3-mini``
- ``o3-pro``
- ``qwen:7b``
- ``qwen2:7b``
- ``qwen2.5-coder:7b``
- ``qwen3:8b``
- ``qwen3:30b-a3b``
- ``r1`` (Perplexity)
- ``sonar`` (Perplexity)
- ``sonar-deep-research`` (Perplexity)
- ``sonar-pro`` (Perplexity)
- ``sonar-reasoning`` (Perplexity)
- ``sonar-reasoning-pro`` (Perplexity)

All models are specified in the configuration file ``models.json``, which you can customize. 
This file is located in your working directory. You can add new models provided directly by ``OpenAI API``
and those supported by ``LlamaIndex`` to this file. Configuration for LlamaIndex in placed in``llama_index`` key.

Adding a custom model
---------------------

You can add your own models. See the section ``Extending PyGPT / Adding a new model`` for more info.

There is built-in support for those LLM providers:

* ``Anthropic`` (anthropic)
* ``Azure OpenAI`` (azure_openai)
* ``Deepseek API`` (deepseek_api)
* ``Google`` (google)
* ``HuggingFace`` (huggingface)
* ``Local models`` (OpenAI API compatible)
* ``Ollama`` (ollama)
* ``OpenAI`` (openai)
* ``Perplexity`` (perplexity)
* ``xAI`` (x_ai)

How to use local or non-GPT models
----------------------------------

Llama 3, Mistral, DeepSeek, and other local models
```````````````````````````````````````````````````

How to use locally installed Llama 3 or Mistral models:

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

You can also import models in real-time from a running Ollama instance using the ``Config -> Models -> Import from Ollama`` tool.

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

    Config -> Settings -> Indexes (LlamaIndex) -> Embeddings -> Embeddings provider

Define parameters like model name and Ollama base URL in the Embeddings provider **kwargs list, e.g.:

- name: ``model_name``, value: ``llama3.1``, type: ``str``

- name: ``base_url``, value: ``http://localhost:11434``, type: ``str``


Google Gemini and Anthropic Claude
``````````````````````````````````
To use ``Gemini`` or ``Claude`` models, select the ``Chat with Files`` mode in PyGPT and select a predefined model.
Remember to configure the required parameters like API keys in the model ENV config fields.

**Google Gemini**

Required ENV:

- GOOGLE_API_KEY

Required **kwargs:

- model

**Anthropic Claude**

Required ENV:

- ANTHROPIC_API_KEY

Required **kwargs:

- model
