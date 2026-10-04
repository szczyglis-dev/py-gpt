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

Current policies allow independent Web/Canvas (`web_browser`) tabs and dialogs, singleton
Python/OS and Agent Workflow tabs, multiple legacy HTML Canvas tabs, multiple
Text Editor/Image Viewer dialogs, and singleton dialogs for the other tools.
Direct core tab creation enforces the same limits. Saved tabs are skipped when
`allow_tab` has subsequently been disabled.


## Selecting a runtime frontend

Tools with independent runtimes can register each one with
`register_surface(instance, widget, tab=tab)` or
`register_surface(instance, dialog_widget, dialog_id=dialog_id)`.
`resolve_surface(create=True, activate=True)` selects the last used live
instance, then the current tab, other tabs in column/index order, and finally
visible dialogs. It reveals the selected column and activates the concrete tab
without changing the chat context, or raises the selected dialog. Implement
`create_surface()` to create and register a runtime if none is available.
Read-only lookups should leave `create=False` (the default).

Tab selection and mouse/focus events track usage. `mark_surface_used(instance)`
can also record explicit runtime operations. Call `unregister_surface(instance)`
on disposal and release that runtime's resources. Closed/removed/deleted
frontends and disabled surface types do not participate in selection.
Web/Canvas routes every plugin command through this API while UI callbacks stay
bound to their own runtime. Each frontend has separate DOM, navigation,
annotations, browser backend and local-server state; address history is shared.

## Left toolbar

Override `BaseTool.get_toolbar()` to return a list of `ToolToolbarItem` objects.
The default is an empty list. Each item supplies an icon resource path, a title
translation key and a zero-argument click handler:

```python
from pygpt_net.tools.base import ToolToolbarItem

def get_toolbar(self):
    return [ToolToolbarItem(
        icon=':/icons/build.svg',
        title='my_tool.title',
        handler=self.open,
    )]
```

The toolbar listens for tool registration, so entries are added even when the
UI has already been constructed. Re-registering a tool replaces its buttons in
place. Buttons appear after Home in tool registration order, and each tool's entries
retain their list order. Files, Notepad and Painter register in that order;
additional tools follow them. Toolbox stays at the bottom. No tab-creation
policy filters toolbar entries, so tools may also provide dialog or custom
commands. Titles use the owning tool's translation domain and update on language
changes. An optional `id` gives additional entries a stable name; buttons are
available as `window.ui.nodes['toolbar.<tool_id>']` for the first unnamed entry,
or `toolbar.<tool_id>.<item_id>` for named entries (subsequent unnamed entries
use their list index).