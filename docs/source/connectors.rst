MCP Connectors
==============

Overview
--------

**MCP Connectors** provide a convenient way to import and manage Model Context Protocol (MCP) server configurations. Enabled connectors are handled by the regular ``MCP`` plugin.

The connector importer understands common MCP configuration layouts used by Claude, Codex, OpenClaw, Cursor, VS Code, OpenCode, MCPorter, and compatible generic JSON, JSONC/JSON5, TOML, YAML, and YML files. This makes it possible to reuse existing MCP server configurations without manually recreating every server entry in PyGPT.

Managing Connectors
-------------------

Open:

.. code-block:: text

   Config -> MCP... -> Connectors...

The dialog has two tabs:

* ``Installed`` - shows the MCP connector definitions currently stored in the MCP plugin configuration. Use the checkbox in the first column to enable or disable a connector. You can also add a connector manually, edit it, delete it, import configurations, or open the normal MCP plugin settings.
* ``Explore`` - browses the connector catalog. Select entries with the checkboxes in the first column and click ``Install selected``. Clicking a row only highlights it; installation is controlled by the checkboxes.

Imported connectors are deliberately **disabled by default**. This applies even when the source configuration marked a server as enabled. Enable a connector explicitly after reviewing its command or URL and configuration. Enabling a connector also enables the MCP plugin when necessary.

A connector entry can contain the server label, command or URL, transport, environment variables, HTTP headers, authorization data, working directory, allow/deny tool filters, startup/tool timeouts, source metadata, and additional vendor metadata.

Importing existing MCP configurations
-------------------------------------

Use ``Import from GitHub``, ``Import file``, or ``Import folder`` from the ``Installed`` tab. Local directory imports search recursively for known MCP configuration filenames and compatible configuration extensions.

Supported configuration styles include common forms such as:

* Claude-style ``mcpServers`` maps.
* Codex-style ``mcp_servers`` maps.
* OpenClaw ``mcp.servers`` configurations.
* OpenCode ``mcp`` configurations.
* VS Code/generic ``servers`` maps.
* MCPorter exports, including wrapped profile/config objects.
* Generic MCP definitions in JSON, JSONC/JSON5, TOML, YAML, or YML files.

Typical recognized filenames include ``.mcp.json``, ``mcp.json``, ``mcp.jsonc``, ``mcporter.json``, ``opencode.json``, ``opencode.jsonc``, ``config.toml``, ``settings.json``, and ``settings.jsonc``.

The GitHub importer accepts GitHub repository/file URLs as well as direct URLs to compatible configuration files. Repository imports inspect suitable configuration files and normalize every discovered MCP server into PyGPT's MCP server format. Existing entries with the same connector identity are not duplicated during a normal import.

Explore catalog
---------------

The ``Explore`` tab reads a JSON catalog of connector definitions. The catalog URL is stored in ``config.json`` as:

.. code-block:: json

   "connectors.catalog.url": "https://example.com/connectors/catalog.json"

When the setting is empty, PyGPT uses its built-in default catalog URL:

.. code-block:: text

   https://github.com/szczyglis-dev/py-gpt-addons/mcp.json

PyGPT also includes a bundled local catalog. If loading the built-in default remote catalog fails, the bundled catalog is used as a fallback. An explicitly configured custom catalog reports its loading error instead of silently switching to the default source.

A catalog entry can embed an MCP configuration directly or point to a GitHub/config URL. For example:

.. code-block:: json

   {
     "connectors": [
       {
         "name": "example",
         "display_name": "Example MCP",
         "description": "Example remote MCP server.",
         "publisher": "Example",
         "config": {
           "mcpServers": {
             "example": {
               "url": "https://example.com/mcp"
             }
           }
         }
       }
     ]
   }

Catalog installations are normalized in the same way as manual imports and are installed disabled until explicitly enabled.

Runtime behavior
----------------

Connectors use the existing ``MCP`` plugin server registry (``plugin.mcp.servers``). There is no second connector-specific tool registry. After a connector is enabled, the MCP plugin handles server startup/connection, tool discovery, cached tool metadata, transport-specific communication, and command filtering according to the MCP plugin configuration.

Supported transports include local ``stdio`` servers and remote HTTP/Streamable HTTP or SSE servers. When a foreign configuration uses vendor-specific field names, PyGPT maps supported values into the MCP plugin fields and preserves unrecognized vendor metadata for reference instead of executing helper metadata automatically.

Security
--------

Treat imported MCP configurations as third-party executable/integration configuration. Before enabling a connector, review at least its command or remote URL, environment variables, headers and authorization values, working directory, and allowed/disabled tool filters.

Local ``stdio`` connectors may start external processes, while remote connectors may send requests and credentials to external services. Importing a connector does not run it; imported connectors remain disabled until you explicitly enable them. Normal MCP plugin settings and PyGPT security controls remain authoritative after import.

For details about MCP tool discovery, transports, and plugin configuration, see the :doc:`plugins` section and the ``MCP (Model Context Protocol)`` plugin documentation.
