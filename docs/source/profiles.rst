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
* **Config files** - profile configuration JSON files together with profile presets, installed external Add-ons under ``addons``, and custom CSS, locale and font data.
* **Files** - the remaining persistent profile files and directories, including images, uploads, captures, indexes, history and other profile-owned working files outside ``data/``.
* **Workdir data/** - only the profile's shared ``data/`` directory. This option is disabled by default; the other three sections are enabled by default.

The dialog shows the approximate size of each section. Temporary files, caches, logs, and project-specific data workdirs outside the profile workdir are not included.

Use ``File -> Import profile...`` to restore an exported ZIP as a **new** profile. Choose the available sections to import, provide a unique profile name, and select its workdir. Archives created by a newer PyGPT version require that version or later.

