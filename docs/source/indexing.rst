Indexing and RAG
================

PyGPT uses LlamaIndex and a vector store to provide persistent RAG data for
``Chat with Files`` and related plugins. File indexing and conversation-context
indexing are separate workflows and can be configured independently in
``Settings -> Indexes / LlamaIndex``.

Index types
-----------

PyGPT uses three related index concepts:

* **Configured indexes** are the normal persistent indexes listed in
  ``Settings -> Indexes / LlamaIndex -> Indexes``. They can contain files,
  external data, and indexed conversation context.
* **Project indexes** are isolated persistent indexes created automatically for
  projects. They are shown to the user as ``Current project`` and are not added
  to the normal configured index list.
* **Temporary indexes** are created in memory for operations such as querying a
  single attachment or using the Files I/O ``query_file`` tool. They are not
  persisted as normal indexes.

.. important::
   Removing an item from the normal ``Indexes`` list removes only its
   configuration entry. It does not delete the already stored vector data. Use
   ``Clear and truncate`` when you want to permanently remove index data.

File indexing
-------------

The ``File indexing`` tab controls how files and directories are embedded into
persistent indexes. Files can be indexed from the Files view with
``RMB -> Embed into index``, from the Indexer tool, or by supported plugins.

The main options include recursive directory indexing, replacement of old
versions during re-indexing, excluded extensions, stop-on-error behavior, and
custom metadata for file and web/external documents.

The Files view is project-aware. If the active conversation belongs to a project
with a custom data workdir, the view uses that directory as its filesystem root;
outside projects, or when ``Use shared workdir`` is enabled, it uses the shared
``<profile workdir>/data`` directory. File-indexing actions therefore operate on
files from the effective data workdir of the active conversation.

When the current conversation belongs to a project, ``Current project`` is
available as a runtime index target. Selecting it indexes the file or directory
into the isolated index for that project. The project's filesystem data workdir
and its isolated vector index are separate concepts: changing the data workdir
does not move, rename or rebuild the project's vector index.

Context indexing
----------------

The ``Context indexing`` tab controls automatic indexing of stored conversation
history. ``Conversation auto-indexing`` has three policies:

``Off``
   Automatic conversation-context indexing is disabled.

``Auto-index all conversations``
   Automatic context indexing is enabled for conversations both inside and
   outside projects.

``Auto-index only in projects``
   Automatic context indexing is enabled only when the conversation belongs to
   a project.

``Enable auto-indexing in modes`` further limits which PyGPT work modes may
trigger the automatic context-indexing path.

Global context indexes
~~~~~~~~~~~~~~~~~~~~~~

``Indexes for global auto-indexing`` is a multi-select list. One or more normal
configured indexes can be selected. When global indexing is used, new context
items are appended to each selected index.

The global selection is used for conversations outside projects and for project
conversations when ``Use isolated index per project`` is disabled. It is not
used when a project conversation is routed to its isolated project index.

Isolated project indexes
------------------------

``Use isolated index per project`` is enabled by default. When it is enabled and
a conversation belongs to a project, PyGPT routes conversation indexing to that
project's isolated index instead of the configured global auto-index targets.

The UI uses the virtual ID ``__project__`` for ``Current project``. At runtime it
is resolved to the physical index ID ``proj_<group_id>``. The physical project
IDs are intentionally not added to the normal ``Indexes`` configuration list,
which keeps the list compact even when many projects exist.

Project context indexing is incremental. PyGPT stores project-index progress in
the database, including the project ID, physical index ID, last indexed context
metadata/item IDs, and the last update time. Later updates continue from the
last indexed item rather than rebuilding the whole project every time.

Project lifecycle
~~~~~~~~~~~~~~~~~

Project indexes follow the project lifecycle:

* ``Update project index`` continues indexing from the last indexed item.
* ``Truncate project index`` permanently removes that project's index data and
  resets its tracked indexing state.
* Deleting a project also removes its isolated project index when it exists.
* Duplicating a project creates/rebuilds an isolated index for the duplicate
  only when the source project already had a project index.

Using the current project index
-------------------------------

The active project index can be used from multiple places:

* In ``Chat with Files``, choose ``Current project`` from the index selector.
* In the Files view, use ``RMB -> Embed into index -> Current project`` for a file or
  directory.
* In the ``Chat with Files (RAG, inline)`` plugin, enable
  ``Use project index if in use`` to query the active project's isolated index
  automatically.
* In the ``Files I/O`` plugin, enable ``Use project index if in use`` so
  persistent file indexing performed by the plugin targets the active project
  instead of the configured global file index.

Outside a project, the virtual ``Current project`` target is unavailable and
normal configured indexes are used.

Data loaders
------------

The ``Data loaders`` tab configures additional arguments for built-in LlamaIndex
file, web, and external-content loaders. It is placed after ``Context indexing``
and before ``Clear and truncate`` in the Settings window.

See :doc:`configuration` for the available configuration fields and loader
arguments.

Clear and truncate
------------------

``Clear and truncate`` is the destructive index-management tab. It can
permanently remove all data belonging to a selected stored index, including
related tracking records. It also provides an action for truncating all tracked
project indexes at once. Both operations require confirmation.

This is different from deleting an entry from the normal ``Indexes`` list,
which intentionally leaves vector-store data untouched.

Performance and indexed-file tracking
-------------------------------------

Indexed-file status is loaded lazily instead of hydrating the complete
indexed-files table when the file explorer opens. This keeps the Files view
responsive when a workdir or vector store contains a large number of indexed
files.

.. warning::
   Indexing uses the configured embedding provider and can generate API usage
   and token costs. Re-indexing large file collections or conversation histories
   may generate many embedding requests. Monitor usage with your selected
   provider.
