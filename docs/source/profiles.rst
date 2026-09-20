Profiles
=========

You can create multiple profiles for an app and switch between them. Each profile uses its own configuration, settings, context history, and a separate folder for user files. This allows you to set up different environments and quickly switch between them, changing the entire setup with just one click.

The app lets you create new profiles, edit existing ones, and duplicate current ones.

To create a new profile, select the option from the menu: ``Config -> Profile -> New Profile...``

To edit saved profiles, choose the option from the menu: ``Config -> Profile -> Edit Profiles...``

To switch to a created profile, pick the profile from the menu: ``Config -> Profile -> [Profile Name]``

Each profile uses its own user directory (workdir). You can link a newly created or edited profile to an existing workdir with its configuration. This profile workdir contains application-level configuration and storage. A project's custom workdir is different: it overrides only the runtime ``data`` directory for conversations in that project and does not replace the profile workdir.

The name of the currently active profile is shown as (Profile Name) in the window title.

Importing and exporting profiles
--------------------------------

Use ``File -> Export profile...`` to create a portable ZIP archive of the currently active profile. The export dialog separates profile data into four sections:

* **Database** - the profile SQLite database. It is exported using a consistent SQLite snapshot, so the application can remain open while the archive is created.
* **Config files** - profile configuration JSON files together with profile presets and custom CSS, locale and font data.
* **Files** - the remaining persistent profile files and directories, including images, uploads, captures, indexes, history and other profile-owned working files outside ``data/``.
* **Workdir data/** - only the profile's shared ``data/`` directory. This option is disabled by default; the other three sections are enabled by default.

The dialog shows an approximate size next to each section, for example ``Database (30 MB)`` or ``Files (1.4 GB)``. Before exporting, PyGPT checks the available disk space with an additional safety margin. Export runs in a background worker and displays the same cancellable loader used for other long-running file operations. The default filename uses the form ``PyGPT_export_YYYY_MM__DD_hh_ii_ss.zip``.

Every archive contains ``export_meta.json`` with the PyGPT version, export time and the list of exported sections. Temporary files, caches, logs, the global ``profile.json`` registry and ``path.cfg`` are not included. Project-specific custom data workdirs located outside the profile workdir are also not included.

Use ``File -> Import profile...`` to restore one of these ZIP archives into a **new** profile. PyGPT validates ``export_meta.json`` before importing. An archive exported by a newer PyGPT version is rejected until the application is updated to at least that version. Only sections present in the archive can be selected for import. The import dialog also requires a non-empty, unique profile name and proposes ``Imported (YYYY-MM-DD)`` by default.

After clicking **Import profile**, select a workdir for the new profile. If the selected directory is not empty, PyGPT warns that all of its current contents will be replaced. Existing profile workdirs and unsafe overlapping locations cannot be selected. Disk space is checked again on the filesystem containing the selected destination.

Import is performed in a background worker. Data is first extracted and validated in a staging directory next to the destination. The destination is replaced only during the final commit, which also allows the previous directory to be restored if the commit fails. Cancellation is available until this final commit begins. Sections that were not exported, were not selected, or contain missing startup files are initialized with fresh-profile defaults.

When import finishes, PyGPT adds the new profile to the profile list and asks whether to switch to it immediately. Choosing **No** keeps the current profile active and only refreshes the profile list.

