Managing models
===============

All models are specified in the configuration file ``models.json``, which you can customize. 
This file is located in your working directory. You can add new models provided directly by ``OpenAI API``
and those supported by ``Langchain`` to this file. Configuration for Langchain wrapper is placed in ``langchain`` key.

Adding custom LLMs via Langchain
--------------------------------

To add a new model using the Langchain wrapper in **PyGPT**, insert the model's configuration details into the ``models.json`` file. This should include the model's name, its supported modes (either ``chat``, ``completion``, or both), the LLM provider (which can be either e.g. ``OpenAI`` or ``HuggingFace``), and, if you are using a ``HuggingFace`` model, an optional ``API KEY``.

Example of models configuration - ``models.json``:

.. code-block:: json

    "gpt-3.5-turbo": {
        "id": "gpt-3.5-turbo",
        "name": "gpt-3.5-turbo",
        "mode": [
            "chat",
            "assistant",
            "langchain",
            "llama_index"
        ],
        "langchain": {
            "provider": "openai",
            "mode": [
                "chat"
            ],
            "args": [
                {
                    "name": "model_name",
                    "value": "gpt-3.5-turbo",
                    "type": "str"
                }
            ],
            "env": [
                {
                    "name": "OPENAI_API_KEY",
                    "value": "{api_key}"
                }
            ]
        },
        "llama_index": {
            "provider": "openai",
            "mode": [
                "chat"
            ],
            "args": [
                {
                    "name": "model",
                    "value": "gpt-3.5-turbo",
                    "type": "str"
                }
            ],
            "env": [
                {
                    "name": "OPENAI_API_KEY",
                    "value": "{api_key}"
                }
            ]
        },
        "ctx": 4096,
        "tokens": 4096,
        "default": false
    },


There is bult-in support for those LLMs providers:


* OpenAI (openai)
* Azure OpenAI (azure_openai)
* HuggingFace (huggingface)
* Anthropic (anthropic)
* Llama 2 (llama2)
* Ollama (ollama)

Adding custom LLM providers
---------------------------

Handling LLMs with Langchain is implemented through separated wrappers. This allows for the addition of support for any provider and model available via Langchain. All built-in wrappers for the models and its providers  are placed in the ``pygpt_net.provider.llms``.

These wrappers are loaded into the application during startup using ``launcher.add_llm()`` method:

.. code-block:: python

    # app.py

    from pygpt_net.provider.llms.openai import OpenAILLM
    from pygpt_net.provider.llms.azure_openai import AzureOpenAILLM
    from pygpt_net.provider.llms.anthropic import AnthropicLLM
    from pygpt_net.provider.llms.hugging_face import HuggingFaceLLM
    from pygpt_net.provider.llms.llama import Llama2LLM
    from pygpt_net.provider.llms.ollama import OllamaLLM

    def run(**kwargs):
        """Runs the app."""
        # Initialize the app
        launcher = Launcher()
        launcher.init()

        # Register plugins
        ...

        # Register langchain LLMs wrappers
        launcher.add_llm(OpenAILLM())
        launcher.add_llm(AzureOpenAILLM())
        launcher.add_llm(AnthropicLLM())
        launcher.add_llm(HuggingFaceLLM())
        launcher.add_llm(Llama2LLM())
        launcher.add_llm(OllamaLLM())

        # Launch the app
        launcher.run()

To add support for providers not included by default, you can create your own wrapper that returns a custom model to the application and then pass this custom wrapper to the launcher.

Extending PyGPT with custom plugins and LLM wrappers is straightforward:

- Pass instances of custom plugins and LLM wrappers directly to the launcher.

To register custom LLM wrappers:

- Provide a list of LLM wrapper instances as the ``llms`` keyword argument when initializing the custom app launcher.

**Example:**

.. code-block:: python

    # my_launcher.py

    from pygpt_net.app import run
    from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
    from my_llms import MyCustomLLM

    plugins = [
        MyCustomPlugin(),
        MyOtherCustomPlugin(),
    ]
    llms = [
        MyCustomLLM(),
    ]
    vector_stores = []

    run(
        plugins=plugins, 
        llms=llms, 
        vector_stores=vector_stores
    )

**Examples (tutorial files)** 

See the ``examples`` directory in this repository with examples of custom launcher, plugin, vector store, LLM (Langchain and Llama-index) provider and data loader:

* ``examples/custom_launcher.py``
* ``examples/example_data_loader.py``
* ``examples/example_llm.py``
* ``examples/example_plugin.py``
* ``examples/example_vector_store.py``

These example files can be used as a starting point for creating your own extensions for **PyGPT**.

To integrate your own model or provider into **PyGPT**, you can also reference the classes located in the ``pygpt_net.provider.llms``. These samples can act as an more complex example for your custom class. Ensure that your custom wrapper class includes two essential methods: ``chat`` and ``completion``. These methods should return the respective objects required for the model to operate in ``chat`` and ``completion`` modes.


Adding custom Vector Store providers
------------------------------------

**From version 2.0.114 you can also register your own Vector Store provider**:

.. code-block:: python

    # app.py

    # vector stores
    from pygpt_net.provider.vector_stores.chroma import ChromaProvider
    from pygpt_net.provider.vector_stores.elasticsearch import ElasticsearchProvider
    from pygpt_net.provider.vector_stores.pinecode import PinecodeProvider
    from pygpt_net.provider.vector_stores.redis import RedisProvider
    from pygpt_net.provider.vector_stores.simple import SimpleProvider

    def run(**kwargs):
        # ...
        # register base vector store providers (llama-index)
        launcher.add_vector_store(ChromaProvider())
        launcher.add_vector_store(ElasticsearchProvider())
        launcher.add_vector_store(PinecodeProvider())
        launcher.add_vector_store(RedisProvider())
        launcher.add_vector_store(SimpleProvider())

        # register custom vector store providers (llama-index)
        vector_stores = kwargs.get('vector_stores', None)
        if isinstance(vector_stores, list):
            for store in vector_stores:
                launcher.add_vector_store(store)

        # ...

To register your custom vector store provider just register it by passing provider instance in ``vector_stores`` keyword argument:

.. code-block:: python

    # my_launcher.py

    from pygpt_net.app import run
    from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
    from my_llms import MyCustomLLM
    from my_vector_stores import MyCustomVectorStore

    plugins = [
        MyCustomPlugin(),
        MyOtherCustomPlugin(),
    ]
    llms = [
        MyCustomLLM(),
    ]
    vector_stores = [
        MyCustomVectorStore(),
    ]

    run(
        plugins=plugins,
        llms=llms,
        vector_stores=vector_stores
    )