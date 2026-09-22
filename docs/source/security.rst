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

The default annotation instructs the model to ignore instructions embedded in external content, especially attempts to override system or user instructions, and to inform the user when a likely prompt-injection attempt is detected. The guard is applied globally to normal work modes and auxiliary model calls, and is also propagated into Agents/worker system prompts.

This is a defense-in-depth prompt-level measure, not a guarantee that every prompt-injection technique will be detected or blocked. Keep tool permissions, filesystem/command restrictions, sandboxing, and provider-side security controls appropriately configured for sensitive workflows.

System commands
~~~~~~~~~~~~~~~

PyGPT provides per-OS command whitelists and blacklists for Linux, Windows and macOS.

* If the whitelist is enabled, only command names listed for the applicable runtime OS are allowed.
* When the whitelist is enabled it takes precedence over the blacklist.
* If the whitelist is disabled, commands listed in the blacklist are blocked.
* The command policy applies to ``sys_exec``, ``python_sys_exec`` and ``ipython_sys_exec`` in every execution backend: ``Disabled`` (host), ``Built-in sandbox`` and ``Docker``.
* Host and Built-in execution use the policy for the host operating system. The stock Docker backends are Linux containers, so Docker system-command tools use the Linux whitelist/blacklist even when PyGPT itself runs on Windows or macOS.

These checks are application-level guards around the dedicated system-command tools. They are not a
process sandbox and do not inspect arbitrary commands started by executed Python code, for example via
``subprocess``, ``os.system`` or an IPython shell escape submitted as normal Python/IPython code.

Sandbox behavior
~~~~~~~~~~~~~~~~

Filesystem and command policies are intentionally separate. The workdir filesystem read/write Security
restrictions keep their existing behavior and are bypassed by sandbox backends. The system-command
whitelist/blacklist is **not** bypassed: it is checked before dedicated system-command tools are sent to
Host, Built-in or Docker execution.

The ``Built-in sandbox`` used by the Python interpreter and System (OS) plugins provides a separate
uv-managed environment and separate-process execution, but it does **not** restrict host filesystem or
network access. Built-in commands run with the OS permissions of the PyGPT process. Treat Built-in as
environment/process separation rather than a filesystem or network security boundary; the command
whitelist/blacklist is an additional application-level guard for the dedicated system-command tools.

``Docker`` provides the container boundary. By default these plugins expose only the active runtime
``data`` workdir to the container at ``/mnt/data``; custom volume mappings can expose additional host
paths. The command whitelist/blacklist is evaluated before a dedicated system-command tool enters the
container. See the Python interpreter and System (OS) sections in :doc:`plugins` for the complete backend
layout and isolation rules.

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
