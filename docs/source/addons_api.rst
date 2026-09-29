Add-ons API
===========

This chapter is the developer reference for external PyGPT Add-ons. It covers the package format, local development and testing, dependency installation, publishing, runtime lifecycle, the supported base classes, and the application/events API that an Add-on can use.

The examples shipped in the main repository under ``examples/addons`` and in the public ``py-gpt-addons`` repository are designed to be copied and modified. They are runnable tutorials, not only registration stubs.

.. important::

   Python Add-ons execute inside the PyGPT process and therefore have the same operating-system permissions as PyGPT. An Add-on can read files available to the process, use the network, import packages and call application APIs. ``trusted`` and ``official`` are catalog metadata, not a sandbox. Review third-party code before installation.

What is an Add-on?
------------------

An Add-on is a profile-scoped extension installed below ``%workdir%/addons``. Every package has a ``manifest.json`` and either:

* a Python entry point that returns an object derived from one of PyGPT's supported base classes, or
* static theme/locale files handled by the existing theme/translation loaders.

Canonical Add-on types are:

.. list-table:: Add-on types
   :header-rows: 1
   :widths: 18 23 24 35

   * - Type
     - Installed directory
     - Python base class
     - Purpose
   * - ``plugin``
     - ``addons/plugins/<id>``
     - ``BasePlugin``
     - Model-callable tools/commands, prompt hooks, application events and plugin settings.
   * - ``tool``
     - ``addons/tools/<id>``
     - ``BaseTool``
     - Desktop GUI utilities, Tools-menu actions, dialogs, tabs and application lifecycle hooks.
   * - ``llm``
     - ``addons/llms/<id>``
     - ``BaseLLM``
     - LlamaIndex LLM/embedding wrappers and provider-owned configuration.
   * - ``vector_store``
     - ``addons/vector_stores/<id>``
     - ``BaseStore``
     - Persistent/index storage backends used by RAG/indexing.
   * - ``loader``
     - ``addons/loaders/<id>``
     - ``BaseLoader``
     - File or web/external data readers used by indexing and attachments.
   * - ``audio_input``
     - ``addons/audio_input/<id>``
     - ``provider.audio_input.base.BaseProvider``
     - Speech/audio-to-text providers.
   * - ``audio_output``
     - ``addons/audio_output/<id>``
     - ``provider.audio_output.base.BaseProvider``
     - Text-to-speech/audio-output providers.
   * - ``web``
     - ``addons/web/<id>``
     - ``provider.web.base.BaseProvider``
     - Search-engine providers used by the Web search plugin.
   * - ``agent``
     - ``addons/agents/<id>``
     - ``BaseAgent``
     - Custom-agents providers/workflows.
   * - ``theme``
     - ``addons/themes/<id>``
     - none
     - Static Qt/QSS and chat CSS theme package.
   * - ``locale``
     - ``addons/locale/<id>``
     - none
     - Static locale override/package.

PyGPT accepts several historical type aliases internally, but distributable manifests should always use the canonical names above.

Quick start: create, test and package an Add-on
-----------------------------------------------

A practical development loop is:

#. Copy the closest tutorial from ``examples/addons/<type>/<example>``.
#. Change the package directory name and manifest ``id`` to a globally unique, stable ID.
#. Change the Python class and entry point while keeping it derived from the documented base class.
#. Install the directory with ``Config -> Install Add-on...``.
#. Approve installation of any missing required ``external_dependencies`` when prompted.
#. Restart PyGPT for Python/runtime Add-ons.
#. Enable/configure the new component and test it.
#. Use ``Config -> Settings -> Debug`` while developing; plugin and event logging are especially useful for plugins.
#. Increase the manifest ``version`` before testing an update, because an incoming version must be newer unless an explicit overwrite path is used.
#. When ready, ZIP exactly one Add-on package or publish it from a GitHub repository/subdirectory.

Minimal directory layout
~~~~~~~~~~~~~~~~~~~~~~~~

For a plugin:

.. code-block:: text

   my_plugin/
   ├── manifest.json
   ├── plugin.py
   └── helpers/
       └── client.py

For manual installation, PyGPT stores it as:

.. code-block:: text

   %workdir%/addons/plugins/my_plugin/
   ├── manifest.json
   ├── plugin.py
   └── helpers/
       └── client.py

The installed directory name must equal the manifest ``id`` and its parent directory must match the manifest ``type``.

Manifest reference
------------------

Manifest version ``1`` is currently supported.

.. code-block:: json

   {
     "manifest_version": 1,
     "id": "githubuser_project_my_plugin",
     "type": "plugin",
     "name": "My Plugin",
     "description": "One sentence explaining what the Add-on does.",
     "version": "1.0.0",
     "min_app_version": "2.8.35",
     "author": "Your Name",
     "contact": {
       "email": "you@example.com",
       "repo": "https://github.com/example/my-pygpt-addon",
       "www": "https://example.com"
     },
     "entrypoint": "plugin.py:Plugin",
     "external_dependencies": [
       {"name": "httpx", "version": ">=0.27,<1.0", "optional": false},
       {"name": "orjson", "version": ">=3.10", "optional": true}
     ]
   }

Required fields
~~~~~~~~~~~~~~~

``manifest_version``
   Integer manifest schema version. Current supported value: ``1``.

``id``
   Stable package identifier. It must be lowercase and match ``^[a-z0-9][a-z0-9._-]*$``. For public Add-ons, use a globally unique ID, for example ``<github_user>_<repo>_<addon>``. Do not change the ID between releases unless you intentionally want a separate Add-on.

``type``
   One canonical type from the table above.

``name``
   Human-readable display name.

``description``
   Short human-readable description.

``version``
   PEP 440-compatible Add-on version. PyGPT compares this with the installed version when updating.

``min_app_version``
   Minimum compatible PyGPT version, also parsed as a PEP 440 version. Installation/loading is rejected when the current app is older.

``author``
   Author or organization name.

``contact``
   Non-empty string, object or array. An object containing ``email``, ``repo`` and/or ``www`` is recommended.

Runtime-only fields
~~~~~~~~~~~~~~~~~~~

Python/runtime types (all types except ``theme`` and ``locale``) also require ``entrypoint``.

An entry point has the form ``relative/module.py:Symbol``. The module path must stay inside the Add-on directory, cannot be absolute and cannot contain ``.``/``..`` traversal segments. The symbol must be a valid Python identifier.

Examples:

.. code-block:: json

   "entrypoint": "plugin.py:Plugin"

.. code-block:: json

   "entrypoint": "providers/main.py:Provider"

One package may register multiple objects of the **same Add-on type**:

.. code-block:: json

   "entrypoint": [
     "providers.py:PrimaryProvider",
     "providers.py:SecondaryProvider"
   ]

The symbol may be:

* a class, instantiated with no arguments;
* a zero-argument factory function;
* a factory/class returning a list or tuple of compatible objects.

PyGPT validates every returned object against the base class required by the manifest type. A plugin entry point cannot return an LLM provider, for example.

Python package namespace and imports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each external Add-on is loaded in its own generated Python package namespace. Relative imports inside the package are supported. The whole ``addons`` directory is not globally prepended to ``sys.path``, so use normal relative imports for your own modules where possible:

.. code-block:: python

   from .helpers.client import Client

External dependencies and Package Manager
-----------------------------------------

``external_dependencies`` declares optional application-runtime Python dependencies. It is not merely informational: during installation PyGPT checks required dependencies and, when something is missing, asks the user to install it with the shared Package Manager.

A dependency can be a requirement string:

.. code-block:: json

   "external_dependencies": ["httpx>=0.27,<1.0"]

or an object:

.. code-block:: json

   {
     "name": "httpx",
     "version": ">=0.27,<1.0",
     "optional": false
   }

Rules:

* ``name`` is required for object syntax.
* ``version`` is appended to the package name and may contain normal PEP 440 constraints.
* ``optional: true`` means PyGPT does not automatically require/install that dependency.
* environment markers in normal requirement strings are evaluated for the current runtime.
* package URLs/direct URL requirements are intentionally rejected; use package names/version constraints.
* dependency packages are application dependencies, not Python/System sandbox packages.

The Package Manager is available directly at ``Config -> Package Manager``. It uses ``uv`` and installs into:

.. code-block:: text

   <application base workdir>/extra_packages/<major.minor>/

For example, a Python 3.13 build uses ``extra_packages/3.13``. The directory is application-wide and shared by profiles using the same application base workdir. A new bundled/runtime Python minor version gets a new directory, which prevents incompatible compiled packages from an older Python ABI from being reused accidentally.

Install/uninstall operations are transactional: PyGPT works on a temporary copy and swaps it into place only after success. Some pure-Python packages become importable immediately; a restart can still be required when modules have already been imported or compiled extensions are involved.

On startup PyGPT also checks installed Add-ons for dependencies missing from the current Python-version directory. This is useful after upgrading to a build that embeds another Python minor version.

Packaging as ZIP
----------------

A ZIP import must resolve to exactly one Add-on root containing ``manifest.json``. A wrapper directory produced by GitHub/archiving tools is allowed as long as PyGPT can unambiguously find one package root.

Recommended:

.. code-block:: text

   my_plugin.zip
   └── my_plugin/
       ├── manifest.json
       ├── plugin.py
       └── helpers/
           └── client.py

Do not package multiple unrelated Add-ons into one ZIP for the **Import from ZIP** flow. A repository may contain multiple Add-ons, but each installed package still has its own manifest root.

PyGPT validates archive paths and rejects unsafe absolute/path-traversal entries. Very large archives are also limited by file-count/download safety limits.

Local testing
-------------

Installer-based test
~~~~~~~~~~~~~~~~~~~~

The recommended path is the same path users will use:

#. Open ``Config -> Install Add-on...``.
#. Choose **Import from directory** and select the package root.
#. Approve required package dependencies if prompted.
#. Restart PyGPT for runtime Add-ons.
#. Enable/configure the component.

Manual-copy test
~~~~~~~~~~~~~~~~

For a faster low-level test you can copy a package directly to the type directory under ``%workdir%/addons``. Keep the exact layout and restart the application. This bypasses installer metadata such as source/trusted/official flags, so use the installer before release testing.

Debugging
~~~~~~~~~

Useful developer settings include:

* ``Config -> Settings -> Debug -> Log events`` for event ordering and payloads.
* plugin logging for command/tool execution.
* API/tool logging when testing model-callable plugin commands.
* normal application log output for ``[Add-ons] WARNING`` messages.

A broken Add-on is isolated during startup. Invalid manifests, incompatible minimum versions, import errors, invalid entry points and registration errors are skipped and logged instead of aborting the whole application.

Runtime lifecycle
-----------------

Python Add-ons are discovered and registered during application startup. The simplified lifecycle is:

.. code-block:: text

   discover %workdir%/addons
        |
        v
   validate manifest + min_app_version
        |
        v
   import entrypoint in isolated package namespace
        |
        v
   instantiate class/factory
        |
        v
   validate returned Base* type
        |
        v
   register through the normal PyGPT registry
        |
        v
   attach window/plugin during registry setup
        |
        v
   application setup / post-setup / event loop
        |
        v
   shutdown hooks

Python Add-ons are process-level registrations. After installation/uninstallation, or after switching to a profile with a different Python Add-on set, restart PyGPT before relying on the new runtime set. Static theme/locale packages can be synchronized through their existing loaders, but a restart is still a safe development workflow.

Publishing on GitHub and in the public registry
-----------------------------------------------

Standalone repository
~~~~~~~~~~~~~~~~~~~~~

For a repository containing one Add-on, put ``manifest.json`` at the repository root.

Monorepository
~~~~~~~~~~~~~~

A repository can contain many packages:

.. code-block:: text

   plugins/
   ├── first_plugin/
   │   ├── manifest.json
   │   └── plugin.py
   └── second_plugin/
       ├── manifest.json
       └── plugin.py

PyGPT accepts a normal GitHub repository URL, a ``/tree/<ref>/<path>`` URL, and a repository/subdirectory location supported by the installer.

Public ``py-gpt-addons`` registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default catalog is:

``https://raw.githubusercontent.com/szczyglis-dev/py-gpt-addons/master/addons.json``

The registry root must contain an ``addons`` array:

.. code-block:: json

   {
     "addons": [
       {
         "id": "githubuser_project_my_plugin",
         "name": "My Plugin",
         "description": "Example third-party Add-on.",
         "author": "Your Name",
         "version": "1.0.0",
         "type": "plugin",
         "github_url": "https://github.com/example/my-pygpt-addons",
         "github_path": "plugins/githubuser_project_my_plugin",
         "ref": "main",
         "trusted": false,
         "official": false
       }
     ]
   }

For a package stored directly in the official ``py-gpt-addons`` repository, a compact relative entry can use ``path`` instead of an external ``github_url``:

.. code-block:: json

   {
     "id": "example_plugin",
     "name": "Example developer plugin",
     "description": "Example stored in the official registry repository.",
     "author": "PyGPT example",
     "version": "1.1.0",
     "type": "plugin",
     "path": "./plugins/example_plugin",
     "trusted": true,
     "official": true
   }

When submitting a public package, document network/filesystem/shell/desktop access, credentials, external dependencies and other security-sensitive behavior. Keep the manifest version and registry version in sync with the actual package release.

Application API available to Python Add-ons
-------------------------------------------

Documented API versus internal object tree
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The base classes, manifest format and ``Event`` constants described in this chapter are the intended Add-on-facing API. Runtime objects also receive access to PyGPT's ``window`` or an owning plugin, which makes much more of the application available, but those deeper controller/core objects are implementation APIs and can change between releases.

Prefer these stable patterns first:

* base-class helpers such as ``BasePlugin.add_option()``, ``BasePlugin.reply()`` and ``BaseTool.add_lang_mapping()``;
* event dispatch/listening through ``Event``;
* provider base-class methods;
* ``self.window.core.config`` for application/profile configuration;
* ``self.window.dispatch(...)`` when an Add-on must request a normal application action;
* owning plugin options for audio/web providers.

Common ``window`` access examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read/write application configuration:

.. code-block:: python

   enabled = self.window.core.config.get("some.key", False)
   self.window.core.config.set("some.key", True)
   self.window.core.config.save()

Resolve profile/application paths:

.. code-block:: python

   profile_workdir = self.window.core.config.get_user_path()
   index_dir = self.window.core.config.get_user_dir("idx")
   data_workdir = self.window.core.config.get_workdir_prefix(ctx=event.ctx)

Dispatch a normal application event:

.. code-block:: python

   from pygpt_net.core.events import Event

   self.window.dispatch(Event(Event.AUDIO_OUTPUT_STOP, {"value": True}))

Read another registered plugin without importing its implementation:

.. code-block:: python

   plugins = self.window.core.plugins
   if plugins.is_registered("files_io"):
       plugin = plugins.get("files_io")

Show an application alert from a plugin:

.. code-block:: python

   self.error("Something went wrong")

For GUI Tools, normal Qt APIs are available and ``self.window`` is the main ``QMainWindow``.

Plugin Add-ons
--------------

Base class
~~~~~~~~~~

.. code-block:: python

   from pygpt_net.plugin.base.plugin import BasePlugin

   class Plugin(BasePlugin):
       ...

A plugin is the most general model-facing Add-on. It can define settings, expose commands/tools, inspect or mutate events, inject prompt text, react to UI/model/context changes and return tool results into the conversation.

Important attributes
~~~~~~~~~~~~~~~~~~~~

``id``
   Stable plugin ID. For external packages it should normally match the package purpose and remain stable across releases.

``name`` / ``description``
   Default UI text. Localized plugin domains may override it.

``prefix``
   Prefix used by ``log()``.

``type``
   Plugin feature types. Common values used by the application include ``cmd``, ``audio.input``, ``audio.output``, ``text.input``, ``text.output``, ``vision`` and ``schedule`` depending on integration.

``allowed_cmds``
   Command names the plugin is willing to execute. ``cmd_allowed()`` checks this list.

``options``
   Plugin settings and command definitions created by ``add_option()``/``add_cmd()``.

``window``
   Attached after registration. Do not assume it is available in ``__init__()``.

Complete public BasePlugin method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: ``BasePlugin`` public methods
   :header-rows: 1
   :widths: 31 43 26

   * - Method
     - What it does
     - Typical use
   * - ``setup()``
     - Returns the current options dictionary.
     - Introspection; normally inherited.
   * - ``add_option(name, type, **kwargs)``
     - Adds a plugin setting definition and returns it.
     - Call in ``__init__()`` to declare settings.
   * - ``add_cmd(cmd, **kwargs)``
     - Adds a ``cmd`` option containing instruction, parameter schema and enabled state. ``hidden=True`` registers a hidden tool.
     - Declare a model-callable command/tool.
   * - ``has_cmd(cmd)``
     - Returns whether the command exists and is enabled.
     - Before publishing syntax/executing a command.
   * - ``cmd_allowed(cmd)``
     - Checks whether ``cmd`` is present in ``allowed_cmds``.
     - Authorization/dispatch guard inside a plugin.
   * - ``cmd_exe()``
     - Returns the global normal Tools/commands switch state.
     - Check whether normal command execution is enabled.
   * - ``get_cmd(cmd)``
     - Returns a deep-copied command schema with its ``cmd`` field.
     - Append to ``Event.CMD_SYNTAX`` / ``CMD_SYNTAX_INLINE``.
   * - ``has_option(name)``
     - Tests whether an option exists.
     - Optional/backward-compatible settings.
   * - ``get_option(name)``
     - Returns the full option definition.
     - Access metadata as well as value.
   * - ``get_option_value(name)``
     - Returns the typed value; bool/int/float are normalized.
     - Normal runtime setting reads.
   * - ``set_option_value(name, value)``
     - Updates a typed option value and refreshes the settings widget.
     - Runtime changes reflected in UI.
   * - ``attach(window)``
     - Stores the main window reference.
     - Called by PyGPT during registration; normally do not call yourself.
   * - ``refresh_option(option_id)``
     - Refreshes one plugin option in the settings UI.
     - After changing dynamic values/choices.
   * - ``handle(event, *args, **kwargs)``
     - Main plugin event listener.
     - Override to handle commands and application events.
   * - ``on_update(*args, **kwargs)``
     - Called from the application's frequent update cycle while the plugin is enabled.
     - Lightweight state/UI updates only.
   * - ``on_post_update(*args, **kwargs)``
     - Called from the slower post-update cycle while enabled.
     - Periodic maintenance that does not need every UI tick.
   * - ``shutdown(enabled=None)``
     - Shutdown hook invoked for every registered plugin, including disabled plugins; receives active state when available.
     - Close sockets, files, threads, clients.
   * - ``trans(text=None)``
     - Translates a key in the ``plugin.<id>`` translation domain.
     - Plugin-localized UI text.
   * - ``error(err)``
     - Logs an exception/error and opens a user alert dialog.
     - User-visible plugin failure.
   * - ``debug(data, console=True)``
     - Sends diagnostic data to PyGPT debug/logger output.
     - Developer diagnostics.
   * - ``reply(response, ctx=None, extra_data=None)``
     - Finishes one plugin command response and attaches it to a context.
     - Standard synchronous command/tool result.
   * - ``is_native_cmd()``
     - Returns whether native provider API command/tool calling is enabled.
     - Conditional behavior for native tool calls.
   * - ``is_log()``
     - Returns plugin-console logging state.
     - Avoid expensive debug formatting when logging is off.
   * - ``is_async(ctx)``
     - Returns whether asynchronous execution is allowed for the context.
     - Decide whether a plugin worker may run asynchronously.
   * - ``log(msg)``
     - Prefixes/logs a plugin message and updates status when appropriate.
     - Normal plugin operational logging.
   * - ``cmd_prepare(ctx, cmds)``
     - Default command-run preparation; dispatches busy state.
     - Can be overridden for command startup behavior.
   * - ``handle_finished(response, ctx=None, extra_data=None)``
     - Qt slot that prepares one response and dispatches a single reply-add event.
     - Worker signal target for one result.
   * - ``handle_finished_more(responses, ctx=None, extra_data=None)``
     - Same as above for multiple command results.
     - Worker returning several results.
   * - ``prepare_reply_ctx(response, ctx=None)``
     - Normalizes/persists tool result data into ``CtxItem`` and handles extra context.
     - Advanced custom reply pipelines; ``reply()`` is preferred.
   * - ``handle_status(data)``
     - Qt slot for worker status messages.
     - Connect worker ``status`` signals.
   * - ``handle_error(err)``
     - Qt slot forwarding a worker error to ``error()``.
     - Connect worker ``error`` signals.
   * - ``handle_debug(msg)``
     - Qt slot forwarding worker debug messages.
     - Connect worker debug signals.
   * - ``handle_log(msg)``
     - Qt slot forwarding worker log messages.
     - Connect worker log signals.
   * - ``is_threaded()``
     - Returns whether the kernel is currently in threaded execution.
     - Avoid direct UI/status work from threaded paths.
   * - ``open_url(url)``
     - Opens a URL with the normal PyGPT/default-browser path.
     - Help/documentation links.

Additional plugin lifecycle conventions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to the methods implemented by ``BasePlugin``, the plugin controller recognizes two optional methods when present on a plugin class:

``setup_ui()``
   Called after the plugin is attached and its persisted settings are restored. Use it only when the plugin must create or connect UI elements. Most command-only plugins do not need it.

``destroy()``
   Optional cleanup hook used when the plugin manager tears down/reloads a plugin instance. Release plugin-owned resources here. Application shutdown is still represented by the base ``shutdown(enabled)`` hook.

Keep UI creation out of ``__init__`` because ``self.window`` may not yet be attached there.

Plugin option schema
~~~~~~~~~~~~~~~~~~~~

Common option types used by built-in plugins are ``text``, ``textarea``, ``bool``, ``int``, ``float``, ``combo``, ``dict``, ``bool_list`` and ``cmd``. ``add_cmd()`` creates ``cmd`` options for you.

Useful common option fields include:

* ``value`` - default/current value;
* ``label`` - UI label;
* ``description`` and ``tooltip``;
* ``min``, ``max``, ``step``, ``multiplier`` and ``slider`` for numeric settings;
* ``keys`` for selectable values;
* ``advanced``;
* ``secret`` for sensitive values;
* ``persist`` to preserve a value across option reset flows;
* ``urls`` for help/resource links;
* ``tab`` used by providers/plugins that group settings.

Command/tool example
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   self.allowed_cmds = ["example_echo"]

   self.add_cmd(
       "example_echo",
       instruction="Echo text through the example plugin.",
       params=[{
           "name": "text",
           "type": "str",
           "description": "Text to return",
           "required": True,
       }],
       enabled=True,
   )

   def handle(self, event):
       if event.name in (Event.CMD_SYNTAX, Event.CMD_SYNTAX_INLINE):
           if self.has_cmd("example_echo"):
               event.data.setdefault("cmd", []).append(self.get_cmd("example_echo"))

       elif event.name in (Event.CMD_EXECUTE, Event.CMD_INLINE):
           for item in event.data.get("commands", []):
               if item.get("cmd") != "example_echo":
                   continue
               params = item.get("params") or {}
               self.reply({
                   "request": {"cmd": "example_echo", "params": params},
                   "result": str(params.get("text", "")),
               }, event.ctx)
               return

``CMD_SYNTAX``/``CMD_EXECUTE`` follow the normal global Tools switch. Inline plugins intentionally use ``CMD_SYNTAX_INLINE``/``CMD_INLINE`` and can operate independently from the normal switch when the owning plugin design calls for it.

Event API
~~~~~~~~~

All generic plugin events are constants on ``pygpt_net.core.events.Event``. ``Event`` derives from ``BaseEvent`` and provides:

``event.name``
   String event identifier.

``event.data``
   Mutable dictionary payload. Many preprocessing hooks intentionally read this dictionary again after dispatch, so modifying documented fields changes the next stage.

``event.ctx``
   Current ``CtxItem`` when the event belongs to a conversation/tool call.

``event.stop``
   Stops propagation to later handlers. It does not automatically cancel the originating operation unless that caller also checks a cancellation field.

``event.internal``
   Marks internal dispatches where used.

``event.call_id``
   Dispatcher-assigned sequence ID for diagnostics.

For ``INPUT_BEFORE``, use ``event.data["stop"] = True`` to abort the supported normal send path; ``event.stop`` alone is only propagation control.

Complete generic Event reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``AI_NAME``
   Assistant name preparation. Mutable ``data["value"]``.

``AGENT_PROMPT``
   Immediately before an input prompt is passed to an agent runner. Mutable ``data["value"]``.

``AUDIO_INPUT_RECORD_START`` / ``AUDIO_INPUT_RECORD_STOP``
   Compatibility/reserved explicit microphone record notifications. Current UI paths primarily use ``AUDIO_INPUT_RECORD_TOGGLE``.

``AUDIO_INPUT_RECORD_TOGGLE``
   Requests microphone recording toggle. Callers may add ``data["state"]`` and ``data["auto"]``.

``AUDIO_INPUT_STOP``
   Requests immediate audio-input processing stop.

``AUDIO_INPUT_TOGGLE``
   Enables/disables audio input; requested boolean is normally ``data["value"]``.

``AUDIO_INPUT_TRANSCRIBE``
   Requests transcription of ``data["path"]`` by the active audio-input provider; ``event.ctx`` may be a temporary context.

``AUDIO_OUTPUT_STOP``
   Stops active TTS/playback.

``AUDIO_OUTPUT_TOGGLE``
   Compatibility/reserved generic audio-output state hook.

``AUDIO_PLAYBACK``
   Requests playback of ``data["audio_file"]``.

``AUDIO_READ_TEXT``
   Requests synthesis/reading of ``data["text"]``; ``data["cache_file"]`` may provide a preferred cache path.

``BRIDGE_BEFORE``
   Before a prepared request enters the bridge/provider layer. Typical payload: ``mode``, ``context`` and ``extra``.

``CMD_EXECUTE``
   Executes normal plugin commands. ``data["commands"]`` contains parsed calls and ``event.ctx`` is the tool-call context.

``CMD_INLINE``
   Inline-plugin command execution counterpart.

``CMD_SYNTAX``
   Requests normal plugin tool definitions. Append command dictionaries to ``data["cmd"]``. Callers may also provide ``prompt``, ``syntax``, ``mode`` and ``is_expert``.

``CMD_SYNTAX_INLINE``
   Inline-plugin command-definition counterpart.

``CTX_AFTER``
   After model output is attached to the current context and before response lifecycle completion.

``CTX_BEFORE``
   After a context item is prepared but before it is committed/sent through the normal processing path.

``CTX_BEGIN``
   Compatibility hook for context-processing start.

``CTX_END``
   Context processing completed. ``event.ctx`` is the finished item.

``CTX_SELECT``
   Conversation selection. ``data["value"]`` contains the context metadata ID.

``DISABLE``
   Plugin disabled. ``data["value"]`` contains the plugin ID; dispatch may be sent to all plugins.

``ENABLE``
   Plugin enabled. ``data["value"]`` contains the plugin ID.

``FORCE_STOP``
   Global request to stop active plugin/background operations.

``INPUT_ACCEPT``
   After ``INPUT_BEFORE`` accepts the message and before normal send processing. Typical fields: ``value``, ``mode``, ``multimodal_ctx``.

``INPUT_BEFORE``
   Main mutable input preprocessing hook. Typical fields: ``mode``, ``value``, ``multimodal_ctx``, ``stop`` and ``silent``. Modify ``value`` to rewrite the input; set ``data["stop"]`` to abort sending.

``INPUT_BEGIN``
   Earliest generic manual-send hook. Typical fields: ``mode`` and ``force``; ``data["stop"]`` can stop the normal manual-send path.

``MODE_BEFORE``
   Before an inline/temporary mode is finalized. ``data["value"]`` is the mode and ``data["prompt"]`` the prompt; replacing ``value`` can redirect mode selection for that request.

``MODE_SELECT``
   Active mode changed; ``data["value"]`` contains mode ID.

``MODEL_BEFORE``
   Before an inline request's model is finalized. ``data["model"]`` contains the proposed ``ModelItem`` and can be replaced.

``MODEL_SELECT``
   Active model changed; ``data["value"]`` contains model ID.

``MODELS_CHANGED``
   Model registry changed. No required payload; use it to invalidate cached model lists.

``PLUGIN_OPTION_GET``
   Dynamic plugin-value query. ``data["name"]`` is the requested name; the handling plugin writes ``data["value"]``.

``PLUGIN_SETTINGS_CHANGED``
   Plugin settings were saved. No required payload.

``POST_PROMPT``
   Main system prompt has been assembled/personalized, before command syntax is appended. Typical fields: ``mode``, ``reply``, ``internal``, ``value`` and ``is_expert``. ``value`` is mutable.

``POST_PROMPT_ASYNC``
   Late mutable system-prompt hook in the asynchronous bridge worker.

``POST_PROMPT_END``
   Final mutable system-prompt hook immediately before provider execution. Usually the safest event for appending a final instruction.

``PRE_PROMPT``
   Early system-prompt hook. Typical fields: ``mode`` and mutable ``value``.

``SETTINGS_CHANGED``
   Main Settings editor saved changes. No required payload.

``SYSTEM_PROMPT``
   Base/final system prompt assembly. Mutable ``data["value"]`` and ``data["mode"]``.

``TOOL_OUTPUT_RENDER``
   Web-renderer hook for custom tool output. Typical fields: ``tool``, ``content``, ``html`` and ``multiple``. Set ``html`` to supply custom rendering.

``UI_ATTACHMENTS``
   Query/mutate attachment-UI visibility. ``data["mode"]`` and boolean ``data["value"]``.

``UI_VISION``
   Query/mutate inline Vision availability indicator. ``data["mode"]`` and boolean ``data["value"]``.

``USER_NAME``
   User-name preparation. Mutable ``data["value"]``.

``USER_SEND``
   Manual user send after reading the input widget but before attachments/kernel/bridge processing. Mutable ``data["value"]`` plus ``data["mode"]``.

Typical text-message ordering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   INPUT_BEGIN
      -> USER_SEND
      -> INPUT_BEFORE
      -> INPUT_ACCEPT
      -> CTX_BEFORE
      -> PRE_PROMPT
      -> SYSTEM_PROMPT
      -> POST_PROMPT
      -> CMD_SYNTAX / CMD_SYNTAX_INLINE
      -> POST_PROMPT_ASYNC
      -> POST_PROMPT_END
      -> provider/model request
      -> CTX_AFTER
      -> CTX_END

Exact ordering differs for image generation, Realtime, agents, internal calls and tool continuations.

GUI Tool Add-ons
----------------

Base class: ``pygpt_net.tools.base.BaseTool``.

A GUI Tool extends the desktop application. Registering a ``tool`` Add-on does **not** expose a model-callable function; use a plugin for that.

Important attributes are ``id``, ``has_tab``, ``tab_title`` and ``tab_icon``. ``window`` is attached during registration.

.. list-table:: ``BaseTool`` public methods
   :header-rows: 1
   :widths: 30 45 25

   * - Method
     - Purpose
     - Override/call
   * - ``setup()``
     - Initial tool setup while application tools are initialized.
     - Override.
   * - ``post_setup()``
     - Called after plugins/application setup.
     - Override for work requiring fully initialized app state.
   * - ``on_update()``
     - Frequent main-loop update hook.
     - Override; keep lightweight.
   * - ``on_post_update()``
     - Slower post-update hook.
     - Override.
   * - ``on_exit()``
     - Application exit hook.
     - Override for cleanup.
   * - ``on_reload()``
     - Profile/application reload hook.
     - Override to refresh profile-dependent state.
   * - ``handle(event)``
     - Receives global application events before plugin dispatch.
     - Override when the GUI tool reacts to events.
   * - ``attach(window)``
     - Stores main window reference.
     - Called by PyGPT.
   * - ``setup_menu()``
     - Return ``{id: QAction}`` entries added to the Tools menu.
     - Override to add menu actions.
   * - ``setup_dialogs()``
     - Create/register static dialogs.
     - Override when needed.
   * - ``setup_theme()``
     - Apply/refresh theme-specific UI state.
     - Override when needed.
   * - ``get_instance(type_id, dialog_id=None)``
     - Factory hook for dialog instances.
     - Override for dynamic dialogs.
   * - ``as_tab(tab)``
     - Return a QWidget to mount as an output tab.
     - Override for tab-capable tools.
   * - ``add_lang_mapping(target, key, setter='setText', domain=None, on_apply=None)``
     - Registers a live translation mapping for a private/dynamic Qt object.
     - Call after creating dynamic UI objects.
   * - ``apply_lang_mappings()``
     - Re-applies all live mappings and removes dead targets.
     - Normally called by PyGPT; may be called after custom language refresh.
   * - ``get_lang_mappings()``
     - Legacy/static mapping hook returning mapping dictionaries.
     - Override only for legacy/static mapping integration.

Runnable menu-action example:

.. code-block:: python

   from PySide6.QtGui import QAction
   from PySide6.QtWidgets import QMessageBox
   from pygpt_net.tools.base import BaseTool

   class ExampleTool(BaseTool):
       def __init__(self):
           super().__init__()
           self.id = "example_tool"

       def setup_menu(self):
           action = QAction("External example", self.window)
           action.triggered.connect(
               lambda: QMessageBox.information(self.window, "Example", "It works")
           )
           return {self.id: action}

LLM Add-ons
-----------

Base class: ``pygpt_net.provider.llms.base.BaseLLM``.

The external ``llm`` registry primarily supplies LlamaIndex/embedding wrappers and provider-owned configuration. It is not automatically a complete new native Chat SDK bridge; native Chat provider paths can require additional core/provider integration. For a normal external provider, implement the LlamaIndex methods needed by the modes you want to support and advertise only those capabilities in ``self.type``.

Important attributes are ``id``, ``name``, ``description``, ``type``, ``config_id`` and ``window``. Registration calls ``bind(window)`` when available.

.. list-table:: ``BaseLLM`` public methods
   :header-rows: 1
   :widths: 31 46 23

   * - Method
     - Purpose
     - Typical action
   * - ``setup()``
     - Returns provider-owned ``settings`` and ``remote_tools`` schema.
     - Override to expose API key/base/extra settings and provider-side tools.
   * - ``get_remote_tools_schema()``
     - Returns normalized provider remote-tool fields from ``setup()``.
     - Usually inherit.
   * - ``get_remote_tools()``
     - Returns schema fields marked as selectable tools.
     - Usually inherit.
   * - ``get_remote_tool_config(key, default)``
     - Reads provider remote-tool config with declared defaults.
     - Call from provider runtime.
   * - ``set_remote_tool_config(key, value)``
     - Updates remote-tool config in memory.
     - Runtime/editor use.
   * - ``is_remote_tool_enabled(tool_id)`` / ``set_remote_tool_enabled(...)``
     - Reads/writes a provider tool toggle.
     - Provider remote tools.
   * - ``supports_remote_tool(model, tool_id)``
     - Capability policy hook.
     - Override when availability depends on model/tool.
   * - ``bind(window)``
     - Attaches window/config and synchronizes provider config.
     - Called by registry.
   * - ``get_config_id()``
     - Logical key under ``config.providers``.
     - Override/use ``config_id`` when several wrappers share config.
   * - ``get_settings_schema()``
     - Normalized provider settings schema.
     - Usually inherit.
   * - ``has_config(key)``
     - Whether a provider setting exists in schema.
     - Runtime checks.
   * - ``requires_api_key()``
     - Whether UI should require provider API key.
     - Override when key is optional/local.
   * - ``get_config(key, default)`` / ``set_config(key, value)``
     - Reads/writes provider-scoped configuration.
     - Preferred provider configuration API.
   * - ``sync_config()``
     - Materializes missing schema defaults into active config.
     - Normally registration/settings infrastructure.
   * - ``init(window, model, mode, sub_mode=None)``
     - Compatibility initialization hook for provider/model/mode.
     - Override only when provider needs explicit initialization.
   * - ``init_embeddings(window, env=None)``
     - Embeddings initialization hook.
     - Override when needed.
   * - ``parse_args(options, window=None)``
     - Parses Advanced ``**kwargs`` style model options.
     - Use/inherit for configurable constructors.
   * - ``get_env_override(window, env, names)``
     - Reads declared model Advanced ENV override values.
     - Helper for wrappers honoring per-model env overrides.
   * - ``get_openai_compatible_env_names()``
     - Common API key/base env names for OpenAI-compatible wrappers.
     - Override for compatible providers with custom names.
   * - ``prepare_openai_compatible_args(...)``
     - Resolves model/provider/global values into LlamaIndex constructor args.
     - Reuse for OpenAI-compatible providers.
   * - ``prepare_openai_compatible_embedding_args(...)``
     - Equivalent helper for embeddings.
     - Reuse for OpenAI-compatible embedding providers.
   * - ``log_llama_create(...)``
     - Logs final LlamaIndex constructor args when API-input logging is enabled.
     - Diagnostic helper.
   * - ``completion(window, model, stream=False)`` / ``chat(...)``
     - Legacy compatibility provider methods.
     - Implement only for a flow that still uses them.
   * - ``llama_completion(window, model, stream=False)``
     - Returns a LlamaIndex LLM for plain-text completion.
     - Override when Completion/RAG completion is supported.
   * - ``llama(window, model, stream=False)``
     - Main LlamaIndex LLM constructor hook.
     - Primary override for RAG/LlamaIndex chat/query.
   * - ``llama_chat_with_files(...)``
     - Compatibility helper for LlamaIndex + Computer Use file flows.
     - Usually inherit/delegate.
   * - ``llama_with_computer_runtime(...)``
     - Returns an LLM bound to shared Computer Use runtime.
     - Override/delegate when provider supports that integration.
   * - ``llama_agent(..., allow_remote_tools=True, force_computer_use=False)``
     - LlamaIndex LLM constructor for Agents v2/agent workflows.
     - Override/delegate if agents need provider-specific tools.
   * - ``llama_multimodal(window, model, stream=False)``
     - Returns multimodal LlamaIndex provider instance.
     - Override for image-capable LlamaIndex path.
   * - ``get_embeddings_model(window, config=None)``
     - Returns a LlamaIndex ``BaseEmbedding`` instance.
     - Override when provider supports embeddings.
   * - ``get_openai_agent_provider(window, model, stream=False)``
     - Compatibility hook for OpenAI-agents provider object.
     - Specialized providers only.
   * - ``get_models(window)``
     - Optional provider model-list discovery.
     - Override for live import/model discovery.
   * - ``get_client(window)``
     - Optional raw SDK/client accessor.
     - Override when useful.
   * - ``inject_llamaindex_http_clients(args, cfg)``
     - Adds configured HTTP clients/timeouts to LlamaIndex LLM args.
     - Helper normally inherited.
   * - ``get_embeddings_timeout(cfg)``
     - Returns global embeddings timeout.
     - Helper.
   * - ``inject_llamaindex_embedding_http_clients(args, cfg)``
     - Adds HTTP clients/timeouts to embedding args.
     - Helper normally inherited.

A minimal offline tutorial can return LlamaIndex ``MockLLM`` and ``MockEmbedding``; see ``examples/addons/llms/example_llm``.

Vector-store Add-ons
--------------------

Base class: ``pygpt_net.provider.vector_stores.base.BaseStore``.

Important attributes: ``id`` (provider ID), ``prefix`` (directory-name prefix) and ``indexes`` (runtime cache).

.. list-table:: ``BaseStore`` public methods
   :header-rows: 1
   :widths: 31 46 23

   * - Method
     - Purpose
     - Notes
   * - ``index_from_store(vector_store, storage_context, llm=None, embed_model=None)``
     - Builds ``VectorStoreIndex`` from a vector-store backend.
     - Reusable helper for backend adapters.
   * - ``index_from_empty(embed_model=None)``
     - Builds an empty ``VectorStoreIndex``.
     - Useful in ``create()``.
   * - ``attach(window=None)``
     - Stores main window reference.
     - Called by storage registry.
   * - ``get_path(id)``
     - Resolves the provider's persistent index path below the PyGPT index directory.
     - Uses ``prefix + id``.
   * - ``exists(id=None)``
     - Checks whether the provider path exists.
     - May be overridden for remote stores.
   * - ``create(id)``
     - Create/persist an empty index.
     - Implement.
   * - ``get(id, llm=None, embed_model=None)``
     - Load/return an index instance.
     - Implement.
   * - ``store(id, index=None)``
     - Persist current index state.
     - Implement.
   * - ``remove(id)``
     - Removes cached/local index data.
     - Inherited behavior works for directory-backed stores.
   * - ``truncate(id)``
     - Clears an index; default delegates to ``remove``.
     - Override for remote backends.
   * - ``remove_document(id, doc_id)``
     - Deletes a reference document without requiring the configured embedding provider.
     - Inherited implementation uses a mock embedding model for delete-only load.

See the persistent local tutorial in ``examples/addons/vector_stores/example_vector_store``.

Data-loader Add-ons
-------------------

Base class: ``pygpt_net.provider.loaders.base.BaseLoader``.

Important attributes:

* ``id`` and ``name``;
* ``extensions`` for file suffixes;
* ``type`` containing ``file`` and/or ``web``;
* ``instructions`` for web-index handling guidance;
* ``init_args`` plus ``init_args_labels``, ``init_args_types`` and ``init_args_desc`` for configurable reader constructor arguments;
* ``allow_compiled`` compatibility flag for loaders with special runtime restrictions. Normal modern Add-ons should leave it ``True`` unless the reader genuinely cannot run in that environment.

.. list-table:: ``BaseLoader`` public methods
   :header-rows: 1
   :widths: 30 48 22

   * - Method
     - Purpose
     - Typical action
   * - ``attach_window(window)``
     - Stores main window reference.
     - Called by indexing registry.
   * - ``set_args(args)``
     - Applies user-configured loader constructor values.
     - Normally called by settings/indexing layer.
   * - ``explode(value)``
     - Splits a comma-separated option into a stripped list.
     - Helper for list-like options.
   * - ``get_args()``
     - Combines ``init_args`` defaults with configured values.
     - Use in ``get()``.
   * - ``prepare_args(**kwargs)``
     - Hook to transform arguments passed to reader ``load_data``.
     - Override for source-specific argument normalization.
   * - ``get_external_id(args=None)``
     - Returns unique external/web content identifier; default uses ``url``.
     - Override for non-URL external sources.
   * - ``is_supported_attachment(source)``
     - Whether a source can be handled as an attachment.
     - Override when attachment use is supported.
   * - ``get()``
     - Returns a LlamaIndex ``BaseReader`` instance.
     - Implement.

The tutorial ``.example`` loader in ``examples/addons/loaders/example_loader`` returns normal LlamaIndex ``Document`` objects with ``metadata``.

Audio-input Add-ons
-------------------

Base class: ``pygpt_net.provider.audio_input.base.BaseProvider``.

Important attributes: ``id``, ``name`` and ``plugin``. The owning Audio input plugin is attached before ``init_options()`` is called, so provider settings are normally declared with ``self.plugin.add_option(...)``.

.. list-table:: Audio-input provider public methods
   :header-rows: 1
   :widths: 30 48 22

   * - Method
     - Purpose
     - Typical action
   * - ``init(plugin)``
     - Attaches owning plugin and calls ``init_options()``.
     - Called by PyGPT.
   * - ``attach(plugin)``
     - Stores owning plugin.
     - Called by ``init``.
   * - ``init_options()``
     - Declares provider-specific plugin settings.
     - Override.
   * - ``transcribe(path)``
     - Converts the supplied audio-file path to text.
     - Implement; return string.
   * - ``is_configured()``
     - Reports whether required credentials/packages/settings are available.
     - Implement.
   * - ``get_config_message()``
     - User-facing explanation when not configured.
     - Override when ``is_configured`` can be false.

Do not hard-code a capture filename; always use the path supplied to ``transcribe``. The runnable tutorial reads WAV metadata and returns a text result without external dependencies.

Audio-output Add-ons
--------------------

Base class: ``pygpt_net.provider.audio_output.base.BaseProvider``.

.. list-table:: Audio-output provider public methods
   :header-rows: 1
   :widths: 31 47 22

   * - Method
     - Purpose
     - Typical action
   * - ``init(plugin)`` / ``attach(plugin)``
     - Attach owning Audio output plugin and initialize options.
     - Called by PyGPT.
   * - ``init_options()``
     - Declare provider-specific settings via owning plugin.
     - Override.
   * - ``speech(text)``
     - Synthesizes audio. Return generated file path, or ``None`` when provider handles playback itself.
     - Implement.
   * - ``prepare_output_path(extension=None)``
     - Creates a unique path under PyGPT's temporary audio-output directory and rotates old files.
     - Call before writing generated audio.
   * - ``is_configured()``
     - Reports provider readiness.
     - Implement.
   * - ``get_config_message()``
     - User-facing setup message.
     - Override.

Use ``prepare_output_path()`` instead of a fixed filename. The runnable tutorial generates a small WAV tone so the complete path can be tested without a cloud TTS API.

Web-search Add-ons
------------------

Base class: ``pygpt_net.provider.web.base.BaseProvider``.

Set ``type = ["search_engine"]`` for a normal search backend.

.. list-table:: Web provider public methods
   :header-rows: 1
   :widths: 31 47 22

   * - Method
     - Purpose
     - Typical action
   * - ``init(plugin)`` / ``attach(plugin)``
     - Attach owning Web search plugin and initialize provider options.
     - Called by PyGPT.
   * - ``init_options()``
     - Declare provider-specific plugin settings.
     - Override.
   * - ``search(query, limit=10, offset=0)``
     - Execute search and return a list of result URLs.
     - Implement.
   * - ``is_configured(cmds)``
     - Reports whether the provider can execute the requested Web-plugin commands.
     - Implement.
   * - ``get_config_message()``
     - Setup/configuration message when unavailable.
     - Override.

The tutorial provider calls MediaWiki OpenSearch and returns real Wikipedia URLs.

Agent Add-ons
-------------

Base class: ``pygpt_net.provider.agents.base.BaseAgent``. External agent providers are used by the **Custom agents**/legacy LlamaIndex agent registry, not by the newer Agents v2 workflow-profile editor itself.

Important attributes: ``id``, ``type``, ``mode``, ``name``, ``custom_id``, ``custom_options`` and ``custom_schema``.

.. list-table:: ``BaseAgent`` public methods
   :header-rows: 1
   :widths: 32 46 22

   * - Method
     - Purpose
     - Typical action
   * - ``get_mode()``
     - Returns runtime mode identifier.
     - Usually inherit after setting ``mode``.
   * - ``get_agent(window, kwargs)``
     - Builds/returns runtime agent/workflow object.
     - Core override for a new provider.
   * - ``set_id(id)``
     - Sets custom runtime ID override.
     - Custom-agent builder/runtime use.
   * - ``set_schema(schema)``
     - Sets a custom workflow schema.
     - Custom flow providers.
   * - ``set_options(options)`` / ``get_options()``
     - Stores/returns provider option schema.
     - Override ``get_options`` for preset UI/defaults.
   * - ``run(window, agent_kwargs=None, previous_response_id=None, messages=None, ctx=None, stream=False, bridge=None)``
     - Async direct-run contract used by agent providers that own execution.
     - Implement for the corresponding provider mode; workflow providers may instead be run through returned workflow object.
   * - ``get_option(preset, section, key)``
     - Resolves provider option from preset with default fallback.
     - Use inside workflow construction.
   * - ``append_security_rule(prompt)``
     - Static helper that keeps the required legacy-agent security boundary exactly once at prompt end.
     - Use when building custom agent prompts.
   * - ``extract_system_prompt_extra(final_prompt, raw_prompt)``
     - Static helper extracting runtime/plugin additions from final bridge prompt.
     - Custom nested-agent prompt construction.
   * - ``get_system_prompt_extra(kwargs)``
     - Resolves runtime prompt additions from agent kwargs/context.
     - Use instead of duplicating the preset/base prompt.
   * - ``append_system_prompt_extra(prompt, kwargs)``
     - Appends runtime additions and mandatory security rule once.
     - Recommended prompt-finalization helper.
   * - ``resolve_model_option(window, preset, section, default_model)``
     - Resolves optional per-section model override with safe fallback.
     - Agent roles/sections.
   * - ``get_default(section, key)``
     - Returns default value from provider option schema.
     - Fallback helper.
   * - ``get_default_prompt()``
     - Returns ``__prompt__`` from options when present.
     - Provider default prompt.

The runnable tutorial inherits the built-in LlamaIndex ``ModeAgent("base")`` workflow and changes its external identity/default prompt. This is useful when your extension changes behavior/options but does not need to duplicate PyGPT's workflow runner. For a completely new runtime, derive directly from ``BaseAgent`` and implement ``get_agent``/the mode-specific execution contract.

Theme Add-ons
-------------

A theme package has ``"type": "theme"`` and no Python ``entrypoint``. Files may live directly in the Add-on root or in a ``theme`` subdirectory. PyGPT deploys them into the normal profile theme directory.

Example:

.. code-block:: text

   example-dark/
   ├── manifest.json
   └── theme/
       ├── app.css
       ├── app.xml
       └── chat.css

The Add-on ID becomes the theme ID. The normal ``-dark`` / ``-light`` suffix rules determine runtime Light/Dark compatibility and are the same rules described in **Extending PyGPT -> Custom themes and styles**.

Theme files:

* ``app.css`` - Qt/QSS application styling;
* ``app.xml`` - qt-material palette when supplied;
* ``chat.css`` - chat/WebView CSS.

Only files present in the package are deployed.

Locale Add-ons
--------------

A locale package has ``"type": "locale"`` and no Python entry point. Put one or more normal PyGPT locale ``.ini`` files in a ``locale`` subdirectory:

.. code-block:: text

   example-locale/
   ├── manifest.json
   └── locale/
       └── locale.en.ini

The files are deployed into the profile locale override directory and loaded by the existing translation mechanism.

Example:

.. code-block:: ini

   [LOCALE]
   my.addon.example = Hello from an Add-on

Using a custom launcher instead of an installed Add-on
------------------------------------------------------

Installed Add-ons are recommended for redistributable profile-scoped extensions. A custom launcher remains useful when you control application startup and want to create/register objects programmatically.

All runtime Add-on types map to the same launcher methods used by the external loader:

.. code-block:: text

   plugin       -> Launcher.add_plugin()
   llm          -> Launcher.add_llm()
   vector_store -> Launcher.add_vector_store()
   loader       -> Launcher.add_loader()
   audio_input  -> Launcher.add_audio_input()
   audio_output -> Launcher.add_audio_output()
   web          -> Launcher.add_web()
   tool         -> Launcher.add_tool()
   agent        -> Launcher.add_agent()

See **Extending PyGPT** for launcher examples and model/theme customization outside the external package format.

Compatibility and API-version guidance
--------------------------------------

* Set ``min_app_version`` to the oldest PyGPT release you have actually tested.
* Treat documented base-class/event APIs as the compatibility surface; deeper ``window.core``/``window.controller`` calls should be considered version-sensitive.
* Avoid importing private helpers with leading underscores.
* Keep external dependencies bounded where API/ABI compatibility matters.
* Do not bundle third-party site-packages inside the Add-on unless their license and loading behavior require it; prefer ``external_dependencies`` and Package Manager.
* Keep a small smoke test that imports the entry point and instantiates the object without requiring the main window. ``window``/owning plugin is attached later.
* Test source and packaged PyGPT builds when your dependency includes compiled/native extensions.

Runnable examples
-----------------

Main PyGPT repository:

.. code-block:: text

   examples/addons/plugins/example_plugin
   examples/addons/tools/example_tool
   examples/addons/llms/example_llm
   examples/addons/vector_stores/example_vector_store
   examples/addons/loaders/example_loader
   examples/addons/audio_input/example_audio_input
   examples/addons/audio_output/example_audio_output
   examples/addons/web/example_web
   examples/addons/agents/example_agent
   examples/addons/themes/example-extension-dark
   examples/addons/locale/example-locale

The public ``py-gpt-addons`` repository contains the same tutorial-oriented package layout so Add-on authors can start from the distribution format they will ultimately publish.
