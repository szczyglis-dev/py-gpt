# Notepad

Notepad is a registered `BaseTool` with multiple independent tabs. `tool.py`
coordinates lifecycle, frontend registration, menu actions, theme and language.
No global controller or UI widget registry is required.

## Components

- `core/documents.py`: live document registry and text operations by note ID.
- `core/document.py`: one document's content, markers, scroll state and save/close.
- `core/storage.py`: repository and the existing SQLite persistence backend.
  A document's writer is bound to its owning database so profile switching cannot
  write a pending edit to the new profile. The database schema remains compatible.
- `core/tabs.py`: navigation, reopening saved notes and numbered titles.
- `core/markers.py`: persistent character markers, including undo/redo.
- `core/view.py`: deferred focus and scroll restoration, with owned Qt timers.
- `ui/editor.py`: Qt editor events, finder integration, typography and autosave.
- `ui/menus.py`: selection, markers, audio, copy/export, date/time, zoom and find.
- `ui/widget.py`: tab layout and microphone controls.
- `ui/highlight.py`: rendering marker metadata without changing document contents.

```python
notepad = window.tools.get('notepad')
notepad.open_tab()                 # standard tools API
notepad.tabs.open(note_id)         # activate or reopen a saved document
notepad.documents.append(text, note_id)
notepad.documents.text(note_id)
notepad.documents.clear(note_id)
notepad.documents.save_all()

editor = notepad.documents.widgets[note_id].textarea
editor.markers.mark()
editor.markers.unmark()
editor.markers.ranges()
```

A new tab uses the lowest note ID not currently open, starting at 1. If that ID
is saved in the database, its content, title, highlights and scroll position are
restored. Explicit tab restoration preserves its existing ID, title and column. Legacy `TAB_NOTEPAD` entries migrate to `TAB_TOOL/notepad`.
Closing a tab flushes pending edits, stops timers, unregisters finder and surface,
and retains the saved note. Restore suppresses autosave and preserves saved scroll
positions until the editor has been laid out.
