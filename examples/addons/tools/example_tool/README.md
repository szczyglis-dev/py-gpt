# Example GUI tool

This `tool` Add-on adds a real action to the **Tools** menu and opens a Qt dialog. It also listens for `CTX_SELECT`, showing how GUI tools can observe the same application event stream as built-in tools. Its `locale/` directory demonstrates `self.trans()` and `add_lang_mapping()`, including live updates of a private `QAction` when the application language changes.

## Try it

Install the directory, restart PyGPT, then choose **Tools -> External add-on example**. Switch conversations and open the action again to see the selected context ID update.

Use this pattern for desktop utilities, dialogs, reusable widgets and optional output tabs. GUI callbacks run in the application process, so follow normal Qt thread-affinity rules.

## Presentation policy

The constructor explicitly configures `allow_tab`, `allow_dialog`, `multi_tab`,
`multi_dialog` and `on_menu_click`. This example permits one reusable dialog,
disables tabs, and uses `ToolMenuAction.ALWAYS_DIALOG`. The menu action connects
to `on_menu_action`, which opens or focuses the allowed surface. `open()` also
checks `can_open_dialog()` for direct calls. The dialog is registered in
`self.window.ui.dialog` under `dialog_id`, allowing the shared policy to detect
and focus it. Closing and reopening reuses the window and refreshes its message.

Other menu policies are `ALWAYS_TAB`, `DIALOG_IF_TAB_EXISTS` (dialog if a tab
exists, otherwise tab), and `TAB_IF_EXISTS` (existing tab, otherwise dialog).
For tabs, enable `allow_tab`, implement `as_tab(tab)` and set `tab_title` and
`tab_icon`. Setting `multi_tab = False` limits the tool to one tab across columns.
A selected menu surface must be allowed; there is no implicit fallback.

Use `can_open_tab()` / `can_open_dialog()` for surface permissions,
`can_add_tab()` / `can_add_dialog()` for new-instance availability, and
`allows_multiple_tabs()` / `allows_multiple_dialogs()` for multiplicity.
`existing_tab()`, `open_tab()` and `open_dialog()` provide shared lookup and
opening behavior. Dynamic dialogs declare `dialog_types`, implement
`get_instance()` and resolve requested IDs with `resolve_dialog_id()` before
creation. Multiple-instance flags require an implementation that creates
independent widgets or windows. `dialog_opener` defaults to `open`.

Legacy `has_tab` and `single_instance` remain aliases for `allow_tab` and
`not multi_tab`; new tools should use the fields and methods above.
