# Terminal

A system shell connected to a real PTY, with independent sessions for each tab
and for the dialog. Starts in `core.filesystem.get_data_dir()` (the same working
directory as Files). Linux/macOS use `$SHELL -i`, falling back to `/bin/sh`;
Windows uses PowerShell 7 when installed, otherwise `%COMSPEC%`.

- `tool.py`: tool lifecycle, menu, toolbar and surface registration.
- `core/process.py`: platform PTY transport and reader thread.
- `core/screen.py`: ANSI screen, soft-wrap tracking and alternate fullscreen buffer.
- `core/reflow.py`: logical-line reflow on width/height changes, including scrollback.
- `ui/widget.py`: cell rendering, keyboard, paste and 2000-line scrollback.
- `ui/dialog.py`: dialog ownership and cleanup.

Closing a tab/dialog or exiting the application terminates its shell. Reopening
starts a new session; saved layouts do not resume running processes.
Ctrl+C interrupts the foreground command; Ctrl+Shift+C copies the selected text,
Ctrl+Shift+V pastes, and the wheel or vertical scrollbar browses scrollback.
Ctrl+wheel and the context-menu Zoom submenu use the shared editor zoom menu and save a separate terminal font size
without refreshing the application theme. The terminal uses the system monospace
font (DejaVu Sans Mono, Menlo or Consolas). Drag to select text; the context menu
provides Copy, Paste and Select all. Ctrl+Shift+A selects the entire buffer.
Ctrl+C and Ctrl+V are passed to the shell.
Clicking the terminal focuses keyboard input; its filled cursor blinks every 500 ms. The terminal supports text
and ANSI colors; graphical terminal protocols and mouse reporting are not implemented.

Dependencies: `pyte>=0.8.2,<0.9`; `ptyprocess>=0.7,<0.8` on Unix;
`pywinpty>=3,<4` on Windows. Imports of new packages are lazy, so other tools can
start without them. A missing dependency appears as an error in the terminal.

Normal shell output is dynamically rewrapped on resize; explicit newlines stay
intact. Resize updates are throttled to 30 ms while dragging. Fullscreen
applications retain coordinate-based rendering and redraw through their PTY.
