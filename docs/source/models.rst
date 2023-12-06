Managing models
===============

All models are specified in the configuration file ``models.json``, which you can customize. 
This file is located in your work directory. You can add new models provided directly by ``OpenAI API``
and those supported by ``Langchain`` to this file. Configuration for Langchain wrapper is placed in ``langchain`` key.

Adding custom LLMs to Langchain
--------------------------------

If you wish to add a model and use it with the Langchain wrapper, simply insert the model configuration into `models.json`. 
You will need to provide the model name, the modes it operates in (either ``chat`` and/or ``completion``), 
the LLM provider (currently either ``OpenAI`` or ``HuggingFace``), and optionally an additional ``API KEY`` if you're using HuggingFace.

Example of models configuration - `models.json`:

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

Handling LLMs with Langchain is implemented through modules. This allows for the addition of support for any model available via Langchain. All built-in modules for models are included in the ``llm`` directory.

These modules are loaded into the application during startup using ``launcher.add_llm()`` method:

.. code-block:: python

    # app.py

    from .llm.OpenAI import OpenAILLM
    from .llm.AzureOpenAI import AzureOpenAILLM
    from .llm.Anthropic import AnthropicLLM
    from .llm.HuggingFace import HuggingFaceLLM
    from .llm.Llama2 import Llama2LLM
    from .llm.Ollama import OllamaLLM

    def run():
        """Runs the app."""
        # Initialize the app
        launcher = Launcher()
        launcher.init()

        # Register plugins
        ...

        # Register Langchain LLMs
        launcher.add_llm(OpenAILLM())
        launcher.add_llm(AzureOpenAILLM())
        launcher.add_llm(AnthropicLLM())
        launcher.add_llm(HuggingFaceLLM())
        launcher.add_llm(Llama2LLM())
        launcher.add_llm(OllamaLLM())

        # Launch the app
        launcher.run()

To add support for any model, simply create your own class that returns a custom model to the application and register your class in a custom launcher, like so:

.. code-block:: python

    # custom_launcher.py

    from my_llm import MyCustomLLM

    def run():
        """Runs the app."""
        # Initialize the app
        launcher = Launcher()
        launcher.init()

        # Register plugins
        ...

        # Register Langchain LLMs
        ...
        launcher.add_llm(MyCustomLLM())

        # Launch the app
        launcher.run()


If you want to create your own class with support for your model, look at the example classes included in the application in the ``llm`` directory - they can serve as a template. Each such custom wrapper must contain two methods: ``chat`` and ``completion``, which return the model's objects for ``chat`` and ``completion`` modes, respectively.