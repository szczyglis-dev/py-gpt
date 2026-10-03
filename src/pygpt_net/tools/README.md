# GUI tool presentation policy

Configure these fields in each tool constructor after `super().__init__()`:

- `allow_tab`: permits a tab surface.
- `allow_dialog`: permits a dialog surface.
- `multi_tab`: permits more than one tab for this tool across both columns.
- `multi_dialog`: permits independent dialog identities; otherwise the existing dialog is reused.
- `on_menu_click`: a `ToolMenuAction` value controlling the Tools menu action.

Menu policies:

| Value | Behavior |
| --- | --- |
| `ALWAYS_DIALOG` | Open or focus a dialog. |
| `ALWAYS_TAB` | Open or focus the tool tab. |
| `DIALOG_IF_TAB_EXISTS` | Open a dialog when a tool tab exists; otherwise open a tab. |
| `TAB_IF_EXISTS` | Focus an existing tool tab; otherwise open a dialog. |

The selected surface must be allowed. A forbidden surface is not silently replaced with another.

Use `can_open_tab()`, `can_add_tab()`, `can_open_dialog()`, `can_add_dialog()`,
`allows_multiple_tabs()` and `allows_multiple_dialogs()` instead of inspecting
presentation flags in application code. `can_add_*` checks whether a new
instance can be created; opening an existing single instance is still allowed.
Menu actions connect to `on_menu_action`.

Static dialog tools declare `dialog_id`. Dynamic dialog tools declare
`dialog_types` and call `resolve_dialog_id()` before opening or accessing their
window. `dialog_opener` defaults to `open`; Image Viewer uses `open_preview`.
Multiple instances require a tool implementation with independently spawned
surfaces, as provided by Text Editor and Image Viewer.

`has_tab` and `single_instance` remain compatibility properties mapping to
`allow_tab` and `not multi_tab`; they do not store a separate policy.

Current policies retain tab-only singleton Canvas (`web_browser`), singleton
Python/OS and Agent Workflow tabs, multiple legacy HTML Canvas tabs, multiple
Text Editor/Image Viewer dialogs, and singleton dialogs for the other tools.
Direct core tab creation enforces the same limits. Saved tabs are skipped when
`allow_tab` has subsequently been disabled.
