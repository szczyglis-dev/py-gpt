Extending PyGPT
===============

Overview
--------

PyGPT exposes extension points through ``pygpt_net.app.run()``. A custom launcher can register additional:

* plugins,
* GUI tools,
* LLM wrappers,
* vector store providers,
* data loaders,
* audio input providers,
* audio output providers,
* web search providers,
* agent providers.

The repository's ``examples`` directory contains tutorial implementations for every extension type:

* ``examples/custom_launcher.py``
* ``examples/example_plugin.py``
* ``examples/example_tool.py``
* ``examples/example_agent.py``
* ``examples/example_llm.py``
* ``examples/example_vector_store.py``
* ``examples/example_data_loader.py``
* ``examples/example_audio_input.py``
* ``examples/example_audio_output.py``
* ``examples/example_web_search.py``

The examples are intentionally small and are the recommended starting point for custom integrations.

Registration in a custom launcher
---------------------------------

``pygpt_net.app.run()`` first registers PyGPT's built-in components and then appends custom instances
provided through keyword arguments.

A minimal launcher can register only one extension type:

.. code-block:: python

   from pygpt_net.app import run
   from example_plugin import Plugin

   run(
       plugins=[
           Plugin(),
       ],
   )

A larger launcher can register all currently supported extension families:

.. code-block:: python

   from pygpt_net.app import run

   from example_agent import ExampleAgent
   from example_audio_input import ExampleAudioInput
   from example_audio_output import ExampleAudioOutput
   from example_data_loader import ExampleDataLoader
   from example_llm import ExampleLlm
   from example_plugin import Plugin
   from example_tool import ExampleTool
   from example_vector_store import ExampleVectorStore
   from example_web_search import ExampleWebSearchEngine


   def main():
       run(
           plugins=[Plugin()],
           tools=[ExampleTool()],
           llms=[ExampleLlm()],
           vector_stores=[ExampleVectorStore()],
           loaders=[ExampleDataLoader()],
           audio_input=[ExampleAudioInput()],
           audio_output=[ExampleAudioOutput()],
           web=[ExampleWebSearchEngine()],
           agents=[ExampleAgent()],
       )


   if __name__ == "__main__":
       main()

``run()`` owns the application lifecycle and should normally be called only once.

Every extension ID should be unique. Reusing a built-in ID may replace or shadow a built-in entry in the
corresponding registry.

During application initialization PyGPT attaches the main ``window`` or owning plugin to registered
objects. Do not assume those references are already available inside your extension's ``__init__()``
unless the relevant base class explicitly provides them.

Plugins and GUI Tools are different
-----------------------------------

A **plugin** participates in application/model events and can expose commands callable by models.

A **GUI Tool** is an application component registered in the Tools subsystem. It can provide a Tools-menu
entry, dialog, tabs, lifecycle hooks and event handling, but registering a GUI Tool does not automatically
make it a callable model function.

Use a plugin when the model should call functionality as a tool/command. Use a GUI Tool when you want to
extend the desktop application's interface or provide a standalone utility.

Adding a custom model
---------------------

Models can be created in ``Config -> Models -> Edit`` or added to ``%workdir%/models.json``.

For a local OpenAI-compatible server a minimal model entry can look like this:

.. code-block:: json

   {
       "id": "my-local-model",
       "name": "My local model",
       "mode": ["chat", "llama_index"],
       "provider": "local_ai",
       "input": ["text"],
       "output": ["text"],
       "ctx": 32768,
       "tokens": 4096,
       "tool_calls": true,
       "custom_api_endpoint": "http://127.0.0.1:1234/v1",
       "custom_api_key": "local",
       "llama_index": {
           "args": [
               {
                   "name": "model",
                   "value": "my-local-model",
                   "type": "str"
               }
           ],
           "env": []
       }
   }

``custom_api_endpoint`` and ``custom_api_key`` correspond to ``API base`` and ``API key`` in the
Models Editor's Advanced section. When non-empty, the OpenAI-compatible Chat client uses these values for
that model. The ``local_ai`` LlamaIndex wrapper also uses them for its ``OpenAILike`` client.

Leave the custom API fields empty if the model should continue using the provider/global API settings.

For built-in providers, provider API keys configured in ``Config -> Settings -> API Keys`` are normally
used automatically if a LlamaIndex argument does not explicitly override them.

Adding a custom plugin
----------------------

Custom plugins normally inherit from ``pygpt_net.plugin.base.plugin.BasePlugin``. A plugin can:

* define settings with ``add_option()``,
* expose model-callable commands with ``add_cmd()``,
* respond to application events in ``handle()``,
* return command results with ``reply()``.

Minimal plugin example
~~~~~~~~~~~~~~~~~~~~~~

The example below adds one option, exposes one model-callable command, modifies the final system prompt,
and handles command execution:

.. code-block:: python

   from pygpt_net.core.events import Event
   from pygpt_net.plugin.base.plugin import BasePlugin


   class Plugin(BasePlugin):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)

           self.id = "example_plugin"
           self.name = "Example Plugin"
           self.description = "Small tutorial plugin."
           self.prefix = "Example"

           self.allowed_cmds = ["funny_cmd"]

           self.add_option(
               "append_footer",
               type="bool",
               value=False,
               label="Append footer",
               description="Append an instruction to the final system prompt.",
           )

           self.add_cmd(
               "funny_cmd",
               instruction="return an example response for the provided query",
               params=[
                   {
                       "name": "query",
                       "type": "str",
                       "description": "Topic to include in the response.",
                       "required": True,
                   },
               ],
               enabled=True,
               description="Enable the example command.",
           )

       def handle(self, event: Event, *args, **kwargs):
           if event.name == Event.POST_PROMPT_END:
               if self.get_option_value("append_footer"):
                   event.data["value"] += "\n\nKeep the final answer concise."

           elif event.name in (Event.CMD_SYNTAX, Event.CMD_SYNTAX_INLINE):
               for cmd_name in self.allowed_cmds:
                   if self.has_cmd(cmd_name):
                       event.data["cmd"].append(self.get_cmd(cmd_name))

           elif event.name in (Event.CMD_EXECUTE, Event.CMD_INLINE):
               self.execute_commands(event)

       def execute_commands(self, event: Event):
           for item in event.data.get("commands", []):
               if item.get("cmd") != "funny_cmd":
                   continue

               params = item.get("params") or {}
               query = str(params.get("query", "")).strip()

               self.reply(
                   {
                       "request": {
                           "cmd": "funny_cmd",
                           "params": params,
                       },
                       "result": f"Example response for: {query}",
                   },
                   event.ctx,
               )
               return

``add_cmd()`` is preferred over manually constructing the command schema. PyGPT can translate registered
commands into the appropriate native function/tool format when native API function calls are enabled.

The complete tutorial implementation is available in ``examples/example_plugin.py``.

Handling events
~~~~~~~~~~~~~~~

Plugins can inspect and, for mutable events, modify data while a request moves through the application.

A basic handler:

.. code-block:: python

   from pygpt_net.core.events import Event


   def handle(self, event: Event, *args, **kwargs):
       if event.name == Event.USER_SEND:
           # USER_SEND is mutable.
           event.data["value"] = event.data["value"].strip()

       elif event.name == Event.POST_PROMPT_END:
           # Final chance to update the system prompt before the API request.
           event.data["value"] += "\n\nAdditional instruction."

       elif event.name == Event.MODELS_CHANGED:
           # Refresh provider/plugin state after the models list changes.
           self.refresh_models()

Most generic events expose three useful attributes:

* ``event.name`` - event identifier.
* ``event.data`` - dictionary with event-specific data.
* ``event.ctx`` - current ``CtxItem`` when the event is associated with a conversation item.

``event.data`` is intentionally mutable for many pre-processing hooks. If the caller reads the changed
value after dispatch, modifying it changes the subsequent application flow.

Stopping propagation
~~~~~~~~~~~~~~~~~~~~

A listener can stop the event from being passed to later listeners:

.. code-block:: python

   if event.name == Event.INPUT_BEFORE:
       if should_handle_input_myself(event.data["value"]):
           event.stop = True

``event.stop`` stops further event propagation. It does **not** automatically cancel the operation that
created the event unless the relevant caller also checks a cancellation field.

For ``INPUT_BEFORE``, the supported way to abort sending is to set ``data["stop"]``:

.. code-block:: python

   if event.name == Event.INPUT_BEFORE:
       if event.data["value"].startswith("/local-only"):
           event.data["stop"] = True
           event.data["silent"] = True

Event reference
~~~~~~~~~~~~~~~

Generic event constants are defined by ``pygpt_net.core.events.Event``.

Some constants are retained as compatibility/reserved hooks even if the current core flow primarily uses
a newer related event. This is noted below.

* ``AI_NAME`` - emitted while the assistant name is being prepared. ``data["value"]`` contains the
  current assistant name and can be replaced.

* ``AGENT_PROMPT`` - emitted immediately before an input prompt is passed to an agent runner.
  ``data["value"]`` contains the prompt and can be modified.

* ``AUDIO_INPUT_RECORD_START`` - compatibility/reserved hook for an explicit microphone recording-start
  notification. The current UI primarily uses ``AUDIO_INPUT_RECORD_TOGGLE`` for recording control.

* ``AUDIO_INPUT_RECORD_STOP`` - compatibility/reserved hook for an explicit microphone recording-stop
  notification. The current UI primarily uses ``AUDIO_INPUT_RECORD_TOGGLE``.

* ``AUDIO_INPUT_RECORD_TOGGLE`` - requests that microphone recording be toggled. Internal callers may
  additionally provide ``data["state"]`` to request a specific state and ``data["auto"]`` to mark an
  automatic/internal transition.

* ``AUDIO_INPUT_STOP`` - requests an immediate stop of audio-input processing. Some callers provide
  ``data["value"] = True``.

* ``AUDIO_INPUT_TOGGLE`` - enables or disables speech/audio input. ``data["value"]`` is the requested
  boolean state.

* ``AUDIO_INPUT_TRANSCRIBE`` - asks the active Audio Input provider to transcribe an existing audio file.
  ``data["path"]`` contains the file path. ``event.ctx`` may be a temporary context when transcription is
  initiated from the Transcript tool.

* ``AUDIO_OUTPUT_STOP`` - requests that active TTS generation/playback be stopped. ``event.ctx`` may
  identify the context whose playback is being stopped.

* ``AUDIO_OUTPUT_TOGGLE`` - compatibility/reserved generic hook for changing audio-output state. Current
  UI code normally enables/disables the Audio Output plugin through the plugin controller.

* ``AUDIO_PLAYBACK`` - requests playback of an already generated audio file. ``data["audio_file"]``
  contains the path and ``event.ctx`` identifies the related context when available.

* ``AUDIO_READ_TEXT`` - asks the Audio Output provider to synthesize/read text. ``data["text"]`` contains
  the text and ``data["cache_file"]`` may contain a preferred cache path. ``event.ctx`` identifies the
  related context.

* ``BRIDGE_BEFORE`` - emitted before a prepared conversation request is handed to the bridge/provider
  layer. Typical fields are ``data["mode"]``, ``data["context"]`` and ``data["extra"]``.

* ``CMD_EXECUTE`` - dispatches normal plugin commands/tools for execution. ``data["commands"]`` is a list
  of parsed command dictionaries. ``data["silent"]`` may be present for internal calls. ``event.ctx``
  identifies the tool-call context.

* ``CMD_INLINE`` - inline-command equivalent of ``CMD_EXECUTE``. It is used by plugins that intentionally
  expose inline commands independently of the normal ``+ Tools`` path.

* ``CMD_SYNTAX`` - asks enabled plugins to publish normal command/tool definitions. Plugins append command
  definitions to ``data["cmd"]``. Depending on the call site, ``data`` can also contain ``prompt``,
  ``syntax``, ``mode`` and ``is_expert``.

* ``CMD_SYNTAX_INLINE`` - inline-plugin equivalent of ``CMD_SYNTAX``. Plugins append their definitions to
  ``data["cmd"]``.

* ``CTX_AFTER`` - emitted after model output has been attached to the current context item and before the
  response lifecycle fully finishes. ``event.ctx`` is the context item; ``data["mode"]`` is normally
  available for text responses.

* ``CTX_BEFORE`` - emitted after a context item has been prepared but before it is committed/sent through
  the normal processing path. ``event.ctx`` contains that item and ``data["mode"]`` is normally present.

* ``CTX_BEGIN`` - compatibility hook for the beginning of context processing. Some plugins still implement
  it, while the current input pipeline relies mainly on ``INPUT_BEGIN``, ``CTX_BEFORE``, ``CTX_AFTER`` and
  ``CTX_END``.

* ``CTX_END`` - emitted when processing of a context item is complete. ``event.ctx`` contains the finished
  item and ``data["mode"]`` is normally present.

* ``CTX_SELECT`` - emitted when a conversation context is selected. ``data["value"]`` contains the context
  metadata ID.

* ``DISABLE`` - emitted when a plugin is disabled. ``data["value"]`` contains the plugin ID. Dispatch may
  be sent to all plugins so a plugin can react to another plugin being disabled.

* ``ENABLE`` - emitted when a plugin is enabled. ``data["value"]`` contains the plugin ID.

* ``FORCE_STOP`` - global request to stop active plugin/background operations, for example after the user
  presses Stop. ``data["value"]`` may be ``True``; listeners should treat the event itself as the stop
  signal.

* ``INPUT_ACCEPT`` - emitted after ``INPUT_BEFORE`` has accepted the message and immediately before normal
  send processing continues. Typical fields are ``data["value"]``, ``data["mode"]`` and
  ``data["multimodal_ctx"]``.

* ``INPUT_BEFORE`` - main mutable input pre-processing hook. It is emitted after raw input reaches the chat
  send pipeline but before the request is sent. Fields include ``data["mode"]``, ``data["value"]``,
  ``data["multimodal_ctx"]``, ``data["stop"]`` and ``data["silent"]``. Modify ``value`` to rewrite input;
  set ``stop`` to ``True`` to abort the send.

* ``INPUT_BEGIN`` - earliest generic hook in a manual send operation, before the textarea content is fully
  processed. ``data["mode"]`` and ``data["force"]`` describe the request; setting ``data["stop"]`` can
  stop the normal manual-send path.

* ``MODE_BEFORE`` - emitted before an inline/temporary mode choice is finalized for a request.
  ``data["value"]`` contains the mode, ``data["prompt"]`` contains the prompt, and ``event.ctx`` is the
  current context. Replacing ``data["value"]`` can redirect the inline mode.

* ``MODE_SELECT`` - emitted when the application's active mode is selected. ``data["value"]`` contains
  the selected mode ID.

* ``MODEL_BEFORE`` - emitted before the model instance used by an inline request is finalized.
  ``data["mode"]`` contains the mode and ``data["model"]`` contains the proposed ``ModelItem``. Replacing
  ``data["model"]`` can override that choice.

* ``MODEL_SELECT`` - emitted when the active model changes. ``data["value"]`` contains the selected model
  ID.

* ``MODELS_CHANGED`` - emitted after the model registry is changed, for example by the Models Editor or
  importer. It has no required payload; listeners normally refresh cached model lists.

* ``PLUGIN_OPTION_GET`` - query hook for plugin-owned dynamic values. ``data["name"]`` identifies the
  requested value and the handling plugin writes the answer to ``data["value"]``.

* ``PLUGIN_SETTINGS_CHANGED`` - emitted after plugin settings are saved. There is no required payload;
  plugins use it to reload runtime configuration.

* ``POST_PROMPT`` - emitted after the main system prompt has been assembled and personalization has been
  applied, before command/tool syntax is appended. Typical fields are ``mode``, ``reply``, ``internal``,
  ``value`` and ``is_expert``. ``event.ctx`` is set. ``data["value"]`` is mutable.

* ``POST_PROMPT_ASYNC`` - emitted in the bridge worker after processing has moved to the asynchronous
  request path. It is a late mutable system-prompt hook. Typical fields are ``mode``, ``reply`` and
  ``value``; ``event.ctx`` is set.

* ``POST_PROMPT_END`` - final mutable system-prompt hook immediately before the provider request is
  executed. Typical fields are ``mode``, ``reply`` and ``value``; ``event.ctx`` is set. This is usually
  the safest event for a plugin that must append a final instruction.

* ``PRE_PROMPT`` - early hook for the system prompt before the main prompt builder finishes processing it.
  ``data["mode"]`` and ``data["value"]`` are provided; expert calls may additionally provide
  ``data["is_expert"]``.

* ``SETTINGS_CHANGED`` - emitted after the main Settings editor saves changes. It has no required payload.
  Plugins/providers can use it to refresh configuration-dependent state.

* ``SYSTEM_PROMPT`` - emitted while the base/final system prompt is being assembled. ``data["value"]`` is
  the mutable prompt text and ``data["mode"]`` identifies the current mode. Depending on the call site,
  ``silent`` or ``is_expert`` may also be present.

* ``TOOL_OUTPUT_RENDER`` - WebView rendering hook for custom tool output. Typical fields are
  ``data["tool"]`` (plugin/tool ID), ``data["content"]`` (tool output data), ``data["html"]`` (custom HTML
  result) and ``data["multiple"]`` (whether the renderer is handling one of multiple tool outputs).
  A plugin can populate ``html`` to provide custom rendering.

* ``UI_ATTACHMENTS`` - asks listeners whether attachment UI should be visible for a mode.
  ``data["mode"]`` identifies the mode and mutable ``data["value"]`` is the visibility boolean.

* ``UI_VISION`` - asks listeners whether the inline Vision availability indicator should be visible.
  ``data["mode"]`` identifies the mode and mutable ``data["value"]`` is the visibility boolean.

* ``USER_NAME`` - emitted while the user display/name value is prepared. ``data["value"]`` contains the
  current name and can be replaced.

* ``USER_SEND`` - emitted for a manual user send after the text has been read from the input widget but
  before attachment handling and the kernel/bridge input event. ``data["mode"]`` contains the current mode
  and mutable ``data["value"]`` contains the text.

Event ordering example
~~~~~~~~~~~~~~~~~~~~~~

For a typical manual text message, a simplified sequence is approximately:

.. code-block:: text

   INPUT_BEGIN
       |
       v
   USER_SEND
       |
       v
   INPUT_BEFORE
       |
       v
   INPUT_ACCEPT
       |
       v
   CTX_BEFORE
       |
       v
   PRE_PROMPT
       |
       v
   SYSTEM_PROMPT
       |
       v
   POST_PROMPT
       |
       v
   CMD_SYNTAX / CMD_SYNTAX_INLINE
       |
       v
   POST_PROMPT_ASYNC
       |
       v
   POST_PROMPT_END
       |
       v
   provider / model request
       |
       v
   CTX_AFTER
       |
       v
   CTX_END

Exact ordering can differ for image generation, Realtime, Assistants, agents, internal calls and tool
continuations.

Event debug logging
~~~~~~~~~~~~~~~~~~~

Event flow can be inspected by enabling:

``Config -> Settings -> Debug -> Log and debug events``

Adding a custom GUI Tool
------------------------

A custom application tool uses the Tools subsystem and is registered through ``tools=[...]``.

Minimal example:

.. code-block:: python

   from PySide6.QtGui import QAction
   from pygpt_net.tools.base import BaseTool


   class ExampleTool(BaseTool):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "example_tool"
           self.opened = False

       def setup(self):
           # self.window is available here.
           pass

       def setup_menu(self) -> dict:
           action = QAction("Example Tool", self.window)
           action.triggered.connect(self.toggle)
           return {"example": action}

       def toggle(self):
           self.opened = not self.opened
           self.window.ui.dialogs.alert(
               f"Example tool opened: {self.opened}"
           )

       def on_reload(self):
           # Called when profile/workdir is reloaded.
           pass

       def on_exit(self):
           # Release external resources here.
           pass

A real GUI Tool can register dialogs, tabs, menus, theme hooks and update hooks. See
``examples/example_tool.py`` for a complete dialog-based tutorial.

Adding a custom LLM wrapper
---------------------------

LLM wrappers are used by the LlamaIndex integration and embeddings. They are not the same thing as the
normal native Chat-provider path.

A wrapper derives from ``pygpt_net.provider.llms.base.BaseLLM`` and declares a unique ``id`` and supported
types.

A compact OpenAI-backed example:

.. code-block:: python

   from llama_index.llms.openai import OpenAI as LlamaOpenAI

   from pygpt_net.core.types import MODE_LLAMA_INDEX
   from pygpt_net.provider.llms.base import BaseLLM


   class ExampleLlm(BaseLLM):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "example_llm"
           self.name = "Example LlamaIndex provider"
           self.type = [MODE_LLAMA_INDEX, "embeddings"]

       def llama(self, window, model, stream=False):
           args = self.parse_args(model.llama_index, window)
           args.setdefault("model", model.id)

           # Global fallback used by this OpenAI-based tutorial.
           args.setdefault(
               "api_key",
               window.core.config.get("api_key", ""),
           )

           # Per-model values have highest priority when configured.
           if model.custom_api_key:
               args["api_key"] = model.custom_api_key

           if model.custom_api_endpoint:
               args["api_base"] = model.custom_api_endpoint

           args = self.inject_llamaindex_http_clients(
               args,
               window.core.config,
           )
           return LlamaOpenAI(**args)

For embeddings, implement ``get_embeddings_model()`` and return a LlamaIndex ``BaseEmbedding`` instance.

Depending on its purpose, a wrapper can implement:

* ``llama()`` - return a LlamaIndex LLM for Chat with Files / LlamaIndex agents.
* ``get_embeddings_model()`` - return a LlamaIndex embedding model.
* ``get_openai_agent_provider()`` - optionally provide a model adapter for OpenAI Agents.
* ``get_models()`` - optionally expose provider-side model discovery.

Legacy ``chat()`` and ``completion()`` methods remain in the base interface for compatibility, but current
custom LlamaIndex integrations should normally follow the ``llama()`` path.

See ``examples/example_llm.py`` for a complete LLM + embeddings example.

Adding a custom vector store
----------------------------

Vector store providers derive from ``pygpt_net.provider.vector_stores.base.BaseStore`` and are registered
through ``vector_stores=[...]``.

The current index creation path passes the LLM and embedding model separately. Older
``ServiceContext``-based examples are no longer appropriate.

Example:

.. code-block:: python

   from llama_index.core import StorageContext, load_index_from_storage

   from pygpt_net.provider.vector_stores.base import BaseStore


   class ExampleVectorStore(BaseStore):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "ExampleVectorStore"
           self.prefix = "example_"

       def create(self, id, embed_model=None):
           if self.exists(id):
               return

           index = self.index_from_empty(embed_model)
           self.store(id=id, index=index)

       def get(self, id, llm=None, embed_model=None):
           if not self.exists(id):
               self.create(id, embed_model)

           storage_context = StorageContext.from_defaults(
               persist_dir=self.get_path(id),
           )
           index = load_index_from_storage(
               storage_context,
               llm=llm,
               embed_model=embed_model,
           )
           self.indexes[id] = index
           return index

       def store(self, id, index=None):
           index = index or self.indexes[id]
           index.storage_context.persist(
               persist_dir=self.get_path(id),
           )
           self.indexes[id] = index

``BaseStore`` already provides common helpers such as ``exists()``, ``remove()``, ``truncate()``,
``remove_document()``, ``attach()`` and ``get_path()``.

See ``examples/example_vector_store.py`` for the complete tutorial.

Adding a custom data loader
---------------------------

Data loaders are registered through ``loaders=[...]`` and normally derive from
``pygpt_net.provider.loaders.base.BaseLoader``.

The loader registers metadata/configuration and returns a LlamaIndex reader:

.. code-block:: python

   from llama_index.core.readers.base import BaseReader
   from llama_index.core.schema import Document

   from pygpt_net.provider.loaders.base import BaseLoader


   class ExampleDataLoader(BaseLoader):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "example_text"
           self.name = "Example text loader"
           self.extensions = ["exampletxt"]
           self.type = ["file"]

           self.init_args = {
               "encoding": "utf-8",
           }
           self.init_args_types = {
               "encoding": "str",
           }

       def get(self) -> BaseReader:
           return ExampleReader(**self.get_args())


   class ExampleReader(BaseReader):
       def __init__(self, encoding="utf-8", **kwargs):
           super().__init__(**kwargs)
           self.encoding = encoding

       def load_data(self, file, extra_info=None):
           with open(file, "r", encoding=self.encoding) as handle:
               text = handle.read()

           return [
               Document(
                   text=text,
                   metadata=extra_info or {},
               )
           ]

Current LlamaIndex ``Document`` objects use the ``metadata`` field for metadata.

See ``examples/example_data_loader.py`` for a configurable CSV-like example.

Adding audio providers
----------------------

Custom speech-to-text providers are registered with ``audio_input=[...]``. Custom text-to-speech
providers are registered with ``audio_output=[...]``.

Audio input
~~~~~~~~~~~

A speech-to-text provider receives the path that PyGPT wants transcribed. Do not hard-code
``input.wav``; application-managed recordings can live under ``%workdir%/tmp``.

.. code-block:: python

   from pygpt_net.provider.audio_input.base import BaseProvider


   class ExampleAudioInput(BaseProvider):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "example_audio_input"
           self.name = "Example audio input"

       def transcribe(self, path: str) -> str:
           client = self.plugin.window.core.api.openai.get_client()

           with open(path, "rb") as audio_file:
               return client.audio.transcriptions.create(
                   model="whisper-1",
                   file=audio_file,
                   response_format="text",
               )

       def is_configured(self) -> bool:
           return bool(
               self.plugin.window.core.config.get("api_key")
           )

See ``examples/example_audio_input.py`` for provider-specific settings and configuration messages.

Audio output
~~~~~~~~~~~~

Use ``prepare_output_path()`` rather than a fixed filename. PyGPT stores generated TTS working files under
``%workdir%/tmp/audio_output`` and uses unique names, which also avoids file-lock issues on Windows.

.. code-block:: python

   from pygpt_net.provider.audio_output.base import BaseProvider


   class ExampleAudioOutput(BaseProvider):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "example_audio_output"
           self.name = "Example audio output"

       def speech(self, text: str) -> str:
           client = self.plugin.window.core.api.openai.get_client()
           path = self.prepare_output_path(extension="mp3")

           response = client.audio.speech.create(
               model="tts-1",
               voice="alloy",
               input=text,
           )
           response.stream_to_file(path)
           return str(path)

See ``examples/example_audio_output.py`` for settings, voices and configuration checks.

Adding a web search provider
----------------------------

Web search providers are registered with ``web=[...]``. They provide a search-engine implementation used
by the Web Search plugin.

A provider normally defines its own settings and implements ``search()``:

.. code-block:: python

   from pygpt_net.provider.web.base import BaseProvider


   class ExampleWebSearchEngine(BaseProvider):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "example_web_search"
           self.name = "Example search engine"
           self.type = ["search_engine"]

       def search(self, query: str, limit: int = 10, offset: int = 0):
           # Call the external search API here.
           # Return result URLs as a list of strings.
           return [
               "https://example.com/result-1",
               "https://example.com/result-2",
           ]

       def is_configured(self, cmds):
           return True

A production provider should define credentials/settings with ``plugin.add_option()`` and use
``self.plugin.get_url()`` or another PyGPT/network helper appropriate for the integration.

See ``examples/example_web_search.py`` for a complete Google Custom Search tutorial.

Adding a custom agent
---------------------

Agent providers are registered with ``agents=[...]``. Built-in providers live under
``pygpt_net.provider.agents`` and include LlamaIndex and OpenAI Agents workflows.

The simplest safe extension is often to subclass an existing workflow and customize one stage:

.. code-block:: python

   from pygpt_net.provider.agents.openai.agent import Agent as OpenAIAgentBase


   class ExampleAgent(OpenAIAgentBase):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.id = "example_agent"
           self.name = "Example custom agent"

       def get_agent(self, window, kwargs):
           kwargs = dict(kwargs or {})

           current = str(
               kwargs.get("system_prompt") or ""
           ).strip()

           prefix = (
               "You are running through the custom "
               "ExampleAgent provider."
           )

           kwargs["system_prompt"] = (
               f"{prefix}\n\n{current}"
               if current
               else prefix
           )

           return super().get_agent(window, kwargs)

The inherited ``run()`` keeps the existing OpenAI Agents execution lifecycle, streaming, tools, response
IDs and PyGPT bridge integration. Override ``run()`` only when a different execution engine/lifecycle is
actually required.

For a completely new runtime, derive from ``pygpt_net.provider.agents.base.BaseAgent`` and implement the
current provider contract.

See ``examples/example_agent.py``.

Source code as API reference
----------------------------

The base interfaces are the source of truth for method signatures. Useful implementation directories are:

* ``pygpt_net.plugin``
* ``pygpt_net.tools``
* ``pygpt_net.provider.llms``
* ``pygpt_net.provider.vector_stores``
* ``pygpt_net.provider.loaders``
* ``pygpt_net.provider.audio_input``
* ``pygpt_net.provider.audio_output``
* ``pygpt_net.provider.web``
* ``pygpt_net.provider.agents``

For complete runnable tutorial files, use the repository ``examples`` directory.
