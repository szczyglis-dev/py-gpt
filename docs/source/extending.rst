Extending PyGPT
===============

Quick start
------------

You can create your own extension for **PyGPT** at any time. 

PyGPT can be extended with:

* custom models
* custom plugins
* custom LLM wrappers
* custom vector store providers
* custom data loaders
* custom audio input providers
* custom audio output providers
* custom web search engine providers
* custom agents (LlamaIndex or OpenAI Agents)

**Examples (tutorial files)** 

See the ``examples`` directory in this repository with examples of custom launcher, plugin, vector store, LLM provider and data loader:

* ``examples/custom_launcher.py``
* ``examples/example_audio_input.py``
* ``examples/example_audio_output.py``
* ``examples/example_data_loader.py``
* ``examples/example_llm.py``
* ``examples/example_plugin.py``
* ``examples/example_vector_store.py``
* ``examples/example_web_search.py``

These example files can be used as a starting point for creating your own extensions for **PyGPT**.

Extending PyGPT with custom plugins, LLMs wrappers and vector stores:

- You can pass custom plugin instances, LLMs wrappers and vector store providers to the launcher.

- This is useful if you want to extend PyGPT with your own plugins, vectors storage and LLMs.

To register custom plugins:

- Pass a list with the plugin instances as ``plugins`` keyword argument.

To register custom LLMs wrappers:

- Pass a list with the LLMs wrappers instances as ``llms`` keyword argument.

To register custom vector store providers:

- Pass a list with the vector store provider instances as ``vector_stores`` keyword argument.

To register custom data loaders:

- Pass a list with the data loader instances as ``loaders`` keyword argument.

To register custom audio input providers:

- Pass a list with the audio input provider instances as ``audio_input`` keyword argument.

To register custom audio output providers:

- Pass a list with the audio output provider instances as ``audio_output`` keyword argument.

To register custom web providers:

- Pass a list with the web provider instances as ``web`` keyword argument.

To register an agent:

- Pass a list with the agent instances as ``agents`` keyword argument.


Adding a custom model
---------------------

To add a new model using the OpenAI API, or LlamaIndex wrapper, use the editor in ``Config -> Models`` or manually edit the ``models.json`` file by inserting the model's configuration details. If you are adding a model via LlamaIndex, ensure to include the model's name, its supported modes (either ``chat``, ``completion``, or both), the LLM provider (such as ``OpenAI`` or ``HuggingFace``), and, if you are using an external API-based model, an optional ``API KEY`` along with any other necessary environment settings.

Example of models configuration - ``%WORKDIR%/models.json``:

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
        "provider": "openai",
        "llama_index": {
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


.. tip::
    ``{api_key}`` in ``models.json`` is a placeholder for the main OpenAI API KEY from the settings. It will be replaced by the configured key value.

There is built-in support for those LLM providers:

* ``Anthropic``
* ``Azure OpenAI``
* ``Deepseek API``
* ``Google``
* ``HuggingFace``
* ``Local models`` (OpenAI API compatible)
* ``Ollama``
* ``OpenAI``
* ``OpenRouter``
* ``Perplexity``
* ``xAI``


Adding a custom plugin
-------------------

Creating Your Own Plugin
````````````````````````
You can create your own plugin for **PyGPT**. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the ``plugin`` directory - you can use them as coding examples for your own plugins.

**Examples (tutorial files)** 

See the example plugin in this ``examples`` directory:

- ``examples/example_plugin.py``

These example file can be used as a starting point for creating your own plugin for **PyGPT**.

To register a custom plugin:

- Create a custom launcher for the app.

- Pass a list with the custom plugin instances as ``plugins`` keyword argument.

**Example of a custom launcher:**

.. code-block:: python

   # custom_launcher.py

   from pygpt_net.app import run
   from plugins import CustomPlugin, OtherCustomPlugin
   from llms import CustomLLM
   from vector_stores import CustomVectorStore

   plugins = [
       CustomPlugin(),
       OtherCustomPlugin(),
   ]
   llms = [
       CustomLLM(),
   ]
   vector_stores = [
       CustomVectorStore(),
   ]

   run(
       plugins=plugins,
       llms=llms,
       vector_stores=vector_stores,
   )

Handling events
```````````````

In the plugin, you can receive and modify dispatched events.
To do this, create a method named ``handle(self, event, *args, **kwargs)`` and handle the received events like here:

.. code-block:: python

   # custom_plugin.py

   from pygpt_net.core.events import Event
   

   def handle(self, event: Event, *args, **kwargs):
       """
       Handle dispatched events

       :param event: event object
       """
       name = event.name
       data = event.data
       ctx = event.ctx

       if name == Event.INPUT_BEFORE:
           self.some_method(data['value'])
       elif name == Event.CTX_BEGIN:
           self.some_other_method(ctx)
       else:
           # ...

List of Events
```````````````

Event names are defined in ``Event`` class in ``pygpt_net.core.events``.

Syntax: ``event name`` - triggered on, ``event data`` *(data type)*:

- ``AI_NAME`` - when preparing an AI name, ``data['value']`` *(string, name of the AI assistant)*

- ``AGENT_PROMPT`` - on agent prompt in eval mode, ``data['value']`` *(string, prompt)*

- ``AUDIO_INPUT_RECORD_START`` - start audio input recording

- ``AUDIO_INPUT_RECORD_STOP`` -  stop audio input recording

- ``AUDIO_INPUT_RECORD_TOGGLE`` - toggle audio input recording

- ``AUDIO_INPUT_TRANSCRIBE`` - on audio file transcribe, ``data['path']`` *(string, path to audio file)*

- ``AUDIO_INPUT_STOP`` - force stop audio input

- ``AUDIO_INPUT_TOGGLE`` - when speech input is enabled or disabled, ``data['value']`` *(bool, True/False)*

- ``AUDIO_OUTPUT_STOP`` - force stop audio output

- ``AUDIO_OUTPUT_TOGGLE`` - when speech output is enabled or disabled, ``data['value']`` *(bool, True/False)*

- ``AUDIO_READ_TEXT`` - on text read using speech synthesis, ``data['text']`` *(str, text to read)*

- ``CMD_EXECUTE`` - when a command is executed, ``data['commands']`` *(list, commands and arguments)*

- ``CMD_INLINE`` - when an inline command is executed, ``data['commands']`` *(list, commands and arguments)*

- ``CMD_SYNTAX`` - when appending syntax for commands, ``data['prompt'], data['syntax']`` *(string, list, prompt and list with commands usage syntax)*

- ``CMD_SYNTAX_INLINE`` - when appending syntax for commands (inline mode), ``data['prompt'], data['syntax']`` *(string, list, prompt and list with commands usage syntax)*

- ``CTX_AFTER`` - after the context item is sent, ``ctx``

- ``CTX_BEFORE`` - before the context item is sent, ``ctx``

- ``CTX_BEGIN`` - when context item create, ``ctx``

- ``CTX_END`` - when context item handling is finished, ``ctx``

- ``CTX_SELECT`` - when context is selected on list, ``data['value']`` *(int, ctx meta ID)*

- ``DISABLE`` - when the plugin is disabled, ``data['value']`` *(string, plugin ID)*

- ``ENABLE`` - when the plugin is enabled, ``data['value']`` *(string, plugin ID)*

- ``FORCE_STOP`` - on force stop plugins

- ``INPUT_BEFORE`` - upon receiving input from the textarea, ``data['value']`` *(string, text to be sent)*

- ``MODE_BEFORE`` - before the mode is selected ``data['value'], data['prompt']`` *(string, string, mode ID)*

- ``MODE_SELECT`` - on mode select ``data['value']`` *(string, mode ID)*

- ``MODEL_BEFORE`` - before the model is selected ``data['value']`` *(string, model ID)*

- ``MODEL_SELECT`` - on model select ``data['value']`` *(string, model ID)*

- ``PLUGIN_SETTINGS_CHANGED`` - on plugin settings update (saving settings)

- ``PLUGIN_OPTION_GET`` - on request for plugin option value ``data['name'], data['value']`` *(string, any, name of requested option, value)*

- ``POST_PROMPT`` - after preparing a system prompt, ``data['value']`` *(string, system prompt)*

- ``POST_PROMPT_ASYNC`` - after preparing a system prompt, just before request in async thread, ``data['value']`` *(string, system prompt)*

- ``POST_PROMPT_END`` - after preparing a system prompt, just before request in async thread, at the very end ``data['value']`` *(string, system prompt)*

- ``PRE_PROMPT`` - before preparing a system prompt, ``data['value']`` *(string, system prompt)*

- ``SYSTEM_PROMPT`` - when preparing a system prompt, ``data['value']`` *(string, system prompt)*

- ``TOOL_OUTPUT_RENDER`` - when rendering extra content from tools from plugins, ``data['content']`` *(string, content)*

- ``UI_ATTACHMENTS`` - when the attachment upload elements are rendered, ``data['value']`` *(bool, show True/False)*

- ``UI_VISION`` - when the vision elements are rendered, ``data['value']`` *(bool, show True/False)*

- ``USER_NAME`` - when preparing a user's name, ``data['value']`` *(string, name of the user)*

- ``USER_SEND`` - just before the input text is sent, ``data['value']`` *(string, input text)*


You can stop the propagation of a received event at any time by setting ``stop`` to `True`:

.. code-block:: python

   event.stop = True


Events flow can be debugged by enabling the option ``Config -> Settings -> Developer -> Log and debug events``.


Adding a custom LLM provider
----------------------------

Handling LLMs with LlamaIndex is implemented through separated wrappers. This allows for the addition of support for any provider and model available via LlamaIndex. All built-in wrappers for the models and its providers  are placed in the ``pygpt_net.provider.llms``.

These wrappers are loaded into the application during startup using ``launcher.add_llm()`` method:

.. code-block:: python

    # app.py

    from pygpt_net.provider.llms.openai import OpenAILLM
    from pygpt_net.provider.llms.azure_openai import AzureOpenAILLM
    from pygpt_net.provider.llms.anthropic import AnthropicLLM
    from pygpt_net.provider.llms.hugging_face import HuggingFaceLLM
    from pygpt_net.provider.llms.ollama import OllamaLLM
    from pygpt_net.provider.llms.google import GoogleLLM

    def run(**kwargs):
        """Runs the app."""
        # Initialize the app
        launcher = Launcher()
        launcher.init()

        # Register plugins
        ...

        # Register langchain and llama-index LLMs wrappers
        launcher.add_llm(OpenAILLM())
        launcher.add_llm(AzureOpenAILLM())
        launcher.add_llm(AnthropicLLM())
        launcher.add_llm(HuggingFaceLLM())
        launcher.add_llm(OllamaLLM())
        launcher.add_llm(GoogleLLM())

        # Launch the app
        launcher.run()

To add support for providers not included by default, you can create your own wrapper that returns a custom model to the application and then pass this custom wrapper to the launcher.

Extending PyGPT with custom plugins and LLM wrappers is straightforward:

- Pass instances of custom plugins and LLM wrappers directly to the launcher.

To register custom LLM wrappers:

- Provide a list of LLM wrapper instances as the ``llms`` keyword argument when initializing the custom app launcher.

**Example:**

.. code-block:: python

    # custom_launcher.py

    from pygpt_net.app import run
    from plugins import CustomPlugin, OtherCustomPlugin
    from llms import CustomLLM

    plugins = [
        CustomPlugin(),
        OtherCustomPlugin(),
    ]
    llms = [
        CustomLLM(),  # <--- custom LLM provider (wrapper)
    ]
    vector_stores = []

    run(
        plugins=plugins, 
        llms=llms, 
        vector_stores=vector_stores,
    )

**Examples (tutorial files)** 

See the ``examples`` directory in this repository with examples of custom launcher, plugin, vector store, LLM provider and data loader:

* ``examples/custom_launcher.py``
* ``examples/example_audio_input.py``
* ``examples/example_audio_output.py``
* ``examples/example_data_loader.py``
* ``examples/example_llm.py``  <-- use it as an example
* ``examples/example_plugin.py``
* ``examples/example_vector_store.py``
* ``examples/example_web_search.py``

These example files can be used as a starting point for creating your own extensions for **PyGPT**.

To integrate your own model or provider into **PyGPT**, you can also reference the classes located in the ``pygpt_net.provider.llms``. These samples can act as an more complex example for your custom class. Ensure that your custom wrapper class includes two essential methods: ``chat`` and ``completion``. These methods should return the respective objects required for the model to operate in ``chat`` and ``completion`` modes.

Every single LLM provider (wrapper) inherits from ``BaseLLM`` class and can provide 2 components: provider for LlamaIndex, and provider for Embeddings.

Adding a custom vector store provider
-------------------------------------

You can create a custom vector store provider or data loader for your data and develop a custom launcher for the application. To register your custom vector store provider or data loader, simply register it by passing the vector store provider instance to ``vector_stores`` keyword argument and loader instance in the ``loaders`` keyword argument:

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

    # custom_launcher.py

    from pygpt_net.app import run
    from plugins import CustomPlugin, OtherCustomPlugin
    from llms import CustomLLM
    from vector_stores import CustomVectorStore

    plugins = [
        CustomPlugin(),
        OtherCustomPlugin(),
    ]
    llms = [
        CustomLLM(),
    ]
    vector_stores = [
        CustomVectorStore(),  # <--- custom vector store provider
    ]

    run(
        plugins=plugins,
        llms=llms,
        vector_stores=vector_stores,
    )


The vector store provider must be an instance of ``pygpt_net.provider.vector_stores.base.BaseStore``. 
You can review the code of the built-in providers in ``pygpt_net.provider.vector_stores`` and use them as examples when creating a custom provider.


Adding a custom data loader
---------------------------


.. code-block:: python

    # custom_launcher.py

    from pygpt_net.app import run
    from plugins import CustomPlugin, OtherCustomPlugin
    from llms import CustomLLM
    from vector_stores import CustomVectorStore
    from loaders import CustomLoader

    plugins = [
        CustomPlugin(),
        OtherCustomPlugin(),
    ]
    llms = [
        CustomLLM(),
    ]
    vector_stores = [
        CustomVectorStore(),
    ]
    loaders = [
        CustomLoader(),  # <---- custom data loader
    ]

    run(
        plugins=plugins,
        llms=llms,
        vector_stores=vector_stores,  # <--- list with custom vector store providers
        loaders=loaders  # <--- list with custom data loaders
    )


The data loader must be an instance of ``pygpt_net.provider.loaders.base.BaseLoader``. 
You can review the code of the built-in loaders in ``pygpt_net.provider.loaders`` and use them as examples when creating a custom loader.