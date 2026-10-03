# Painter

`Painter` is a registered `BaseTool` with ID `painter`. It owns one tab, creates
its frontend lazily, and participates in tools menu, tab policy, localization,
profile reload and shutdown. Call `window.tools.get("painter").open(path)` to
open an image. There is no separate Painter controller or global UI widget.

Responsibilities:

- `tool.py`: tool lifecycle and frontend ownership.
- `core/document.py`: logical image dimensions, original source, drawing layers
  and composited image. Display zoom never changes document resolution.
- `core/history.py`: layered snapshots and undo/redo, including text edit stages.
- `core/selection.py`: cropping, fitting and content bounds.
- `core/viewport.py`: zoom, coordinate transforms, scrolling and panning.
- `core/modes/`: free drawing, shapes and text strategies.
- `core/files.py` and `core/clipboard.py`: image IO and clipboard operations.
- `core/settings.py`: drawing controls and persisted preferences.
- `core/capture.py`: camera/screen capture and chat/runtime image attachments.
- `core/storage.py`: current drawing persistence, bound to its owning profile.
- `ui/canvas.py`: Qt drawing surface, input dispatch and action bindings.
- `ui/layout.py`: controls, scroll area and tab cleanup.

Components own their state and are composed explicitly. Call them directly,
e.g. `tool.canvas.history.undo()`, `tool.canvas.document.resize(width, height)`
or `tool.capture.screenshot(silent=True)`. The widget does not duplicate their
APIs through forwarding methods or mixins.

`TAB_TOOL_PAINTER` is retained only for saved-layout migration. Restoration
converts it to `TAB_TOOL` with `tool_id="painter"`; closing Painter no longer
causes the next startup to recreate its tab.

Tests live in `tests/tools/painter`, including real Qt checks for drawing,
zoom, crop, text undo/redo, reopening and profile isolation.
