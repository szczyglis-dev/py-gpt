# Files

`Files` is a registered, single-tab `BaseTool`. `tool.py` owns lifecycle,
frontend registration, menus, translations, theme updates and root refreshes.
Services remain available while the explorer tab is closed.

## Components

- `core/operations.py`: create, rename, duplicate and delete files/directories.
- `core/transfers.py`: upload/import and download/export.
- `core/paths.py`: external applications, file manager, path mapping and timestamps.
- `core/chat.py`: attachments, mentions, path insertion and uploaded IDs.
- `core/clipboard.py`: OS clipboard integration and copy/move operations.
- `core/archives.py`: archive packing and unpacking.
- `ui/explorer.py`: compose widgets and coordinate navigation/selection.
- `ui/tree.py`, `drop.py`, `empty.py`, `model.py`, `menus.py`, `search.py`:
  tree rendering, drag/drop, empty state, indexing metadata, actions and search.
- `ui/preview/`: provider-based previews, text editing, media and directories.

Call the component that owns the operation directly:

```python
files = window.tools.get("files")
files.open(path)                      # activate Files and navigate
files.paths.open(path)                # launch the external application
files.paths.reveal(path, select=True) # reveal in the system file manager
files.operations.rename(path)
files.transfers.import_paths(paths)
files.chat.attach(path)
files.refresh(reload=True)            # change root without opening a closed tab
```

The explorer owns its clipboard/archive/menu helpers. Closing it cancels search
and timers, unregisters the frontend and clears `Files.explorer`. Opening it again
creates a frontend against the current project root. Legacy `TAB_FILES` entries
are migrated to `TAB_TOOL` / `files` while preserving identity and custom titles.
