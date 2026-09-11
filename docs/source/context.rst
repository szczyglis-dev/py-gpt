Context and memory
==================

Short and long-term memory
--------------------------
**PyGPT** features a continuous chat mode that maintains a long context of the ongoing dialogue. It preserves the entire conversation history and automatically appends it to each new message (prompt) you send to the AI. Additionally, you have the flexibility to revisit past conversations whenever you choose. The application keeps a record of your chat history, allowing you to resume discussions from the exact point you stopped.


Handling multiple contexts
---------------------------
On the left side of the application interface, there is a panel that displays a list of saved conversations. You can save numerous contexts and switch between them with ease. This feature allows you to revisit and continue from any point in a previous conversation. **PyGPT** automatically generates a summary for each context, akin to the way ``ChatGPT`` operates and gives you the option to modify these titles itself.

You can disable context support in the settings by using the following option:

.. code-block:: ini

   Config -> Settings -> Use context 


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
``Files I/O``, Code Interpreter, filesystem-aware tools and model-facing data
paths use the data directory that belongs to the current conversation. In
Docker sandboxes the same host directory is exposed as ``/data``. Switching to
a conversation in another project therefore changes the effective ``data``
root without changing the application's base workdir.

.. important::
   The internal ``tmp`` directory always remains in the base profile workdir.
   ``img``, ``capture`` and ``upload`` also remain in their normal base-profile
   locations unless ``Store images, captures, and uploads in the data directory``
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
In addition, all history is also saved to ``.txt`` files for easy reading.