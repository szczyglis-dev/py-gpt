Security
========

Runtime Security settings
-------------------------

PyGPT includes application-level guards for host-side plugin operations. They are configured in
``Config -> Settings -> Security``.

Filesystem access
~~~~~~~~~~~~~~~~~

Two independent restrictions are available:

* ``Restrict plugin file reads to working directory`` - enabled by default.
* ``Restrict plugin file writes to working directory`` - enabled by default.

When a restriction is enabled, plugin-mediated host filesystem access is limited to the active
conversation's user-facing ``data`` workdir. Normally this is ``%workdir%/data``. If the conversation
belongs to a project with a custom data workdir, that project directory becomes the allowed data root
for the operation. PyGPT also allows its own internal base-profile ``%workdir%/tmp`` directory so
application-managed temporary workflows can function without disabling filesystem protection. Examples
include audio input, HTML Canvas, Python interpreter/IPython and Transcript working files.

The project override affects only the logical ``data`` root. The ``tmp`` exception remains tied to the
base profile and does not make arbitrary directories outside the effective data workdir available to
plugins.

Prompt injection protection
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **General** tab in ``Config -> Settings -> Security`` also provides an optional system-prompt guard:

* ``Auto-prevent prompt injections`` - disabled by default. When enabled, PyGPT appends the configured security annotation to system prompts before they are sent to models. The annotation tells the model to treat RAG/retrieval results, tool output, files, web/API content, and other external content as untrusted data rather than instructions.
* ``Prompt injection security annotation`` - editable text containing the instruction appended when the option above is enabled.

The default annotation instructs the model to ignore instructions embedded in external content, especially attempts to override system or user instructions, and to inform the user when a likely prompt-injection attempt is detected. The guard is applied globally to normal work modes and auxiliary model calls, and is also propagated into Chat with Agents/worker system prompts.

This is a defense-in-depth prompt-level measure, not a guarantee that every prompt-injection technique will be detected or blocked. Keep tool permissions, filesystem/command restrictions, sandboxing, and provider-side security controls appropriately configured for sensitive workflows.

System commands
~~~~~~~~~~~~~~~

PyGPT provides per-OS command whitelists and blacklists for Linux, Windows and macOS.

* If the whitelist is enabled, only command names listed for the current OS are allowed.
* When the whitelist is enabled it takes precedence over the blacklist.
* If the whitelist is disabled, commands listed in the blacklist are blocked.

These checks are application-level guards around host-side plugin command execution. They are not a
process sandbox.

Sandbox behavior
~~~~~~~~~~~~~~~~

Configured sandbox execution is isolated separately and bypasses the host-side Security filters described
above. For process-level isolation, use a supported sandbox such as the Docker mode provided by the
Python interpreter plugin.

Computer Use confirmations
~~~~~~~~~~~~~~~~~~~~~~~~~~

``Halt on potentially unsafe operation`` is enabled by default. For non-sandbox Computer Use, when a
provider flags an operation as requiring confirmation, PyGPT pauses the operation and displays a warning
in chat. The operation continues only after the user types ``continue``. When the option is disabled,
provider safety acknowledgements are handled automatically as before.

Reporting a Vulnerability
-------------------------

If you believe you have found a security issue in the project, please report it responsibly by email to
``info@pygpt.net``. Include a clear description and, when possible, reproduction steps or a proof of
concept.

External Libraries
------------------

PyGPT uses external libraries and attempts to keep them up to date. If you discover a vulnerability in a
dependency, report it to that dependency's maintainers and also let the PyGPT project know when it affects
PyGPT.
