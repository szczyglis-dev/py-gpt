Agent Skills
============

Overview
--------

**Agent Skills** are portable instruction packages that extend agents with reusable procedures, domain knowledge, scripts, references, and supporting assets. PyGPT supports the common ``SKILL.md``-based Agent Skills layout used by agent systems such as Claude Code, Codex, and compatible community tools.

A skill is stored as a directory whose root contains ``SKILL.md``. The file contains YAML frontmatter followed by Markdown instructions for the agent. A typical package can look like this:

.. code-block:: text

   my-skill/
   ├── SKILL.md
   ├── scripts/
   │   └── run.py
   ├── references/
   │   └── API.md
   ├── assets/
   │   └── template.json
   └── agents/
       └── openai.yaml

The minimum portable frontmatter contains a skill name and description:

.. code-block:: yaml

   ---
   name: my-skill
   description: Performs a reusable task for the agent.
   ---

   # Instructions

   Follow these steps when this skill is relevant...

PyGPT keeps the complete imported skill directory intact. Vendor-specific files and metadata are preserved instead of being converted into a PyGPT-only format. This includes, for example, Codex metadata in ``agents/openai.yaml`` and compatible OpenClaw-style frontmatter extensions.

Managing Skills
---------------

Use the top-level ``Skills`` menu to manage Agent Skills. The menu provides:

* ``Manage skills...`` - opens the installed-skills list and lets you enable or disable individual skills.
* ``Explore...`` - opens the skill catalog browser.
* ``Import from GitHub...`` - imports a skill or a repository containing one or more skills.
* ``Import file/archive...`` - imports a local ``SKILL.md``, ``.skill`` package, ZIP, or TAR archive.
* ``Import folder...`` - imports a local directory containing a skill or multiple skill directories.
* ``Open skills directory`` - opens the profile-level skill storage directory.

Newly imported skills are enabled by default. Disable a skill in the ``Installed`` tab when you want to keep it installed but prevent agents from discovering or loading it.

Installed skill packages are profile-scoped and stored under:

.. code-block:: text

   <profile workdir>/agents/skills/<skill-name>/

PyGPT keeps enable/disable state and source information in ``.registry.json`` inside the skills directory. Removing a skill from the Skills dialog removes it from the current profile.

Importing from GitHub
---------------------

The GitHub importer accepts several useful forms, including:

.. code-block:: text

   https://github.com/owner/repository
   https://github.com/owner/repository/tree/main/path/to/skill
   https://github.com/owner/repository/blob/main/path/to/skill/SKILL.md
   https://raw.githubusercontent.com/owner/repository/main/path/to/skill/SKILL.md
   owner/repository:path/to/skill

When a repository or imported archive contains multiple ``SKILL.md`` roots, PyGPT can import multiple skills from that source. Skill directories are discovered recursively. The import is validated before the profile is modified so a conflict in one skill does not intentionally leave a partially imported set.

Existing skills are not silently overwritten by a normal import. Remove or replace the existing package explicitly when you want to install a different copy with the same skill name.

Explore catalog
---------------

The ``Explore`` tab loads a JSON catalog containing discoverable skills. Select skills using the checkboxes in the first column and click ``Install selected``. The catalog can provide fields such as a name, description, author, standard, install URL, and optional icon metadata.

The catalog URL is configurable in ``config.json`` using:

.. code-block:: json

   "skills.catalog.url": "https://raw.githubusercontent.com/szczyglis-dev/py-gpt/master/src/pygpt_net/data/skills/catalog.json"

The current catalog URL is also editable directly in the ``Explore`` tab. PyGPT has a built-in default URL and a bundled local catalog fallback. The bundled fallback is used when the default remote catalog cannot be loaded; an explicitly configured custom URL reports its error instead of silently switching to the default catalog.

A simple catalog can use the following structure:

.. code-block:: json

   {
     "skills": [
       {
         "name": "example-skill",
         "description": "Example reusable agent workflow.",
         "author": "Example Author",
         "standard": "Agent Skills",
         "url": "https://github.com/example/skills/tree/main/example-skill"
       }
     ]
   }

Runtime behavior
----------------

Agent Skills are integrated with ``Chat with Agents`` and its Agents v2 runtime. PyGPT uses **progressive disclosure** so installing many skills does not automatically inject the full contents of every ``SKILL.md`` into each request.

At runtime:

1. The agent receives compact metadata for enabled skills, primarily the skill name and description.
2. When a task clearly matches a skill, the agent can load that skill on demand.
3. Loading the skill returns its ``SKILL.md`` instructions and a manifest of packaged resources.
4. Individual text resources can be read only when required.
5. The skill directory is materialized inside the active conversation data workdir so normal PyGPT file, Python, and system tools can use its scripts and assets.

The Agents v2 runtime exposes the following internal tools to the agent:

* ``list_skills(query)`` - lists enabled skills, optionally filtered by a search query.
* ``load_skill(name)`` - loads one enabled skill, returns its instructions and resource manifest, and materializes the package for runtime use.
* ``read_skill_resource(name, path)`` - reads one specific text resource such as ``references/API.md`` or ``scripts/helper.py``.

Skills marked by compatible metadata as explicit-only are not automatically selected by the model. They are intended to be loaded when the user explicitly names or invokes that skill.

Working directory and scripts
-----------------------------

The installed source package lives in the profile-level ``agents/skills`` directory, but a loaded skill is copied into the **active conversation data workdir** before its files are used. The runtime copy is placed at:

.. code-block:: text

   .pygpt/skills/<skill-name>/

relative to the current data workdir. This also makes Skills compatible with project-specific data workdirs.

For local host execution, PyGPT gives the agent the absolute host path to the materialized skill. When a Python or system tool is running in the Docker sandbox, the same active data directory is mounted under ``/mnt/data``, so the skill is available at:

.. code-block:: text

   /mnt/data/.pygpt/skills/<skill-name>/

Skill packages often contain Python modules under ``scripts/`` and use commands such as:

.. code-block:: bash

   python -m scripts.run_loop --skill-path .

PyGPT tells the agent to execute bundled skill modules with the **skill root as the current working directory**. This is important for ``python -m scripts...`` imports and for relative paths used by the skill. ``PYTHONPATH`` is treated only as a fallback when the selected execution surface cannot change its working directory.

If a skill uses the ``{baseDir}`` placeholder, PyGPT resolves it to the appropriate materialized skill path for the currently preferred execution environment. Runtime information also contains both host and Docker paths so the agent can switch execution tools without guessing the filesystem mapping.

Resources and binary files
--------------------------

Text resources can be read through ``read_skill_resource``. This includes Markdown, source code, JSON, YAML, shell scripts, and other text-based files packaged with the skill.

Binary resources are not injected into the prompt as text. They remain available in the materialized skill directory and can be used through normal PyGPT tools when those tools and permissions are available.

Security and permissions
------------------------

A downloaded skill should be treated as third-party extension content. Installing or enabling a skill does **not** grant it additional permissions.

In particular:

* ``SKILL.md`` instructions do not override PyGPT system instructions, user intent, tool permissions, sandbox rules, or approval requirements.
* Bundled scripts are not executed automatically when a skill is loaded.
* A script is executed only if the agent actually needs it for the user's task and an enabled PyGPT tool permits the operation.
* Skill metadata such as ``allowed-tools`` is informational in PyGPT and does not enable plugins or bypass their security settings.
* Imported archives are checked for unsafe paths, and symbolic links are not copied into installed skill packages.

Before installing a third-party skill, review its ``SKILL.md`` and any executable files under directories such as ``scripts/``. This is especially important when the skill asks the agent to run shell commands, install packages, access external services, or modify files.

Creating a simple Skill
-----------------------

For a minimal custom skill, create a directory such as:

.. code-block:: text

   hello-skill/
   └── SKILL.md

Then add:

.. code-block:: markdown

   ---
   name: hello-skill
   description: Writes a short friendly greeting and explains what it can do.
   ---

   # Hello Skill

   Use this skill when the user asks for the Hello Skill.

   1. Greet the user.
   2. Briefly describe the skill.
   3. Keep the response concise.

Import the directory with ``Skills -> Import folder...``. After it is enabled, ``Chat with Agents`` can discover it from its description and load the full instructions only when needed.
