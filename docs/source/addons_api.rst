Add-ons API
===========

This chapter is the developer reference for external PyGPT Add-ons. It covers the package format, local development and testing, dependency installation, publishing, runtime lifecycle, the supported base classes, and the application/events API that an Add-on can use.

The examples shipped in the main repository under ``examples/addons`` and in the public ``py-gpt-addons`` repository are designed to be copied and modified. They are runnable tutorials, not only registration stubs.

.. important::

   Python Add-ons execute inside the PyGPT process and therefore have the same operating-system permissions as PyGPT. An Add-on can read files available to the process, use the network, import packages and call application APIs. ``trusted`` and ``official`` are not a sandbox or a code-safety guarantee. Public-registry ``trusted`` entries are additionally content-pinned with SHA-256, so PyGPT can detect code changed after registry review, but a matching hash does not make the reviewed code harmless. Review third-party code before installation.

What is an Add-on?
------------------

An Add-on is an application-wide extension installed below ``<application base workdir>/addons``. The application base workdir is the directory that owns ``path.cfg`` (normally ``{HOME_DIR}/.config/pygpt-net/``); it is independent of the currently active profile workdir. Every package has a ``manifest.json`` and either:

* a Python entry point that returns an object derived from one of PyGPT's supported base classes, or
* static theme/locale files handled by the existing theme/translation loaders.

Storage scope and migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting with PyGPT 2.8.36, the installed Add-on tree is **shared by all profiles**:

.. code-block:: text

   <application base workdir>/
   ├── path.cfg
   ├── addons/
   │   ├── .registry.json
   │   ├── plugins/
   │   ├── tools/
   │   ├── llms/
   │   └── ...
   ├── sandbox/
   └── extra_packages/

``path.cfg`` may redirect the active profile to another workdir, but it does not move ``addons``. Installing, updating or removing an Add-on therefore changes the Add-on set for the whole PyGPT application, not only for the currently selected profile.

When upgrading from 2.8.35 or earlier, PyGPT migrates a legacy ``<profile workdir>/addons`` directory into the application base workdir. If the global destination does not exist, the complete directory is moved. If it already contains Add-ons from another migrated profile, missing packages are merged, byte-identical packages are deduplicated, and a package with the same ``type/id`` but different contents is **not overwritten**; PyGPT keeps the global copy and leaves the conflicting legacy profile copy in place while printing a warning. This avoids silent data loss when old profiles contained different revisions of the same Add-on.

The Add-on registry is global as well. Static ``theme`` and ``locale`` Add-ons are fully application-wide too: PyGPT reads their assets directly from ``<application base workdir>/addons/themes`` and ``<application base workdir>/addons/locale``. Their files are **not** copied or mirrored into the active profile. Existing profile-local ``css`` and ``locale`` directories remain supported only as explicit user overrides.

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
   * - ``file_preview``
     - ``addons/file_previews/<id>``
     - ``BaseFilePreview``
     - Inline Files preview widgets for declared file extensions.
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
   ├── locale/                 # optional, private translations for this Add-on
   │   ├── locale.en.ini
   │   └── locale.pl.ini
   └── helpers/
       └── client.py

For manual installation, PyGPT stores it as:

.. code-block:: text

   <application base workdir>/addons/plugins/my_plugin/
   ├── manifest.json
   ├── plugin.py
   ├── locale/
   │   ├── locale.en.ini
   │   └── locale.pl.ini
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
     "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
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

Integrity field: ``sha256``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``sha256`` is a 64-character hexadecimal SHA-256 content pin for one exact Add-on tree. It is optional for local/manual development packages, but **required for every Add-on submitted to the public ``py-gpt-addons`` registry**. A public registry entry stores the same digest. For an entry marked ``trusted: true``, installation is rejected if the registry digest or manifest digest is missing/invalid, if the two values differ, or if the downloaded files do not reproduce the digest.

The digest uses the versioned ``PYGPT-ADDON-SHA256-V1`` algorithm. It hashes every regular file below the Add-on root recursively using sorted UTF-8 POSIX-style relative paths and byte-length framing. File payloads are hashed byte-for-byte. ``manifest.json`` is also protected, but before hashing it PyGPT parses the JSON, removes only the top-level ``sha256`` field and serializes the remaining object canonically (UTF-8, sorted keys, compact separators). This removes the circular self-reference while keeping fields such as ``entrypoint`` and ``external_dependencies`` inside the integrity check. ``.git`` metadata, permissions, timestamps and empty directories are not included; symlinks are rejected.

The main PyGPT repository contains matching helper scripts. ``--write`` both computes the digest and writes it into ``manifest.json``; because the field itself is excluded from canonical manifest hashing, printing the digest again gives the same value.

.. code-block:: bash

   ./bin/addon-sha256.sh /path/to/addon --write
   ./bin/addon-sha256.sh /path/to/addon

On Windows:

.. code-block:: bat

   bin\addon-sha256.bat C:\path\to\addon --write
   bin\addon-sha256.bat C:\path\to\addon

Generate the digest from the exact content that will be committed/published. Since file bytes are protected, local line-ending conversions must not produce content different from the repository revision PyGPT will download.

For public registry releases, the SHA-256 pin must be paired with an **immutable Git ref**. Create a release tag such as ``v1.0.0`` for the exact commit/tree that was hashed and use that tag as the registry ``ref``. Do not point a published registry entry at ``main``, ``master`` or another moving branch: if that branch changes while the registry still contains the previous SHA-256, the previously approved version can no longer be downloaded successfully. An exact commit SHA is also acceptable, but a version tag is usually easier for users and maintainers to read.

Release tags used by the public registry must be treated as immutable: create/push the tag before opening the registry PR, and do not move, overwrite or delete it after review. Development may continue normally on ``main``/``master`` after the release tag is created.

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

PyGPT validates archive paths and rejects unsafe absolute/path-traversal entries. Very large archives are also limited by file-count/download safety limits. If the package declares ``sha256``, its extracted tree must reproduce that digest before installation continues.

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

For a faster low-level test you can copy a package directly to the type directory under ``<application base workdir>/addons``. Keep the exact layout and restart the application. This bypasses installer metadata such as source/trusted/official flags, so use the installer before release testing.

Debugging
~~~~~~~~~

Useful developer settings include:

* ``Config -> Settings -> Debug -> Log events`` for event ordering and payloads.
* plugin logging for command/tool execution.
* API/tool logging when testing model-callable plugin commands.
* normal application log output for ``[Add-ons] WARNING`` messages.

A broken Add-on is isolated during startup. Invalid manifests, incompatible minimum versions, import errors, invalid entry points and registration errors are skipped and logged instead of aborting the whole application.

Add-on-owned translations
-------------------------

Runtime Add-ons can ship their **own private translation domain**. This is different from a ``type: locale`` Add-on: a locale Add-on extends the application's main translation domain and is read directly from the application-wide ``addons/locale/<id>`` package, while an Add-on-owned ``locale/`` directory belongs to one executable Add-on and is automatically scoped to that package.

Supported runtime types are ``plugin``, ``tool``, ``llm``, ``vector_store``, ``loader``, ``audio_input``, ``audio_output``, ``web`` and ``agent``. No manifest flag is required. If the installed Add-on root contains a directory named ``locale``, PyGPT detects it while loading the Add-on and binds it to every runtime object returned by that manifest.

Directory and file naming
~~~~~~~~~~~~~~~~~~~~~~~~~

Put locale files directly below the Add-on's ``locale`` directory and name them ``locale.<lang>.ini``:

.. code-block:: text

   my_addon/
   ├── manifest.json
   ├── provider.py
   └── locale/
       ├── locale.en.ini
       ├── locale.pl.ini
       └── locale.de.ini

Every file uses the normal PyGPT INI format:

.. code-block:: ini

   [LOCALE]
   provider.name = Example provider
   settings.timeout.label = Request timeout
   settings.timeout.description = Timeout in seconds.
   dialog.title = Example dialog

Use UTF-8. The language suffix is the same language code used by PyGPT, for example ``en``, ``pl``, ``de`` or ``fr``. English is the fallback language, so shipping a complete ``locale.en.ini`` is recommended even if the Add-on also provides other languages.

Automatic domain assignment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For an installed runtime Add-on, the manifest ID defines the logical domain automatically:

.. code-block:: text

   manifest id: my_company_example
   locale dir:  <addon-root>/locale
   domain:      addon.my_company_example

The physical path is intentionally separate from the logical domain. Add-on code normally **does not register this domain itself** and should not hard-code the installation path. The loader registers ``<addon-root>/locale`` and assigns ``addon.<manifest_id>`` to each runtime object after the entry point has been instantiated and before the object is registered in the normal PyGPT subsystem.

All runtime base classes that support Add-ons expose the locale-domain helpers inherited from ``LocaleDomain``:

``self.trans(key)``
   Translate ``key`` using the object's assigned domain. If the key is not present in the Add-on domain, normal PyGPT locale is used as the final fallback.

``self.get_locale_domain()``
   Return the assigned logical domain, for example ``addon.my_company_example``.

``self.get_locale_dir()``
   Return the physical Add-on ``locale`` directory when one was assigned.

``self.set_locale_domain(domain, path=None, register=False)``
   Assign a domain manually. Installed Add-ons normally do not need this; it is mainly useful for custom-launcher objects or advanced integrations.

Because the domain is assigned **after the entry-point object is constructed**, avoid resolving final translated UI strings with ``self.trans()`` inside ``__init__()``. Store translation keys there and let the relevant PyGPT UI translate them later, or call ``self.trans()`` from lifecycle/UI methods that run after registration (for example a Tool's ``setup_menu()``).

Fallback and overrides
~~~~~~~~~~~~~~~~~~~~~~

A custom domain is loaded in this order:

#. ``locale.en.ini`` from the Add-on directory (English baseline).
#. ``locale.<active-lang>.ini`` from the Add-on directory, if present.
#. ``<profile workdir>/locale/addon.<manifest_id>.<lang>.ini`` as the profile/user override.

A missing key in the selected Add-on domain falls back to the normal application locale domain. This makes it possible to reuse common PyGPT keys without duplicating them in every Add-on.

Changing the application language reloads domains that are already in use. UI components integrated with the locale system therefore update without the Add-on maintaining its own language watcher.

Plugin Add-ons
~~~~~~~~~~~~~~

For an external ``plugin`` Add-on, the presence of ``locale/`` automatically enables plugin localization. The following conventional keys are consumed by the Plugins UI:

.. code-block:: ini

   [LOCALE]
   plugin.name = My localized plugin name
   plugin.description = Localized plugin description

   uppercase.label = Uppercase result
   uppercase.description = Convert the result to upper case.

   example_cmd.label = Example command
   example_cmd.description = Allow the model to call the example command.

   tab.advanced = Advanced

Plugin settings are translated by option ID, using ``<option_id>.label``, ``<option_id>.description`` and, where supported, ``<option_id>.tooltip``. Command options created by ``add_cmd()`` use the same Add-on domain for their UI labels/descriptions. ``plugin.name`` and ``plugin.description`` replace the Python fallback strings in the Plugins UI.

Calling ``self.trans("some.key")`` also uses the assigned ``addon.<manifest_id>`` domain. Built-in PyGPT plugins use the same logical-domain mechanism but their bundled files live under ``data/locale/plugin/<plugin_id>/locale.<lang>.ini`` and use the ``plugin.<plugin_id>`` domain.

GUI Tool Add-ons
~~~~~~~~~~~~~~~~

A Tool can translate text directly in setup/runtime code:

.. code-block:: python

   def setup_menu(self):
       action = QAction(self.trans("menu.title"), self.window)
       action.setToolTip(self.trans("menu.tooltip"))
       self.add_lang_mapping(action, "menu.title")
       self.add_lang_mapping(action, "menu.tooltip", setter="setToolTip")
       return {self.id: action}

``add_lang_mapping()`` defaults to the Tool's assigned Add-on domain and reapplies the translation when the application language changes. This is the preferred API for dynamically created/private Qt objects. Existing ``get_lang_mappings()`` mappings are also scoped to the Tool's Add-on domain automatically.

LLM provider Add-ons
~~~~~~~~~~~~~~~~~~~~

``BaseLLM.get_name()`` checks ``provider.name`` in the provider's assigned domain before falling back to ``self.name``. Provider-owned Settings fields can opt in to the same domain by using ``use_locale: True`` in the ``setup()`` schema:

.. code-block:: python

   def setup(self):
       return {
           "openai_compatible": False,
           "settings": {
               "extra": {
                   "timeout": {
                       "type": "int",
                       "default": 30,
                       "label": "settings.timeout.label",
                       "description": "settings.timeout.description",
                       "use_locale": True,
                   },
               },
           },
           "remote_tools": {},
       }

With ``use_locale: True``, PyGPT attaches the provider's ``addon.<manifest_id>`` domain to the field. Labels, descriptions, combo items and other supported Settings widgets are then translated from the provider's own ``locale/`` directory and refreshed on a runtime language change.

Audio-input, audio-output and Web provider Add-ons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``audio_input``, ``audio_output`` and ``web`` providers are attached to their owning built-in plugin. Their Add-on domain is propagated automatically while ``init_options()`` adds provider settings. This means the existing provider code can keep normal fallback labels while locale files provide translations by **option ID**:

.. code-block:: python

   def init_options(self):
       self.plugin.add_option(
           "request_timeout",
           type="int",
           value=30,
           label="Request timeout",          # English fallback
           description="Timeout in seconds.", # English fallback
           tab=self.id,
       )

.. code-block:: ini

   [LOCALE]
   provider.name = My provider
   request_timeout.label = Request timeout
   request_timeout.description = Timeout in seconds.

The provider tab/name uses ``provider.name`` when available. There is no need to pass ``domain=`` to ``plugin.add_option()`` manually.

Loader Add-ons
~~~~~~~~~~~~~~

Loader configuration metadata also carries the loader's Add-on domain. Translation keys can therefore be supplied in ``init_args_labels`` and ``init_args_desc``:

.. code-block:: python

   self.init_args = {"encoding": "utf-8"}
   self.init_args_types = {"encoding": "str"}
   self.init_args_labels = {"encoding": "encoding.label"}
   self.init_args_desc = {"encoding": "encoding.description"}

and in ``locale.en.ini``:

.. code-block:: ini

   [LOCALE]
   encoding.label = Text encoding
   encoding.description = Encoding used to read input files.

For web-loader instructions, PyGPT also propagates the loader domain to the instruction and its argument metadata before building the configuration UI.

Other runtime Add-ons
~~~~~~~~~~~~~~~~~~~~~

``vector_store`` and ``agent`` objects receive the same domain and can use ``self.trans()`` anywhere translation is required. The same applies to custom UI/messages created by any runtime Add-on type. Automatic translation of a specific framework-owned field only happens where that subsystem exposes locale-aware metadata; otherwise call ``self.trans()`` or register a UI language mapping explicitly.

Custom launcher objects
~~~~~~~~~~~~~~~~~~~~~~~

The automatic ``locale/`` discovery described above belongs to the manifest/Add-on loader. Objects registered directly through ``pygpt_net.app.run(...)`` have no manifest root, so assign/register their domain manually if they need private locale files:

.. code-block:: python

   from pathlib import Path

   provider = ExampleLLM()
   locale_dir = Path(__file__).with_name("locale")
   provider.set_locale_domain(
       "custom.example_llm",
       str(locale_dir),
       register=True,
   )

Use a stable, unique domain name. The files in ``locale_dir`` still use the canonical ``locale.<lang>.ini`` naming convention.

Runtime lifecycle
-----------------

Python Add-ons are discovered and registered during application startup. The simplified lifecycle is:

.. code-block:: text

   discover <application base workdir>/addons
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

Python Add-ons are process-level registrations. Because the installed package tree is application-wide, switching profiles does **not** select a different Python Add-on set. Restart PyGPT after installing, updating or uninstalling a runtime Add-on so the process-level registry is rebuilt. Static theme/locale packages are application-wide as well and are read directly from the global Add-ons tree; profile switching does not copy or synchronize their payloads.

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
         "ref": "v1.0.0",
         "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
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
     "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
     "trusted": true,
     "official": true
   }

Every public registry entry must pin the exact Add-on contents with ``sha256`` **and an immutable source revision**. Put the generated digest in the upstream ``manifest.json`` first, commit the release, create an immutable version tag such as ``v1.0.0`` for that exact commit, and copy the identical digest plus the tag name into ``addons.json``. The public registry rejects/ignores entries without a valid pin, and ``trusted`` installation additionally requires the upstream manifest to carry the same pin. Integrity verification is performed before dependency installation or Add-on code loading.

Do not use ``main``, ``master`` or another moving branch as ``ref`` for a public release. If the branch moves before the corresponding registry PR is merged, the registry still expects the old digest while GitHub serves the new tree, making the currently approved version temporarily impossible to install. A stable version tag avoids this availability gap. An exact commit SHA may be used instead when desired.

Third-party authors should keep their code in their own GitHub repository and submit only a registry link/metadata PR to ``py-gpt-addons``. **Every update to any file in the published Add-on tree requires a new version/release ref, a new digest and a new registry PR.** The old release tag must remain available and unchanged. Until the updated registry entry is reviewed and merged, users continue downloading the previously approved tag and its matching content pin.

When submitting a public package, document network/filesystem/shell/desktop access, credentials, external dependencies and other security-sensitive behavior. Keep the manifest version, registry version and SHA-256 pin in sync with the actual package release. See the ``CONTRIBUTING.md`` file in ``py-gpt-addons`` for the submission checklist.

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

Resolve application/profile paths:

.. code-block:: python

   import os

   app_base_workdir = self.window.core.config.get_base_workdir()
   addons_dir = os.path.join(app_base_workdir, "addons")
   profile_workdir = self.window.core.config.get_user_path()
   index_dir = self.window.core.config.get_user_dir("idx")
   data_workdir = self.window.core.config.get_workdir_prefix(ctx=event.ctx)

``get_base_workdir()`` returns the application-wide root used by ``addons``, ``sandbox`` and ``extra_packages``. ``get_user_path()`` returns the active profile workdir and may point somewhere else through ``path.cfg``.

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

What a plugin Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A plugin is the general-purpose **model-facing** extension point. Use it when the extension must expose model-callable commands/tools, add settings to the Plugins UI, modify prompts or conversation events, react to application state, or return tool results back into the active conversation.

A plugin is different from a GUI ``tool`` Add-on: a plugin participates in the prompt/command/event pipeline, while a GUI tool primarily extends the desktop interface. A plugin may still create UI when needed, but model-callable functionality belongs here.

PyGPT creates the plugin object first, restores its persisted options, attaches the main ``window`` and then dispatches events to ``handle()`` while the plugin is enabled. Therefore ``__init__()`` should define metadata, options and commands, but code that requires ``self.window`` should run later (for example in ``setup_ui()`` or an event handler).

Minimum useful plugin
~~~~~~~~~~~~~~~~~~~~~

A command plugin normally needs four things:

#. stable metadata such as ``id``, ``name`` and ``description``;
#. one or more commands declared with ``add_cmd()``;
#. the command names in ``allowed_cmds``;
#. a ``handle()`` implementation that publishes command syntax and handles execution.

.. code-block:: python

   from pygpt_net.core.events import Event
   from pygpt_net.plugin.base.plugin import BasePlugin

   class Plugin(BasePlugin):
       def __init__(self):
           super().__init__()
           self.id = "example_echo"
           self.name = "Example Echo"
           self.description = "Returns text through a model-callable tool."
           self.type = ["cmd"]
           self.allowed_cmds = ["example_echo"]

           self.add_cmd(
               "example_echo",
               instruction="Echo the supplied text.",
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
                   event.data.setdefault("cmd", []).append(
                       self.get_cmd("example_echo")
                   )
               return

           if event.name not in (Event.CMD_EXECUTE, Event.CMD_INLINE):
               return

           for item in event.data.get("commands", []):
               cmd = item.get("cmd")
               if cmd != "example_echo":
                   continue
               if not self.cmd_allowed(cmd) or not self.has_cmd(cmd):
                   continue
               params = item.get("params") or {}
               self.reply({
                   "request": {
                       "cmd": "example_echo",
                       "params": params,
                   },
                   "result": str(params.get("text", "")),
               }, event.ctx)
               return

The base class contains many helpers, but they are **not a checklist of methods that every plugin must override**. Most plugins only override ``__init__()``, ``handle()`` and, when needed, one or two lifecycle/UI hooks.

Core methods you will use most often
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``add_option(name, type, **kwargs)``
   Declare a setting in ``__init__()``. The option is persisted and rendered by the normal plugin settings UI. Read it later with ``get_option_value()``. Use ``secret=True`` for credentials and ``advanced=True`` for expert-only settings.

``add_cmd(cmd, **kwargs)``
   Declare a model-callable command. The important fields are ``instruction``, ``params`` and ``enabled``. Add the same command ID to ``allowed_cmds``. ``hidden=True`` marks an implementation/internal tool that should not be persisted/displayed like a normal visible tool call.

``handle(event)``
   This is the main plugin entry point. PyGPT sends application and model-pipeline events here. Command plugins normally react to two phases: syntax publication (``CMD_SYNTAX`` or ``CMD_SYNTAX_INLINE``) and execution (``CMD_EXECUTE`` or ``CMD_INLINE``). Other plugin types may listen to prompt, context, audio, UI or lifecycle events instead.

``has_cmd()`` and ``get_cmd()``
   ``has_cmd()`` checks whether a declared command is currently enabled. ``get_cmd()`` returns the normalized command schema that should be appended to ``event.data["cmd"]`` during the syntax phase.

``reply(response, ctx)``
   Return a completed command/tool result to PyGPT. In the normal synchronous path pass the current ``event.ctx``. The response should normally contain ``request`` and ``result``. ``context`` can additionally inject extra context when the corresponding application option is enabled.

Returning command results
~~~~~~~~~~~~~~~~~~~~~~~~~

For a normal tool call, return a dictionary in this shape:

.. code-block:: python

   self.reply({
       "request": {
           "cmd": "example_echo",
           "params": {"text": "hello"},
       },
       "result": "hello",
   }, event.ctx)

``request.cmd`` lets PyGPT associate the result with the originating tool call, including parallel/native function calls. ``result`` is the tool output exposed to the next model step and stored in the tool transcript. ``context`` is optional and is intended for extra context rather than a normal visible tool result. Keys beginning with ``agent_`` are reserved for agent/runtime integrations.

If a worker/thread produces the result, connect it to ``handle_finished()`` (single result) or ``handle_finished_more()`` (multiple results), or call ``reply()`` from the appropriate safe path. Those helpers normalize the result into ``CtxItem`` and dispatch the continuation event.

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
               cmd = item.get("cmd")
               if cmd != "example_echo":
                   continue
               if not self.cmd_allowed(cmd) or not self.has_cmd(cmd):
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

Full ``BasePlugin`` method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - Translates a key in the plugin's assigned locale domain (``addon.<manifest_id>`` for an external Add-on, ``plugin.<id>`` for a built-in plugin).
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

GUI Tool Add-ons
----------------

Base class: ``pygpt_net.tools.base.BaseTool``.

What a GUI Tool Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``tool`` Add-on extends the **desktop application UI and lifecycle**. It is the correct type for Tools-menu actions, Qt dialogs, utility windows, custom output tabs and application-level UI helpers. Registering a GUI Tool does **not** make a function callable by the model; use a ``plugin`` Add-on when the model must invoke it.

PyGPT attaches ``self.window`` during registration, then runs the normal tool lifecycle. Static dialogs are prepared first, ``setup()`` is called during application tool initialization, and ``post_setup()`` runs after plugins are loaded. The periodic hooks and exit/reload hooks are optional.

Minimum implementation
~~~~~~~~~~~~~~~~~~~~~~

A menu-only tool can be very small. Set a stable ``id`` and override ``setup_menu()``:

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
               lambda: QMessageBox.information(
                   self.window,
                   "Example",
                   "It works",
               )
           )
           return {self.id: action}

Only override the hooks your tool actually needs. ``setup()``, ``post_setup()``, ``handle()``, update hooks and exit/reload hooks are optional no-op methods in the base class.

Creating a tab-capable tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set ``allow_tab = True``, provide ``tab_title``/``tab_icon`` and override ``as_tab(tab)`` to return the ``QWidget`` mounted in a PyGPT tool tab. The application controls tab creation and passes the tab descriptor to your method.

.. code-block:: python

   from PySide6.QtWidgets import QLabel
   from pygpt_net.tools.base import BaseTool, ToolMenuAction

   class ExampleTabTool(BaseTool):
       def __init__(self):
           super().__init__()
           self.id = "example_tab"
           self.allow_tab = True
           self.allow_dialog = False
           self.multi_tab = False
           self.on_menu_click = ToolMenuAction.ALWAYS_TAB
           self.tab_title = "Example"
           self.tab_icon = ":/icons/build.svg"

       def as_tab(self, tab):
           return QLabel("Example tool content")

For dynamically created Qt controls that must follow runtime language changes, use ``add_lang_mapping()`` after creating the object instead of maintaining a separate translation refresh mechanism.

Presentation policy: tabs, dialogs and menu actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure presentation in the constructor after ``super().__init__()``. These fields are the single source of truth for the Tools menu, tab-add menus, dialog creation and restored tabs.

.. list-table:: Presentation fields
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Default
     - Meaning
   * - ``allow_tab``
     - ``False``
     - Permit a tool tab; implement ``as_tab(tab)``.
   * - ``allow_dialog``
     - ``True``
     - Permit a dialog; implement the dialog opener.
   * - ``multi_tab``
     - ``True``
     - Permit multiple tabs across both columns. If false, existing tabs are reused.
   * - ``hide_in_tab_tools``
     - ``False``
     - Hide the automatic entry in the tab bar's [+] menu under Add Tool. Custom top-level actions, toolbar buttons and Tools-menu actions remain available.
   * - ``multi_dialog``
     - ``False``
     - Permit independent dialog identities. If false, reuse the existing dialog.
   * - ``on_menu_click``
     - ``ALWAYS_DIALOG``
     - A ``ToolMenuAction`` enum value controlling the menu action.
   * - ``dialog_id``
     - ``''``
     - Static dialog key in ``self.window.ui.dialog``.
   * - ``dialog_types``
     - ``()``
     - Type IDs handled by a dynamic dialog factory.
   * - ``dialog_opener``
     - ``'open'``
     - Name of the no-argument method called to open a dialog.

Import ``ToolMenuAction`` from ``pygpt_net.tools.base`` and connect the menu action with ``action.triggered.connect(self.on_menu_action)``. The supported policies are:

.. list-table:: ``ToolMenuAction``
   :header-rows: 1
   :widths: 35 65

   * - Value
     - Behavior
   * - ``ALWAYS_DIALOG``
     - Open or focus a dialog.
   * - ``ALWAYS_TAB``
     - Open or focus the tool tab.
   * - ``DIALOG_IF_TAB_EXISTS``
     - Open a dialog when a tool tab exists; otherwise open a tab.
   * - ``TAB_IF_EXISTS``
     - Focus an existing tool tab; otherwise open a dialog.

The selected surface must be allowed; a forbidden surface does not fall back to another surface. Multiple-instance flags permit creation, but your implementation must also create independent widgets/windows.

Use ``can_open_tab()`` and ``can_open_dialog()`` to check permitted surfaces, and ``can_add_tab()`` / ``can_add_dialog()`` to check whether a new instance may be created. A singleton can still be opened or focused when creation of another instance is prohibited. ``allows_multiple_tabs()`` and ``allows_multiple_dialogs()`` include the corresponding permission flag. ``existing_tab()`` returns the preferred existing tab using the application-wide selection policy, or ``None``.

``open_tab()`` and ``open_dialog()`` enforce presentation permissions. Also guard direct custom opener/factory calls with the corresponding ``can_open_*()`` method. Register static dialogs under ``dialog_id`` in ``self.window.ui.dialog`` so existing windows can be focused and counted. For dynamic dialogs, declare ``dialog_types``, implement ``get_instance()`` and call ``resolve_dialog_id(requested_id)`` before looking up or creating a window. It returns ``None`` when dialogs are disabled, preserves independent IDs for multiple dialogs and selects one stable ID for a singleton.

The legacy ``has_tab`` property aliases ``allow_tab``; ``single_instance`` aliases ``not multi_tab``. New Add-ons should use the presentation fields and methods above. See ``examples/addons/tools/example_tool`` for a runnable singleton-dialog example with a policy-aware menu action.

Tab bar titles and context menus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tool tabs have two separate context menus: the **[+] menu** creates tabs, while the **existing tab menu** operates on a particular tab. These hooks belong to the tool; the tab bar does not need tool-specific branches.

``get_tab_title(tab)``
   Return the displayed title for a tab. The default translates ``self.tab_title``. Override it for document names or numbered instances. PyGPT calls it after ``as_tab(tab)``; the tab descriptor includes ``data_id``, ``column_idx`` and ``title``. A saved/custom user name (``tab.custom_name``) takes precedence.

``get_tab_tooltip(tab)``
   Return the tooltip text for a tool tab. The default returns ``tab.title`` or an empty string. Override it for metadata such as a document path. This hook computes text; if metadata changes while a tab is open, update the affected tab tooltip as part of your tool's refresh.

``get_tab_menu(parent, idx, column_idx, caller)``
   Return a list of ``QAction`` objects to insert at the top level of the **[+] menu**. The default returns ``[]``. ``parent`` is the menu: parent new actions to it. ``idx`` is the requested insertion position (``-2`` for the [+] menu), ``column_idx`` is the column that opened the menu, and ``caller`` exposes ``add_tab(idx, column_idx, Tab.TAB_TOOL, tool_id)``. Use these supplied values so an action creates its tab in the invoking column.

``populate_tab_menu(menu, tab)``
   Add actions directly to the context menu of an **existing tool tab**, before the standard tab controls. This hook returns nothing and does nothing by default. Parent actions to ``menu`` and use the supplied ``tab`` to target that instance, rather than looking up whichever tab happens to be active.

By default, a tab-capable tool gets an automatic entry in **[+] → Add Tool**, using ``tab_title`` and ``tab_icon``. Set ``self.hide_in_tab_tools = True`` to replace that entry with your own top-level action without creating a duplicate. This flag only hides the automatic submenu entry; it does not disable tab creation or affect ``setup_menu()``, ``populate_tab_menu()`` or ``get_toolbar()``.

Both the automatic submenu entry and ``get_tab_menu()`` are offered only when ``can_add_tab()`` is true. A singleton tool with an existing tab is therefore absent from the creation menu. Existing tabs can still be opened or focused through ``open_tab()``. Custom top-level actions appear after the fixed Add Chat action, in tool registration order and then in the order returned by each hook; the Add Tool submenu follows them.

For example, a document tool can expose a top-level New document action and a tab-specific clear action:

.. code-block:: python

   from PySide6.QtGui import QAction, QIcon
   from PySide6.QtWidgets import QPlainTextEdit
   from pygpt_net.core.tabs.tab import Tab
   from pygpt_net.tools.base import BaseTool, ToolMenuAction

   class DocumentTool(BaseTool):
       def __init__(self):
           super().__init__()
           self.id = "document_tool"
           self.allow_tab = True
           self.allow_dialog = False
           self.multi_tab = True
           self.hide_in_tab_tools = True
           self.on_menu_click = ToolMenuAction.ALWAYS_TAB
           self.tab_title = "document_tool.title"
           self.tab_icon = ":/icons/note1.svg"

       def as_tab(self, tab):
           return QPlainTextEdit()

       def get_tab_menu(self, parent, idx, column_idx, caller):
           action = QAction(QIcon(self.tab_icon), "", parent)
           self.add_lang_mapping(action, "document_tool.new")
           action.triggered.connect(
               lambda checked=False: caller.add_tab(
                   idx, column_idx, Tab.TAB_TOOL, self.id
               )
           )
           return [action]

       def populate_tab_menu(self, menu, tab):
           editor = tab.child.findChild(QPlainTextEdit)
           action = QAction("", menu)
           self.add_lang_mapping(action, "document_tool.clear")
           action.triggered.connect(lambda checked=False: editor.clear())
           menu.addAction(action)
           menu.addSeparator()

The built-in Notepad uses ``hide_in_tab_tools`` and ``get_tab_menu()`` to supply its Add a new notepad action. Add translation keys used by your actions to your Add-on's locale files; ``add_lang_mapping()`` uses the tool's translation domain and keeps live actions updated on language changes.

Left toolbar entries
~~~~~~~~~~~~~~~~~~~~

Override ``get_toolbar()`` to return a list of ``ToolToolbarItem`` objects from ``pygpt_net.tools.base``. The default returns ``[]``. Each item has:

.. list-table:: ``ToolToolbarItem`` fields
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Meaning
   * - ``icon``
     - Icon resource/path, for example ``':/icons/build.svg'``.
   * - ``title``
     - Translation key for the button tooltip, resolved in the tool's locale domain and refreshed on language changes.
   * - ``handler``
     - Zero-argument callable invoked when the button is clicked.
   * - ``id``
     - Optional stable entry ID (default ``''``), useful when the tool supplies multiple buttons.

For a tab tool, a toolbar button can simply open or focus its existing tab:

.. code-block:: python

   from pygpt_net.tools.base import ToolToolbarItem

   # Add this method to your BaseTool subclass:
   def get_toolbar(self):
       return [ToolToolbarItem(
           icon=self.tab_icon,
           title=self.tab_title,
           handler=self.open_tab,
       )]

Return multiple items to provide additional actions. A toolbar entry does not require ``allow_tab`` and is not filtered by ``can_add_tab()`` or ``hide_in_tab_tools``: its handler may open a dialog or perform another UI command.

Home remains a fixed button. Tool entries follow it in **tool registration order**, preserving each returned list's order. The built-in tools register Files, Notepad and Painter in that order; additional tools follow them. Toolbox remains fixed at the bottom. The toolbar listens for registration after UI construction as well, and re-registering the same tool ID replaces its buttons in place.

The first unnamed button is available as ``self.window.ui.nodes['toolbar.<tool_id>']``. Named entries use ``toolbar.<tool_id>.<item_id>``; subsequent unnamed entries use their zero-based list index as the suffix. ``id`` controls this identifier, not display order. Toolbar buttons receive live tooltip mappings automatically; you do not need to add them to the global language mapping table.

Selecting an independent runtime
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For tools with multiple independent frontends, register each runtime with ``register_surface(instance, widget, tab=tab)`` or ``register_surface(instance, dialog_widget, dialog_id=dialog_id)``. Route model operations through ``resolve_surface(create=True, activate=True)``. Tab selection uses the application-wide policy: first a selected tab in an expanded, visible column, then a recently used/active tab, then the first existing tab in column/index order. When several tabs are selected and visible, the first in column/index order wins. A hidden recently used tab cannot override a visible selected one. Dialog frontends retain their own focus tracking: a recently used visible dialog is preferred when applicable, and another visible dialog is a fallback when no tab runtime is available. Activation reveals the relevant column and selects the concrete tab without switching the conversation context, or focuses the dialog.

Override ``create_surface()`` to create and register a runtime when none is available. The resolver returns that runtime; without ``create=True`` it returns ``None`` if none exists. Use the latter for read-only context/annotation queries. Tab selection and mouse/focus events record recent usage; ``mark_surface_used(instance)`` also records explicit operations. Call ``unregister_surface(instance)`` and release runtime resources when disposing a frontend. Removed tabs, closed dialogs, deleted Qt widgets and forbidden surface types are excluded.

The built-in Web/Canvas uses this API for all plugin commands, including HTML, browser interaction and local-server operations. UI callbacks remain bound to their own runtime. Each tab/dialog has independent document, navigation, annotation and browser state.

Lifecycle hooks in practice
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``setup()``
   Main initialization hook. Use it for state that needs an attached ``window`` but not necessarily fully initialized plugins.

``post_setup()``
   Use when your tool depends on plugins or other application components being fully initialized.

``handle(event)``
   Optional global-event listener. GUI tools receive events before normal plugin dispatch; set/observe event fields only when your integration intentionally participates in that flow.

``on_update()`` / ``on_post_update()``
   Optional periodic hooks. Keep ``on_update()`` very lightweight because it belongs to a frequent UI/application update cycle.

``on_exit()`` / ``on_reload()``
   Release resources on application exit or refresh profile-dependent state after reload.

Full ``BaseTool`` method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: ``BaseTool`` public methods
   :header-rows: 1
   :widths: 30 45 25

   * - Method
     - Purpose
     - Override/call
   * - ``setup()``
     - Initial tool setup while application tools are initialized.
     - Override when needed.
   * - ``post_setup()``
     - Called after plugins/application setup.
     - Override for work requiring fully initialized app state.
   * - ``on_update()``
     - Frequent main-loop update hook.
     - Optional; keep lightweight.
   * - ``on_post_update()``
     - Slower post-update hook.
     - Optional.
   * - ``on_exit()``
     - Application exit hook.
     - Optional cleanup.
   * - ``on_reload()``
     - Profile/application reload hook.
     - Optional state refresh.
   * - ``handle(event)``
     - Receives global application events before plugin dispatch.
     - Optional event integration.
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
   * - ``get_tab_title(tab)``
     - Return the displayed tab title; defaults to translated ``tab_title``.
     - Override for document-specific titles.
   * - ``get_tab_tooltip(tab)``
     - Return tab tooltip metadata; defaults to its visible title.
     - Override for tool-specific metadata.
   * - ``get_tab_menu(parent, idx, column_idx, caller)``
     - Return QActions for the top level of the [+] tab creation menu.
     - Override to add custom creation actions.
   * - ``populate_tab_menu(menu, tab)``
     - Add actions to an existing tab's context menu.
     - Override for actions on that concrete tab.
   * - ``get_toolbar()``
     - Return a list of ``ToolToolbarItem`` left toolbar entries.
     - Override to add toolbar buttons.
   * - ``add_lang_mapping(target, key, setter='setText', domain=None, on_apply=None)``
     - Registers a live translation mapping for a private/dynamic Qt object.
     - Call after creating dynamic UI objects.
   * - ``apply_lang_mappings()``
     - Re-applies all live mappings and removes dead targets.
     - Normally called by PyGPT; may be called after custom language refresh.
   * - ``get_lang_mappings()``
     - Legacy/static mapping hook returning mapping dictionaries.
     - Override only for legacy/static mapping integration.

LLM Add-ons
-----------

Base class: ``pygpt_net.provider.llms.base.BaseLLM``.

What an LLM Add-on provides
~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ``llm`` Add-on registers a provider in PyGPT's LLM registry. Its primary external contract is the **LlamaIndex provider layer** used by RAG, Completion, Custom agents and other LlamaIndex-backed flows. It can also expose an embedding model and provider-owned configuration/model discovery.

An external LLM Add-on does not automatically create a brand-new native Chat SDK transport. Native Chat provider paths may require application/core integration. For a normal third-party Add-on, implement the LlamaIndex hooks you need and advertise only those capabilities in ``self.type``.

The most important rule is: **``self.type`` is a capability declaration, not descriptive metadata.** If you include ``MODE_LLAMA_INDEX``, ``llama()`` must return a working LlamaIndex LLM. If you include ``MODE_EMBEDDINGS``, ``llama_embeddings()`` must return a working LlamaIndex ``BaseEmbedding``.

Provider identity and capabilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A typical constructor sets:

.. code-block:: python

   from pygpt_net.core.types import MODE_EMBEDDINGS, MODE_LLAMA_INDEX
   from pygpt_net.provider.llms.base import BaseLLM

   class MyProvider(BaseLLM):
       def __init__(self):
           super().__init__()
           self.id = "my_provider"
           self.name = "My Provider"
           self.description = "Example external LLM provider."
           self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

``id`` is the provider ID used by models and, by default, the key below ``config.providers``. Set ``config_id`` only when multiple provider objects intentionally share one configuration entry.

``setup()``: provider-owned configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Providers should override ``setup()`` when they expose credentials, endpoints, extra settings, OpenAI-compatible transport capability or provider-side remote tools. The returned dictionary is the provider's settings contract.

A common shape is:

.. code-block:: python

   def setup(self):
       return {
           "openai_compatible": False,
           "require_api_key": True,
           "settings": {
               "api_key": {
                   "type": "str",
                   "default": "",
                   "secret": True,
               },
               "api_base": {
                   "type": "str",
                   "default": "https://api.example.com/v1",
               },
               "extra": {
                   "organization": {
                       "type": "str",
                       "default": "",
                       "label": "Organization",
                       "advanced": True,
                   },
               },
           },
           "remote_tools": {},
       }

The recognized top-level fields are:

``openai_compatible``
   ``True`` when the provider can use PyGPT's OpenAI-compatible direct API transport. This is separate from the LlamaIndex wrapper itself.

``require_api_key``
   Optional. Controls whether the UI treats an API key as mandatory. If omitted, the base class derives it from whether ``settings.api_key`` exists.

``settings``
   Provider configuration. ``api_key`` and ``api_base`` are first-class fields; provider-specific settings belong under ``extra``. Individual fields use the normal settings schema and commonly define ``type``, ``default``, ``secret``, ``label``, ``desc``, ``use_locale``, ``advanced``, ``urls`` and/or ``env``.

``remote_tools``
   Optional provider-native tool switches/parameters. A field with ``tool=True`` is exposed as a selectable remote tool. Use the inherited ``get_remote_tool_config()``/``is_remote_tool_enabled()`` helpers at runtime.

After registration, PyGPT calls ``bind(window)`` and uses the schema to synchronize missing defaults. Provider code should read values with ``get_config()`` instead of reaching into global config keys directly.

``llama()``: the main LlamaIndex wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For an LLM-capable provider, ``llama(window, model, stream=False)`` is the primary method to implement. It must return a LlamaIndex LLM object compatible with the model and options supplied by PyGPT.

.. code-block:: python

   def llama(self, window, model, stream=False):
       from llama_index.llms.openai_like import OpenAILike

       args = self.parse_args(model.llama_index or {}, window)
       args.setdefault("model", model.id)
       args.setdefault("api_key", self.get_config("api_key"))
       args.setdefault("api_base", self.get_config("api_base"))
       args.setdefault("is_chat_model", True)
       return OpenAILike(**args)

Use ``model.llama_index``/``parse_args()`` for model-level Advanced overrides instead of inventing a second per-model configuration path. OpenAI-compatible implementations can reuse ``prepare_openai_compatible_args()`` when appropriate.

Additional capability hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``llama_completion()``
   Implement when Completion mode needs behavior different from the main ``llama()`` wrapper. If the same LlamaIndex object correctly supports completion, delegating to ``llama()`` is normally enough.

``llama_embeddings()``
   Required when ``MODE_EMBEDDINGS`` is advertised. Return a LlamaIndex ``BaseEmbedding`` configured from the active provider/model settings.

``llama_agent()`` / ``llama_with_computer_runtime()``
   Override only when agent or Computer Use execution needs provider-specific construction/tool wiring. Many providers can delegate to ``llama()``.

``get_models()``: model discovery/import
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_models(window)`` returns a list of model dictionaries used by provider model discovery/import. At minimum each item should contain ``id`` and ``name``:

.. code-block:: python

   def get_models(self, window):
       return [
           {"id": "example-chat", "name": "Example Chat"},
           {"id": "example-vision", "name": "Example Vision", "input": ["text", "image"]},
       ]

The base implementation calls an OpenAI-compatible ``/models`` endpoint through ``get_client()`` and returns an empty list on failure. **Override ``get_models()`` for providers whose discovery API is not OpenAI-compatible**, or when you want to return richer capabilities such as ``input``, context/output token limits, tool-call support or reasoning support.

Minimal provider skeleton
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pygpt_net.core.types import MODE_LLAMA_INDEX
   from pygpt_net.provider.llms.base import BaseLLM

   class MyProvider(BaseLLM):
       def __init__(self):
           super().__init__()
           self.id = "my_provider"
           self.name = "My Provider"
           self.type = [MODE_LLAMA_INDEX]

       def setup(self):
           return {
               "settings": {
                   "api_key": {
                       "type": "str",
                       "default": "",
                       "secret": True,
                   },
                   "api_base": {
                       "type": "str",
                       "default": "https://api.example.com/v1",
                   },
               },
           }

       def llama(self, window, model, stream=False):
           from llama_index.llms.openai_like import OpenAILike
           return OpenAILike(
               model=model.id,
               api_key=self.get_config("api_key"),
               api_base=self.get_config("api_base"),
               is_chat_model=True,
           )

       def get_models(self, window):
           return [{"id": "example-chat", "name": "Example Chat"}]

For an offline starting point, the shipped tutorial can return LlamaIndex ``MockLLM`` and ``MockEmbedding``; see ``examples/addons/llms/example_llm``.

Full ``BaseLLM`` method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: ``BaseLLM`` public methods
   :header-rows: 1
   :widths: 31 46 23

   * - Method
     - Purpose
     - Typical action
   * - ``setup()``
     - Returns provider-owned setup metadata including ``settings`` and ``remote_tools`` schema.
     - Override for provider configuration/capabilities.
   * - ``is_openai_compatible()``
     - Reads the ``openai_compatible`` flag from ``setup()``.
     - Usually inherit.
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
     - Attaches window/config and initializes default ``config_id``.
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
     - Override only for special policy; normally declare it in ``setup()``.
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
   * - ``llama_completion(window, model, stream=False)``
     - Returns a LlamaIndex LLM for plain-text completion.
     - Override/delegate when Completion is supported.
   * - ``llama(window, model, stream=False)``
     - Main LlamaIndex LLM constructor hook.
     - Primary override for LlamaIndex/RAG flows.
   * - ``llama_with_computer_runtime(...)``
     - Returns an LLM bound to shared Computer Use runtime.
     - Override/delegate when provider supports that integration.
   * - ``llama_agent(..., allow_remote_tools=True, force_computer_use=False)``
     - LlamaIndex LLM constructor for agent workflows.
     - Override/delegate if agents need provider-specific tools.
   * - ``llama_embeddings(window, config=None)``
     - Returns a LlamaIndex ``BaseEmbedding`` instance.
     - Required when embeddings capability is advertised.
   * - ``get_embeddings_model(window, config=None)``
     - Compatibility entry point delegating to ``llama_embeddings()``.
     - Inherit; implement ``llama_embeddings()`` instead.
   * - ``get_openai_agent_provider(window, model, stream=False)``
     - Compatibility hook for OpenAI-agents provider object.
     - Specialized providers only.
   * - ``get_models(window)``
     - Provider model-list discovery.
     - Override for non-OpenAI discovery or richer metadata.
   * - ``get_client(window)``
     - Raw/default SDK client accessor used by base model discovery.
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

Vector-store Add-ons
--------------------

Base class: ``pygpt_net.provider.vector_stores.base.BaseStore``.

What a vector-store Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``vector_store`` Add-on implements the persistence layer used by PyGPT indexing/RAG. The application owns document ingestion, embeddings and query orchestration; the store provider is responsible for creating, loading and persisting the LlamaIndex index/backend identified by a PyGPT index ID.

For a normal persistent backend the essential contract is ``create()``, ``get()`` and ``store()``. The remaining base methods are helpers or override points for special storage systems.

Required identity and state
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``id``
   Unique provider ID used by the storage registry.

``prefix``
   Optional prefix used by the inherited ``get_path()`` helper for directory-backed stores.

``indexes``
   Runtime cache available to implementations that keep loaded index objects in memory.

PyGPT calls ``attach(window)`` during registration, so filesystem/config access that needs the application should happen after attachment, not in import-time code.

Core persistence methods
~~~~~~~~~~~~~~~~~~~~~~~~

``create(id)``
   Create a new empty index/backend for the supplied PyGPT index ID and persist enough state for a later ``get(id)`` call. ``index_from_empty()`` is a convenient helper when the backend is represented by a normal LlamaIndex ``VectorStoreIndex``.

``get(id, llm=None, embed_model=None)``
   Return the LlamaIndex index object for an existing index. Honor the supplied ``llm``/``embed_model`` when your backend construction requires them. Cache the instance in ``self.indexes`` if that is useful, but do not assume the same process instance will exist forever.

``store(id, index=None)``
   Persist the current index/backend state. If ``index`` is supplied, persist that object; otherwise an implementation may use its cached object for the ID.

``exists(id)``
   The inherited implementation checks ``get_path(id)``. Override it for a remote/database backend whose existence cannot be determined by a local directory.

``remove()`` / ``truncate()``
   The base implementation is suitable for directory-backed providers. Remote services should override these methods so deletion really removes/clears the remote index.

Minimal directory-backed pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pygpt_net.provider.vector_stores.base import BaseStore

   class ExampleStore(BaseStore):
       def __init__(self):
           super().__init__()
           self.id = "example_store"
           self.prefix = "example_"

       def create(self, id):
           index = self.index_from_empty()
           self.indexes[id] = index
           self.store(id, index)
           return index

       def get(self, id, llm=None, embed_model=None):
           # Load your vector store + StorageContext here, then for example:
           # return self.index_from_store(store, storage_context, llm, embed_model)
           return self.indexes.get(id)

       def store(self, id, index=None):
           # Persist the index/backend here.
           self.indexes[id] = index or self.indexes.get(id)

See the persistent local tutorial in ``examples/addons/vector_stores/example_vector_store`` for a complete implementation.

Full ``BaseStore`` method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - Override for remote stores.
   * - ``create(id)``
     - Creates/persists an empty index.
     - Core implementation method.
   * - ``get(id, llm=None, embed_model=None)``
     - Loads/returns an index instance.
     - Core implementation method.
   * - ``store(id, index=None)``
     - Persists current index state.
     - Core implementation method.
   * - ``remove(id)``
     - Removes cached/local index data.
     - Inherited behavior works for directory-backed stores.
   * - ``truncate(id)``
     - Clears an index; default delegates to ``remove``.
     - Override for remote backends.
   * - ``remove_document(id, doc_id)``
     - Deletes a reference document without requiring the configured embedding provider.
     - Inherited implementation uses a mock embedding model for delete-only load.

Data-loader Add-ons
-------------------

Base class: ``pygpt_net.provider.loaders.base.BaseLoader``.

What a loader Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``loader`` Add-on connects a file format or external/web source to PyGPT indexing. The Add-on does **not** implement the whole indexing pipeline. Its main job is to advertise what it can read and return a LlamaIndex ``BaseReader`` from ``get()``. PyGPT then calls the reader's ``load_data(...)`` and feeds the returned ``Document`` objects into the normal indexing/RAG flow.

A loader can support files, web/external sources, or both by setting ``self.type`` to include ``"file"`` and/or ``"web"``.

Required metadata and ``get()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a file loader, set at least ``id``, ``name``, ``type`` and ``extensions`` and implement ``get()``:

.. code-block:: python

   from pygpt_net.provider.loaders.base import BaseLoader

   class ExampleLoader(BaseLoader):
       def __init__(self):
           super().__init__()
           self.id = "example_text"
           self.name = "Example text loader"
           self.type = ["file"]
           self.extensions = ["example"]

       def get(self):
           return ExampleReader(**self.get_args())

``extensions`` controls which file suffixes are routed to the loader. Use lowercase extensions **without a leading dot** (for example ``"pdf"`` or ``"example"``); PyGPT strips the dot before looking up the loader.

``get()`` must return a reader object with the normal LlamaIndex ``load_data(...)`` contract. The reader should return LlamaIndex ``Document`` objects and attach useful source metadata when available.

Web/external loaders
~~~~~~~~~~~~~~~~~~~~

For a web source, include ``"web"`` in ``type``. PyGPT registers the loader by its ``id`` and can expose constructor settings from ``init_args``.

``prepare_args(**kwargs)``
   Optional hook for converting the arguments passed by PyGPT into the exact ``load_data`` arguments expected by your reader.

``get_external_id(args)``
   Return a stable identifier for the remote source so PyGPT can distinguish/update indexed external content. The default returns ``args["url"]``.

``instructions``
   Optional command-specific guidance consumed by the web-index integration.

Configurable reader constructor arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``init_args`` to declare default reader-constructor values. Companion mappings control how those arguments appear in settings:

.. code-block:: python

   self.init_args = {
       "timeout": 30,
       "include_links": False,
   }
   self.init_args_labels = {
       "timeout": "Timeout",
       "include_links": "Include links",
   }
   self.init_args_types = {
       "timeout": "int",
       "include_links": "bool",
   }
   self.init_args_desc = {
       "timeout": "Request timeout in seconds.",
   }

PyGPT calls ``set_args()`` with saved values. Use ``get_args()`` when constructing the reader; it merges configured values over ``init_args`` defaults.

Attachments and runtime compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``is_supported_attachment(source)`` is optional and should return ``True`` only when the loader can safely handle that source through the attachment path.

``allow_compiled`` defaults to ``True``. Set it to ``False`` only for a reader that genuinely cannot work in compiled/Snap builds (for example because its dependency model requires a normal Python environment).

The tutorial ``.example`` loader in ``examples/addons/loaders/example_loader`` demonstrates a normal reader returning LlamaIndex ``Document`` objects with metadata.

Full ``BaseLoader`` method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - Core implementation method.

Audio-input Add-ons
-------------------

Base class: ``pygpt_net.provider.audio_input.base.BaseProvider``.

What an audio-input Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ``audio_input`` Add-on is a **speech/audio-to-text provider** used by PyGPT's Audio input plugin. PyGPT owns microphone capture, recording controls, temporary files and the surrounding UI. The provider receives the path of an already captured audio file and is responsible only for turning that file into text.

The provider is registered globally, then the built-in Audio input plugin calls ``provider.init(plugin)``. That attaches the owning plugin and immediately calls ``init_options()``. Because of this lifecycle, provider settings are declared on the owning plugin with ``self.plugin.add_option(...)`` rather than through an LLM-style ``setup()`` method.

Minimum implementation
~~~~~~~~~~~~~~~~~~~~~~

A provider needs ``id``/``name`` plus a working ``transcribe()`` and ``is_configured()``. Override ``init_options()`` only when the provider has settings.

.. code-block:: python

   from pygpt_net.provider.audio_input.base import BaseProvider

   class ExampleInput(BaseProvider):
       def __init__(self):
           super().__init__()
           self.id = "example_input"
           self.name = "Example Input"

       def init_options(self):
           self.plugin.add_option(
               "example_input_language",
               "text",
               value="en",
               label="Language",
               tab=self.id,
           )

       def transcribe(self, path):
           language = self.plugin.get_option_value("example_input_language")
           return transcribe_file(path, language=language)

       def is_configured(self):
           return True

``transcribe(path)`` contract
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``path`` is the audio file selected/captured by PyGPT. Read that exact path; do not assume a fixed filename or a particular current working directory. Return the transcription as a string. Let failures raise a useful exception unless your provider can convert them into a better provider-specific error.

The capture format can depend on the active audio backend, so implementations that require one codec/format should explicitly decode/convert the supplied file rather than relying on a hard-coded capture artifact.

Configuration checks
~~~~~~~~~~~~~~~~~~~~

``is_configured()`` is called before provider use. Return ``True`` when all required credentials/packages/settings are available. If it can return ``False``, implement ``get_config_message()`` with a user-facing explanation of what must be configured.

For credentials, declare plugin options with ``secret=True``. For dependencies that must be installed with the Add-on, declare them in manifest ``external_dependencies`` rather than attempting ad-hoc installation in ``transcribe()``.

Full audio-input provider method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - Override when settings are needed.
   * - ``transcribe(path)``
     - Converts the supplied audio-file path to text.
     - Core implementation method; return string.
   * - ``is_configured()``
     - Reports whether required credentials/packages/settings are available.
     - Core implementation method.
   * - ``get_config_message()``
     - User-facing explanation when not configured.
     - Override when ``is_configured`` can be false.

Audio-output Add-ons
--------------------

Base class: ``pygpt_net.provider.audio_output.base.BaseProvider``.

What an audio-output Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ``audio_output`` Add-on is a **text-to-speech provider** used by PyGPT's Audio output plugin. The application decides when text should be spoken, cleans the visible text, manages the playback worker/backends and handles UI state. The provider's main responsibility is to synthesize the supplied text.

As with audio input, PyGPT attaches the built-in Audio output plugin through ``init(plugin)`` and then calls ``init_options()``. Provider-specific settings therefore belong to ``self.plugin``.

Minimum implementation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pygpt_net.provider.audio_output.base import BaseProvider

   class ExampleOutput(BaseProvider):
       def __init__(self):
           super().__init__()
           self.id = "example_tts"
           self.name = "Example TTS"

       def init_options(self):
           self.plugin.add_option(
               "example_tts_voice",
               "text",
               value="default",
               label="Voice",
               tab=self.id,
           )

       def speech(self, text):
           path = self.prepare_output_path("wav")
           synthesize_to_wav(
               text,
               path,
               voice=self.plugin.get_option_value("example_tts_voice"),
           )
           return path

       def is_configured(self):
           return True

``speech(text)`` and playback ownership
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The normal contract is to synthesize to a file and return its path. PyGPT's Audio output worker will then play that file using the selected application audio backend.

A provider may return ``None`` when it deliberately performs playback itself, but in that case the provider owns that playback path and PyGPT will not receive a file to play/cache through the normal generated-file flow.

Use ``prepare_output_path(extension)`` for generated files. It creates a unique filename under the PyGPT temporary audio-output directory and rotates old generated files. Do not write every request to the same fixed filename; fixed names are especially fragile with overlapping calls and on Windows when a previous file is still held by an audio backend.

Configuration checks
~~~~~~~~~~~~~~~~~~~~

``is_configured()`` should validate required credentials/settings before synthesis. Implement ``get_config_message()`` with a useful setup message when the provider may be unavailable.

Declare credentials/options in ``init_options()`` through ``self.plugin.add_option(...)``. Keep package installation in manifest ``external_dependencies`` rather than running an installer during synthesis.

Full audio-output provider method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - Override when settings are needed.
   * - ``speech(text)``
     - Synthesizes audio. Return generated file path, or ``None`` when provider handles playback itself.
     - Core implementation method.
   * - ``prepare_output_path(extension=None)``
     - Creates a unique path under PyGPT's temporary audio-output directory and rotates old files.
     - Call before writing generated audio.
   * - ``is_configured()``
     - Reports provider readiness.
     - Core implementation method.
   * - ``get_config_message()``
     - User-facing setup message.
     - Override when provider may be unavailable.

Web-search Add-ons
------------------

Base class: ``pygpt_net.provider.web.base.BaseProvider``.

What a web-search Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``web`` Add-on supplies a search backend to PyGPT's Web search plugin. The Web plugin owns model commands, page fetching/parsing and the surrounding tool workflow; the provider is responsible for executing the search query and returning result URLs.

For a normal search engine set ``type = ["search_engine"]``. PyGPT registers providers according to the entries in ``type``.

Provider lifecycle and settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After global registration, the built-in Web plugin calls ``provider.init(plugin)``. The base implementation attaches the plugin and calls ``init_options()``, so API keys, engine IDs and other provider settings should be created through ``self.plugin.add_option(...)``.

.. code-block:: python

   from pygpt_net.provider.web.base import BaseProvider

   class ExampleSearch(BaseProvider):
       def __init__(self):
           super().__init__()
           self.id = "example_search"
           self.name = "Example Search"
           self.type = ["search_engine"]

       def init_options(self):
           self.plugin.add_option(
               "example_search_key",
               "text",
               value="",
               label="API key",
               secret=True,
               tab=self.id,
           )

       def search(self, query, limit=10, offset=0):
           # Execute provider request and return URLs only.
           return ["https://example.com/result"][:limit]

       def is_configured(self, cmds):
           return bool(self.plugin.get_option_value("example_search_key"))

``search()`` contract
~~~~~~~~~~~~~~~~~~~~~

``search(query, limit=10, offset=0)`` should return a list of URL strings. Respect ``limit`` and ``offset`` when the remote API supports them. The rest of the Web plugin can then resolve/fetch those URLs using the normal PyGPT web pipeline.

Do not return provider-specific response objects from this method. Convert the provider response to stable URLs here and keep API-specific metadata inside your implementation unless the Web API is extended explicitly.

``is_configured(cmds)``
~~~~~~~~~~~~~~~~~~~~~~~

This method receives the Web-plugin commands being executed and should return whether your provider is ready for that request. This allows a provider to require credentials only for commands/features that need them. If configuration is missing, ``get_config_message()`` supplies the user-facing setup explanation.

The shipped tutorial provider uses MediaWiki OpenSearch and returns real Wikipedia URLs without requiring cloud credentials.

Full web-provider method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - Override when settings are needed.
   * - ``search(query, limit=10, offset=0)``
     - Execute search and return a list of result URLs.
     - Core implementation method.
   * - ``is_configured(cmds)``
     - Reports whether the provider can execute the requested Web-plugin commands.
     - Core implementation method.
   * - ``get_config_message()``
     - Setup/configuration message when unavailable.
     - Override when provider may be unavailable.

Agent Add-ons
-------------

Base class: ``pygpt_net.provider.agents.base.BaseAgent``.

What an Agent Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ``agent`` Add-on extends the **Custom agents / legacy LlamaIndex agent provider registry**. It is not an Agents v2 workflow-profile package. Use this Add-on type when you want to register another selectable agent strategy/provider for the Custom agents runtime.

An agent provider describes its identity, option schema and execution strategy. In the common LlamaIndex workflow mode, the provider's central job is to implement ``get_agent(window, kwargs)`` and return the runtime workflow/agent object that PyGPT will execute.

Required identity
~~~~~~~~~~~~~~~~~

Set the following in ``__init__()``:

``id``
   Stable provider ID used by presets and the agent registry.

``name``
   Human-readable name shown in provider choices.

``type``
   Agent provider family/type used to filter choices (for example the LlamaIndex agent type used by built-in Custom agents).

``mode``
   Runtime execution mode. Built-in LlamaIndex workflow providers use the workflow mode constant.

The exact constants should match the existing Custom-agent runtime you are extending; copying the nearest built-in/tutorial agent is safer than inventing new string values.

``get_agent()``: common workflow-provider contract
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the ordinary workflow-style provider, override ``get_agent(window, kwargs)`` and return the object that owns the agent run. ``kwargs`` contains the runtime context prepared by PyGPT, such as the active model/LLM, tools, system prompt, limits and bridge/runtime context depending on the caller.

A very small external provider can reuse an existing PyGPT strategy and change only identity/options. The shipped tutorial follows this pattern by inheriting the built-in LlamaIndex ``ModeAgent("base")`` implementation instead of duplicating its workflow runner.

.. code-block:: python

   from pygpt_net.provider.agents.llama_index.modes import ModeAgent

   class ExampleAgent(ModeAgent):
       def __init__(self):
           super().__init__("base")
           self.id = "example_agent"
           self.name = "Example Agent"

Use direct ``BaseAgent`` inheritance only when you really implement a new execution path.

Options and prompts
~~~~~~~~~~~~~~~~~~~

``get_options()`` returns the provider option schema used by Custom-agent presets. ``get_option(preset, section, key)`` then resolves the saved value with a schema default fallback. This is the preferred way to expose agent-role settings instead of reading arbitrary preset dictionaries throughout your runtime code.

``get_default_prompt()`` returns the special ``__prompt__`` entry when present in the option schema.

When constructing nested/custom agent prompts, use ``append_system_prompt_extra()`` rather than manually concatenating the final bridge system prompt. It appends runtime/plugin additions and keeps the mandatory legacy-agent security rule exactly once.

Model selection inside agent roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``resolve_model_option()`` implements the normal per-section model-overwrite behavior. Use it when your workflow has multiple roles that may optionally override the active model; it safely falls back to the currently active model when the configured model no longer exists.

Direct ``run()`` providers
~~~~~~~~~~~~~~~~~~~~~~~~~~

``run(...)`` is the async direct-execution contract for provider modes that own execution themselves. Workflow providers that return a workflow object from ``get_agent()`` do not need to duplicate the same work in ``run()``. Implement the method that corresponds to the mode/runtime architecture you are registering.

The base class intentionally leaves both execution methods as stubs because different agent modes are orchestrated differently.

Full ``BaseAgent`` method reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - Core override for workflow-style providers.
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
     - Implement for the corresponding direct-run provider mode.
   * - ``get_option(preset, section, key)``
     - Resolves provider option from preset with default fallback.
     - Use inside workflow construction.
   * - ``append_security_rule(prompt)``
     - Static helper that keeps the required legacy-agent security boundary exactly once at prompt end.
     - Use when manually building custom agent prompts.
   * - ``extract_system_prompt_extra(final_prompt, raw_prompt)``
     - Static helper extracting runtime/plugin additions from final bridge prompt.
     - Custom nested-agent prompt construction.
   * - ``get_system_prompt_extra(kwargs)``
     - Resolves runtime prompt additions from agent kwargs/context.
     - Prefer over duplicating the preset/base prompt.
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

Theme Add-ons
-------------

What a Theme Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``theme`` Add-on packages PyGPT application/chat styling without executing Python code. Use it to distribute a complete visual theme or an override of one or more normal theme files. Theme packages have no Python base class and no ``entrypoint`` in the manifest.

The Add-on ID becomes the installed theme ID. Files may live directly in the Add-on root or in a ``theme`` subdirectory. PyGPT reads those files **in place** from ``<application base workdir>/addons/themes/<id>``; nothing is copied into a profile's ``css`` directory.

Package layout
~~~~~~~~~~~~~~

.. code-block:: text

   example-dark/
   ├── manifest.json
   └── theme/
       ├── app.css
       ├── app.xml
       └── chat.css

Theme files have the same responsibilities as normal PyGPT themes:

* ``app.css`` - Qt/QSS application styling;
* ``app.xml`` - qt-material palette when supplied;
* ``chat.css`` - chat/WebView CSS.

Only files present in the package participate in the theme layers, so an Add-on may intentionally override only a subset. The effective order is bundled theme data -> application-base custom ``css`` -> Theme Add-on -> active-profile ``css`` override.

Naming and compatibility
~~~~~~~~~~~~~~~~~~~~~~~~

The normal ``-dark`` / ``-light`` suffix rules determine runtime Light/Dark compatibility and are the same rules described in **Extending PyGPT -> Custom themes and styles**. Keep the Add-on ``id`` stable because it becomes the theme identifier used by configuration.

Theme Add-ons are static, but a restart remains the safest installation/update test because the application can have already loaded/cached theme resources for the active profile.

Locale Add-ons
--------------

What a Locale Add-on is for
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``locale`` Add-on distributes translation files without executing Python code. The package is fully application-wide and its files are read directly from ``<application base workdir>/addons/locale/<id>``. Nothing is copied into a profile's ``locale`` directory. It is useful for adding a new language or shipping maintained overrides and additional translation keys independently from the main PyGPT release. Locale packages have no Python base class and no ``entrypoint``.

This is separate from the private ``locale/`` directory supported by runtime Add-ons. If a plugin/tool/provider only needs translations for its own UI and settings, keep those files inside that runtime Add-on and use its automatic ``addon.<manifest_id>`` domain instead of publishing a second ``type: locale`` package.

Package layout
~~~~~~~~~~~~~~

Put one or more normal PyGPT locale ``.ini`` files in a ``locale`` subdirectory:

.. code-block:: text

   example-locale/
   ├── manifest.json
   └── locale/
       └── locale.xx.ini

Use the same key/value format and language-code naming convention as files in ``pygpt_net/data/locale``. The package can contain multiple locale files when one Add-on intentionally maintains several languages.

.. code-block:: ini

   [LOCALE]
   my.addon.example = Hello from an Add-on

Runtime behavior
~~~~~~~~~~~~~~~~

PyGPT loads locale files directly from every installed ``addons/locale/<id>`` package. Files may be placed in the package root or in its ``locale`` subdirectory. For the main application locale the effective order is bundled locale -> application-base ``locale`` override -> Locale Add-ons -> active-profile ``locale`` override. Translation keys are then available to the normal ``trans(...)`` infrastructure and to UI components that support live language refresh.

Treat locale Add-ons as data packages: do not include Python startup logic just to register translations. If an extension also needs executable behavior, package that behavior as the appropriate runtime Add-on type instead of hiding code in a locale package.

When overriding existing keys, test both initial application startup and a runtime language switch where applicable. A restart is still the safest installation/update validation path.

Files preview providers (v2.8.38+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``file_preview`` Add-on type installs into
``addons/file_previews/<id>`` and derives from
``pygpt_net.provider.file_preview.BaseFilePreview``. It supplies a desktop Qt
widget for an inline Files preview, independently of indexing/data loaders.
The built-in image, media and text/code previews remain available. Markdown
(``.md`` and ``.markdown``) has a built-in rendered, read-only preview, with
relative images/links resolved from the document directory.
Use Ctrl + mouse wheel to zoom. Links use light blue in dark themes and dark
blue in light themes. The context menu offers **Edit source** and **Back to
preview**; returning from modified source offers save, discard or cancel.

A minimal provider is::

   from PySide6.QtCore import Qt
   from PySide6.QtWidgets import QLabel
   from pygpt_net.provider.file_preview import BaseFilePreview

   class Preview(BaseFilePreview):
       id = "example_preview"
       name = "Example preview"
       extensions = ("example",)

       def create_widget(self, path, parent):
           with open(path, encoding="utf-8") as stream:
               text = stream.read()
           widget = QLabel(parent)
           widget.setTextFormat(Qt.PlainText)
           widget.setText(text)
           return widget

The package manifest contains ``"type": "file_preview"`` and
``"entrypoint": "preview.py:Preview"``. See the runnable JSON tree package in
``examples/addons/file_previews/example_file_preview``.

Provider contract:

* ``id`` is a nonempty, unique provider ID; ``name`` is its human-readable name.
* ``extensions`` declares case-insensitive suffixes, with or without a leading
  dot. Override ``accepts(path) -> bool`` for content-based detection; keep this
  method fast because it runs while selecting files.
* ``attach_window(window)`` attaches the application; ``self.window`` is available
  inside the provider. The default implementation does this automatically.
* ``create_widget(path, parent) -> QWidget`` receives an absolute path and the
  Files panel, on the GUI thread. Return a fresh widget per call. Files owns,
  reparents and deletes it. Multiple Files tabs can use the same provider, so
  keep per-preview state on the widget rather than on the provider.
* ``release_widget(widget)`` is an optional cleanup hook called before the
  preview is replaced or the panel is deleted. Stop timers/media and release external resources here;
  do not delete the widget yourself.
* Exceptions show an error with an external-open action. Normal file actions
  remain on the preview panel (open externally, open folder, save as).
* Add-on providers take precedence over built-ins. Later registrations take
  precedence over earlier providers for overlapping extensions.

For direct development registration use ``run(file_previews=[Preview()])`` or
``launcher.add_file_preview(Preview())``. The window-scoped registry is
``window.core.file_previews``: ``register(provider)``, ``unregister(provider_id)``
and ``resolve(path)``. Every Files tab consults it on file selection, including
already-created tabs. Removing a registration affects future selections; an
existing preview remains usable until replaced. Installed runtime Add-ons are
loaded at application startup, so restart after installing/updating a package.

Using a custom launcher instead of an installed Add-on
------------------------------------------------------

Installed Add-ons are recommended for redistributable application-wide extensions. A custom launcher remains useful when you control application startup and want to create/register objects programmatically.

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
