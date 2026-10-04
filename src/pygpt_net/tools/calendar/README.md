# Calendar tool

`Calendar` owns the desktop Calendar, its date-based notes and independent view
sessions. It is registered through `window.tools`, after Web/Canvas. Its Tools
menu action defaults to a singleton dialog (`ALWAYS_DIALOG`); the [+] Add Tool
menu can also create one Calendar tab across all columns. A dialog and tab can
coexist with independent selected dates and month pages.

- `tool.py`: presentation policy, menu action, frontend lifecycle and shared refresh.
- `core/storage.py`: existing SQLite note schema, cached records and profile-aware repository.
- `core/notes.py`: headless copy-to-today operation; does not open a frontend.
- `core/session.py`: one frontend's selected date, navigation and popup lifecycle.
- `core/editor.py`: editing and restoring the selected day note.
- `core/counters.py`: chat and note counters, adjacent months and search filters.
- `ui/widget.py`: responsive Calendar frontend and disposal of its timers/editor.
- `ui/dialog.py`: single independent dialog and cleanup on close/Escape.
- `ui/select.py`, `ui/delegate.py`: month grid, native painting and day actions.
- `ui/editor.py`, `ui/popup.py`: day-note text editor and floating popup.
- `ui/filters.py`, `ui/labels.py`: private conversation-filter controls per frontend.
- `ui/clock.py`, `ui/host.py`: localized clock and square responsive month host.

External callers use the tool's services directly:

```python
calendar = window.tools.get('calendar')
calendar.open_dialog()                       # Tools-menu default
calendar.open_tab()                          # Reuse or create the single tab
calendar.notes.append_today('A reminder')    # Save without opening Calendar
calendar.storage.load_note(2026, 10, 4)      # Commands/RPC by explicit date
calendar.refresh()                          # Refresh counters and filters
session = calendar.resolve_surface(create=True)
session.note.append_text('Selected day')
```

Notes are saved immediately. Updating a day note refreshes markers in all live
frontends and synchronizes other editors showing the same date without emitting
a second save. Browsing months does not retarget the selected note. Chat filters
remain application-wide; each Calendar owns its own controls and mirrors the
same saved filter state. Profile reload clears the repository cache and restores
editors from the current profile. Closing a frontend unregisters it, stops the
clock and finder, and disposes its floating popup.
