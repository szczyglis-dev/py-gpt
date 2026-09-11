Debugging and Logging
======================

Most diagnostic and logging options are available in ``Config -> Settings -> Debug``. To expose the developer tools in the main menu, enable ``Show debug menu`` in this section.

Logging
-------

PyGPT writes application logs to:

.. code-block:: ini

    %workdir%/app.log

The log level can be selected directly in ``Config -> Settings -> Debug -> Log Level``. The available levels are:

* ``ERROR`` - the default level. Logs errors and uncaught exceptions.
* ``WARNING`` - logs warnings in addition to errors.
* ``INFO`` - logs normal diagnostic and operational information in addition to warnings and errors.
* ``DEBUG`` - the most verbose level. Intended for detailed troubleshooting and development.

The log level can also be forced from the command line. Command-line ``--debug`` takes precedence over the setting selected in the application and is especially useful when diagnosing startup problems:

.. code-block:: console

    python3 run.py --debug=1

or:

.. code-block:: console

    python3 run.py --debug=2

``--debug=1`` enables the ``INFO`` level and ``--debug=2`` enables the ``DEBUG`` level. The same arguments can be appended when launching a compiled build, for example ``./pygpt --debug=2``.

Additional logging switches are available in ``Config -> Settings -> Debug``:

* ``Log and debug context`` - logs detailed conversation-context input, output and processing information.
* ``Log and debug events`` - logs application event dispatch and handling.
* ``Log plugin usage to console`` - logs plugin execution and usage details.
* ``Log image and video generation to console`` - logs image and video generation activity.
* ``Log attachments usage to console`` - logs attachment processing and usage details.
* ``Log Agents usage to console`` - logs agent and expert execution details.
* ``Log Chat with Agents workflow`` - logs a concise, human-readable Chat with Agents workflow trace, including important orchestration events, agent operations, tool names, statuses, waits and response previews. It omits stream chunks, full tool definitions and large JSON payloads.
* ``Chat with Agents verbose (log full flow to console)`` - logs the complete Chat with Agents orchestration flow, including full system prompts, available tools and tool calls, worker operations and states, inputs, outputs, RAG context and workflow lifecycle. This output can contain sensitive prompt or tool data.
* ``Log LlamaIndex usage to console`` - logs LlamaIndex indexing, querying and related activity.
* ``Log Realtime sessions to console`` - logs real-time audio session activity and provider details.
* ``Log legacy API usage to console`` - logs activity from legacy API code paths.

Enable only the additional traces you need. Some of them can produce a large amount of console output and may include prompts, tool arguments, retrieved context or other application data.

Debug Menu
----------

The ``Debug`` menu is hidden by default. To enable it, go to ``Config -> Settings -> Debug`` and turn on ``Show debug menu``.

The menu contains the following diagnostic tools:

* ``Open Logger`` - opens the real-time Logger window and its built-in developer console. See the ``Logger`` section below.
* ``Render...`` - toggles renderer debug information and refreshes the current conversation output. This is useful when diagnosing message/PID/context rendering issues.
* ``DB Viewer`` - opens the internal SQLite database browser/editor described in ``Access to database``.
* ``View log file (app.log)`` - opens the current ``app.log`` in the built-in viewer. The viewer can reload or clear the log and can open it in an external editor.
* ``Fixture: stream`` - enables the bundled fake OpenAI stream fixture for testing streaming and rendering behavior without relying on a normal live stream response.
* ``Agent...`` - displays internal agent state, including registered LlamaIndex agent providers and legacy agent execution state.
* ``Legacy...`` - displays diagnostic state for legacy assistant/thread and remote-store related components.
* ``Files / attachments...`` - displays attachment definitions and attachment-related state for the available modes.
* ``Config...`` - displays configuration paths, workdirs, active profile, registered fonts, Settings sections/options and the current values of application configuration keys.
* ``Context...`` - displays the current conversation/context state, recent bridge calls, reply queue state, system prompt, commands/functions, attachment context, current metadata and conversation items.
* ``Events...`` - displays registered application, control, kernel, render and plugin events together with available voice-control commands.
* ``Indexes...`` - displays current index/storage state, configured indexes, database counters, loaders, temporary indexes and indexing metadata.
* ``Kernel...`` - displays kernel state such as busy/halt flags, status, state and the latest stack information.
* ``Models...`` - displays model configuration, model capabilities, editor state and native tool-call status.
* ``Plugins...`` - displays the current plugin registry and plugin state.
* ``Presets...`` - displays preset editor state and the loaded preset definitions and paths.
* ``Tabs...`` - displays tab/column/PID state and context-to-PID mappings; tab debugging remains enabled while this debug view is active.
* ``UI...`` - displays registered UI objects and mappings, including menus, nodes, dialogs, editors, tabs, splitters and language mappings.
* ``Chromium`` - contains Chromium/WebEngine-related diagnostic pages for renderer, GPU, sandbox, networking, media, WebRTC, processes and other Chromium internals.
* ``Open DevTools`` - opens Chromium DevTools for the current Web renderer output when the web rendering engine is active.

Most state viewers provide ``Refresh`` and ``Realtime`` controls. ``Refresh`` reloads the current diagnostic snapshot, while ``Realtime`` keeps active debug views updated as the application state changes.

Logger / Console
----------------

``Debug -> Open Logger`` opens a live diagnostic window. Messages emitted through PyGPT's debug/logger subsystem are appended to this window with timestamps; messages originating from worker threads are additionally marked with the thread identifier. The window also contains a small developer console with command history and TAB completion.

The following console commands are available:

* ``clr`` - clears the Logger output.
* ``mem`` - runs garbage collection and prints memory diagnostics, including process memory usage, widget/thread counts and additional object statistics when the optional ``pympler`` package is installed.
* ``free`` - clears the current temporary output state and forces memory cleanup.
* ``css`` - reloads the active theme/CSS without restarting the application.
* ``lang`` - reloads the language/translation data.
* ``oclr`` - closes the currently initialized OpenAI client, if one exists.
* ``dump(object|expr)`` - evaluates a Python expression in the running application process and prints its result. This is a developer command and should only be used with trusted expressions.
* ``js(expr)`` - evaluates a JavaScript expression in the current Web renderer. It is available only when the web rendering engine is active.
* ``help``, ``/help`` or ``/h`` - prints the built-in console help.
* ``quit``, ``exit`` or ``/q`` - closes PyGPT.

The console help also lists JavaScript-side debug switches available under ``window.*`` for stream, Markdown language and code/markup debugging: ``STREAM_DEBUG``, ``MD_LANG_DEBUG`` and ``CM_DEBUG``.

Access to database
------------------

PyGPT stores internal application data in the SQLite database located at ``%workdir%/db.sqlite``. A built-in database browser/editor is available for debugging and development.

To open it:

#. Go to ``Config -> Settings -> Debug``.
#. Enable ``Show debug menu``.
#. Open ``Debug -> DB Viewer`` from the main menu.

The DB Viewer allows you to browse, search, sort and edit records in the supported internal tables. Select a cell to display its full value in the editor on the right, then use ``Save/update`` to write the changed value back to the database. Rows can also be deleted, and the ``Actions`` menu provides operations for deleting all records or truncating the selected table. Automatic database backup before write/delete operations is enabled by default in the viewer.

The following tables are available:

* ``ctx_meta`` - conversation/thread metadata, including titles, modes, models, timestamps, status, project/group assignment, indexing state and provider-related IDs.
* ``ctx_item`` - individual conversation turns containing user input, assistant output, tool/results metadata, attachments, files, URLs, images, token usage and other per-message data.
* ``ctx_item_partial`` - persistent logical fragments/partials of assistant responses associated with a conversation item.
* ``ctx_item_partial_task`` - tasks and tool calls attached to response partials, including tool-call IDs, inputs, outputs and additional task metadata.
* ``ctx_group`` - conversation groups/projects and their project-level metadata/additional context.
* ``calendar_note`` - day notes stored by the built-in Calendar.
* ``notepad`` - pages and contents of the built-in Notepad, including highlights and UI state.
* ``memory`` - long-term data used by the ``Memory (inline)`` plugin; stores the global memory and separate per-project memories.
* ``idx_ctx`` - indexing metadata that maps stored conversations to documents in configured vector indexes.
* ``idx_file`` - indexing metadata for local files embedded into vector indexes.
* ``idx_external`` - indexing metadata/content records for external or web sources added to indexes.
* ``idx_proj`` - project-index tracking data, including the project index ID and incremental indexing cursors.
* ``remote_store`` - metadata for remote provider-side stores, such as remote vector stores, including provider, status, usage and synchronization information.
* ``remote_file`` - metadata for files uploaded to remote providers and their association with remote stores or threads.
* ``config`` - internal database key/value parameters, such as the database migration version; this is separate from the main ``config.json`` application configuration.

.. warning::

   The DB Viewer edits the live application database. Incorrect changes can break conversation history, indexes, project relations or other application state. Keep automatic backup enabled unless you intentionally want to disable it.

Debugging compiled builds
-------------------------

When a compiled build crashes, fails during startup or behaves differently from the source/PyPI version, launch it directly from a terminal instead of a desktop shortcut. This keeps the process attached to the console so startup messages, Python tracebacks, Qt/WebEngine diagnostics and other stdout/stderr output remain visible.

For a compiled Linux archive, open a terminal in the extracted application directory and run:

.. code-block:: console

    ./pygpt

For a Snap installation, run the application through its executable in ``/snap/bin``:

.. code-block:: console

    /snap/bin/pygpt

For an AppImage, make the downloaded file executable if necessary and launch that file directly from the terminal:

.. code-block:: console

    chmod +x ./PyGPT-X.X.X-x86_64.AppImage
    ./PyGPT-X.X.X-x86_64.AppImage

Use the actual AppImage filename if the version or architecture is different.

On Windows, open ``Command Prompt`` or ``PowerShell`` and run the installed executable directly. For example, if PyGPT is installed under the current user's roaming application-data directory:

.. code-block:: console

    C:\Users\<USER>\AppData\Roaming\PyGPT\PyGPT.exe

The exact installation path can differ depending on the package/version. If necessary, open the properties of the PyGPT shortcut and use the executable path shown in ``Target``.

You can combine compiled-build debugging with the logging arguments described above, for example:

.. code-block:: console

    ./pygpt --debug=2

or on Windows:

.. code-block:: console

    C:\Users\<USER>\AppData\Roaming\PyGPT\PyGPT.exe --debug=2

This is particularly useful for problems that occur before the graphical Logger or ``Debug`` menu can be opened.
