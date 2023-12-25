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

    "gpt-4-1106-preview": {
        "id": "gpt-4-1106-preview",
        "name": "gpt-4-turbo-1106",
        "mode": [
            "chat",
            "assistant",
            "langchain"
        ],
        "langchain": {
                "provider": "openai",
                "mode": [
                    "chat"
                ],
                "args": {
                    "model_name": "gpt-4-1106-preview"
                }
            },
            "ctx"
        "ctx": 128000,
        "tokens": 4096
    },
    "google/flan-t5-xxl": {
        "id": "google/flan-t5-xxl",
        "name": "Google - flan-t5-xxl",
        "mode": [
            "langchain"
        ],
        "langchain": {
            "provider": "huggingface",
            "mode": [
                "chat"
            ],
            "args": {
                "repo_id": "google/flan-t5-xxl"
            },
            "api_key": "XXXXXXXXXXXXXXXXXXXXXX"
        },
        "ctx": 4096,
        "tokens": 4096
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

    def run(plugins=None, llms=None):
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

    run(plugins, llms)  # <-- LLMs as the second argument


To integrate your own model or provider into **PyGPT**, you can reference the sample classes located in the ``llm`` directory of the application. These samples can act as an example for your custom class. Ensure that your custom wrapper class includes two essential methods: ``chat`` and ``completion``. These methods should return the respective objects required for the model to operate in ``chat`` and ``completion`` modes.