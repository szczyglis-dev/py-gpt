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

Handling LLMs with Langchain is implemented through separated wrappers. This allows for the addition of support for any provider and model available via Langchain. All built-in wrappers for the models and its providers  are placed in the ``llm`` directory.

These wrappers are loaded into the application during startup using ``launcher.add_llm()`` method:

.. code-block:: python

    # app.py

    from pygpt_net.llm.OpenAI import OpenAILLM
    from pygpt_net.llm.AzureOpenAI import AzureOpenAILLM
    from pygpt_net.llm.Anthropic import AnthropicLLM
    from pygpt_net.llm.HuggingFace import HuggingFaceLLM
    from pygpt_net.llm.Llama2 import Llama2LLM
    from pygpt_net.llm.Ollama import OllamaLLM

    def run(
        plugins=None, 
        llms=None, 
        vector_stores=vector_stores
    ):
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

- Provide a list of LLM wrapper instances as the second argument when initializing the custom app launcher.

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


To integrate your own model or provider into **PyGPT**, you can reference the sample classes located in the ``llm`` directory of the application. These samples can act as an example for your custom class. Ensure that your custom wrapper class includes two essential methods: ``chat`` and ``completion``. These methods should return the respective objects required for the model to operate in ``chat`` and ``completion`` modes.


Adding custom Vector Store providers
------------------------------------

**From version 2.0.114 you can also register your own Vector Store provider**:

.. code-block:: python

    # app.y

    # vector stores
    from pygpt_net.core.idx.storage.chroma import ChromaProvider as ChromaVectorStore
    from pygpt_net.core.idx.storage.elasticsearch import ElasticsearchProvider as ElasticsearchVectorStore
    from pygpt_net.core.idx.storage.pinecode import PinecodeProvider as PinecodeVectorStore
    from pygpt_net.core.idx.storage.redis import RedisProvider as RedisVectorStore
    from pygpt_net.core.idx.storage.simple import SimpleProvider as SimpleVectorStore

    def run(plugins: list = None,
            llms: list = None,
            vector_stores: list = None
        ):

To register your custom vector store provider just register it by passing provier instance to ``vector_stores`` list:

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