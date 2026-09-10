Debugging and Logging
======================

In ``Settings -> Debug`` dialog, you can enable the ``Show debug menu`` option to turn on the debugging menu. The menu allows you to inspect the status of application elements. In the debugging menu, there is a ``Logger`` option that opens a log window. In the window, the program's operation is displayed in real-time.

Internal database access
------------------------

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

**Logging levels**:

By default, all errors and exceptions are logged to the file:

.. code-block:: ini

	{HOME_DIR}/.config/pygpt-net/app.log

To increase the logging level (``ERROR`` level is default), run the application with ``--debug`` argument:

.. code-block:: ini

	python3 run.py --debug=1

or

.. code-block:: ini

	python3 run.py --debug=2

* The value ``1`` enables the ``INFO`` logging level.
* The value ``2`` enables the ``DEBUG`` logging level (most information).


**Compatibility (legacy) mode**

If you have problems with `WebEngine / Chromium` renderer you can force the legacy mode by launching the app with command line arguments:

.. code-block:: console

    python3 run.py --legacy=1

and to force disable OpenGL hardware acceleration:

.. code-block:: console

    python3 run.py --disable-gpu=1

You can also manualy enable legacy mode by editing config file - open the ``%WORKDIR%/config.json`` config file in editor and set the following options:

.. code-block:: json

    "render.engine": "legacy",
    "render.open_gl": false,