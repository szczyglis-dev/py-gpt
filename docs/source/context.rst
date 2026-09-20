Context and memory
==================

Short and long-term memory
--------------------------
**PyGPT** features a continuous chat mode that maintains a long context of the ongoing dialogue. It preserves the entire conversation history and automatically appends it to each new message (prompt) you send to the AI. Additionally, you have the flexibility to revisit past conversations whenever you choose. The application keeps a record of your chat history, allowing you to resume discussions from the exact point you stopped.

Settings layout
---------------

The ``Config -> Settings -> Context`` section is divided into ``General``, ``Tools``, and ``Advanced handling`` tabs. ``General`` contains the main context-size sliders, ``Tools`` contains tool-call storage/replay controls, and ``Advanced handling`` contains the experimental long-context checkpoint settings.

Advanced context handling (experimental)
-----------------------------------------

.. warning::

   **Advanced context handling is experimental.** It changes how long model-facing histories are compacted and continued. Keep it disabled if you need the legacy history-selection behavior, and verify important long-running workflows when enabling it for production work.

Advanced context handling is designed for conversations and agent workflows that approach the model's usable input-context limit. Enable it in ``Config -> Settings -> Context -> Advanced handling -> Enable advanced context handling``. The full durable conversation remains stored in the SQLite history; only the history sent to the model is compacted.

When the unsummarized model-facing conversation reaches the configured checkpoint threshold, PyGPT creates compact **conversation-scoped continuation notes** from older completed turns and advances a checkpoint. Newer turns remain verbatim in the active context tail, while turns already represented by the checkpoint are omitted from subsequent model-facing history. The notes preserve useful state such as goals, constraints, decisions, completed work, important findings, identifiers, and pending work. They are stored in the ``memory_ctx`` table with one row per conversation (``ctx_meta``).

The feature is independent from global/project long-term memory. Conversation continuation notes belong only to one conversation and are never shared automatically with other chats in the same project. They can also be accessed explicitly through ``memory_ctx_get``, ``memory_ctx_add`` and ``memory_ctx_replace``. In Chat with Agents these tools remain available as core context tools when advanced context handling is enabled even if the optional ``Memory (inline)`` plugin is disabled; the Memory plugin exposes the same conversation-note operations to its supported inline-tool flow.

For Chat with Agents, PyGPT additionally uses bounded rolling LlamaIndex memory. The main agent's compact continuation state is persisted to ``memory_ctx`` so it can survive context-window rollover and later turns, while worker rolling summaries remain runtime-local and do not overwrite the canonical conversation notes. Stateful provider chains are restarted when necessary after a checkpoint so provider-side history does not silently continue to grow beyond the locally compacted window. The Chat with Agents setting ``Restore full workflow history on next request`` is respected here as well: when it is disabled, checkpoint token estimates and continuation snapshots use each completed turn's final response instead of its full persisted workflow.

The related settings are:

* ``Checkpoint threshold (%)`` - starts compaction when the unsummarized model-facing history approaches this percentage of the usable input budget. Default: ``75``.
* ``Context tail after checkpoint (%)`` - target size for the recent verbatim tail after a checkpoint. Default: ``45``.
* ``Maximum continuation note characters`` - character safety ceiling for compact per-conversation notes. Default: ``24000``; additional token-aware clipping is applied when required by the selected model.

Handling multiple contexts
---------------------------
On the left side of the application interface, there is a panel that displays a list of saved conversations. You can save numerous contexts and switch between them with ease. This feature allows you to revisit and continue from any point in a previous conversation. **PyGPT** automatically generates a summary for each context, akin to the way ``ChatGPT`` operates and gives you the option to modify these titles itself.

Projects and project data workdirs
----------------------------------

Conversations can be organized into projects. By default, every project uses the
shared profile ``data`` directory. When creating a project, leave
``Use shared workdir`` enabled to keep this behavior, or disable it and select a
custom directory for that project. Existing projects can be changed from the
project context menu with ``RMB -> Edit``. Hovering a project item in the context
list shows the effective data workdir used by that project.

A project workdir overrides **only the logical ``data`` directory** used by
conversations in that project. It does not replace the application's/profile's
main workdir. Configuration files, ``db.sqlite``, ``tmp``, ``cache``, ``css``,
``locale``, fonts, logs and other profile-level paths continue to use the base
profile workdir. Conversations outside projects, and projects with
``Use shared workdir`` enabled, use the normal ``<profile workdir>/data``
directory.

The active project data workdir is resolved at runtime. The ``Files`` tab,
``Files I/O``, Python interpreter, filesystem-aware tools and model-facing data
paths use the data directory that belongs to the current conversation. In
Docker sandboxes the same host directory is exposed as ``/data``. Switching to
a conversation in another project therefore changes the effective ``data``
root without changing the application's base workdir.

.. important::
   The internal ``tmp`` directory always remains in the base profile workdir.
   ``img``, ``capture`` and ``upload`` also remain in their normal base-profile
   locations unless ``Store images, captures, and uploads in the workdir data directory``
   is enabled. When that option is enabled, those three directories follow the
   active project data workdir.


Clearing history
-----------------

You can clear the entire memory (all contexts) by selecting the menu option:

.. code-block:: ini

   File -> Clear history...


Context storage
-----------------
On the application side, the context is stored in the ``SQLite`` database located in the base profile/application workdir (``db.sqlite``). A project data-workdir override does not move this database.

Tool call storage
~~~~~~~~~~~~~~~~~

Tool requests and results can contain large payloads, for example file contents, generated data, or long command output. These payloads can significantly increase the size of the context database. Their persistence can be configured in:

.. code-block:: ini

   Config -> Settings -> Context -> Tools -> Store tool calls in database

The available modes are:

* ``Do not store`` - tool calls and results are used normally during the live request, but are not written to durable history.
* ``Store truncated`` - keeps the tool-call structure for history and UI rendering, but recursively truncates every stored string value in tool input/output to 20 characters and appends ``....``. Object keys and nesting are preserved.
* ``Store full input/output`` - stores complete tool requests and results, matching the previous behavior. This is the default for backward compatibility.

The storage policy applies to all modes that use tools, including Chat, Chat with Files, legacy Agents, and Chat with Agents. It affects only durable database persistence.

Tool-call rendering is configured separately in ``Settings -> Chats -> Render -> Display tool calls JSON``. When enabled (default), completed calls can be shown as expandable request/response JSON blocks. When disabled, those blocks are hidden and live tool activity is shown only as one aggregated ``Tool/Tools`` status row. This display option does not change tool execution, persistence, or replay to the model.

``Restore tool calls in runtime`` controls whether completed tool calls/results from earlier turns are replayed to the model while the current conversation remains active in memory. It is enabled by default and is independent from the database storage mode. Disabling it removes completed tool protocol from later runtime turns, but does not interrupt the tool-call/result sequence that is currently in progress.

By default, historical tool calls and results loaded from the database are not replayed to the model on later turns. To restore persisted tool protocol after reloading a conversation, enable ``Restore tool calls from history`` in ``Settings -> Context -> Tools``. This option applies only to history restored from the database, requires ``Store full input/output``, and is ignored when tool calls are not stored or are stored truncated.
