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
include audio input, HTML Canvas, Code interpreter (v2)/IPython and Transcript working files.

The project override affects only the logical ``data`` root. The ``tmp`` exception remains tied to the
base profile and does not make arbitrary directories outside the effective data workdir available to
plugins.

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
Code interpreter (v2) plugin.

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
