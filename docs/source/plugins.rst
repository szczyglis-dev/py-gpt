Plugins
=======

**PyGPT** can be enhanced with plugins to add new features.

The following plugins are currently available, and model can use them instantly:

* ``Audio Input`` - provides speech recognition.
* ``Audio Output`` - provides voice synthesis.
* ``Autonomous Mode (inline)`` - enables autonomous conversation (AI to AI), manages loop, and connects output back to input. This is the inline Agent mode.
* ``Chat with files (Llama-index, inline)`` - plugin integrates Llama-index storage in any chat and provides additional knowledge into context (from indexed files).
* ``Command: API calls`` - plugin lets you connect the model to the external services using custom defined API calls.
* ``Command: Code Interpreter`` - responsible for generating and executing Python code, functioning much like the `Code Interpreter` on `ChatGPT`, but locally. This means GPT can interface with any script, application, or code. The plugin can also execute system commands, allowing GPT to integrate with your operating system. Plugins can work in conjunction to perform sequential tasks; for example, the `Files` plugin can write generated Python code to a file, which the `Code Interpreter` can execute it and return its result to GPT.
* ``Command: Custom Commands`` - allows you to create and execute custom commands on your system.
* ``Command: Files I/O`` - grants access to the local filesystem, enabling GPT to read and write files, as well as list and create directories.
* ``Command: Web Search`` - allows searching the internet and reading web pages.
* ``Command: Serial port / USB`` - plugin provides commands for reading and sending data to USB ports.
* ``Context history (calendar, inline)`` - provides access to context history database.
* ``Crontab / Task scheduler`` - plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.
* ``DALL-E 3: Image Generation (inline)`` - integrates DALL-E 3 image generation with any chat and mode. Just enable and ask for image in Chat mode, using standard model like GPT-4. The plugin does not require the ``Execute commands`` option to be enabled.
* ``GPT-4 Vision (inline)`` - integrates vision capabilities with any chat mode, not just Vision mode. When the plugin is enabled, the model temporarily switches to vision in the background when an image attachment or vision capture is provided.
* ``Real Time`` - automatically appends the current date and time to the system prompt, informing the model about current time.
* ``System Prompt Extra (append)`` - appends additional system prompts (extra data) from a list to every current system prompt. You can enhance every system prompt with extra instructions that will be automatically appended to the system prompt.


Creating Your Own Plugins
-------------------------

You can create your own plugin for **PyGPT** at any time. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the ``plugin`` directory - you can use them as coding examples for your own plugins.

PyGPT can be extended with:

* Custom plugins
* Custom LLMs wrappers
* Custom vector store providers
* Custom data loaders
* Custom audio input providers
* Custom audio output providers
* Custom web search engine providers

**Examples (tutorial files)** 

See the ``examples`` directory in this repository with examples of custom launcher, plugin, vector store, LLM (Langchain and Llama-index) provider and data loader:

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

**Example:**

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
       vector_stores=vector_stores
   )

Handling events
---------------

In the plugin, you can receive and modify dispatched events.
To do this, create a method named ``handle(self, event, *args, **kwargs)`` and handle the received events like here:

.. code-block:: python

   # custom_plugin.py

   from pygpt_net.core.dispatcher import Event
   

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

**List of Events**

Event names are defined in ``Event`` class in ``pygpt_net.core.dispatcher.Event``.

Syntax: ``event name`` - triggered on, ``event data`` *(data type)*:

- ``AI_NAME`` - when preparing an AI name, ``data['value']`` *(string, name of the AI assistant)*

- ``AUDIO_INPUT_STOP`` - force stop audio input

- ``AUDIO_INPUT_TOGGLE`` - when speech input is enabled or disabled, ``data['value']`` *(bool, True/False)*

- ``AUDIO_OUTPUT_STOP`` - force stop audio output

- ``AUDIO_OUTPUT_TOGGLE`` - when speech output is enabled or disabled, ``data['value']`` *(bool, True/False)*

- ``AUDIO_READ_TEXT`` - on text read with speech synthesis, ``data['value']`` *(str)*

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

- ``PLUGIN_SETTINGS_CHANGED`` - on plugin settings update

- ``PLUGIN_OPTION_GET`` - on request for plugin option value ``data['name'], data['value']`` *(string, any, name of requested option, value)*

- ``POST_PROMPT`` - after preparing a system prompt, ``data['value']`` *(string, system prompt)*

- ``PRE_PROMPT`` - before preparing a system prompt, ``data['value']`` *(string, system prompt)*

- ``SYSTEM_PROMPT`` - when preparing a system prompt, ``data['value']`` *(string, system prompt)*

- ``UI_ATTACHMENTS`` - when the attachment upload elements are rendered, ``data['value']`` *(bool, show True/False)*

- ``UI_VISION`` - when the vision elements are rendered, ``data['value']`` *(bool, show True/False)*

- ``USER_NAME`` - when preparing a user's name, ``data['value']`` *(string, name of the user)*

- ``USER_SEND`` - just before the input text is sent, ``data['value']`` *(string, input text)*


You can stop the propagation of a received event at any time by setting ``stop`` to ``True``:

.. code-block:: python

   event.stop = True